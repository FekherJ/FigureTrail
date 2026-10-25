"""Prepare and verify the pinned FinQA corpus without model requests."""

import argparse
import json
from pathlib import Path

from app.corpus import encode, load_prepared, prepare_corpus, read_current, write_prepared

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="Verify the existing output without writing."
    )
    args = parser.parse_args()
    selection = json.loads((ROOT / "data/finqa-corpus-selection.json").read_text(encoding="utf-8"))
    try:
        bundle, report = prepare_corpus((ROOT / "data/raw/finqa-dev.json").read_bytes(), selection)
        version = bundle["manifest"]["corpus_version"]
        output_dir = ROOT / "data/corpus/prepared"
        destination = output_dir / f"{version}.json"
        if args.check:
            if read_current(output_dir, "corpus_version").with_suffix(".json") != destination:
                raise ValueError(
                    "The current prepared-corpus pointer differs from this preparation."
                )
            if (
                load_prepared(destination) != bundle
                or destination.read_bytes() != encode(bundle) + b"\n"
            ):
                raise ValueError("The existing corpus differs from the reproducible preparation.")
        else:
            write_prepared(bundle, output_dir)
            report_path = ROOT / "data/local/corpus-preparation" / f"{version}.json"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError) as error:
        parser.exit(1, f"Corpus preparation failed: {error}\n")
    print(
        json.dumps(
            {
                "status": "verified" if args.check else "prepared",
                "corpus_version": version,
                "path": destination.relative_to(ROOT).as_posix(),
                **bundle["manifest"]["counts"],
                "selected_entries": report["selected_entries"],
                "normalization_differences": len(report["normalization_differences"]),
                "numeric_conflicts": sum(
                    item["kind"] == "numeric_conflict"
                    for item in report["normalization_differences"]
                ),
                "model_requests": 0,
                "indexes_ready": False,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
