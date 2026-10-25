"""Verify source isolation, original-cell identity and repeatable corpus preparation."""

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest

from app.corpus import (
    decimal_value,
    corpus_version,
    encode,
    load_prepared,
    prepare_corpus,
    write_prepared,
)


def fixture():
    original = [["", "Total (MMBoe)"], ["Canada", "60"], ["Missing", "—"], ["Total", "243"]]
    normalized = deepcopy(original)
    normalized[2][1] = "2014"
    source = {
        "filename": "DVN/2007/page_58.pdf",
        "pre_text": ["Estimates for 2008 in MMBoe."],
        "post_text": ["Keep the reported units."],
        "table": normalized,
        "table_ori": original,
        "qa": {"answer": "ANNOTATION-SECRET", "program": "DO-NOT-EXECUTE"},
    }
    duplicate = {**deepcopy(source), "qa": {"answer": "ANOTHER-ANSWER"}}
    other = {
        **deepcopy(source),
        "filename": "OTHER/2014/page.pdf",
        "pre_text": ["A different report for 2014."],
    }
    alias = {**deepcopy(source), "filename": "ZZZ/2007/duplicate.pdf"}
    raw = encode([source, duplicate, other, alias])
    selection = {
        "selection_version": "finqa-corpus-v1",
        "raw_sha256": sha256(raw).hexdigest(),
        "source_filenames": [source["filename"], other["filename"], alias["filename"]],
    }
    return raw, selection


class CorpusTests(unittest.TestCase):
    def test_numeric_formats_preserve_missing_and_unsupported_values(self):
        cases = {
            "$2,467.1": "2467.1",
            "$ 330.2": "330.2",
            "-1,234.50": "-1234.50",
            "—": None,
            "1,00": None,
            "(123)": None,
            "12%": None,
            "$$1": None,
        }
        for original, expected in cases.items():
            with self.subTest(value=original):
                self.assertEqual(decimal_value(original), expected)

    def test_annotations_original_cells_and_context(self):
        raw, selection = fixture()
        bundle, report = prepare_corpus(raw, selection)
        self.assertEqual(bundle["manifest"]["counts"]["sources"], 2)
        self.assertEqual(report["repeated_question_copies_collapsed"], 1)
        self.assertEqual(
            report["duplicate_contexts"],
            [{"skipped": "ZZZ/2007/duplicate.pdf", "kept": "DVN/2007/page_58.pdf"}],
        )
        self.assertNotIn("ANNOTATION-SECRET", encode(bundle).decode())
        self.assertNotIn("DO-NOT-EXECUTE", encode(bundle).decode())
        self.assertNotIn("ANOTHER-ANSWER", encode(bundle).decode())
        cell = next(
            item
            for item in bundle["cells"]
            if item["cell_id"] == "DVN/2007/page_58.pdf#table[2][1]"
        )
        self.assertEqual(cell["source_value"], "—")
        self.assertIsNone(cell["decimal_value"])
        row = next(
            item
            for item in bundle["chunks"]
            if item["chunk_id"] == "DVN/2007/page_58.pdf#table-row[1]"
        )
        self.assertIn("2008", row["text"])
        self.assertIn("MMBoe", row["text"])
        self.assertEqual(row["cell_ids"], ["DVN/2007/page_58.pdf#table[1][1]"])
        for item in bundle["sources"]:
            self.assertEqual(item["source"]["table"], item["source"]["table_ori"])

    def test_repeatable_artifact_and_tamper_rejection(self):
        raw, selection = fixture()
        first, _ = prepare_corpus(raw, selection)
        second, _ = prepare_corpus(raw, selection)
        self.assertEqual(encode(first), encode(second))
        with tempfile.TemporaryDirectory() as folder:
            path = write_prepared(first, Path(folder))
            self.assertEqual(write_prepared(second, Path(folder)), path)
            self.assertEqual(load_prepared(path), first)
            damaged = deepcopy(first)
            damaged["cells"][0]["source_value"] = "999"
            path.write_bytes(encode(damaged))
            with self.assertRaises(ValueError):
                load_prepared(path)
            with self.assertRaises(ValueError):
                write_prepared(first, Path(folder))
            self.assertEqual(path.read_bytes(), encode(damaged))

    def test_reject_bad_hash_missing_sources_and_ambiguous_contexts(self):
        raw, selection = fixture()
        with self.assertRaises(ValueError):
            prepare_corpus(raw + b" ", selection)
        with self.assertRaises(ValueError):
            prepare_corpus(raw, {**selection, "source_filenames": ["absent"]})
        entries = json.loads(raw)
        entries[1]["pre_text"] = ["Different context under the same filename."]
        changed = encode(entries)
        with self.assertRaises(ValueError):
            prepare_corpus(changed, {**selection, "raw_sha256": sha256(changed).hexdigest()})
        for invalid in ("ragged", "oversized"):
            entries = json.loads(raw)
            if invalid == "ragged":
                entries[0]["table_ori"][1] = ["Canada"]
            else:
                entries[0]["pre_text"] = ["x" * 6001]
                entries[1]["pre_text"] = entries[0]["pre_text"]
            changed = encode(entries)
            with self.subTest(input=invalid), self.assertRaises(ValueError):
                prepare_corpus(changed, {**selection, "raw_sha256": sha256(changed).hexdigest()})

    def test_reject_annotation_fields_even_with_a_new_fingerprint(self):
        raw, selection = fixture()
        bundle, _ = prepare_corpus(raw, selection)
        bundle["sources"][0]["source"]["answer"] = "ANNOTATION-SECRET"
        bundle["manifest"]["corpus_version"] = corpus_version(bundle)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "tampered.json"
            path.write_bytes(encode(bundle))
            with self.assertRaises(ValueError):
                load_prepared(path)


if __name__ == "__main__":
    unittest.main()
