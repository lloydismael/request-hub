from django.test import TestCase
from django.urls import reverse


class LoginPageTests(TestCase):
    def test_login_renders_accessible_liquid_glass_contract(self):
        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/login.html")
        self.assertContains(response, 'class="login-card login-card--glass lg-surface lg-enter"')
        self.assertContains(response, 'id="lg-edge-refraction"')
        self.assertContains(response, "feDisplacementMap")
        self.assertContains(response, '<span class="login-card__lens" aria-hidden="true"></span>', html=True)
        self.assertContains(response, '<span class="login-card__rim" aria-hidden="true"></span>', html=True)
        self.assertContains(response, '<span class="login-card__sheen" aria-hidden="true"></span>', html=True)

    def test_login_preserves_form_and_theme_contracts(self):
        response = self.client.get(reverse("login"))
        content = response.content.decode()

        self.assertContains(response, "csrfmiddlewaretoken")
        self.assertEqual(content.count('id="theme-checkbox"'), 1)
        self.assertEqual(response.context["form"].fields["username"].widget.attrs["placeholder"], " ")
        self.assertEqual(response.context["form"].fields["password"].widget.attrs["placeholder"], " ")

    def test_anonymous_landing_still_redirects_to_login(self):
        response = self.client.get(reverse("landing"))

        self.assertRedirects(response, reverse("login"))
