from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Notification, Request


def _resolve_actor(instance):
    actor_user = getattr(instance, "_actor_user", None)
    if actor_user:
        return actor_user.get_full_name() or actor_user.username
    return "System"


def _resolve_source(instance, default_label):
    return getattr(instance, "_actor_source", default_label)


@receiver(pre_save, sender=Request)
def cache_previous_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_status = None
        return
    try:
        previous = sender.objects.get(pk=instance.pk)
        instance._previous_status = previous.status
    except sender.DoesNotExist:
        instance._previous_status = None


@receiver(post_save, sender=Request)
def notify_on_completion(sender, instance, created, **kwargs):
    previous_status = getattr(instance, "_previous_status", None)
    if instance.status == Request.Status.COMPLETED and previous_status != Request.Status.COMPLETED:
        code = instance.reference_code or f"REQ-{instance.pk:05d}"
        actor = _resolve_actor(instance)
        source = _resolve_source(instance, "Request · Completion")
        Notification.objects.create(
            recipient=instance.requestor,
            related_request=instance,
            message=f"Request {code} has been completed.",
            actor=actor,
            source=source,
        )
        if instance.engineer:
            Notification.objects.create(
                recipient=instance.engineer,
                related_request=instance,
                message=f"Request {code} closed by admin.",
                actor=actor,
                source=source,
            )


# Assignment notifications are created by hub.services.notifications.
ASSIGNMENT_NOTIFICATIONS_CENTRALIZED = True
