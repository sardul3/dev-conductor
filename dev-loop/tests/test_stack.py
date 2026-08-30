from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import unittest
from stack import split_paths

class StackTests(unittest.TestCase):
    def test_given_few_files_when_split_then_one_stack(self) -> None:
        self.assertEqual(split_paths(["a.py", "b.py"], max_files=10), [["a.py", "b.py"]])

    def test_given_many_files_when_split_then_chunks(self) -> None:
        files = [f"f{i}.py" for i in range(5)]
        chunks = split_paths(files, max_files=2)
        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[0], ["f0.py", "f1.py"])
        self.assertEqual(chunks[-1], ["f4.py"])
