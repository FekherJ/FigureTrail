"""Content-addressed embedding cache and conservative pacing for one local builder."""

from collections import deque
from contextlib import closing
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import time

import numpy as np

from app.corpus import digest, encode
from app.llm import DIMENSIONS, EMBEDDING_MODEL

EMBEDDING_CONFIG = {
    "model": EMBEDDING_MODEL,
    "dimensions": DIMENSIONS,
    "dtype": "<f4",
    "format_version": "retrieval-prefix-v1",
    "document_format": "title: none | text: {content}",
    "query_format": "task: search result | query: {query}",
}
PACING_RPM = 80
PACING_INPUT_ALLOWANCE = 24_000


def document_input(text: str) -> str:
    return "title: none | text: " + text


def input_key(text: str) -> str:
    return digest(
        {"configuration": EMBEDDING_CONFIG, "input_sha256": sha256(text.encode()).hexdigest()}
    )


def checked_vector(values) -> np.ndarray:
    vector = np.asarray(values, dtype="<f4")
    if (
        vector.shape != (DIMENSIONS,)
        or not np.isfinite(vector).all()
        or not np.isclose(np.linalg.norm(vector), 1, rtol=1e-3, atol=1e-3)
    ):
        raise ValueError("Embedding vector has invalid dimensions, values or norm.")
    return vector


class EmbeddingCache:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(path)) as database, database:
            database.execute(
                "CREATE TABLE IF NOT EXISTS embeddings (cache_key TEXT PRIMARY KEY, vector BLOB NOT NULL, metadata TEXT NOT NULL)"
            )

    def get(self, text: str):
        key = input_key(text)
        with closing(sqlite3.connect(self.path)) as database:
            row = database.execute(
                "SELECT vector, metadata FROM embeddings WHERE cache_key = ?", (key,)
            ).fetchone()
        if row is None:
            return None
        blob, raw_metadata = row
        metadata = json.loads(raw_metadata)
        if not isinstance(metadata, dict) or set(metadata) != {
            "configuration",
            "input_sha256",
            "vector_sha256",
            "call_id",
            "run_id",
        }:
            raise ValueError("Unexpected embedding cache metadata.")
        if (
            metadata["configuration"] != EMBEDDING_CONFIG
            or metadata["input_sha256"] != sha256(text.encode()).hexdigest()
            or metadata["vector_sha256"] != sha256(blob).hexdigest()
        ):
            raise ValueError("Embedding cache metadata or fingerprint mismatch.")
        vector = checked_vector(np.frombuffer(blob, dtype="<f4")).copy()
        return {"key": key, "vector": vector, "metadata": metadata}

    def put(self, text: str, values, call: dict):
        input_hash = sha256(text.encode()).hexdigest()
        if (
            call["status"] != "passed"
            or call["requested_model"] != EMBEDDING_MODEL
            or call["metadata"]["input_sha256"] != input_hash
        ):
            raise ValueError("Embedding provenance does not match the requested input.")
        blob = checked_vector(values).tobytes()
        metadata = {
            "configuration": EMBEDDING_CONFIG.copy(),
            "input_sha256": input_hash,
            "vector_sha256": sha256(blob).hexdigest(),
            "call_id": call["call_id"],
            "run_id": call["run_id"],
        }
        # Cache transactions finish before any subsequent provider request.
        with closing(sqlite3.connect(self.path)) as database, database:
            database.execute(
                "INSERT OR IGNORE INTO embeddings VALUES (?, ?, ?)",
                (input_key(text), blob, encode(metadata).decode()),
            )
        return self.get(text)


class EmbeddingPacer:
    def __init__(
        self, journal: Path, *, clock=time.monotonic, sleep=time.sleep, wall_time=time.time
    ):
        self.clock, self.sleep = clock, sleep
        self.events = deque()
        if journal.exists():
            now, utc_now = clock(), wall_time()
            with closing(sqlite3.connect(journal)) as database:
                rows = database.execute("SELECT record_json FROM calls").fetchall()
            recent = []
            for row in rows:
                call = json.loads(row[0])
                if call["kind"] != "embedding":
                    continue
                age = max(0, utc_now - datetime.fromisoformat(call["created_at_utc"]).timestamp())
                if age < 60:
                    recent.append(
                        (now - age, call.get("metadata", {}).get("input_token_allowance", 8192))
                    )
            self.events.extend(sorted(recent))

    def wait(self, allowance: int, *, deadline=None, cancelled=None) -> float:
        if not 1 <= allowance <= 8192:
            raise ValueError("Embedding input exceeds the conservative per-request allowance.")
        started = self.clock()
        # ponytail: one builder process; coordinate rate reservations if concurrent builds are needed.
        while True:
            now = self.clock()
            if (deadline is not None and now >= deadline) or (
                cancelled is not None and cancelled.is_set()
            ):
                raise TimeoutError("Embedding pacing deadline reached.")
            while self.events and now - self.events[0][0] >= 60:
                self.events.popleft()
            if (
                len(self.events) < PACING_RPM
                and sum(value for _, value in self.events) + allowance <= PACING_INPUT_ALLOWANCE
            ):
                self.events.append((now, allowance))
                return self.clock() - started
            delay = min(1, max(0.01, 60 - (now - self.events[0][0]) + 0.01))
            if deadline is not None:
                delay = min(delay, max(0, deadline - now))
            self.sleep(delay)
