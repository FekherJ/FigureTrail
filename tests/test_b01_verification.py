"""Offline negative checks for B01 reference-data boundaries."""

import copy
import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("b01_inspection", ROOT / "scripts/inspect_finqa.py")
inspection = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inspection)


class VerificationGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ROOT / "evals/cases/finqa-b01-reviewed.json").read_text(encoding="utf-8"))
        cls.cases = {c["id"]: c for c in json.loads((ROOT / "data/raw/finqa-dev.json").read_text(encoding="utf-8"))}
        cls.growth = cls.manifest["cases"][1]

    def test_wrong_year_rejected(self):
        changed = copy.deepcopy(self.growth)
        changed["operands"][0]["cell"] = [1, 3]  # 2015 instead of 2017.
        with self.assertRaises(AssertionError):
            inspection.verify_case(self.cases[changed["case_id"]], changed)

    def test_ratio_percentage_confusion_rejected(self):
        changed = copy.deepcopy(self.growth)
        changed["exe_ans_unit"] = "percent"  # 0.0289 is not 2.89%.
        with self.assertRaises(AssertionError):
            inspection.verify_case(self.cases[changed["case_id"]], changed)

    def test_answer_in_source_export_rejected(self):
        with tempfile.TemporaryDirectory(prefix=".b01-", dir=ROOT / "tests") as directory:
            root = Path(directory).resolve()
            assert root.is_relative_to((ROOT / "tests").resolve())
            for relative in ("data/raw/finqa-dev.json", "evals/cases/finqa-b01-reviewed.json",
                             "evals/cases/finqa-b01-reference.json", "data/samples/finqa-b01-source.json"):
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, target)
            path = root / "data/samples/finqa-b01-source.json"
            source = json.loads(path.read_text(encoding="utf-8"))
            source["answer"] = "24.69%"
            path.write_text(json.dumps(source), encoding="utf-8")
            with patch.object(inspection, "ROOT", root), patch.object(sys, "argv", ["inspect_finqa.py", "--check"]):
                with self.assertRaisesRegex(AssertionError, "Export mismatch"):
                    inspection.main()


if __name__ == "__main__":
    unittest.main()
