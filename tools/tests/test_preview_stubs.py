import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = 'preview_stubs.py'
TOOLS = Path(__file__).resolve().parents[1]


class Tests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def run_tool(self, *args):
        return subprocess.run([sys.executable, str(TOOLS / SCRIPT), *map(str, args)], capture_output=True,
                              encoding="utf-8", timeout=10, env={**os.environ, "PYTHONIOENCODING": "ascii"})

    def test_json_contains_existing_generation_without_writes(self):
        nids = self.root / "输入.txt"
        nids.write_text("AAAAAAAAAAA\nAAAAAAAAAAA\nBBBBBBBBBBB\n", encoding="utf-8-sig")
        before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.iterdir()}
        result = self.run_tool("--module", "libSceExample", "--nids", nids, "--td-path", "自定义.cpp")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["nids"], ["AAAAAAAAAAA", "BBBBBBBBBBB"])
        self.assertIn('APS5_EXPORT("AAAAAAAAAAA", sceExampleUnknown00)', report["code"])
        self.assertEqual(report["code"].count("NotImplemented_nid_no_patch"), 2)
        self.assertIn("自定义.cpp", report["technical_debt"])
        original = subprocess.run([sys.executable, str(TOOLS / "stubgen.py"), "--module", "libSceExample",
                                   "--nids", str(nids), "--td-path", "自定义.cpp"], capture_output=True, encoding="utf-8", timeout=10)
        self.assertEqual(original.returncode, 0, original.stderr)
        self.assertEqual(report["code"], original.stdout)
        self.assertEqual(report["technical_debt"], original.stderr)
        self.assertEqual(before, {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.iterdir()})

    def test_invalid_nid_database_and_empty_input(self):
        nids = self.root / "nids"
        nids.write_text("bad\n", encoding="utf-8")
        result = self.run_tool("--module", "libSceExample", "--nids", nids)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        nids.write_bytes(b"")
        result = self.run_tool("--module", "libSceExample", "--nids", nids)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["nids"], [])
        database = self.root / "db"
        database.write_text("bad line\n", encoding="utf-8")
        self.assertEqual(self.run_tool("--module", "libSceExample", "--nids", nids, "--db", database).returncode, 2)


if __name__ == "__main__":
    unittest.main()
