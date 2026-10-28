import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import relinker_fuzz_seeds


class RelinkerFuzzConfigurationsTests(unittest.TestCase):
    def test_opt_in_corpus_covers_every_configuration_and_preserves_default_seeds(self):
        expected = {(target, intel, validation) for target in range(3) for intel in (False, True) for validation in range(3)}
        images = dict(relinker_fuzz_seeds.images())
        self.assertTrue(images)
        self.assertEqual(relinker_fuzz_seeds.SELECTORS, (0, 1, 2, 4))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for all_configurations in (False, True):
                output = root / ("all" if all_configurations else "default")
                command = [sys.executable, str(Path(relinker_fuzz_seeds.__file__)), str(output)]
                result = subprocess.run(command + (["--all-configurations"] if all_configurations else []),
                                        capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stderr)
                count = 18 if all_configurations else 4
                self.assertEqual(len(list(output.iterdir())), len(images) * count)
                for name, image in images.items():
                    configurations = set()
                    selectors = set()
                    for seed in output.glob(name + "-*"):
                        data = seed.read_bytes()
                        selector = data[0]
                        self.assertEqual(seed.name, name + "-" + str(selector))
                        self.assertEqual(data[1:], image)
                        selectors.add(selector)
                        configurations.add((selector % 3, bool(selector & 4), (selector >> 3) % 3))
                    if all_configurations:
                        self.assertEqual(configurations, expected)
                    else:
                        self.assertEqual(selectors, {0, 1, 2, 4})


if __name__ == "__main__":
    unittest.main()
