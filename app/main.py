"""B02: a local health endpoint without corpus or provider access."""

from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    corpus_version: str | None = None


app = FastAPI(title="FigureTrail", version="0.1.0")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Report process availability; no corpus is loaded at this milestone."""
    return HealthResponse()
