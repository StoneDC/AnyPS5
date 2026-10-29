import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class FeatureTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="tool feature 界 ")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def cli(self, script, *args):
        return subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / script), *map(str, args)],
                              capture_output=True, encoding="utf-8", timeout=15)

    def test_real_elf_symbols_need_no_disassembler_or_reports(self):
        from test_annotate_module import build_module, DEFAULT_SYMBOLS, TLS_NAME, EXPORT_ADDRESS, SLOT, IMPORT_NAME, symbol_name
        source = self.root / "module.prx"
        source.write_bytes(build_module(symbols=[*DEFAULT_SYMBOLS, (TLS_NAME, 1, 0x16, 8)]))
        before = source.read_bytes()
        result = self.cli("annotate_module.py", source, "--no-names", "--symbols-json")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["imports"][0]["address"], SLOT)
        self.assertEqual(data["imports"][0]["symbol"], symbol_name(IMPORT_NAME))
        self.assertEqual(data["exports"][0]["address"], EXPORT_ADDRESS)
        self.assertEqual(data["tls_exports"][0]["address"], 8)
        self.assertEqual(source.read_bytes(), before)
        self.assertEqual(list(self.root.iterdir()), [source])

    def test_unicode_symbol_json_works_with_no_objdump_and_ascii_stdio(self):
        from test_annotate_module import build_module
        import nid_names
        name = "function_界"
        source = self.root / "module.prx"
        source.write_bytes(build_module(symbols=[(name, 1, 0x12, 0x1000)], relocations=()))
        db = self.root / "db.csv"
        db.write_text(nid_names.compute_nid(name) + " " + name + "\n", encoding="utf-8")
        result = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / "annotate_module.py"), str(source),
                                 "--db", str(db), "--symbols-json"], capture_output=True,
                                env={**os.environ, "PATH": "", "PYTHONIOENCODING": "ascii"}, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout.decode("utf-8"))["exports"][0]["name"], name)

    def test_json_mode_rejects_output_prefix_and_bad_elf(self):
        source = self.root / "bad.prx"
        source.write_bytes(b"not ELF")
        result = self.cli("annotate_module.py", source, "--no-names", "--symbols-json", "--out", self.root / "prefix")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        empty = self.cli("annotate_module.py", source, "--no-names", "--symbols-json", "--out", "")
        self.assertEqual((empty.returncode, empty.stdout), (2, ""))
        result = self.cli("annotate_module.py", source, "--no-names", "--symbols-json")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
