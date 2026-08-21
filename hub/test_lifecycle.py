from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from hub.models import Account, EngineerActivityLog, Request, RequestCommunication, RequestLifecycleEvent
from hub.services import request_lifecycle


class RequestLifecycleServiceTests(TestCase):
    def setUp(self):
        self.requestor = User.objects.create_user(
            username="lifecycle-requestor",
            password="pass12345",
            role=User.Roles.REQUESTOR,
        )
        self.primary = User.objects.create_user(
            username="lifecycle-primary",
            password="pass12345",
            role=User.Roles.ENGINEER,
        )
        self.backup = User.objects.create_user(
            username="lifecycle-backup",
            password="pass12345",
            role=User.Roles.ENGINEER,
        )
        self.manager = User.objects.create_user(
            username="lifecycle-manager",
            password="pass12345",
            role=User.Roles.PM_ESG,
        )
        self.account = Account.objects.create(name="Lifecycle Account")

    def create_request(self, **overrides):
        values = {
            "requestor": self.requestor,
            "account": self.account,
            "account_manager": "Lifecycle Requestor",
            "product_category": "Azure",
            "engagement_type": Request.Engagement.SUPPORT,
            "priority": Request.Priority.MEDIUM,
        }
        values.update(overrides)
        return Request.objects.create(**values)

    def test_record_created_tracks_unassigned_request(self):
        request = self.create_request()

        result = request_lifecycle.record_created(request.pk, actor=self.requestor, source="test")

        self.assertEqual(result.request.lifecycle_stage, Request.LifecycleStage.CREATED)
        self.assertEqual(result.request.assignment_revision, 0)
        self.assertEqual(list(request.lifecycle_events.values_list("event_type", flat=True)), ["created"])

    def test_request_save_restores_missing_lifecycle_defaults(self):
        request = Request(
            requestor=self.requestor,
            account=self.account,
            account_manager="Lifecycle Requestor",
            product_category="Azure",
            engagement_type=Request.Engagement.SUPPORT,
            priority=Request.Priority.MEDIUM,
            assignment_revision=None,
            lifecycle_stage=None,
        )

        request.save()

        request.refresh_from_db()
        self.assertEqual(request.assignment_revision, 0)
        self.assertEqual(request.lifecycle_stage, Request.LifecycleStage.CREATED)

    def test_assigned_request_requires_primary_acceptance(self):
        request = self.create_request(engineer=self.primary, backup_engineer=self.backup)
        request_lifecycle.record_created(request.pk, actor=self.requestor, source="test")
        request.refresh_from_db()

        with self.assertRaises(PermissionDenied):
            request_lifecycle.acknowledge_request(
                request.pk,
                actor=self.backup,
                expected_revision=request.assignment_revision,
            )

        result = request_lifecycle.acknowledge_request(
            request.pk,
            actor=self.primary,
            expected_revision=request.assignment_revision,
        )

        self.assertEqual(result.request.lifecycle_stage, Request.LifecycleStage.ONGOING)
        self.assertEqual(
            list(request.lifecycle_events.values_list("event_type", flat=True)),
            ["created", "assigned", "acknowledged", "started"],
        )

    def test_primary_reassignment_returns_ongoing_request_to_assigned(self):
        request = self.create_request(engineer=self.primary, backup_engineer=self.backup)
        request_lifecycle.record_created(request.pk, actor=self.requestor)
        request.refresh_from_db()
        request_lifecycle.acknowledge_request(request.pk, actor=self.primary, expected_revision=request.assignment_revision)
        previous_revision = request.assignment_revision
        request.engineer = self.backup
        request.save()

        result = request_lifecycle.record_assignment_change(
            request.pk,
            previous_engineer_id=self.primary.pk,
            previous_backup_id=self.backup.pk,
            actor=self.manager,
        )

        self.assertEqual(result.request.lifecycle_stage, Request.LifecycleStage.ASSIGNED)
        self.assertEqual(result.request.assignment_revision, previous_revision + 1)
        self.assertEqual(result.events[0].event_type, RequestLifecycleEvent.EventType.ASSIGNED)

    def test_backup_only_change_does_not_reset_progress(self):
        request = self.create_request(engineer=self.primary)
        request_lifecycle.record_created(request.pk, actor=self.requestor)
        request.refresh_from_db()
        request_lifecycle.acknowledge_request(request.pk, actor=self.primary, expected_revision=request.assignment_revision)
        request.refresh_from_db()
        previous_revision = request.assignment_revision
        request.backup_engineer = self.backup
        request.save()

        result = request_lifecycle.record_assignment_change(
            request.pk,
            previous_engineer_id=self.primary.pk,
            previous_backup_id=None,
            actor=self.manager,
        )

        self.assertEqual(result.request.lifecycle_stage, Request.LifecycleStage.ONGOING)
        self.assertEqual(result.request.assignment_revision, previous_revision + 1)
        self.assertEqual(result.events, ())
        self.assertTrue(result.backup_changed)

    def test_assignment_change_preserves_authorized_capacity_override(self):
        request = self.create_request()
        request_lifecycle.record_created(request.pk, actor=self.requestor)
        for index in range(3):
            self.create_request(
                engineer=self.primary,
                engagement_type=(
                    Request.Engagement.DEPLOYMENT
                    if index == 0
                    else Request.Engagement.SUPPORT
                ),
            )
        request.engineer = self.primary
        request._allow_capacity_override = True
        request.save()

        result = request_lifecycle.record_assignment_change(
            request.pk,
            previous_engineer_id=None,
            previous_backup_id=None,
            actor=self.manager,
            allow_capacity_override=True,
        )

        self.assertEqual(result.request.engineer, self.primary)
        self.assertEqual(result.request.lifecycle_stage, Request.LifecycleStage.ASSIGNED)
        self.assertEqual(result.request.assignment_revision, 1)

    def test_acknowledge_does_not_recheck_engineer_capacity(self):
        request = self.create_request()
        request_lifecycle.record_created(request.pk, actor=self.requestor)
        for index in range(3):
            self.create_request(
                engineer=self.primary,
                engagement_type=(
                    Request.Engagement.DEPLOYMENT
                    if index == 0
                    else Request.Engagement.SUPPORT
                ),
            )
        request.engineer = self.primary
        request._allow_capacity_override = True
        request.save()
        request_lifecycle.record_assignment_change(
            request.pk,
            previous_engineer_id=None,
            previous_backup_id=None,
            actor=self.manager,
            allow_capacity_override=True,
        )
        request.refresh_from_db()

        result = request_lifecycle.acknowledge_request(
            request.pk,
            actor=self.primary,
            expected_revision=request.assignment_revision,
        )

        self.assertEqual(result.request.lifecycle_stage, Request.LifecycleStage.ONGOING)
        self.assertEqual(result.request.status, Request.Status.ONGOING)

    def test_completion_and_reopen_are_recorded(self):
        request = self.create_request(engineer=self.primary)
        request_lifecycle.record_created(request.pk, actor=self.requestor)
        request.refresh_from_db()
        request_lifecycle.acknowledge_request(request.pk, actor=self.primary, expected_revision=request.assignment_revision)
        EngineerActivityLog.objects.create(
            engineer=self.primary,
            account=self.account,
            request=request,
            request_date=timezone.now().date(),
            activity_type=EngineerActivityLog.ActivityType.INTERNAL_SUPPORT,
            actual_hours="1.00",
            details="Worked request",
            location=EngineerActivityLog.Location.OFFICE,
        )
        request.status = Request.Status.COMPLETED
        request.end_date = timezone.now().date()
        request.save()
        completed = request_lifecycle.record_status_change(
            request.pk,
            previous_status=Request.Status.ONGOING,
            actor=self.primary,
        )
        self.assertEqual(completed.request.lifecycle_stage, Request.LifecycleStage.COMPLETED)

        request = completed.request
        request.status = Request.Status.ONGOING
        request.end_date = None
        request.save()
        reopened = request_lifecycle.record_status_change(
            request.pk,
            previous_status=Request.Status.COMPLETED,
            actor=self.manager,
        )
        self.assertEqual(reopened.request.lifecycle_stage, Request.LifecycleStage.ONGOING)
        self.assertIsNone(reopened.request.end_date)
        self.assertEqual(reopened.events[0].event_type, RequestLifecycleEvent.EventType.REOPENED)


class RequestLifecycleManagePageTests(TestCase):
    def setUp(self):
        self.requestor = User.objects.create_user(
            username="tracker-requestor",
            password="pass12345",
            role=User.Roles.REQUESTOR,
            email="tracker.requestor@example.com",
        )
        self.primary = User.objects.create_user(
            username="tracker-primary",
            password="pass12345",
            role=User.Roles.ENGINEER,
            first_name="Primary",
            last_name="Engineer",
            email="tracker.primary@example.com",
        )
        self.account = Account.objects.create(name="Tracker Account")
        self.request = Request.objects.create(
            requestor=self.requestor,
            account=self.account,
            account_manager="Tracker Requestor",
            product_category="Azure",
            engagement_type=Request.Engagement.SUPPORT,
            priority=Request.Priority.MEDIUM,
            engineer=self.primary,
        )
        request_lifecycle.record_created(self.request.pk, actor=self.requestor)

    def test_manage_page_renders_tracker_and_acknowledge_for_primary(self):
        self.client.force_login(self.primary)
        response = self.client.get(reverse("hub:request-manage-collab", args=[self.request.pk]))

        self.assertContains(response, "Request progress")
        self.assertContains(response, "Current stage: <strong>Assigned</strong>", html=True)
        self.assertContains(response, "Primary Engineer")
        self.assertContains(response, "Acknowledge request")
        self.assertContains(response, 'aria-current="step"')

    def test_acknowledge_endpoint_advances_request_and_opens_email_draft(self):
        self.request.refresh_from_db()
        self.client.force_login(self.primary)
        response = self.client.post(
            reverse("hub:request-lifecycle-acknowledge", args=[self.request.pk]),
            {"assignment_revision": self.request.assignment_revision},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Opening Mail Draft")
        self.assertContains(response, "acknowledge%20your%20request")
        self.request.refresh_from_db()
        self.assertEqual(self.request.lifecycle_stage, Request.LifecycleStage.ONGOING)

    def test_acknowledge_relaunches_email_draft_after_existing_outlook_lock(self):
        self.request.refresh_from_db()
        RequestCommunication.objects.create(
            request=self.request,
            user=self.primary,
            channel=RequestCommunication.Channel.OUTLOOK,
        )
        self.client.force_login(self.primary)
        first = self.client.post(
            reverse("hub:request-lifecycle-acknowledge", args=[self.request.pk]),
            {"assignment_revision": self.request.assignment_revision},
        )
        self.assertEqual(first.status_code, 200)
        self.assertContains(first, "Opening Mail Draft")

        second = self.client.post(
            reverse("hub:request-lifecycle-acknowledge", args=[self.request.pk]),
            {"assignment_revision": self.request.assignment_revision},
        )
        self.assertEqual(second.status_code, 200)
        self.assertContains(second, "Opening Mail Draft")
        self.assertNotContains(second, "You already launched the Outlook draft for this request.")

        manage_page = self.client.get(reverse("hub:request-manage-collab", args=[self.request.pk]))
        self.assertContains(manage_page, "Send acknowledgement email")

    def test_requestor_cannot_acknowledge(self):
        self.request.refresh_from_db()
        self.client.force_login(self.requestor)
        self.client.post(
            reverse("hub:request-lifecycle-acknowledge", args=[self.request.pk]),
            {"assignment_revision": self.request.assignment_revision},
        )
        self.request.refresh_from_db()
        self.assertEqual(self.request.lifecycle_stage, Request.LifecycleStage.ASSIGNED)
