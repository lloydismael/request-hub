from unittest.mock import patch

from django.contrib.messages import get_messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase
from django.urls import reverse

from accounts.models import User
from hub.models import Account, Request
from hub.views import AssignmentEmailResult, DashboardView, notify_engineer_assignment_email


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