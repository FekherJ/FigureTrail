"""Vérifier les dix cas B01 hors ligne ; aucune recherche ni inférence LLM."""

import argparse
import hashlib
import json
import re
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIELDS = ("filename", "pre_text", "post_text", "table", "table_ori")
REFERENCE_FIELDS = ("question", "answer", "exe_ans", "program", "gold_inds")


def source_only(case):
    return {key: case[key] for key in SOURCE_FIELDS}


def context_hash(case):
    # Exclure filename pour repérer aussi un même contexte sous un autre chemin.
    context = {key: case[key] for key in SOURCE_FIELDS if key != "filename"}
    return hashlib.sha256(json.dumps(context, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def number(text):
    # Parseur limité aux cellules positives relues ; aucun traitement implicite des tirets.
    cleaned = text.replace("$", "").replace(",", "").strip()
    assert re.fullmatch(r"\d+(?:\.\d+)?", cleaned), f"Cellule non prise en charge : {text!r}"
    return Decimal(cleaned)


def verify_case(case, spec):
    source = source_only(case)
    for proof in spec["checks"]:
        actual = source
        for key in proof["path"]:
            actual = actual[key]
        assert proof["contains"] in actual, f"Preuve différente : {proof['path']}"
    values = []
    for operand in spec["operands"]:
        row, col = operand["cell"]
        value = number(source["table"][row][col])
        assert value == Decimal(operand["value"]), "Valeur différente de la cellule relue"
        assert number(source["table_ori"][row][col]) == value, "Les deux tableaux divergent sur un opérande"
        values.append(value)
    a, b = values
    assert b > 0
    assert spec["unit"] and spec["scale"]
    assert all(o["period"] for o in spec["operands"])
    if spec["operation"] == "ratio_percent":
        assert [o["role"] for o in spec["operands"]] == ["numerator", "denominator"]
        result = Decimal(100) * a / b
        formula = f"100 * {a} / {b}"
    else:
        assert spec["operation"] == "percent_change"
        assert [o["role"] for o in spec["operands"]] == ["new", "old"]
        result = Decimal(100) * (a - b) / b
        formula = f"100 * ({a} - {b}) / {b}"
    assert result == Decimal(spec["expected_percent"])
    comparison = result if spec["exe_ans_unit"] == "percent" else result / Decimal(100)
    assert spec["exe_ans_unit"] in ("ratio", "percent")
    error = abs(comparison - Decimal(str(case["qa"]["exe_ans"])))
    assert error <= Decimal(spec["exe_ans_tolerance"]), "Écart avec exe_ans hors tolérance"
    display = f"{result:.{spec['precision']}f}%"
    assert display == case["qa"]["answer"], "Arrondi différent de la réponse originale"
    return {"key": spec["key"], "case_id": case["id"], "filename": case["filename"],
            "document_group": case["filename"].rsplit("/", 1)[0], "operation": spec["operation"],
            "expected_percent": str(result), "display": display, "formula": formula,
            "exe_ans_unit": spec["exe_ans_unit"], "reference_error_native_unit": str(error),
            "context_sha256": context_hash(case), "status": "verified"}


def audit_contexts(dataset, selected, distractors):
    by_hash, by_filename = defaultdict(list), defaultdict(list)
    for case in dataset:
        by_hash[context_hash(case)].append(case["id"])
        by_filename[case["filename"]].append(case["id"])
    chosen = {c["id"]: c for c in dataset}
    hashes = [context_hash(chosen[s["case_id"]]) for s in selected]
    groups = [chosen[s["case_id"]]["filename"].rsplit("/", 1)[0] for s in selected]
    assert len(set(hashes)) == len(selected), "Deux exemples choisis partagent un contexte exact"
    assert len(set(groups)) == len(selected), "Deux exemples choisis partagent un rapport"
    distractor_hashes = [context_hash(chosen[d["case_id"]]) for d in distractors]
    assert len(set(distractor_hashes)) == len(distractors)
    assert not set(hashes).intersection(distractor_hashes)
    return {"raw_entries": len(dataset), "unique_exact_contexts": len(by_hash),
            "unique_filenames": len(by_filename),
            "exact_context_groups_with_multiple_questions": sum(len(ids) > 1 for ids in by_hash.values()),
            "selected_unique_contexts": len(set(hashes)), "selected_unique_report_groups": len(set(groups)),
            "selected_matches": [{"case_id": s["case_id"],
                                  "same_exact_context_ids": by_hash[context_hash(chosen[s["case_id"]])],
                                  "same_filename_ids": by_filename[chosen[s["case_id"]]["filename"]]} for s in selected],
            "distractors": [{**d, "filename": chosen[d["case_id"]]["filename"],
                             "context_sha256": context_hash(chosen[d["case_id"]])} for d in distractors]}


def main():
    if not __debug__:
        raise SystemExit("Ne pas utiliser -O : ce contrôle pédagogique repose sur assert.")
    manifest = json.loads((ROOT / "evals/cases/finqa-b01-reviewed.json").read_text(encoding="utf-8"))
    specs = manifest["cases"]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=["all", *(s["key"] for s in specs)], default="ratio")
    parser.add_argument("--check", action="store_true", help="Vérifier les exports existants sans écriture.")
    args = parser.parse_args()
    raw = (ROOT / "data/raw/finqa-dev.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == manifest["raw_sha256"], "Le téléchargement a changé"
    dataset = json.loads(raw)
    by_id = {c["id"]: c for c in dataset}
    selected = specs if args.case == "all" else [s for s in specs if s["key"] == args.case]
    assert len(specs) == 10 and len({s["case_id"] for s in specs}) == 10
    for spec in selected:
        case = by_id[spec["case_id"]]
        result = verify_case(case, spec)
        reference = {"case_id": case["id"], "partition": manifest["partition"]}
        reference.update({key: case["qa"][key] for key in REFERENCE_FIELDS})
        for relative, content in ((f"data/samples/{spec['stem']}-source.json", source_only(case)),
                                  (f"evals/cases/{spec['stem']}-reference.json", reference)):
            path = ROOT / relative
            if args.check:
                assert json.loads(path.read_text(encoding="utf-8")) == content, f"Export différent : {relative}"
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                assert json.loads(path.read_text(encoding="utf-8")) == content
        print(f"OK {spec['key']}: {case['id']} | {result['formula']} = {result['expected_percent']} % | {result['display']}")
        if args.case != "all":
            print(f"Unité/échelle : {spec['unit']} / {spec['scale']} ; {spec['nature']}")
            for note in spec["notes"]:
                print(f"Note : {note}")
    audit = audit_contexts(dataset, specs, manifest["distractor_candidates"])
    print(f"Contextes distincts sélectionnés : {audit['selected_unique_contexts']}/10 ; rapports : {audit['selected_unique_report_groups']}/10")
    print(f"Contrôles réussis : {len(selected)} cas ; sources/références séparées ; coût API : 0 €.")


if __name__ == "__main__":
    main()
