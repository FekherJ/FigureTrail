"""Publish and validate a local SQLite/FTS5 corpus with an aligned vector matrix."""

from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import tempfile

import numpy as np

from app.corpus import digest, encode, read_current, verify_prepared, write_atomic
from app.embeddings import EMBEDDING_CONFIG, checked_vector, document_input, input_key

INDEX_VERSION = "figuretrail-index-v1"
TABLES = {
    "metadata",
    "sources",
    "cells",
    "chunks",
    "chunk_fts",
    "chunk_fts_data",
    "chunk_fts_idx",
    "chunk_fts_content",
    "chunk_fts_docsize",
    "chunk_fts_config",
}


def file_hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def write_database(path: Path, corpus: dict, embeddings: list[dict]) -> None:
    with closing(sqlite3.connect(path)) as database, database:
        database.executescript("""
            PRAGMA foreign_keys=ON;
            CREATE TABLE metadata (name TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE sources (source_id TEXT PRIMARY KEY, record TEXT NOT NULL);
            CREATE TABLE cells (ordinal INTEGER PRIMARY KEY, cell_id TEXT UNIQUE NOT NULL,
                                source_id TEXT NOT NULL REFERENCES sources(source_id), record TEXT NOT NULL);
            CREATE TABLE chunks (ordinal INTEGER PRIMARY KEY, chunk_id TEXT UNIQUE NOT NULL,
                                 source_id TEXT NOT NULL REFERENCES sources(source_id),
                                 embedding_key TEXT NOT NULL, record TEXT NOT NULL);
            CREATE VIRTUAL TABLE chunk_fts USING fts5(chunk_id UNINDEXED, text, tokenize='unicode61');
            PRAGMA user_version=1;
        """)
        database.execute(
            "INSERT INTO metadata VALUES (?, ?)",
            ("prepared_manifest", encode(corpus["manifest"]).decode()),
        )
        database.executemany(
            "INSERT INTO sources VALUES (?, ?)",
            [(item["source_id"], encode(item).decode()) for item in corpus["sources"]],
        )
        database.executemany(
            "INSERT INTO cells VALUES (?, ?, ?, ?)",
            [
                (i, item["cell_id"], item["source_id"], encode(item).decode())
                for i, item in enumerate(corpus["cells"])
            ],
        )
        for ordinal, (chunk, embedding) in enumerate(
            zip(corpus["chunks"], embeddings, strict=True)
        ):
            database.execute(
                "INSERT INTO chunks VALUES (?, ?, ?, ?, ?)",
                (
                    ordinal,
                    chunk["chunk_id"],
                    chunk["source_id"],
                    embedding["key"],
                    encode(chunk).decode(),
                ),
            )
            database.execute(
                "INSERT INTO chunk_fts(rowid, chunk_id, text) VALUES (?, ?, ?)",
                (ordinal + 1, chunk["chunk_id"], chunk["text"]),
            )
        database.execute("INSERT INTO chunk_fts(chunk_fts) VALUES ('integrity-check')")


def load_index(directory: Path, expected_corpus_version: str | None = None):
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    fields = {
        "format_version",
        "index_version",
        "corpus_version",
        "embedding",
        "counts",
        "rows",
        "files",
    }
    if (
        not isinstance(manifest, dict)
        or set(manifest) != fields
        or manifest["format_version"] != INDEX_VERSION
    ):
        raise ValueError("Unsupported index manifest.")
    if manifest["embedding"] != EMBEDDING_CONFIG or manifest["index_version"] != digest(
        {key: value for key, value in manifest.items() if key != "index_version"}
    ):
        raise ValueError("Index configuration or fingerprint mismatch.")
    if (
        expected_corpus_version is not None
        and manifest["corpus_version"] != expected_corpus_version
    ):
        raise ValueError("Index belongs to a different corpus version.")
    if set(manifest["files"]) != {"corpus.sqlite", "vectors.npy"}:
        raise ValueError("Unexpected index files.")
    for name, expected in manifest["files"].items():
        if file_hash(directory / name) != expected:
            raise ValueError("Index file fingerprint mismatch.")
    # Open existing SQLite read-only; validation must not mutate the published bundle.
    uri = (directory / "corpus.sqlite").resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as database:
        database.execute("PRAGMA query_only=ON")
        tables = {
            row[0] for row in database.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if (
            tables != TABLES
            or database.execute(
                "SELECT count(*) FROM sqlite_master WHERE type IN ('view','trigger')"
            ).fetchone()[0]
        ):
            raise ValueError("Unexpected SQLite schema.")
        if (
            database.execute("PRAGMA quick_check").fetchone()[0] != "ok"
            or database.execute("PRAGMA foreign_key_check").fetchall()
        ):
            raise ValueError("SQLite integrity check failed.")
        metadata = dict(database.execute("SELECT name, value FROM metadata"))
        if set(metadata) != {"prepared_manifest"}:
            raise ValueError("Unexpected SQLite metadata fields.")
        corpus = {"manifest": json.loads(metadata["prepared_manifest"])}
        source_rows = database.execute(
            "SELECT source_id, record FROM sources ORDER BY source_id"
        ).fetchall()
        cell_rows = database.execute(
            "SELECT ordinal, cell_id, source_id, record FROM cells ORDER BY ordinal"
        ).fetchall()
        corpus["sources"] = [json.loads(row[1]) for row in source_rows]
        corpus["cells"] = [json.loads(row[3]) for row in cell_rows]
        chunk_rows = database.execute(
            "SELECT ordinal, chunk_id, source_id, embedding_key, record FROM chunks ORDER BY ordinal"
        ).fetchall()
        corpus["chunks"] = [json.loads(row[4]) for row in chunk_rows]
        fts_rows = database.execute(
            "SELECT rowid, chunk_id, text FROM chunk_fts ORDER BY rowid"
        ).fetchall()
    verify_prepared(corpus)
    if any(
        row[0] != item["source_id"]
        for row, item in zip(source_rows, corpus["sources"], strict=True)
    ) or any(
        row[:3] != (i, item["cell_id"], item["source_id"])
        for i, (row, item) in enumerate(zip(cell_rows, corpus["cells"], strict=True))
    ):
        raise ValueError("SQLite source or cell keys disagree with their records.")
    if (
        manifest["corpus_version"] != corpus["manifest"]["corpus_version"]
        or manifest["counts"] != corpus["manifest"]["counts"]
    ):
        raise ValueError("Corpus and index manifest disagree.")
    vectors = np.load(directory / "vectors.npy", allow_pickle=False)
    if (
        vectors.dtype.str != "<f4"
        or vectors.shape != (len(chunk_rows), EMBEDDING_CONFIG["dimensions"])
        or len(manifest["rows"]) != len(chunk_rows)
    ):
        raise ValueError("Vector matrix dimensions or type do not match the chunks.")
    if len(fts_rows) != len(chunk_rows):
        raise ValueError("FTS row count mismatch.")
    for ordinal, (chunk, row, vector) in enumerate(
        zip(corpus["chunks"], manifest["rows"], vectors, strict=True)
    ):
        if not isinstance(row, dict) or set(row) != {
            "chunk_id",
            "embedding_key",
            "vector_sha256",
            "provider_call_id",
            "provider_run_id",
        }:
            raise ValueError("Unexpected vector-row metadata.")
        checked_vector(vector)
        key = input_key(document_input(chunk["text"]))
        if (
            row["chunk_id"] != chunk["chunk_id"]
            or row["embedding_key"] != key
            or row["vector_sha256"] != sha256(vector.tobytes()).hexdigest()
        ):
            raise ValueError("A vector row does not match its source chunk.")
        if chunk_rows[ordinal][:4] != (
            ordinal,
            chunk["chunk_id"],
            chunk["source_id"],
            key,
        ) or fts_rows[ordinal] != (ordinal + 1, chunk["chunk_id"], chunk["text"]):
            raise ValueError("SQLite, FTS and vector row mappings disagree.")
    vectors.setflags(write=False)
    return manifest, corpus, vectors


def publish_index(corpus: dict, embeddings: list[dict], output_dir: Path) -> Path:
    verify_prepared(corpus)
    if len(embeddings) != len(corpus["chunks"]):
        raise ValueError("Every chunk requires an embedding.")
    output_dir.mkdir(parents=True, exist_ok=True)
    root = output_dir.resolve()
    with tempfile.TemporaryDirectory(dir=root, prefix=".build-") as folder:
        temporary = Path(folder).resolve()
        if temporary.parent != root:
            raise ValueError("Index staging must stay in the output directory.")
        write_database(temporary / "corpus.sqlite", corpus, embeddings)
        vectors = np.stack([checked_vector(item["vector"]) for item in embeddings]).astype(
            "<f4", copy=False
        )
        np.save(temporary / "vectors.npy", vectors, allow_pickle=False)
        rows = [
            {
                "chunk_id": chunk["chunk_id"],
                "embedding_key": item["key"],
                "vector_sha256": item["metadata"]["vector_sha256"],
                "provider_call_id": item["metadata"]["call_id"],
                "provider_run_id": item["metadata"]["run_id"],
            }
            for chunk, item in zip(corpus["chunks"], embeddings, strict=True)
        ]
        manifest = {
            "format_version": INDEX_VERSION,
            "corpus_version": corpus["manifest"]["corpus_version"],
            "embedding": EMBEDDING_CONFIG.copy(),
            "counts": corpus["manifest"]["counts"],
            "rows": rows,
            "files": {
                name: file_hash(temporary / name) for name in ("corpus.sqlite", "vectors.npy")
            },
        }
        manifest["index_version"] = digest(manifest)
        (temporary / "manifest.json").write_bytes(encode(manifest) + b"\n")
        load_index(temporary, corpus["manifest"]["corpus_version"])
        destination = root / manifest["index_version"]
        if destination.parent != root:
            raise ValueError("Index destination must stay in the output directory.")
        if destination.exists():
            load_index(destination, corpus["manifest"]["corpus_version"])
        else:
            temporary.rename(destination)
    write_atomic(
        root / "current.json", encode({"index_version": manifest["index_version"]}) + b"\n"
    )
    return destination


def current_index(directory: Path, corpus_version: str):
    path = read_current(directory, "index_version")
    return path, load_index(path, corpus_version)
