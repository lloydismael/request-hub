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
        self.assertContains(response, "var useDark = savedTheme === 'dark';")
        self.assertContains(response, "const startsDark = currentTheme === 'dark';")
        self.assertContains(response, "document.documentElement.style.colorScheme")
        self.assertContains(response, "const THEME_REVEAL_DURATION = 620;")
        self.assertContains(response, "body.classList.contains('pref-reduce-motion')")
        self.assertContains(response, "body.classList.contains('pref-reduce-effects')")
        self.assertContains(response, "activeTransition.skipTransition()")
        self.assertContains(response, "typeof overlay.animate !== 'function'")
        self.assertNotContains(response, "themeTransitionInFlight")
        self.assertNotContains(response, "brightness(1.08) saturate(0.9)")
        self.assertNotContains(response, "!savedTheme && window.matchMedia('(prefers-color-scheme: dark)').matches")
        self.assertEqual(response.context["form"].fields["username"].widget.attrs["placeholder"], " ")
        self.assertEqual(response.context["form"].fields["password"].widget.attrs["placeholder"], " ")

    def test_login_includes_progressive_page_transition_contract(self):
        response = self.client.get(reverse("login"))

        self.assertContains(response, 'id="request-hub-page"')
        self.assertContains(response, 'class="request-hub-page"')
        self.assertContains(response, "/static/css/app.")
        self.assertContains(response, "css?v=19")
        self.assertContains(response, "/static/js/page-transitions.")
        self.assertContains(response, "js?v=1")
        self.assertContains(response, "reqHubPageTransitionDirection")
        self.assertContains(response, "dataset.pageTransitionDirection")

    def test_login_includes_adaptive_navbar_contrast_contract(self):
        response = self.client.get(reverse("login"))

        self.assertContains(response, 'data-nav-surface="light"')
        self.assertContains(response, 'data-nav-default-surface="light"')
        self.assertContains(response, "/static/js/navbar-contrast.")
        self.assertContains(response, "js?v=1")
        self.assertContains(response, "navbar.dataset.navSurface = surface;")
        self.assertContains(response, "navbar.dataset.navDefaultSurface = surface;")
        self.assertContains(response, "requesthub:theme-changed")

    def test_login_loads_shared_semantic_theme_stylesheet(self):
        response = self.client.get(reverse("login"))

        self.assertContains(response, "/static/css/liquid-glass.")
        self.assertContains(response, "css?v=12")

    def test_anonymous_landing_still_redirects_to_login(self):
        response = self.client.get(reverse("landing"))

        self.assertRedirects(response, reverse("login"))
