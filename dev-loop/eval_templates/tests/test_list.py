import json
import unittest
from app import handle, reset

class ListTests(unittest.TestCase):
    def setUp(self) -> None:
        reset()

    def test_given_created_when_list_then_includes_task(self) -> None:
        handle("POST", "/tasks", json.dumps({"title": "a"}).encode())
        code, body = handle("GET", "/tasks")
        self.assertEqual(code, 200)
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["title"], "a")
