"""Index/cache integrity and pacing checks; all embeddings here are simulated."""

from contextlib import closing
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from app.corpus import digest, encode, prepare_corpus, read_current, write_atomic, write_prepared
from app.embeddings import EMBEDDING_CONFIG, EmbeddingCache, EmbeddingPacer, document_input
from app.llm import DIMENSIONS, EMBEDDING_MODEL, ProviderError
from app.storage import file_hash, load_index, publish_index
from scripts.build_index import collect_embeddings
from test_corpus import fixture


class FakeProvider:
    def __init__(self, fail_after=None):
        self.attempts, self.fail_after = 0, fail_after

    def embed_text(self, text, *, run_id, metadata=None):
        self.attempts += 1
        record = {
            "status": "passed",
            "requested_model": EMBEDDING_MODEL,
            "call_id": f"simulated-{self.attempts}",
            "run_id": run_id,
            "metadata": {**(metadata or {}), "input_sha256": sha256(text.encode()).hexdigest()},
        }
        if self.fail_after is not None and self.attempts > self.fail_after:
            record["status"] = "failed"
            raise ProviderError("simulated_quota", record)
        angle = int(sha256(text.encode()).hexdigest()[:8], 16) / (16**8) * math.tau
        vector = np.zeros(DIMENSIONS, dtype="<f4")
        vector[:2] = [math.cos(angle), math.sin(angle)]
        return vector, record


def report():
    return {
        "run_id": "simulated-index",
        "calls": [],
        "cache_hits": 0,
        "completed_rows": 0,
        "pacing_wait_seconds": 0.0,
    }


def populate(corpus, cache, provider, journal):
    output = report()
    rows = collect_embeddings(
        corpus,
        cache,
        output,
        lambda: None,
        provider,
        EmbeddingPacer(journal),
        progress=lambda *args, **kwargs: None,
    )
    return rows, output


class IndexTests(unittest.TestCase):
    def test_atomic_progress_write_tolerates_a_transient_windows_lock(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "progress.json"
            path.write_bytes(b"old")
            original_replace = Path.replace
            attempts = []

            def replace(source, target):
                attempts.append(target)
                if len(attempts) == 1:
                    raise PermissionError("simulated sharing violation")
                return original_replace(source, target)

            with (
                patch.object(Path, "replace", autospec=True, side_effect=replace),
                patch("app.corpus.sleep") as sleep,
            ):
                write_atomic(path, b"new")
            self.assertEqual(path.read_bytes(), b"new")
            self.assertEqual(len(attempts), 2)
            sleep.assert_called_once_with(0.05)

    def test_returned_vector_is_cached_before_progress_failure(self):
        corpus, _ = prepare_corpus(*fixture())
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            cache, provider, output = (
                EmbeddingCache(root / "cache.sqlite"),
                FakeProvider(),
                report(),
            )

            def fail_save():
                raise OSError("simulated progress failure")

            with self.assertRaises(OSError):
                collect_embeddings(
                    corpus, cache, output, fail_save, provider, EmbeddingPacer(root / "no-journal")
                )
            self.assertEqual(provider.attempts, 1)
            self.assertEqual(len(output["calls"]), 1)
            self.assertIsNotNone(cache.get(document_input(corpus["chunks"][0]["text"])))

    def test_cached_rebuild_and_sqlite_vector_alignment(self):
        corpus, _ = prepare_corpus(*fixture())
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            prepared_path = write_prepared(corpus, root / "prepared")
            self.assertEqual(
                read_current(root / "prepared", "corpus_version").with_suffix(".json"),
                prepared_path,
            )
            cache, provider = EmbeddingCache(root / "cache.sqlite"), FakeProvider()
            rows, first = populate(corpus, cache, provider, root / "unused-journal.sqlite")
            expected_inputs = {document_input(chunk["text"]) for chunk in corpus["chunks"]}
            self.assertEqual(provider.attempts, len(expected_inputs))
            self.assertEqual(len(first["calls"]), len(expected_inputs))
            second = report()
            cached_rows = collect_embeddings(corpus, cache, second, lambda: None)
            self.assertEqual(second["calls"], [])
            self.assertEqual(second["cache_hits"], len(corpus["chunks"]))
            destination = publish_index(corpus, rows, root / "indexes")
            manifest, loaded, vectors = load_index(
                destination, corpus["manifest"]["corpus_version"]
            )
            self.assertEqual(loaded, corpus)
            self.assertEqual(vectors.shape, (len(corpus["chunks"]), DIMENSIONS))
            self.assertFalse(vectors.flags.writeable)
            self.assertEqual(publish_index(corpus, cached_rows, root / "indexes"), destination)
            self.assertEqual(manifest["embedding"], EMBEDDING_CONFIG)
            with closing(sqlite3.connect(destination / "corpus.sqlite")) as database:
                self.assertGreater(
                    database.execute(
                        "SELECT count(*) FROM chunk_fts WHERE chunk_fts MATCH ?", ("canada",)
                    ).fetchone()[0],
                    0,
                )
            (root / "prepared/current.json").write_bytes(
                encode({"corpus_version": "../../private"})
            )
            with self.assertRaises(ValueError):
                read_current(root / "prepared", "corpus_version")

    def test_partial_failure_resumes_and_bad_cache_is_not_reused(self):
        corpus, _ = prepare_corpus(*fixture())
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            cache = EmbeddingCache(root / "cache.sqlite")
            failed = report()
            with self.assertRaises(ProviderError):
                collect_embeddings(
                    corpus,
                    cache,
                    failed,
                    lambda: None,
                    FakeProvider(fail_after=2),
                    EmbeddingPacer(root / "no-journal"),
                    progress=lambda *a, **k: None,
                )
            self.assertEqual(len(failed["calls"]), 3)
            self.assertEqual(failed["completed_rows"], 2)
            self.assertEqual(failed["calls"][-1]["status"], "failed")
            provider = FakeProvider()
            rows, resumed = populate(corpus, cache, provider, root / "no-journal")
            unique = {document_input(chunk["text"]) for chunk in corpus["chunks"]}
            self.assertEqual(provider.attempts, len(unique) - 2)
            self.assertEqual(len(rows), len(corpus["chunks"]))
            self.assertGreaterEqual(resumed["cache_hits"], 2)
            with closing(sqlite3.connect(cache.path)) as database, database:
                database.execute(
                    "UPDATE embeddings SET vector = ? WHERE cache_key = ?", (b"bad", rows[0]["key"])
                )
            with self.assertRaises(ValueError):
                cache.get(document_input(corpus["chunks"][0]["text"]))

    def test_reject_mismatched_matrix_rows_fts_and_configuration(self):
        corpus, _ = prepare_corpus(*fixture())
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            rows, _ = populate(
                corpus, EmbeddingCache(root / "cache.sqlite"), FakeProvider(), root / "no-journal"
            )
            original = publish_index(corpus, rows, root / "indexes")
            for case in ("swapped", "shape", "nan", "fts", "extra_table", "model"):
                with self.subTest(case=case):
                    target = root / case
                    shutil.copytree(original, target)
                    manifest = json.loads((target / "manifest.json").read_text())
                    if case in ("swapped", "shape", "nan"):
                        values = np.load(target / "vectors.npy", allow_pickle=False)
                        if case == "swapped":
                            values[[0, 1]] = values[[1, 0]]
                        elif case == "shape":
                            values = values[:, :2]
                        else:
                            values[0, 0] = np.nan
                        np.save(target / "vectors.npy", values, allow_pickle=False)
                        manifest["files"]["vectors.npy"] = file_hash(target / "vectors.npy")
                    elif case in ("fts", "extra_table"):
                        with (
                            closing(sqlite3.connect(target / "corpus.sqlite")) as database,
                            database,
                        ):
                            if case == "fts":
                                database.execute(
                                    "UPDATE chunk_fts SET text='wrong evidence' WHERE rowid=1"
                                )
                            else:
                                database.execute("CREATE TABLE answers (value TEXT)")
                        manifest["files"]["corpus.sqlite"] = file_hash(target / "corpus.sqlite")
                    else:
                        manifest["embedding"]["model"] = "other-model"
                    manifest["index_version"] = digest(
                        {key: value for key, value in manifest.items() if key != "index_version"}
                    )
                    (target / "manifest.json").write_bytes(encode(manifest))
                    with self.assertRaises(ValueError):
                        load_index(target, corpus["manifest"]["corpus_version"])
            with self.assertRaises(ValueError):
                load_index(original, "0" * 64)

    def test_pacing_limits_and_restart_history(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            clock, sleeps = [0.0], []

            def sleep(duration):
                sleeps.append(duration)
                clock[0] += duration

            pacer = EmbeddingPacer(root / "missing", clock=lambda: clock[0], sleep=sleep)
            for _ in range(3):
                self.assertEqual(pacer.wait(8000), 0)
            self.assertGreaterEqual(pacer.wait(8000), 60)
            self.assertLessEqual(max(sleeps), 1)
            with self.assertRaises(ValueError):
                pacer.wait(8193)
            journal = root / "journal.sqlite"
            with closing(sqlite3.connect(journal)) as database, database:
                database.execute("CREATE TABLE calls(record_json TEXT)")
                call = {
                    "kind": "embedding",
                    "created_at_utc": datetime.fromtimestamp(1800000000, timezone.utc).isoformat(),
                    "metadata": {"input_token_allowance": 8000},
                }
                database.executemany("INSERT INTO calls VALUES (?)", [(json.dumps(call),)] * 3)
            resumed = EmbeddingPacer(
                journal, clock=lambda: clock[0], sleep=sleep, wall_time=lambda: 1800000000
            )
            self.assertGreaterEqual(resumed.wait(1), 60)
            rpm = EmbeddingPacer(root / "missing", clock=lambda: clock[0], sleep=sleep)
            for _ in range(80):
                rpm.wait(1)
            self.assertGreaterEqual(rpm.wait(1), 60)


if __name__ == "__main__":
    unittest.main()
