import contextlib
import io
import json
import subprocess
import unittest
from unittest.mock import patch

import test_suggest_patches as fixtures
from test_suggest_patches import suggest_patches, VERIFIED


class PatchAdvisorJsonTests(unittest.TestCase):
    setUp = fixtures.PatchAdvisorTests.setUp
    write_index = fixtures.PatchAdvisorTests.write_index
    advise = fixtures.PatchAdvisorTests.advise

    def test_json_recommendation_and_hash_rejection(self):
        result = subprocess.CompletedProcess([], 0, VERIFIED, "")
        output = io.StringIO()
        with patch.object(suggest_patches.subprocess, "run", return_value=result), contextlib.redirect_stdout(output):
            self.assertEqual(self.advise("--json"), 0)
        data = json.loads(output.getvalue())
        self.assertEqual(data["status"], "recommended")
        self.assertEqual(data["entries"][0]["verification"]["summary"], [1, 1, 0, 0])
        self.assertEqual(data["entries"][0]["targets"], self.entry["targets"])
        self.module.write_bytes(b"changed module")
        output = io.StringIO()
        with patch.object(suggest_patches.subprocess, "run", side_effect=AssertionError("unmatched hash")), contextlib.redirect_stdout(output):
            self.assertEqual(self.advise("--json"), 1)
        self.assertEqual(json.loads(output.getvalue())["entries"][0]["status"], "rejected")

    def test_json_error_and_multiple_matches(self):
        self.write_index([self.entry, self.entry])
        with patch.object(suggest_patches.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, VERIFIED, "")):
            for extra, status in (([], "multiple_matches"), (["--list-verified"], "verified_list")):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.assertEqual(self.advise("--json", *extra), int(not extra))
                self.assertEqual(json.loads(output.getvalue())["status"], status)
        self.param.write_text("invalid json")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(self.advise("--json"), 2)
        self.assertEqual(json.loads(output.getvalue())["status"], "error")


if __name__ == "__main__":
    unittest.main()
