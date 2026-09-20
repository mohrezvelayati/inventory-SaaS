from django.test import SimpleTestCase

from config.celery import app, health_check


class CeleryInfrastructureTests(SimpleTestCase):
    def test_health_check_task_is_registered(self):
        self.assertIn(
            "config.health_check",
            app.tasks,
        )

    def test_health_check_task_runs_eagerly(self):
        result = health_check.delay()

        self.assertTrue(result.successful())
        self.assertEqual(
            result.get(),
            {"status": "ok"},
        )
