import json
import unittest
from app import handle, reset

class CompleteTests(unittest.TestCase):
    def setUp(self) -> None:
        reset()

    def test_given_task_when_complete_then_done(self) -> None:
        _, created = handle("POST", "/tasks", json.dumps({"title": "x"}).encode())
        code, body = handle("POST", f"/tasks/{created['id']}/complete")
        self.assertEqual(code, 200)
        self.assertEqual(body["status"], "done")

    def test_given_unknown_when_complete_then_404(self) -> None:
        code, _ = handle("POST", "/tasks/999/complete")
        self.assertEqual(code, 404)
