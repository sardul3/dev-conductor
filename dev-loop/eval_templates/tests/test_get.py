import json
import unittest
from app import handle, reset

class GetTests(unittest.TestCase):
    def setUp(self) -> None:
        reset()

    def test_given_id_when_get_then_found(self) -> None:
        _, created = handle("POST", "/tasks", json.dumps({"title": "x"}).encode())
        code, body = handle("GET", f"/tasks/{created['id']}")
        self.assertEqual(code, 200)
        self.assertEqual(body["title"], "x")

    def test_given_unknown_when_get_then_404(self) -> None:
        code, _ = handle("GET", "/tasks/999")
        self.assertEqual(code, 404)
