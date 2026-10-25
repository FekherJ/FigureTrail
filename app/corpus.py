"""Prepare a small, source-only corpus; indexes are built in a later B04 step."""

from collections import defaultdict
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import re
import tempfile
from time import sleep
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas import SourceDocument

VERSION = "finqa-prepared-v1"
SOURCE_FIELDS = ("filename", "pre_text", "post_text", "table", "table_ori")
CHUNKING = {
    "text_target_chars": 1200,
    "max_chunk_chars": 6000,
    "pre_context_paragraphs": 5,
    "post_context_paragraphs": 3,
}


class CorpusSelection(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    selection_version: Literal["finqa-corpus-v1"]
    raw_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_filenames: list[str] = Field(min_length=1, max_length=40)


def encode(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def digest(value) -> str:
    return sha256(encode(value)).hexdigest()


def decimal_value(text: str) -> str | None:
    # Unsupported formatting and missing-value dashes stay unknown, never zero.
    cleaned = text.strip()
    if cleaned.startswith("$"):
        cleaned = cleaned[1:].strip()
    if not re.fullmatch(r"[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?", cleaned):
        return None
    return str(Decimal(cleaned.replace(",", "")))


def document(source: SourceDocument) -> dict:
    content = source.model_dump()
    context = {key: content[key] for key in SOURCE_FIELDS if key != "filename"}
    return {
        "source_id": source.filename,
        "report_id": source.filename.rsplit("/", 1)[0],
        "content_sha256": digest(context),
        "source": content,
    }


def records(item: dict) -> tuple[list[dict], list[dict]]:
    source = SourceDocument.model_validate(item["source"])
    cells, chunks = [], []

    def add_chunk(chunk_id, kind, text, cell_ids):
        if len(text) > CHUNKING["max_chunk_chars"]:
            raise ValueError(f"Chunk exceeds the supported size: {chunk_id}")
        chunks.append(
            {
                "chunk_id": chunk_id,
                "source_id": source.filename,
                "report_id": item["report_id"],
                "kind": kind,
                "text": text,
                "cell_ids": cell_ids,
            }
        )

    for section in ("pre_text", "post_text"):
        parts, start, end = [], 0, 0
        for index, text in enumerate(getattr(source, section)):
            if not text.strip():
                continue
            if parts and len("\n".join(parts + [text])) > CHUNKING["text_target_chars"]:
                add_chunk(
                    f"{source.filename}#{section}[{start}:{end}]", "text", "\n".join(parts), []
                )
                parts = []
            if not parts:
                start = index
            parts.append(text)
            end = index + 1
        if parts:
            add_chunk(f"{source.filename}#{section}[{start}:{end}]", "text", "\n".join(parts), [])

    before = "\n".join(source.pre_text[-CHUNKING["pre_context_paragraphs"] :])
    after = "\n".join(source.post_text[: CHUNKING["post_context_paragraphs"]])
    headers = " | ".join(source.table_ori[0])
    for row_index, row in enumerate(source.table_ori[1:], 1):
        ids = []
        for column, value in enumerate(row[1:], 1):
            cell_id = source.cell_id(row_index, column)
            ids.append(cell_id)
            cells.append(
                {
                    "cell_id": cell_id,
                    "source_id": source.filename,
                    "row": row_index,
                    "column": column,
                    "source_value": value,
                    "decimal_value": decimal_value(value),
                    "row_label": row[0],
                    "column_header": source.table_ori[0][column],
                }
            )
        # Rows carry headers and neighboring context; the complete parent text is retained too.
        text = f"Before table:\n{before}\nColumns: {headers}\nRow {row_index}: {' | '.join(row)}\nAfter table:\n{after}"
        add_chunk(f"{source.filename}#table-row[{row_index}]", "table_row", text, ids)
    return cells, chunks


def corpus_version(bundle: dict) -> str:
    manifest = {key: value for key, value in bundle["manifest"].items() if key != "corpus_version"}
    return digest({**bundle, "manifest": manifest})


def verify_prepared(bundle: dict) -> None:
    if not isinstance(bundle, dict) or set(bundle) != {"manifest", "sources", "cells", "chunks"}:
        raise ValueError("Unexpected prepared-corpus fields.")
    manifest = bundle["manifest"]
    expected_fields = {
        "preparation_version",
        "source_policy",
        "raw_sha256",
        "selection_sha256",
        "chunking",
        "counts",
        "corpus_version",
    }
    if not isinstance(manifest, dict) or set(manifest) != expected_fields:
        raise ValueError("Unexpected corpus manifest fields.")
    if (
        manifest["preparation_version"] != VERSION
        or manifest["source_policy"] != "original-table-v1"
        or manifest["chunking"] != CHUNKING
    ):
        raise ValueError("Unsupported preparation or chunking version.")
    if manifest["corpus_version"] != corpus_version(bundle):
        raise ValueError("Prepared-corpus fingerprint mismatch.")
    if any(not isinstance(bundle[key], list) for key in ("sources", "cells", "chunks")):
        raise ValueError("Corpus sources, cells and chunks must be lists.")
    sources, cells, chunks, ids = bundle["sources"], [], [], set()
    for item in sources:
        if not isinstance(item, dict) or set(item) != {
            "source_id",
            "report_id",
            "content_sha256",
            "source",
        }:
            raise ValueError("Unexpected source-record fields.")
        source = SourceDocument.model_validate(item["source"])
        if source.table != source.table_ori or item != document(source) or source.filename in ids:
            raise ValueError("Invalid, duplicate or inconsistent source record.")
        ids.add(source.filename)
        item_cells, item_chunks = records(item)
        cells.extend(item_cells)
        chunks.extend(item_chunks)
    counts = {
        "sources": len(sources),
        "report_groups": len({item["report_id"] for item in sources}),
        "cells": len(cells),
        "chunks": len(chunks),
    }
    if not 1 <= len(sources) <= 40 or len(chunks) > 500:
        raise ValueError("Prepared corpus exceeds its supported scope.")
    if bundle["cells"] != cells or bundle["chunks"] != chunks or manifest["counts"] != counts:
        raise ValueError("Corpus cells, chunks or counts do not match original sources.")


def prepare_corpus(raw: bytes, selection_data: dict) -> tuple[dict, dict]:
    selection = CorpusSelection.model_validate(selection_data)
    if sha256(raw).hexdigest() != selection.raw_sha256:
        raise ValueError("The pinned raw dataset hash does not match.")
    names = selection.source_filenames
    if len(set(names)) != len(names):
        raise ValueError("The source selection contains duplicate filenames.")
    selected = defaultdict(list)
    for entry in json.loads(raw):
        if entry["filename"] in names:
            # Raw QA/retrieval annotations are never passed to the source model or corpus.
            selected[entry["filename"]].append({key: entry[key] for key in SOURCE_FIELDS})
    sources, differences, duplicates, seen = [], [], [], {}
    selected_entries = 0
    for filename in sorted(names):
        if not selected[filename]:
            raise ValueError(f"Selected source is absent: {filename}")
        candidates = [SourceDocument.model_validate(value) for value in selected[filename]]
        selected_entries += len(candidates)
        originals = []
        for candidate in candidates:
            # Canonical inference tables use original values; normalized variants are audit-only.
            original = candidate.model_copy(update={"table": candidate.table_ori})
            originals.append(document(original))
        item = originals[0]
        if any(value != item for value in originals[1:]):
            raise ValueError(f"One filename has different original contexts: {filename}")
        if item["content_sha256"] in seen:
            duplicates.append({"skipped": filename, "kept": seen[item["content_sha256"]]})
            continue
        seen[item["content_sha256"]] = filename
        sources.append(item)
        source = candidates[0]
        for row, values in enumerate(source.table_ori):
            for column, original in enumerate(values):
                normalized = source.table[row][column]
                if original.strip().casefold() == normalized.strip().casefold():
                    continue
                old, new = decimal_value(original), decimal_value(normalized)
                kind = (
                    "label_difference"
                    if row == 0 or column == 0
                    else (
                        "formatting_difference"
                        if old is not None and old == new
                        else "numeric_conflict"
                        if old is not None or new is not None
                        else "text_difference"
                    )
                )
                differences.append(
                    {
                        "cell_id": source.cell_id(row, column),
                        "kind": kind,
                        "original": original,
                        "normalized": normalized,
                        "resolution": "use_original",
                    }
                )
    cells, chunks = [], []
    for item in sources:
        item_cells, item_chunks = records(item)
        cells.extend(item_cells)
        chunks.extend(item_chunks)
    manifest = {
        "preparation_version": VERSION,
        "source_policy": "original-table-v1",
        "raw_sha256": selection.raw_sha256,
        "selection_sha256": digest(selection.model_dump()),
        "chunking": CHUNKING.copy(),
        "counts": {
            "sources": len(sources),
            "report_groups": len({item["report_id"] for item in sources}),
            "cells": len(cells),
            "chunks": len(chunks),
        },
    }
    bundle = {"manifest": manifest, "sources": sources, "cells": cells, "chunks": chunks}
    manifest["corpus_version"] = corpus_version(bundle)
    verify_prepared(bundle)
    report = {
        "corpus_version": manifest["corpus_version"],
        "selected_entries": selected_entries,
        "repeated_question_copies_collapsed": selected_entries - len(names),
        "duplicate_contexts": duplicates,
        "normalization_differences": differences,
        "difference_scope": "One representative per retained original context.",
        "model_requests": 0,
        "indexes_ready": False,
    }
    return bundle, report


def load_prepared(path: Path) -> dict:
    bundle = json.loads(path.read_text(encoding="utf-8"))
    verify_prepared(bundle)
    return bundle


def write_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".write-", delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(content)
    try:
        # Windows readers/scanners can briefly deny replacement of an open file.
        for attempt in range(5):
            try:
                temporary.replace(path)
                break
            except PermissionError:
                if attempt == 4:
                    raise
                sleep(0.05 * (attempt + 1))
    finally:
        temporary.unlink(missing_ok=True)


def read_current(directory: Path, key: str) -> Path:
    pointer = json.loads((directory / "current.json").read_text(encoding="utf-8"))
    if (
        not isinstance(pointer, dict)
        or set(pointer) != {key}
        or not re.fullmatch(r"[0-9a-f]{64}", str(pointer[key]))
    ):
        raise ValueError("Invalid current-version pointer.")
    return directory / pointer[key]


def write_prepared(bundle: dict, output_dir: Path) -> Path:
    verify_prepared(bundle)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_dir = output_dir.resolve()
    destination = output_dir / f"{bundle['manifest']['corpus_version']}.json"
    if destination.parent != output_dir:
        raise ValueError("Corpus destination must stay within its output directory.")
    content = encode(bundle) + b"\n"
    if destination.exists():
        load_prepared(destination)
        if destination.read_bytes() != content:
            raise ValueError("Existing corpus bytes differ; refusing to overwrite them.")
    else:
        write_atomic(destination, content)
    write_atomic(
        output_dir / "current.json",
        encode({"corpus_version": bundle["manifest"]["corpus_version"]}) + b"\n",
    )
    return destination
