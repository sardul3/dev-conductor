import unittest
from app import handle, reset

class HealthTests(unittest.TestCase):
    def setUp(self) -> None:
        reset()

    def test_given_probe_when_get_health_then_ok(self) -> None:
        code, body = handle("GET", "/health")
        self.assertEqual(code, 200)
        self.assertEqual(body["status"], "ok")
