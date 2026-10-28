"""Source-only input and the structured cell-selection contract."""

import json
from decimal import Decimal, InvalidOperation
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CellSelection(BaseModel):
    # Pydantic uses these fields for runtime validation and Gemini's JSON output schema.
    model_config = ConfigDict(extra="forbid", strict=True)
    status: Literal["ready", "insufficient_evidence", "unsupported_request"]
    operation: Literal["ratio_percent", "percent_change"] | None
    cell_ids: list[str] = Field(max_length=2)

    @model_validator(mode="after")
    def check_outcome(self):
        if self.status == "ready":
            if self.operation is None or len(self.cell_ids) != 2 or len(set(self.cell_ids)) != 2:
                raise ValueError("Ready requires an operation and two distinct cell IDs.")
        elif self.operation is not None or self.cell_ids:
            raise ValueError("An abstention must not contain an operation or cells.")
        return self


class EvidenceRead(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    cell_ids: list[str] = Field(min_length=1, max_length=2)

    @model_validator(mode="after")
    def check_distinct_cells(self):
        if len(set(self.cell_ids)) != len(self.cell_ids):
            raise ValueError("Evidence cell IDs must be distinct.")
        return self


class SourceDocument(BaseModel):
    # Accept source fields only; answers and programs belong in evaluation.
    model_config = ConfigDict(extra="forbid", strict=True)
    filename: str = Field(min_length=1, max_length=300)
    pre_text: list[str]
    post_text: list[str]
    table: list[list[str]]
    table_ori: list[list[str]]

    @model_validator(mode="after")
    def check_table_shape(self):
        if not self.table_ori or len(self.table_ori[0]) < 2:
            raise ValueError("The original table requires headers and labels.")
        width = len(self.table_ori[0])
        if any(len(row) != width for row in self.table_ori):
            raise ValueError("The original table must be rectangular.")
        if len(self.table) != len(self.table_ori) or any(len(row) != width for row in self.table):
            raise ValueError("Original and normalized table coordinates must align.")
        return self

    def cell_id(self, row: int, column: int) -> str:
        # Coordinates are zero-based in table_ori, including its header row and column.
        return f"{self.filename}#table[{row}][{column}]"

    def model_input(self, question: str) -> str:
        if not question.strip() or len(question) > 2_000:
            raise ValueError("Question is empty or exceeds 2000 characters.")
        # Normalized FinQA tables have known conflicts; retain original cell text.
        context = {
            "source_id": self.filename,
            "pre_text": self.pre_text,
            "post_text": self.post_text,
            "table_rows": [
                [{"cell_id": self.cell_id(r, c), "text": value} for c, value in enumerate(row)]
                for r, row in enumerate(self.table_ori)
            ],
        }
        if len(json.dumps(context, ensure_ascii=False)) > 20_000:
            raise ValueError("Source context exceeds 20000 characters.")
        return json.dumps({"question": question, "source": context}, ensure_ascii=False)

    def resolve_selection(self, selection: CellSelection) -> list[dict]:
        return self.read_evidence(selection.cell_ids)

    def read_evidence(self, cell_ids: list[str]) -> list[dict]:
        # Resolve operands from the supplied source, never from model-generated numbers.
        cells = {
            self.cell_id(r, c): (r, c, value)
            for r, row in enumerate(self.table_ori)
            for c, value in enumerate(row)
            if r > 0 and c > 0
        }
        evidence = []
        for cell_id in cell_ids:
            if cell_id not in cells:
                raise ValueError("Cell is outside the supplied numeric evidence.")
            row, column, value = cells[cell_id]
            try:
                number = Decimal(value.strip().replace(",", ""))
            except InvalidOperation:
                raise ValueError("The selected source cell is not a decimal number.") from None
            if not number.is_finite():
                raise ValueError("Source numbers must be finite.")
            evidence.append(
                {
                    "cell_id": cell_id,
                    "source_value": value,
                    "row_label": self.table_ori[row][0],
                    "column_header": self.table_ori[0][column],
                }
            )
        return evidence


class AnalysisRequest(BaseModel):
    """Public input; model, prompts, paths and retrieval settings are server-controlled."""

    model_config = ConfigDict(extra="forbid", strict=True)
    question: str = Field(min_length=1, max_length=2000)
    report_ids: list[str] | None = Field(default=None, min_length=1, max_length=40)
    mode: Literal["fixed"] = "fixed"

    @model_validator(mode="after")
    def check_question(self):
        if not self.question.strip():
            raise ValueError("Question must contain non-whitespace text.")
        return self


class APIError(BaseModel):
    status: Literal["failed", "blocked"]
    error_code: str
    message: str
    run_id: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    corpus_version: str | None = None


class ReportSummary(BaseModel):
    report_id: str
    source_ids: list[str]
    chunk_count: int


class ReportsResponse(BaseModel):
    corpus_version: str
    index_version: str
    reports: list[ReportSummary]


class RetrievedEvidence(BaseModel):
    rank: int
    score: float
    chunk_id: str
    source_id: str
    report_id: str
    kind: str
    text: str
    cell_ids: list[str]


class OperandContext(BaseModel):
    unit: str
    scale: int
    year: int
    date: str | None
    nature: str
    period_basis: str
    unit_basis: str


class Operand(BaseModel):
    cell_id: str
    source_id: str
    row: int
    column: int
    source_value: str
    row_label: str
    column_header: str
    value: str
    context: OperandContext


class Calculation(BaseModel):
    operation: Literal["ratio_percent", "percent_change"]
    formula: str
    # Preserve Decimal precision as text; JSON floating-point numbers can lose digits.
    value: str
    display: str
    unit: Literal["%"]
    operands: list[Operand] = Field(min_length=2, max_length=2)
    calculator_version: str
    decimal_precision: int
    display_rounding: str


class CallSummary(BaseModel):
    call_id: str
    kind: str
    status: str
    requested_model: str
    returned_model: str | None = None
    usage: dict[str, int | None] | None = None
    duration_seconds: float | None = None
    allowance_eur: str
    actual_charge_eur: str | None = None


class AnalysisResponse(BaseModel):
    run_id: str
    status: Literal[
        "started", "success", "insufficient_evidence", "unsupported_request", "blocked", "failed"
    ]
    mode: Literal["fixed"]
    question: str
    report_ids: list[str] | None
    retrieval_method: Literal["lexical", "semantic"]
    corpus_version: str
    index_version: str
    prompt_version: str
    prompt_sha256: str
    configuration_sha256: str
    code_sha256: str
    created_at_utc: str
    finished_at_utc: str | None = None
    duration_seconds: float | None = None
    evidence: list[RetrievedEvidence]
    selection: CellSelection | None
    calculation: Calculation | None
    calls: list[CallSummary]
    error_code: str | None
