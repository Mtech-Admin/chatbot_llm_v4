"""
Helpers for ingesting policy Q&A files.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

QUESTION_HEADERS = {
    "question",
    "questions",
    "query",
    "faq_question",
    "user_question",
}

ANSWER_HEADERS = {
    "answer",
    "answers",
    "response",
    "faq_answer",
    "bot_answer",
}


def _normalize_header(name: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in name).strip("_")


def _match_header(headers: list[str], candidates: set[str]) -> int:
    normalized = [_normalize_header(h) for h in headers]
    for idx, header in enumerate(normalized):
        if header in candidates:
            return idx
    raise RuntimeError(
        f"Could not find required header in file. Expected one of: {sorted(candidates)}"
    )


def read_policy_rows(file_path: Path) -> list[dict[str, Any]]:
    suffix = file_path.suffix.lower()
    if suffix == ".csv":
        return _read_csv(file_path)
    if suffix in {".xlsx", ".xlsm"}:
        return _read_xlsx(file_path)
    raise ValueError(f"Unsupported file extension: {suffix}")


def _read_csv(file_path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with file_path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        headers = next(reader, None)
        if not headers:
            return rows
        q_idx = _match_header([str(h) for h in headers], QUESTION_HEADERS)
        a_idx = _match_header([str(h) for h in headers], ANSWER_HEADERS)
        for i, row in enumerate(reader, start=2):
            question = row[q_idx].strip() if q_idx < len(row) and row[q_idx] is not None else ""
            answer = row[a_idx].strip() if a_idx < len(row) and row[a_idx] is not None else ""
            rows.append({"question": question, "answer": answer, "row_number": i})
    return rows


def _read_xlsx(file_path: Path) -> list[dict[str, Any]]:
    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise RuntimeError("openpyxl is required for xlsx ingestion. Install: pip install openpyxl") from exc

    wb = load_workbook(file_path, read_only=True, data_only=True)
    ws = wb.active
    headers = [str(c.value).strip() if c.value is not None else "" for c in next(ws.iter_rows(min_row=1, max_row=1))]
    q_idx = _match_header(headers, QUESTION_HEADERS)
    a_idx = _match_header(headers, ANSWER_HEADERS)

    rows: list[dict[str, Any]] = []
    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        question = "" if row[q_idx] is None else str(row[q_idx]).strip()
        answer = "" if row[a_idx] is None else str(row[a_idx]).strip()
        rows.append({"question": question, "answer": answer, "row_number": row_idx})
    wb.close()
    return rows
