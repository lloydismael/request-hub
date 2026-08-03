import json
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from django.contrib.messages import get_messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from hub.forms import RequestForm
from hub.models import Account, Request, RequestCommunication, SqrSubmission, SqrSubmissionChange, SqrSubmissionHistory
from hub.views import (
    AssignmentEmailResult,
    DashboardView,
    RequestCollaborativeManageView,
    clear_engineer_outlook_lock_on_reassignment,
    notify_engineer_assignment_email,
)


class AssignmentEmailTests(TestCase):
    def setUp(self):
        self.requestor = User.objects.create_user(
            username="requestor1",
            password="pass12345",
            role=User.Roles.REQUESTOR,
            email="requestor@example.com",
        )
        self.engineer = User.objects.create_user(
            username="engineer1",
            password="pass12345",
            role=User.Roles.ENGINEER,
            email="engineer@example.com",
        )

    def test_notify_engineer_assignment_email_returns_no_new_assignee_without_assignment(self):
        request_obj = Request.objects.create(
            requestor=self.requestor,
            account_manager="Requestor One",
            product_category="Azure",
            engagement_type=Request.Engagement.SUPPORT,
            priority=Request.Priority.MEDIUM,
            account_id=self._create_account_id("Account A"),
        )

        result = notify_engineer_assignment_email(request_obj, actor_user=self.requestor)

        self.assertEqual(result.status, "no_new_assignee")

    def test_notify_engineer_assignment_email_returns_missing_email_when_assignee_has_no_email(self):
        self.engineer.email = ""
        self.engineer.save(update_fields=["email"])
        request_obj = Request.objects.create(
            requestor=self.requestor,
            account_manager="Requestor One",
            product_category="Azure",
            engagement_type=Request.Engagement.SUPPORT,
            priority=Request.Priority.MEDIUM,
            engineer=self.engineer,
            account_id=self._create_account_id("Account B"),
        )

        result = notify_engineer_assignment_email(request_obj, actor_user=self.requestor)

        self.assertEqual(result.status, "missing_assignee_email")

    def test_dashboard_post_surfaces_assignment_delivery_failure(self):
        factory = RequestFactory()
        request = factory.post(
            reverse("hub:dashboard"),
            data={
                "account_name": "Account C",
                "needed_by": "2026-04-19",
                "product_category": "Azure",
                "engagement_type": Request.Engagement.SUPPORT,
                "priority": Request.Priority.MEDIUM,
                "description": "Need deployment help.",
                "engineer": str(self.engineer.pk),
            },
        )
        request.user = self.requestor
        self._attach_session_and_messages(request)

        with patch("hub.views.notify_engineer_assignment_email", return_value=AssignmentEmailResult("delivery_failed")):
            response = DashboardView.as_view()(request)

        self.assertEqual(response.status_code, 302)
        messages = [message.message for message in get_messages(request)]
        self.assertIn("Request submitted", messages)
        self.assertTrue(any("assignment email could not be delivered" in message for message in messages))

    @staticmethod
    def _attach_session_and_messages(request):
        session_middleware = SessionMiddleware(lambda req: None)
        session_middleware.process_request(request)
        request.session.save()
        setattr(request, "_messages", FallbackStorage(request))

    def _create_account_id(self, name: str) -> int:
        return Account.objects.create(name=name).pk


class OutlookThreadingTests(TestCase):
    def setUp(self):
        self.requestor = User.objects.create_user(
            username="thread_requestor",
            password="pass12345",
            role=User.Roles.REQUESTOR_ESS,
            email="thread.requestor@example.com",
            first_name="Thread",
            last_name="Requestor",
        )
        self.engineer = User.objects.create_user(
            username="thread_engineer",
            password="pass12345",
            role=User.Roles.ENGINEER,
            email="thread.engineer@example.com",
            first_name="Thread",
            last_name="Engineer",
        )
        self.backup_engineer = User.objects.create_user(
            username="thread_backup",
            password="pass12345",
            role=User.Roles.ENGINEER,
            email="thread.backup@example.com",
        )
        self.account = Account.objects.create(name="Thread Account")
        self.request_obj = Request.objects.create(
            requestor=self.requestor,
            account=self.account,
            account_manager="Thread Requestor",
            product_category="Azure",
            engagement_type=Request.Engagement.SUPPORT,
            priority=Request.Priority.MEDIUM,
            engineer=self.engineer,
            backup_engineer=self.backup_engineer,
            status=Request.Status.COMPLETED,
            description="Threading support request.",
        )

    def test_closing_draft_reuses_acknowledgement_subject(self):
        contexts = self._post_acknowledgement_and_closing_with_captured_contexts()
        acknowledgement_query = self._mailto_query(contexts[0]["mailto_url"])
        closing_query = self._mailto_query(contexts[1]["mailto_url"])

        self.assertEqual(acknowledgement_query["subject"], [f"Re: {self.request_obj.reference_code} · Thread Account"])
        self.assertEqual(closing_query["subject"], acknowledgement_query["subject"])
        self.assertNotIn("Advisory Only", closing_query["subject"][0])
        self.assertIn("Advisory Only", closing_query["body"][0])

    def test_closing_draft_keeps_requestor_ess_cc_consistent_with_acknowledgement(self):
        contexts = self._post_acknowledgement_and_closing_with_captured_contexts()
        acknowledgement_cc = set(self._mailto_query(contexts[0]["mailto_url"])["cc"][0].split(","))
        closing_cc = set(self._mailto_query(contexts[1]["mailto_url"])["cc"][0].split(","))

        self.assertIn("JoanI@phildata.com", acknowledgement_cc)
        self.assertIn("JoanI@phildata.com", closing_cc)
        self.assertEqual(closing_cc, acknowledgement_cc)

    def _post_acknowledgement_and_closing_with_captured_contexts(self) -> list[dict]:
        self.client.force_login(self.engineer)
        contexts = []

        def capture_render(request, template_name, context=None, *args, **kwargs):
            contexts.append(context or {})
            return HttpResponse("OK")

        with patch("hub.views.render", side_effect=capture_render):
            acknowledgement_response = self.client.post(
                reverse("hub:request-outlook", args=[self.request_obj.pk]),
                HTTP_REFERER=reverse("hub:dashboard"),
            )
            closing_response = self.client.post(
                reverse("hub:request-outlook-closing", args=[self.request_obj.pk]),
                HTTP_REFERER=reverse("hub:request-manage-collab", args=[self.request_obj.pk]),
            )

        self.assertEqual(acknowledgement_response.status_code, 200)
        self.assertEqual(closing_response.status_code, 200)
        self.assertEqual(len(contexts), 2)
        return contexts

    @staticmethod
    def _mailto_query(mailto_url: str) -> dict[str, list[str]]:
        return parse_qs(urlparse(mailto_url).query)


class DashboardViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.pm_ess = User.objects.create_user(
            username="pmess1",
            password="pass12345",
            role=User.Roles.PM_ESS,
            email="pmess@example.com",
        )
        self.requestor_ess = User.objects.create_user(
            username="requestoress1",
            password="pass12345",
            role=User.Roles.REQUESTOR_ESS,
            email="requestoress@example.com",
        )
        self.requestor = User.objects.create_user(
            username="requestor2",
            password="pass12345",
            role=User.Roles.REQUESTOR,
            email="requestor2@example.com",
        )
        self.pm_esg = User.objects.create_user(
            username="pmesg1",
            password="pass12345",
            role=User.Roles.PM_ESG,
            email="pmesg@example.com",
            first_name="PM",
            last_name="ESG",
        )
        self.engineer = User.objects.create_user(
            username="engineer_dashboard",
            password="pass12345",
            role=User.Roles.ENGINEER,
            email="engineer.dashboard@example.com",
        )
        self.account = Account.objects.create(name="Dashboard Account")

    def test_pm_ess_dashboard_includes_own_and_requestor_ess_requests(self):
        own_request = Request.objects.create(
            requestor=self.pm_ess,
            account=self.account,
            account_manager="PM ESS",
            product_category="Azure",
            engagement_type=Request.Engagement.SUPPORT,
            priority=Request.Priority.MEDIUM,
        )
        requestor_ess_request = Request.objects.create(
            requestor=self.requestor_ess,
            account=self.account,
            account_manager="Requestor ESS",
            product_category="M365",
            engagement_type=Request.Engagement.TRAINING,
            priority=Request.Priority.MEDIUM,
        )
        other_request = Request.objects.create(
            requestor=self.requestor,
            account=self.account,
            account_manager="Regular Requestor",
            product_category="Dell",
            engagement_type=Request.Engagement.INQUIRY,
            priority=Request.Priority.MEDIUM,
        )

        request = self.factory.get(reverse("hub:dashboard"))
        request.user = self.pm_ess

        view = DashboardView()
        view.setup(request)
        context = view.get_context_data()

        request_ids = {item.pk for item in context["requests"]}

        self.assertIn(own_request.pk, request_ids)
        self.assertIn(requestor_ess_request.pk, request_ids)
        self.assertNotIn(other_request.pk, request_ids)

    def test_pm_ess_dashboard_my_requests_tab_shows_only_own_requests(self):
        own_request = Request.objects.create(
            requestor=self.pm_ess,
            account=self.account,
            account_manager="PM ESS",
            product_category="Azure",
            engagement_type=Request.Engagement.SUPPORT,
            priority=Request.Priority.MEDIUM,
        )
        requestor_ess_request = Request.objects.create(
            requestor=self.requestor_ess,
            account=self.account,
            account_manager="Requestor ESS",
            product_category="M365",
            engagement_type=Request.Engagement.TRAINING,
            priority=Request.Priority.MEDIUM,
        )

        request = self.factory.get(reverse("hub:dashboard"), data={"request_tab": "mine"})
        request.user = self.pm_ess

        view = DashboardView()
        view.setup(request)
        context = view.get_context_data()
        request_ids = {item.pk for item in context["requests"]}

        self.assertEqual(context["pm_ess_request_tab"], "mine")
        self.assertIn(own_request.pk, request_ids)
        self.assertNotIn(requestor_ess_request.pk, request_ids)

    def test_pm_esg_can_submit_request_from_dashboard(self):
        request = self.factory.post(
            reverse("hub:dashboard"),
            data={
                "account_name": self.account.name,
                "needed_by": "2026-04-19",
                "product_category": "Azure",
                "engagement_type": Request.Engagement.SUPPORT,
                "priority": Request.Priority.MEDIUM,
                "description": "PM ESG submitted request.",
                "engineer": str(self.engineer.pk),
            },
        )
        request.user = self.pm_esg
        AssignmentEmailTests._attach_session_and_messages(request)

        with patch("hub.views.notify_engineer_assignment_email", return_value=AssignmentEmailResult("sent")):
            response = DashboardView.as_view()(request)

        self.assertEqual(response.status_code, 302)
        request_obj = Request.objects.get(description="PM ESG submitted request.")
        self.assertEqual(request_obj.requestor, self.pm_esg)
        self.assertEqual(request_obj.account_manager, "PM ESG")

    def test_engineer_completed_filter_orders_recent_first(self):
        engineer = User.objects.create_user(
            username="engineer_completed_order",
            password="pass12345",
            role=User.Roles.ENGINEER,
            email="engineer.completed@example.com",
        )

        older_request = Request.objects.create(
            requestor=self.requestor,
            account=self.account,
            account_manager="Regular Requestor",
            product_category="Azure",
            engagement_type=Request.Engagement.SUPPORT,
            priority=Request.Priority.MEDIUM,
            engineer=engineer,
            status=Request.Status.COMPLETED,
            end_date=timezone.now().date(),
            description="older completed request",
        )
        newer_request = Request.objects.create(
            requestor=self.requestor,
            account=self.account,
            account_manager="Regular Requestor",
            product_category="M365",
            engagement_type=Request.Engagement.SUPPORT,
            priority=Request.Priority.MEDIUM,
            engineer=engineer,
            status=Request.Status.COMPLETED,
            end_date=timezone.now().date(),
            description="newer completed request",
        )

        older_timestamp = timezone.now() - timedelta(days=2)
        newer_timestamp = timezone.now() - timedelta(days=1)
        Request.objects.filter(pk=older_request.pk).update(created_at=older_timestamp, updated_at=older_timestamp)
        Request.objects.filter(pk=newer_request.pk).update(created_at=newer_timestamp, updated_at=newer_timestamp)

        request = self.factory.get(reverse("hub:dashboard"), data={"metric_filter": "completed"})
        request.user = engineer

        view = DashboardView()
        view.setup(request)
        context = view.get_context_data()
        request_ids = [item.pk for item in context["requests"]]

        self.assertEqual(context["active_metric_filter"], "completed")
        self.assertEqual(request_ids, [newer_request.pk, older_request.pk])






class OnHoldRoleTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.requestor = User.objects.create_user(
            username="requestor_onhold",
            password="pass12345",
            role=User.Roles.REQUESTOR,
            email="requestor.onhold@example.com",
        )
        self.engineer = User.objects.create_user(
            username="engineer_active",
            password="pass12345",
            role=User.Roles.ENGINEER,
            email="engineer.active@example.com",
        )
        self.on_hold_engineer = User.objects.create_user(
            username="engineer_onhold",
            password="pass12345",
            role=User.Roles.ON_HOLD,
            email="engineer.onhold@example.com",
        )
        self.account = Account.objects.create(name="On Hold Account")

    def test_new_request_form_excludes_on_hold_engineers_from_assignment_choices(self):
        form = RequestForm(actor_role=User.Roles.REQUESTOR)
        engineer_ids = set(form.fields["engineer"].queryset.values_list("id", flat=True))

        self.assertIn(self.engineer.pk, engineer_ids)
        self.assertNotIn(self.on_hold_engineer.pk, engineer_ids)

    def test_edit_request_form_keeps_current_on_hold_assignee_visible(self):
        request_obj = Request.objects.create(
            requestor=self.requestor,
            account=self.account,
            account_manager="Requestor On Hold",
            product_category="Azure",
            engagement_type=Request.Engagement.SUPPORT,
            priority=Request.Priority.MEDIUM,
            engineer=self.on_hold_engineer,
        )

        form = RequestForm(instance=request_obj, actor_role=User.Roles.REQUESTOR)
        engineer_ids = set(form.fields["engineer"].queryset.values_list("id", flat=True))

        self.assertIn(self.on_hold_engineer.pk, engineer_ids)

    def test_on_hold_user_dashboard_shows_assigned_requests(self):
        assigned_request = Request.objects.create(
            requestor=self.requestor,
            account=self.account,
            account_manager="Requestor On Hold",
            product_category="Azure",
            engagement_type=Request.Engagement.SUPPORT,
            priority=Request.Priority.MEDIUM,
            engineer=self.on_hold_engineer,
        )
        other_request = Request.objects.create(
            requestor=self.requestor,
            account=self.account,
            account_manager="Requestor On Hold",
            product_category="M365",
            engagement_type=Request.Engagement.TRAINING,
            priority=Request.Priority.MEDIUM,
            engineer=self.engineer,
        )

        request = self.factory.get(reverse("hub:dashboard"))
        request.user = self.on_hold_engineer

        view = DashboardView()
        view.setup(request)
        context = view.get_context_data()
        request_ids = {item.pk for item in context["requests"]}

        self.assertEqual(context["role"], User.Roles.ENGINEER)
        self.assertIn(assigned_request.pk, request_ids)
        self.assertNotIn(other_request.pk, request_ids)

    def test_on_hold_user_can_manage_previously_assigned_request(self):
        request_obj = Request.objects.create(
            requestor=self.requestor,
            account=self.account,
            account_manager="Requestor On Hold",
            product_category="Azure",
            engagement_type=Request.Engagement.SUPPORT,
            priority=Request.Priority.MEDIUM,
            engineer=self.on_hold_engineer,
        )

        request = self.factory.get(reverse("hub:request-manage-collab", args=[request_obj.pk]))
        request.user = self.on_hold_engineer

        view = RequestCollaborativeManageView()
        view.setup(request, pk=request_obj.pk)
        view.kwargs = {"pk": request_obj.pk}

        self.assertEqual(view.get_object(), request_obj)


class SqrEngineerLinkedRequestAccessTests(TestCase):
    def setUp(self):
        self.engineer = User.objects.create_user(
            username="sqr_link_owner",
            password="pass12345",
            role=User.Roles.ENGINEER,
            email="sqr.link.owner@example.com",
        )
        self.other_engineer = User.objects.create_user(
            username="sqr_link_request_assignee",
            password="pass12345",
            role=User.Roles.ENGINEER,
            email="sqr.link.assignee@example.com",
        )
        self.pm = User.objects.create_user(
            username="sqr_link_pm",
            password="pass12345",
            role=User.Roles.PM_ESG,
            email="sqr.link.pm@example.com",
            first_name="Linked",
            last_name="PM",
        )
        self.requestor = User.objects.create_user(
            username="sqr_link_requestor",
            password="pass12345",
            role=User.Roles.REQUESTOR,
            email="sqr.link.requestor@example.com",
        )
        self.account = Account.objects.create(name="SQR Linked Request Account")
        self.linked_request = Request.objects.create(
            requestor=self.requestor,
            account=self.account,
            account_manager="SQR Link Requestor",
            product_category="Azure",
            engagement_type=Request.Engagement.SUPPORT,
            priority=Request.Priority.MEDIUM,
            engineer=self.other_engineer,
        )
        self.submission = SqrSubmission.objects.create(
            linked_request=self.linked_request,
            engineer=self.engineer,
            pm_esg_reviewer=self.pm,
            customer_name="Linked Customer",
            customer_company="ESS",
            customer_contact="Linked Contact",
            project_title="Linked Project",
            project_details="Implementation",
            sse_manhrs=Decimal("20"),
            documentation_links="https://example.com/doc",
            sqr_folder_link="https://example.com/sqr",
        )

    def test_engineer_can_open_request_linked_to_owned_sqr(self):
        request = RequestFactory().get(reverse("hub:request-manage-collab", args=[self.linked_request.pk]))
        request.user = self.engineer
        view = RequestCollaborativeManageView()
        view.setup(request, pk=self.linked_request.pk)
        view.kwargs = {"pk": self.linked_request.pk}

        self.assertEqual(view.get_object(), self.linked_request)

    def test_engineer_can_save_own_sqr_with_preserved_linked_request(self):
        self.client.force_login(self.engineer)

        response = self.client.post(
            reverse("hub:sqr-edit", args=[self.submission.pk]),
            data={
                "linked_request": str(self.linked_request.pk),
                "customer_company": "ESS",
                "customer_contact": "Linked Contact",
                "pm_esg_reviewer": str(self.pm.pk),
                "customer_name": "Linked Customer Updated",
                "project_title": "Linked Project Updated",
                "project_details": "Implementation",
                "sse_manhrs": "20",
                "sqr_folder_link": "https://example.com/sqr",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.linked_request, self.linked_request)
        self.assertEqual(self.submission.customer_name, "Linked Customer Updated")


class SqrInlineUndoTests(TestCase):
    def setUp(self):
        self.engineer = User.objects.create_user(
            username="sqr_engineer",
            password="pass12345",
            role=User.Roles.ENGINEER,
            email="sqr.engineer@example.com",
        )
        self.pm = User.objects.create_user(
            username="sqr_pm",
            password="pass12345",
            role=User.Roles.PM_ESG,
            email="sqr.pm@example.com",
            first_name="SQR",
            last_name="PM",
        )
        self.requestor = User.objects.create_user(
            username="sqr_requestor",
            password="pass12345",
            role=User.Roles.REQUESTOR,
            email="sqr.requestor@example.com",
        )
        self.account = Account.objects.create(name="SQR Undo Account")
        self.request_obj = Request.objects.create(
            requestor=self.requestor,
            account=self.account,
            account_manager="SQR Requestor",
            product_category="Azure",
            engagement_type=Request.Engagement.SUPPORT,
            priority=Request.Priority.MEDIUM,
            engineer=self.engineer,
        )
        self.submission = SqrSubmission.objects.create(
            linked_request=self.request_obj,
            engineer=self.engineer,
            pm_esg_reviewer=self.pm,
            customer_name="Undo Customer",
            customer_company="ESS",
            customer_contact="Undo Contact",
            project_title="Undo Project",
            project_details="Implementation",
            sse_manhrs=Decimal("20"),
            documentation_links="https://example.com/doc",
            sqr_folder_link="https://example.com/sqr",
        )
        self.client.force_login(self.pm)

    def _inline_update(self, field, value):
        return self.client.post(
            reverse("hub:sqr-inline-update", args=[self.submission.pk]),
            data=json.dumps({"field": field, "value": value}),
            content_type="application/json",
        )

    def _undo(self, change):
        return self.client.post(reverse("hub:sqr-inline-undo", args=[self.submission.pk, change.pk]))

    def test_inline_update_creates_undo_change(self):
        response = self._inline_update("pm_manhrs", "16")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertIn("undo_url", data)
        change = SqrSubmissionChange.objects.get(pk=data["change_id"])
        self.assertEqual(change.field, "pm_manhrs")
        self.assertEqual(change.old_values["pm_manhrs"], "8")
        self.assertEqual(change.new_values["pm_manhrs"], "16")
        self.assertEqual(change.old_values["pm_amount"], "24000")
        self.assertEqual(change.new_values["pm_amount"], "48000")

    def test_undo_restores_dependent_sse_values(self):
        response = self._inline_update("sse_manhrs", "50")
        self.assertEqual(response.status_code, 200)
        change = SqrSubmissionChange.objects.get(pk=response.json()["change_id"])
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.sse_manhrs, Decimal("50"))
        self.assertEqual(self.submission.pm_manhrs, Decimal("24"))

        undo_response = self._undo(change)

        self.assertEqual(undo_response.status_code, 200)
        undo_data = undo_response.json()
        self.assertTrue(undo_data["ok"])
        self.assertTrue(undo_data["undone"])
        self.submission.refresh_from_db()
        change.refresh_from_db()
        self.assertEqual(self.submission.sse_manhrs, Decimal("20"))
        self.assertEqual(self.submission.sse_amount, Decimal("40000.00"))
        self.assertEqual(self.submission.pm_manhrs, Decimal("8"))
        self.assertEqual(self.submission.pm_amount, Decimal("24000.00"))
        self.assertIsNotNone(change.undone_at)
        self.assertEqual(change.undone_by, self.pm)

    def test_status_undo_restores_status_metadata_with_warning(self):
        response = self._inline_update("status", SqrSubmission.Status.APPROVED)
        self.assertEqual(response.status_code, 200)
        change = SqrSubmissionChange.objects.get(pk=response.json()["change_id"])
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, SqrSubmission.Status.APPROVED)
        self.assertIsNotNone(self.submission.reviewed_at)
        self.assertIsNotNone(self.submission.validity_due_date)

        undo_response = self._undo(change)

        self.assertEqual(undo_response.status_code, 200)
        undo_data = undo_response.json()
        self.assertTrue(undo_data["workflow_side_effect_warning"])
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, SqrSubmission.Status.FOR_PROCESSING)
        self.assertIsNone(self.submission.reviewed_at)
        self.assertIsNone(self.submission.validity_due_date)

    def test_stale_undo_is_rejected(self):
        response = self._inline_update("pm_manhrs", "16")
        self.assertEqual(response.status_code, 200)
        change = SqrSubmissionChange.objects.get(pk=response.json()["change_id"])
        SqrSubmission.objects.filter(pk=self.submission.pk).update(
            pm_manhrs=Decimal("24"),
            pm_amount=Decimal("72000.00"),
        )

        undo_response = self._undo(change)

        self.assertEqual(undo_response.status_code, 409)
        self.assertFalse(undo_response.json()["ok"])

    def test_non_pm_admin_cannot_inline_update(self):
        self.client.force_login(self.engineer)

        response = self._inline_update("pm_manhrs", "16")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(SqrSubmissionChange.objects.count(), 0)


class SqrHistoryTests(TestCase):
    def setUp(self):
        self.engineer = User.objects.create_user(
            username="sqr_history_engineer",
            password="pass12345",
            role=User.Roles.ENGINEER,
            email="sqr.history.engineer@example.com",
        )
        self.pm = User.objects.create_user(
            username="sqr_history_pm",
            password="pass12345",
            role=User.Roles.PM_ESG,
            email="sqr.history.pm@example.com",
            first_name="History",
            last_name="PM",
        )
        self.admin = User.objects.create_user(
            username="sqr_history_admin",
            password="pass12345",
            role=User.Roles.ADMIN,
            email="sqr.history.admin@example.com",
        )
        self.requestor = User.objects.create_user(
            username="sqr_history_requestor",
            password="pass12345",
            role=User.Roles.REQUESTOR,
            email="sqr.history.requestor@example.com",
        )
        self.account = Account.objects.create(name="SQR History Account")
        self.request_obj = Request.objects.create(
            requestor=self.requestor,
            account=self.account,
            account_manager="SQR History Requestor",
            product_category="Azure",
            engagement_type=Request.Engagement.SUPPORT,
            priority=Request.Priority.MEDIUM,
            engineer=self.engineer,
        )
        self.submission = SqrSubmission.objects.create(
            linked_request=self.request_obj,
            engineer=self.engineer,
            pm_esg_reviewer=self.pm,
            customer_name="History Customer",
            customer_company="ESS",
            customer_contact="History Contact",
            project_title="History Project",
            project_details="Implementation",
            sse_manhrs=Decimal("20"),
            documentation_links="https://example.com/doc",
            sqr_folder_link="https://example.com/sqr",
        )
        self.client.force_login(self.pm)

    def _inline_update(self, field, value):
        return self.client.post(
            reverse("hub:sqr-inline-update", args=[self.submission.pk]),
            data=json.dumps({"field": field, "value": value}),
            content_type="application/json",
        )

    def test_inline_update_creates_permanent_history(self):
        response = self._inline_update("pm_manhrs", "16")

        self.assertEqual(response.status_code, 200)
        history = SqrSubmissionHistory.objects.get(submission=self.submission)
        self.assertEqual(history.action, SqrSubmissionHistory.Action.UPDATED)
        self.assertEqual(history.field, "pm_manhrs")
        self.assertEqual(history.old_values["pm_manhrs"], "8")
        self.assertEqual(history.new_values["pm_manhrs"], "16")
        self.assertIn("PM Man-hrs", history.summary)

    def test_pm_admin_can_fetch_history(self):
        self._inline_update("pm_manhrs", "16")

        pm_response = self.client.get(reverse("hub:sqr-history", args=[self.submission.pk]))
        self.assertEqual(pm_response.status_code, 200)
        self.assertTrue(pm_response.json()["ok"])
        self.assertEqual(len(pm_response.json()["entries"]), 1)

        self.client.force_login(self.admin)
        admin_response = self.client.get(reverse("hub:sqr-history", args=[self.submission.pk]))
        self.assertEqual(admin_response.status_code, 200)
        self.assertTrue(admin_response.json()["ok"])

    def test_engineer_cannot_fetch_history(self):
        self._inline_update("pm_manhrs", "16")
        self.client.force_login(self.engineer)

        response = self.client.get(reverse("hub:sqr-history", args=[self.submission.pk]))

        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.json()["ok"])

    def test_restore_reverts_history_entry(self):
        response = self._inline_update("pm_manhrs", "16")
        self.assertEqual(response.status_code, 200)
        history = SqrSubmissionHistory.objects.get(action=SqrSubmissionHistory.Action.UPDATED)

        restore_response = self.client.post(reverse("hub:sqr-history-restore", args=[self.submission.pk, history.pk]))

        self.assertEqual(restore_response.status_code, 200)
        self.assertTrue(restore_response.json()["ok"])
        self.submission.refresh_from_db()
        history.refresh_from_db()
        self.assertEqual(self.submission.pm_manhrs, Decimal("8"))
        self.assertEqual(self.submission.pm_amount, Decimal("24000.00"))
        self.assertIsNotNone(history.restored_at)
        self.assertEqual(history.restored_by, self.pm)
        restore_entry = SqrSubmissionHistory.objects.get(action=SqrSubmissionHistory.Action.RESTORED)
        self.assertEqual(restore_entry.metadata["restored_history_id"], history.pk)

    def test_stale_restore_is_rejected(self):
        response = self._inline_update("pm_manhrs", "16")
        self.assertEqual(response.status_code, 200)
        history = SqrSubmissionHistory.objects.get(action=SqrSubmissionHistory.Action.UPDATED)
        SqrSubmission.objects.filter(pk=self.submission.pk).update(
            pm_manhrs=Decimal("24"),
            pm_amount=Decimal("72000.00"),
        )

        restore_response = self.client.post(reverse("hub:sqr-history-restore", args=[self.submission.pk, history.pk]))

        self.assertEqual(restore_response.status_code, 409)
        self.assertFalse(restore_response.json()["ok"])