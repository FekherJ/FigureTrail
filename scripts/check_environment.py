"""Check the B02 runtime offline, without reading sources or references."""

import json
import platform
import sqlite3
from contextlib import closing
from importlib.metadata import version

import numpy as np


def check_environment() -> dict:
    with closing(sqlite3.connect(":memory:")) as database:
        database.execute("CREATE VIRTUAL TABLE evidence USING fts5(content)")
        database.execute("INSERT INTO evidence VALUES (?)", ("FigureTrail source evidence",))
        matches = database.execute(
            "SELECT content FROM evidence WHERE evidence MATCH ?", ("source",)
        ).fetchall()
        if matches != [("FigureTrail source evidence",)]:
            raise RuntimeError("SQLite FTS5 search check failed.")

    vector = np.array([1.0, 0.0])
    product = float(np.dot(vector, vector))
    if not np.isclose(product, 1.0):
        raise RuntimeError("NumPy dot-product check failed.")

    return {
        "python": platform.python_version(),
        "sqlite": sqlite3.sqlite_version,
        "fts5": True,
        "numpy_dot_product": product,
        "packages": {name: version(name) for name in ("fastapi", "pydantic", "uvicorn", "numpy")},
    }


if __name__ == "__main__":
    print(json.dumps(check_environment(), indent=2))
