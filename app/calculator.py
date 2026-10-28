"""Validate a bounded table calculation; operands always come from source cells."""

from datetime import date
from decimal import Context, Decimal, DecimalException, ROUND_HALF_EVEN, ROUND_HALF_UP, localcontext
from html import unescape
import re

from app.corpus import decimal_value

VERSION = "table-calculation-v2"
PHYSICAL_UNITS = {
    "mmboe": ("MMBoe", 1000000),
    "mmbbls": ("MMBbls", 1000000),
    "bcf": ("Bcf", 1000000000),
}
MONTHS = {
    name: index
    for index, name in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split(), 1)
}
DATE = r"\b([a-z]{3,9})\.?\s+(\d{1,2})\s*,?\s*((?:19|20)\d{2})\b"


class EvidenceError(ValueError):
    def __init__(self, code, status="insufficient_evidence"):
        super().__init__(code)
        self.code, self.status = code, status


def clean(text):
    return unescape(re.sub(r"<[^>]*>", "", text)).casefold()


def years(text):
    return {int(value) for value in re.findall(r"\b(?:19|20)\d{2}\b", text)}


def dates(text):
    values = set()
    for month, day, year in re.findall(DATE, clean(text)):
        if month[:3] in MONTHS:
            try:
                values.add(date(int(year), MONTHS[month[:3]], int(day)).isoformat())
            except ValueError:
                raise EvidenceError("invalid_period") from None
    return values


def context_for(cell, chunks):
    """Establish the units, scale and period supported by one retrieved source cell.

    Args:
        cell: Original cell record, including cell_id, value, row label and column header.
        chunks: Retrieved excerpts; only those referencing this cell supply context.

    Returns:
        A dictionary with unit, scale, year/date, reported/estimate nature and source
        text supporting those choices. Missing/ambiguous context raises EvidenceError.
    """
    text = "\n".join(chunk["text"] for chunk in chunks if cell["cell_id"] in chunk["cell_ids"])
    if not text:
        raise EvidenceError("invalid_cell_reference", "failed")
    # Chunk format is versioned by the validated corpus; no parent-table expansion.
    before, _, remainder = clean(text).partition("columns: ")
    header = remainder.splitlines()[0] if remainder else ""
    nearby = before.splitlines()[-1] if before.splitlines() else ""
    anchor = header + "\n" + nearby
    column = clean(cell["column_header"])
    units = [
        value for token, value in PHYSICAL_UNITS.items() if re.search(r"\b" + token + r"\b", column)
    ]
    if not units and "square feet" in header:
        units = [("square feet", 1000000)] if "in millions" in header else [("square feet", 1)]
    if not units and ("$" in cell["source_value"] or "dollars" in anchor):
        scales = set(re.findall(r"\bin\s+(millions|thousands)\b", anchor))
        scales.update(re.findall(r"\b(millions|thousands)\s+of\s+dollars\b", anchor))
        if len(scales) > 1:
            raise EvidenceError("ambiguous_scale")
        units = [("$", {"millions": 1000000, "thousands": 1000}.get(next(iter(scales), ""), 1))]
    if len(units) != 1:
        raise EvidenceError("ambiguous_unit")
    column_years, row_years = years(column), years(cell["row_label"])
    period_text, nature = cell["column_header"], "reported"
    if len(column_years) == 1:
        period_years = column_years
    elif not column_years and len(row_years) == 1:
        period_years, period_text = row_years, cell["row_label"]
    else:
        estimates = re.findall(r"\bestimates?[^\n]{0,180}\bfor\s+((?:19|20)\d{2})\b", before)
        as_of = re.findall(r"\bas\s+of\s+(" + DATE + ")", before)
        if len(set(estimates)) == 1:
            period_years, period_text, nature = {int(estimates[0])}, before, "estimate"
        elif len(as_of) == 1:
            period_text = as_of[0][0]
            period_years, nature = years(period_text), "as_of"
        else:
            raise EvidenceError("ambiguous_period")
    period_dates = dates(period_text)
    if len(period_dates) > 1:
        raise EvidenceError("ambiguous_period")
    return {
        "unit": units[0][0],
        "scale": units[0][1],
        "year": next(iter(period_years)),
        "date": next(iter(period_dates), None),
        "nature": nature,
        "period_basis": period_text,
        "unit_basis": anchor,
    }


def calculate(selection, question, cells, chunks):
    """Validate the selected source operands and calculate an allowed percentage.

    Args:
        selection: Validated ready CellSelection with operation and two ordered cell IDs.
        question: User question used to check requested units and periods.
        cells: Original corpus cell records from which values are resolved.
        chunks: Evidence actually retrieved for this question; limits accessible cells.

    Returns:
        A dictionary with formula, Decimal value as text, rounded display and source
        operands/context. Invalid evidence raises EvidenceError for analyze() to record;
        no model-generated number or code is executed.
    """
    if selection.status != "ready":
        raise EvidenceError("selection_not_ready")
    # A cell must have been retrieved for this question; existing somewhere in the corpus
    # is not enough to make it permitted evidence for this calculation.
    allowed = {cell_id for chunk in chunks for cell_id in chunk["cell_ids"]}
    source_cells = {cell["cell_id"]: cell for cell in cells}
    if any(cell_id not in allowed or cell_id not in source_cells for cell_id in selection.cell_ids):
        raise EvidenceError("invalid_cell_reference", "failed")
    chosen = [source_cells[cell_id] for cell_id in selection.cell_ids]
    if len({cell["source_id"] for cell in chosen}) != 1:
        raise EvidenceError("cross_source_calculation", "unsupported_request")
    operands = []
    for cell in chosen:
        number = decimal_value(cell["source_value"])
        if number is None:
            raise EvidenceError("unusable_source_value")
        if len(number) > 100:
            raise EvidenceError("numeric_range", "unsupported_request")
        operands.append({**cell, "value": number, "context": context_for(cell, chunks)})
    first, second = [item["context"] for item in operands]
    if first["unit"] != second["unit"] or first["scale"] != second["scale"]:
        raise EvidenceError("incompatible_units_or_scales")
    requested_units = {
        unit
        for token, (unit, _) in PHYSICAL_UNITS.items()
        if re.search(r"\b" + token + r"\b", question.casefold())
    }
    if requested_units and requested_units != {first["unit"]}:
        raise EvidenceError("question_unit_mismatch")
    if not years(question) or years(question) != {first["year"], second["year"]}:
        raise EvidenceError("question_period_mismatch")
    question_dates = dates(question)
    if question_dates and question_dates != {first["date"], second["date"]}:
        raise EvidenceError("question_period_mismatch")
    if re.search(r"\bactual\b", question.casefold()) and "estimate" in {
        first["nature"],
        second["nature"],
    }:
        raise EvidenceError("question_period_mismatch")
    if selection.operation == "ratio_percent":
        if any(first[key] != second[key] for key in ("year", "date", "nature")):
            raise EvidenceError("incompatible_periods")
    elif selection.operation == "percent_change":
        labels = [
            re.sub(r"\b(?:19|20)\d{2}\b", "", clean(cell["row_label"])).strip() for cell in chosen
        ]
        if labels[0] != labels[1] or first["year"] <= second["year"]:
            raise EvidenceError("incompatible_change_periods_or_labels")
    else:
        raise EvidenceError("unsupported_operation", "unsupported_request")
    # Operand order is numerator/denominator for a ratio, and new/old for a change.
    a, b = [Decimal(item["value"]) for item in operands]
    if b <= 0:
        raise EvidenceError("nonpositive_denominator", "unsupported_request")
    try:
        # Use explicit decimal precision for arithmetic; round to two places only for display.
        with localcontext(Context(prec=28, rounding=ROUND_HALF_EVEN)):
            answer = Decimal(100) * (a if selection.operation == "ratio_percent" else a - b) / b
            display = answer.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except DecimalException:
        raise EvidenceError("numeric_range", "unsupported_request") from None
    formula = (
        f"100 * {a} / {b}" if selection.operation == "ratio_percent" else f"100 * ({a} - {b}) / {b}"
    )
    return {
        "operation": selection.operation,
        "formula": formula,
        "value": str(answer),
        "display": f"{display} %",
        "unit": "%",
        "operands": operands,
        "calculator_version": VERSION,
        "decimal_precision": 28,
        "display_rounding": "ROUND_HALF_UP",
    }
