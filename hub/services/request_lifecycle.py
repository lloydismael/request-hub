from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Max
from django.urls import reverse
from django.utils import timezone

from hub.models import Request, RequestLifecycleEvent


MANAGER_ROLES = {"admin", "pm_esg"}


class LifecycleConflictError(ValidationError):
    pass


@dataclass(frozen=True)
class TransitionResult:
    request: Request
    events: tuple[RequestLifecycleEvent, ...]
    previous_stage: str
    current_stage: str
    primary_changed: bool = False
    backup_changed: bool = False


def _user_label(user) -> str:
    if not user:
        return ""
    return user.get_full_name().strip() or user.username


def _next_sequence(request: Request) -> int:
    maximum = request.lifecycle_events.aggregate(value=Max("sequence"))["value"] or 0
    return maximum + 1


def _create_event(
    request: Request,
    *,
    event_type: str,
    stage: str,
    previous_stage: str,
    actor=None,
    source: str = "",
    idempotency_key: str,
    occurred_at=None,
    is_synthetic: bool = False,
    metadata: dict | None = None,
) -> RequestLifecycleEvent:
    event, _ = RequestLifecycleEvent.objects.get_or_create(
        request=request,
        idempotency_key=idempotency_key,
        defaults={
            "sequence": _next_sequence(request),
            "stage": stage,
            "event_type": event_type,
            "previous_stage": previous_stage,
            "actor": actor,
            "primary_owner": request.engineer,
            "backup_owner": request.backup_engineer,
            "actor_label": _user_label(actor),
            "primary_owner_label": _user_label(request.engineer),
            "backup_owner_label": _user_label(request.backup_engineer),
            "assignment_revision": request.assignment_revision,
            "occurred_at": occurred_at or timezone.now(),
            "source": source,
            "is_synthetic": is_synthetic,
            "metadata": metadata or {},
        },
    )
    return event


def _ensure_created_event(request: Request, *, actor=None, source: str = "") -> RequestLifecycleEvent:
    existing = request.lifecycle_events.filter(event_type=RequestLifecycleEvent.EventType.CREATED).first()
    if existing:
        return existing
    return _create_event(
        request,
        event_type=RequestLifecycleEvent.EventType.CREATED,
        stage=Request.LifecycleStage.CREATED,
        previous_stage="",
        actor=actor,
        source=source,
        idempotency_key="created",
        occurred_at=request.created_at,
    )


@transaction.atomic
def record_created(request_id: int, *, actor=None, source: str = "") -> TransitionResult:
    request = Request.all_objects.select_for_update(of=("self",)).select_related("engineer", "backup_engineer").get(pk=request_id)
    events = [_ensure_created_event(request, actor=actor, source=source)]
    previous_stage = request.lifecycle_stage
    request.assignment_revision = 1 if request.engineer_id or request.backup_engineer_id else 0
    request.lifecycle_stage = Request.LifecycleStage.ASSIGNED if request.engineer_id else Request.LifecycleStage.CREATED
    request.status = Request.Status.ONGOING
    request.end_date = None
    request.save(update_fields=["assignment_revision", "lifecycle_stage", "status", "end_date", "updated_at"])
    if request.engineer_id:
        events.append(
            _create_event(
                request,
                event_type=RequestLifecycleEvent.EventType.ASSIGNED,
                stage=Request.LifecycleStage.ASSIGNED,
                previous_stage=Request.LifecycleStage.CREATED,
                actor=actor,
                source=source,
                idempotency_key=f"assigned:{request.assignment_revision}:{request.engineer_id}",
            )
        )
    return TransitionResult(request, tuple(events), previous_stage, request.lifecycle_stage, bool(request.engineer_id), bool(request.backup_engineer_id))


@transaction.atomic
def record_assignment_change(
    request_id: int,
    *,
    previous_engineer_id: int | None,
    previous_backup_id: int | None,
    actor=None,
    source: str = "",
    allow_capacity_override: bool = False,
) -> TransitionResult:
    request = Request.all_objects.select_for_update(of=("self",)).select_related("engineer", "backup_engineer").get(pk=request_id)
    if allow_capacity_override:
        request._allow_capacity_override = True
    _ensure_created_event(request, actor=actor, source=source)
    primary_changed = previous_engineer_id != request.engineer_id
    backup_changed = previous_backup_id != request.backup_engineer_id
    previous_stage = request.lifecycle_stage
    events: list[RequestLifecycleEvent] = []
    if primary_changed or backup_changed:
        request.assignment_revision += 1
    if primary_changed:
        request.lifecycle_stage = Request.LifecycleStage.ASSIGNED if request.engineer_id else Request.LifecycleStage.CREATED
        request.status = Request.Status.ONGOING
        request.end_date = None
        request.save(update_fields=["assignment_revision", "lifecycle_stage", "status", "end_date", "updated_at"])
        event_type = RequestLifecycleEvent.EventType.ASSIGNED if request.engineer_id else RequestLifecycleEvent.EventType.UNASSIGNED
        owner_key = request.engineer_id or "none"
        events.append(
            _create_event(
                request,
                event_type=event_type,
                stage=request.lifecycle_stage,
                previous_stage=previous_stage,
                actor=actor,
                source=source,
                idempotency_key=f"assignment:{request.assignment_revision}:{owner_key}",
                metadata={"previous_engineer_id": previous_engineer_id},
            )
        )
    elif backup_changed:
        request.save(update_fields=["assignment_revision", "updated_at"])
    return TransitionResult(request, tuple(events), previous_stage, request.lifecycle_stage, primary_changed, backup_changed)


@transaction.atomic
def acknowledge_request(
    request_id: int,
    *,
    actor,
    expected_revision: int,
    source: str = "Manage Request · Acknowledge",
) -> TransitionResult:
    request = Request.all_objects.select_for_update(of=("self",)).select_related("engineer", "backup_engineer").get(pk=request_id)
    if not request.engineer_id or actor.pk != request.engineer_id:
        raise PermissionDenied("Only the current primary assignee can acknowledge this request.")
    if request.assignment_revision != expected_revision:
        raise LifecycleConflictError("The assignment changed. Refresh the page before acknowledging.")
    if request.lifecycle_stage != Request.LifecycleStage.ASSIGNED:
        raise LifecycleConflictError("This request is no longer awaiting acknowledgement.")

    occurred_at = timezone.now()
    acknowledged = _create_event(
        request,
        event_type=RequestLifecycleEvent.EventType.ACKNOWLEDGED,
        stage=Request.LifecycleStage.ACKNOWLEDGED,
        previous_stage=Request.LifecycleStage.ASSIGNED,
        actor=actor,
        source=source,
        idempotency_key=f"accepted:{request.assignment_revision}",
        occurred_at=occurred_at,
    )
    started = _create_event(
        request,
        event_type=RequestLifecycleEvent.EventType.STARTED,
        stage=Request.LifecycleStage.ONGOING,
        previous_stage=Request.LifecycleStage.ACKNOWLEDGED,
        actor=actor,
        source=source,
        idempotency_key=f"started:{request.assignment_revision}",
        occurred_at=occurred_at,
    )
    request.lifecycle_stage = Request.LifecycleStage.ONGOING
    request.status = Request.Status.ONGOING
    request.save(update_fields=["lifecycle_stage", "status", "updated_at"])
    return TransitionResult(request, (acknowledged, started), Request.LifecycleStage.ASSIGNED, request.lifecycle_stage)


@transaction.atomic
def record_status_change(
    request_id: int,
    *,
    previous_status: str,
    actor=None,
    source: str = "",
) -> TransitionResult:
    request = Request.all_objects.select_for_update(of=("self",)).select_related("engineer", "backup_engineer").get(pk=request_id)
    _ensure_created_event(request, actor=actor, source=source)
    previous_stage = request.lifecycle_stage
    events: list[RequestLifecycleEvent] = []
    if request.status == Request.Status.COMPLETED and previous_status != Request.Status.COMPLETED:
        request.lifecycle_stage = Request.LifecycleStage.COMPLETED
        request.save(update_fields=["lifecycle_stage", "updated_at"])
        events.append(
            _create_event(
                request,
                event_type=RequestLifecycleEvent.EventType.COMPLETED,
                stage=Request.LifecycleStage.COMPLETED,
                previous_stage=previous_stage,
                actor=actor,
                source=source,
                idempotency_key=f"completed:{_next_sequence(request)}",
            )
        )
    elif request.status == Request.Status.ONGOING and previous_status == Request.Status.COMPLETED:
        request.lifecycle_stage = Request.LifecycleStage.ONGOING
        request.end_date = None
        request.save(update_fields=["lifecycle_stage", "end_date", "updated_at"])
        events.append(
            _create_event(
                request,
                event_type=RequestLifecycleEvent.EventType.REOPENED,
                stage=Request.LifecycleStage.ONGOING,
                previous_stage=Request.LifecycleStage.COMPLETED,
                actor=actor,
                source=source,
                idempotency_key=f"reopened:{_next_sequence(request)}",
            )
        )
    return TransitionResult(request, tuple(events), previous_stage, request.lifecycle_stage)


def _stage_state(stage_value: str, current_stage: str) -> str:
    order = list(Request.LifecycleStage.values)
    current_index = order.index(current_stage)
    stage_index = order.index(stage_value)
    if stage_index < current_index or current_stage == Request.LifecycleStage.COMPLETED:
        return "complete"
    if stage_index == current_index:
        return "current"
    return "upcoming"


def _action_label(request: Request) -> str:
    labels = {
        Request.LifecycleStage.CREATED: "Assign a primary owner to the request.",
        Request.LifecycleStage.ASSIGNED: "Primary owner must acknowledge the request and send the acknowledgement email.",
        Request.LifecycleStage.ACKNOWLEDGED: "Prepare to begin work.",
        Request.LifecycleStage.ONGOING: "Complete the work and record related activity.",
        Request.LifecycleStage.COMPLETED: "No pending action. This request is complete.",
    }
    return labels[request.lifecycle_stage]


def _current_assignment_acknowledged(request: Request) -> bool:
    return request.lifecycle_events.filter(
        event_type=RequestLifecycleEvent.EventType.ACKNOWLEDGED,
        assignment_revision=request.assignment_revision,
    ).exists()


def build_lifecycle_context(request: Request, actor) -> dict:
    stages = []
    for value, label in Request.LifecycleStage.choices:
        state = _stage_state(value, request.lifecycle_stage)
        stages.append(
            {
                "value": value,
                "label": label,
                "state": state,
                "state_label": {"complete": "Complete", "current": "Current", "upcoming": "Upcoming"}[state],
                "is_complete": state == "complete",
                "is_current": state == "current",
            }
        )

    if request.lifecycle_stage == Request.LifecycleStage.CREATED:
        owner_label = "Admin / PM-ESG triage"
    elif request.lifecycle_stage == Request.LifecycleStage.COMPLETED:
        owner_label = "No pending owner"
    else:
        owner_label = _user_label(request.engineer) or "Unassigned"

    events = []
    event_queryset: Iterable[RequestLifecycleEvent] = request.lifecycle_events.select_related("actor").order_by("-sequence")
    for event in event_queryset:
        events.append(
            {
                "label": event.get_event_type_display(),
                "occurred_at": event.occurred_at,
                "actor_label": event.actor_label or _user_label(event.actor) or "System",
                "owner_label": event.primary_owner_label,
                "is_inferred": event.is_synthetic,
            }
        )

    return {
        "current_stage": request.lifecycle_stage,
        "current_stage_label": request.get_lifecycle_stage_display(),
        "current_action_label": _action_label(request),
        "current_owner_label": owner_label,
        "backup_support_label": _user_label(request.backup_engineer),
        "assignment_revision": request.assignment_revision,
        "can_acknowledge": bool(
            request.engineer_id
            and actor.pk == request.engineer_id
            and request.lifecycle_stage
            in {
                Request.LifecycleStage.ASSIGNED,
                Request.LifecycleStage.ACKNOWLEDGED,
                Request.LifecycleStage.ONGOING,
            }
            and not _current_assignment_acknowledged(request)
        ),
        "acknowledge_sent": bool(
            request.engineer_id
            and actor.pk == request.engineer_id
            and _current_assignment_acknowledged(request)
            and request.lifecycle_stage
            in {
                Request.LifecycleStage.ASSIGNED,
                Request.LifecycleStage.ACKNOWLEDGED,
                Request.LifecycleStage.ONGOING,
            }
        ),
        "acknowledge_url": reverse("hub:request-lifecycle-acknowledge", kwargs={"pk": request.pk}),
        "stages": stages,
        "events": events,
    }
