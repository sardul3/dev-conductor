import json
import unittest
from app import handle, reset

class CreateTests(unittest.TestCase):
    def setUp(self) -> None:
        reset()

    def test_given_title_when_post_task_then_created(self) -> None:
        code, body = handle("POST", "/tasks", json.dumps({"title": "ship"}).encode())
        self.assertEqual(code, 201)
        self.assertEqual(body["title"], "ship")
        self.assertEqual(body["status"], "todo")
        self.assertIn("id", body)

    def test_given_empty_when_post_task_then_400(self) -> None:
        code, _ = handle("POST", "/tasks", json.dumps({}).encode())
        self.assertEqual(code, 400)
