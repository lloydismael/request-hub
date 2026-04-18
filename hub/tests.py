from unittest.mock import patch

from django.contrib.messages import get_messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase
from django.urls import reverse

from accounts.models import User
from hub.models import Request
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
        from hub.models import Account

        return Account.objects.create(name=name).pk