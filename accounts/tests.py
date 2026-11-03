from django.test import TestCase
from django.urls import reverse

from .models import User


class WorkbenchLandingTests(TestCase):
    def test_home_page_guides_visitors_to_login(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("login"))
        self.assertContains(response, "Log in to your workbench")

    def test_login_page_is_available_at_login_url(self):
        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Welcome back")

    def test_inspector_lands_on_inspection_checklist(self):
        inspector = User.objects.create_user(
            username="landing-inspector",
            email="landing-inspector@example.com",
            role=User.Role.FLOOR_INSPECTOR,
        )
        self.client.force_login(inspector)

        response = self.client.get(reverse("workbench"))

        self.assertRedirects(response, reverse("inspection-list"))

    def test_supervisor_lands_on_approval_queue(self):
        supervisor = User.objects.create_user(
            username="landing-supervisor",
            email="landing-supervisor@example.com",
            role=User.Role.SHIFT_SUPERVISOR,
        )
        self.client.force_login(supervisor)

        response = self.client.get(reverse("workbench"))

        self.assertRedirects(response, reverse("approval-queue"))
