"""
Helpers for ingesting policy Q&A files and structured PDF policy documents.
"""

from __future__ import annotations

import csv
import json
import logging
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

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

logger = logging.getLogger(__name__)


CHUNK_TYPE_CHAPTER_SUMMARY = "chapter_summary"
CHUNK_TYPE_RULE = "rule_chunk"
CHUNK_TYPE_TABLE = "table_chunk"
CHUNK_TYPE_AUTHORITY = "authority_chunk"
CHUNK_TYPE_OO_INDEX = "oo_index"
CHUNK_TYPE_CROSS_REF = "cross_ref"
CHUNK_TYPE_FAQ = "faq_entry"

# Known DMRC HR Compendium chapter letters → titles (updated when a chapter header is found)
_CHAPTER_TITLES: dict[str, str] = {
    "A": "General Administration",
    "B": "Recruitment and Appointment",
    "C": "Pay and Allowances",
    "D": "Travelling Allowance",
    "E": "Medical Attendance",
    "F": "Leave Rules",
    "G": "Provident Fund",
    "H": "House Building Advance",
    "I": "Conveyance Advance",
    "J": "Computer Advance",
    "K": "LTC",
    "L": "Disciplinary Proceedings",
    "M": "Miscellaneous",
}


@dataclass
class PolicyDocChunk:
    chunk_index: int
    content: str
    # Structured metadata fields
    chunk_type: str = CHUNK_TYPE_RULE
    chapter: str | None = None
    chapter_title: str | None = None
    rule_number: str | None = None
    rule_title: str | None = None
    applies_to: list[str] = field(default_factory=list)
    oo_references: list[str] = field(default_factory=list)
    # Legacy / positional fields kept for DOCX compatibility
    section_title: str | None = None
    page_number: int | None = None
    char_start: int = 0
    char_end: int = 0
    metadata: dict[str, Any] | None = None

    def to_metadata_dict(self) -> dict[str, Any]:
        """Return a flat dict suitable for storing in the metadata JSONB column."""
        base = dict(self.metadata or {})
        base["chunk_type"] = self.chunk_type
        if self.chapter:
            base["chapter"] = self.chapter
        if self.chapter_title:
            base["chapter_title"] = self.chapter_title
        if self.rule_number:
            base["rule_number"] = self.rule_number
        if self.rule_title:
            base["rule_title"] = self.rule_title
        if self.applies_to:
            base["applies_to"] = self.applies_to
        if self.oo_references:
            base["oo_references"] = self.oo_references
        return base


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


def deduplicate_faq_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """
    Remove duplicate FAQ rows using a case-insensitive, whitespace-normalised
    question as the deduplication key.  The first occurrence of each unique
    question is kept; subsequent duplicates are silently discarded.

    Returns (deduplicated_rows, duplicate_count).
    """
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    duplicates = 0
    for row in rows:
        question = str(row.get("question", "")).strip()
        if not question:
            continue
        key = re.sub(r"\s+", " ", question.lower())
        if key in seen:
            duplicates += 1
            logger.debug("Duplicate FAQ question skipped (row %s): %r", row.get("row_number"), question[:80])
            continue
        seen.add(key)
        unique.append(row)
    if duplicates:
        logger.info("FAQ deduplication: %s duplicate(s) removed, %s unique rows kept", duplicates, len(unique))
    return unique, duplicates


def read_policy_docx_chunks(
    file_path: Path,
    *,
    chunk_size_chars: int = 2200,
    chunk_overlap_chars: int = 300,
    min_chunk_chars: int = 220,
) -> list[PolicyDocChunk]:
    """
    Parse DOCX and return heading-aware chunks for long-form policy retrieval.
    """
    if file_path.suffix.lower() != ".docx":
        raise ValueError("DOCX ingestion requires a .docx file")

    try:
        from docx import Document
    except ImportError as exc:
        raise RuntimeError("python-docx is required for .docx ingestion. Install: pip install python-docx") from exc

    try:
        sections = _extract_docx_sections_via_python_docx(file_path)
    except Exception as exc:
        logger.warning("python-docx parse failed for %s: %s. Falling back to XML parser.", file_path, str(exc))
        sections = _extract_docx_sections_via_xml(file_path)

    chunks: list[PolicyDocChunk] = []
    chunk_index = 0
    for heading, section_text in sections:
        chunks.extend(
            _chunk_section_text(
                section_text,
                section_title=heading,
                start_index=chunk_index,
                chunk_size_chars=chunk_size_chars,
                chunk_overlap_chars=chunk_overlap_chars,
                min_chunk_chars=min_chunk_chars,
            )
        )
        chunk_index = len(chunks)

    return chunks


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


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _extract_docx_sections_via_python_docx(file_path: Path) -> list[tuple[str, str]]:
    from docx import Document

    doc = Document(str(file_path))
    section_title = "Policy Document"
    sections: list[tuple[str, str]] = []
    current_lines: list[str] = []

    for paragraph in doc.paragraphs:
        raw = paragraph.text or ""
        text = _clean_text(raw)
        if not text:
            continue

        style_name = (paragraph.style.name or "").lower() if paragraph.style else ""
        if "heading" in style_name:
            if current_lines:
                sections.append((section_title, "\n".join(current_lines).strip()))
                current_lines = []
            section_title = text
            continue

        current_lines.append(text)

    if current_lines:
        sections.append((section_title, "\n".join(current_lines).strip()))
    return sections


def _extract_docx_sections_via_xml(file_path: Path) -> list[tuple[str, str]]:
    """
    Fallback parser for malformed .docx archives where python-docx fails
    (e.g., broken rel targets like word/NULL).
    """
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

    with zipfile.ZipFile(file_path, "r") as zf:
        if "word/document.xml" not in zf.namelist():
            raise ValueError("Invalid DOCX: missing word/document.xml")
        doc_root = ET.fromstring(zf.read("word/document.xml"))

        style_to_name: dict[str, str] = {}
        if "word/styles.xml" in zf.namelist():
            try:
                styles_root = ET.fromstring(zf.read("word/styles.xml"))
                for style in styles_root.findall(".//w:style", ns):
                    style_id = style.attrib.get(f"{{{ns['w']}}}styleId", "")
                    name_node = style.find("w:name", ns)
                    if style_id and name_node is not None:
                        style_name = name_node.attrib.get(f"{{{ns['w']}}}val", "")
                        if style_name:
                            style_to_name[style_id] = style_name
            except Exception:
                style_to_name = {}

    section_title = "Policy Document"
    sections: list[tuple[str, str]] = []
    current_lines: list[str] = []

    for paragraph in doc_root.findall(".//w:body/w:p", ns):
        texts = []
        for text_node in paragraph.findall(".//w:t", ns):
            if text_node.text:
                texts.append(text_node.text)
        text = _clean_text("".join(texts))
        if not text:
            continue

        style_id = ""
        style_node = paragraph.find("w:pPr/w:pStyle", ns)
        if style_node is not None:
            style_id = style_node.attrib.get(f"{{{ns['w']}}}val", "")
        style_name = style_to_name.get(style_id, style_id)
        is_heading = style_name.lower().startswith("heading")

        if is_heading:
            if current_lines:
                sections.append((section_title, "\n".join(current_lines).strip()))
                current_lines = []
            section_title = text
            continue

        current_lines.append(text)

    if current_lines:
        sections.append((section_title, "\n".join(current_lines).strip()))

    if not sections:
        raise ValueError("Could not extract readable text from DOCX")
    return sections


def _chunk_section_text(
    section_text: str,
    *,
    section_title: str,
    start_index: int,
    chunk_size_chars: int,
    chunk_overlap_chars: int,
    min_chunk_chars: int,
) -> list[PolicyDocChunk]:
    if not section_text:
        return []

    chunks: list[PolicyDocChunk] = []
    text_len = len(section_text)
    cursor = 0
    local_index = 0
    overlap = max(0, min(chunk_overlap_chars, max(0, chunk_size_chars - 50)))

    while cursor < text_len:
        end = min(text_len, cursor + chunk_size_chars)
        if end < text_len:
            split = section_text.rfind(". ", cursor, end)
            if split > cursor + min_chunk_chars:
                end = split + 1
            else:
                split = section_text.rfind(" ", cursor, end)
                if split > cursor + min_chunk_chars:
                    end = split

        content = section_text[cursor:end].strip()
        if len(content) >= min_chunk_chars or (end >= text_len and content):
            chunks.append(
                PolicyDocChunk(
                    chunk_index=start_index + local_index,
                    content=content,
                    section_title=section_title,
                    char_start=cursor,
                    char_end=end,
                    metadata={"strategy": "heading_aware_char_chunk"},
                )
            )
            local_index += 1

        if end >= text_len:
            break
        cursor = max(cursor + 1, end - overlap)

    return chunks


# ---------------------------------------------------------------------------
# PDF ingestion — structured extraction for DMRC HR Compendium
# ---------------------------------------------------------------------------

# Regex patterns for structured PDF parsing
_RE_CHAPTER = re.compile(
    r"(?:CHAPTER\s+([A-M])\s*[:\-–—]\s*(.+)|^([A-M])\.\s+([A-Z][A-Z\s\-]{4,})$)",
    re.IGNORECASE | re.MULTILINE,
)
_RE_RULE_NUMBER = re.compile(
    r"^(\d{1,2}\.\d{1,2}(?:\.\d{1,2})?)\s+([A-Z][A-Z\s\-/]{3,})",
    re.MULTILINE,
)
_RE_OO_REF = re.compile(
    r"(?:O\.O\.|Office\s+Order|OO)\s*(?:No\.?|Number)?\s*(PP/[\w/]+|\w+/[\w/]+/\d{2,4})",
    re.IGNORECASE,
)
_RE_AUTHORITY = re.compile(
    r"(?:sanction(?:ing)?\s+authority|approv(?:al|ing|ed)\s+(?:authority|by)|"
    r"competent\s+authority|delegat(?:ion|ed)\s+of\s+(?:power|authority)|"
    r"power\s+to\s+(?:sanction|approve)|authoris(?:ed|ation)\s+to\s+(?:grant|approve))",
    re.IGNORECASE,
)
_RE_CROSS_REF = re.compile(
    r"(?:see|refer(?:red)?\s+to|as\s+(?:per|in))\s+(?:Chapter|Ch\.?)\s*([A-M])\b",
    re.IGNORECASE,
)
_RE_APPLIES_TO = re.compile(
    r"\b(executive|non[-\s]executive|consultant|trainee|officer|staff|probationer)\b",
    re.IGNORECASE,
)
_RE_RATE_TABLE = re.compile(
    r"(?:rate|amount|limit|ceiling|per\s+day|per\s+month|Rs\.?|INR|allowance\s+of)\s*[:\-]?\s*\d",
    re.IGNORECASE,
)


def read_policy_pdf_chunks(
    file_path: Path,
    *,
    chunk_size_chars: int = 1800,
    chunk_overlap_chars: int = 200,
    min_chunk_chars: int = 150,
) -> list[PolicyDocChunk]:
    """
    Parse a structured PDF policy document (e.g. DMRC HR Compendium) and return
    semantically typed chunks with rich metadata.

    Chunk types produced:
    - chapter_summary  : one per detected chapter (first ~600 chars)
    - rule_chunk       : numbered rule blocks
    - table_chunk      : extracted tables serialised as JSON
    - authority_chunk  : paragraphs about sanction/approval authority
    - oo_index         : paragraphs carrying O.O. / Office Order references
    - cross_ref        : cross-chapter references

    Requires pdfplumber (pip install pdfplumber).
    """
    if file_path.suffix.lower() != ".pdf":
        raise ValueError("PDF ingestion requires a .pdf file")

    try:
        import pdfplumber
    except ImportError as exc:
        raise RuntimeError(
            "pdfplumber is required for PDF ingestion. Install: pip install pdfplumber"
        ) from exc

    # ---- Pass 1: collect per-page content (text + tables) ----
    raw_pages: list[dict[str, Any]] = []
    with pdfplumber.open(str(file_path)) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            page_text = page.extract_text() or ""
            tables = []
            try:
                for tbl in page.extract_tables() or []:
                    cleaned = _clean_pdf_table(tbl)
                    if cleaned:
                        tables.append(cleaned)
            except Exception:
                pass
            raw_pages.append({"page": page_num, "text": page_text, "tables": tables})

    if not raw_pages:
        raise ValueError("No text could be extracted from PDF")

    # ---- Pass 2: detect chapter boundaries ----
    page_chapter: list[str | None] = [None] * len(raw_pages)
    current_chapter: str | None = None
    for idx, page_data in enumerate(raw_pages):
        text = page_data["text"]
        m = _RE_CHAPTER.search(text)
        if m:
            # Groups: (1,2) from "CHAPTER X: title" form or (3,4) from "X. TITLE" form
            ch_letter = (m.group(1) or m.group(3) or "").upper().strip()
            ch_title_raw = (m.group(2) or m.group(4) or "").strip()
            if ch_letter and ch_letter in "ABCDEFGHIJKLM":
                current_chapter = ch_letter
                if ch_title_raw:
                    _CHAPTER_TITLES[ch_letter] = _clean_text(ch_title_raw)
        page_chapter[idx] = current_chapter

    # ---- Pass 3: build structured chunks ----
    chunks: list[PolicyDocChunk] = []
    chunk_idx = 0
    seen_chapter_summaries: set[str] = set()

    # Buffer for accumulating rule/prose text within a chapter
    prose_buffer: list[str] = []
    prose_page_start: int = 1
    prose_chapter: str | None = None
    prose_rule_number: str | None = None
    prose_rule_title: str | None = None

    def flush_prose_buffer() -> None:
        nonlocal chunk_idx, prose_buffer, prose_rule_number, prose_rule_title
        if not prose_buffer:
            return
        combined = "\n".join(prose_buffer).strip()
        if not combined or len(combined) < min_chunk_chars:
            prose_buffer = []
            prose_rule_number = None
            prose_rule_title = None
            return

        chapter = prose_chapter
        oo_refs = _extract_oo_refs(combined)
        applies = _extract_applies_to(combined)
        chunk_type = _classify_prose_chunk(combined, oo_refs)

        new_chunks = _split_text_into_chunks(
            combined,
            chunk_size_chars=chunk_size_chars,
            chunk_overlap_chars=chunk_overlap_chars,
            min_chunk_chars=min_chunk_chars,
        )
        for part in new_chunks:
            ch_title = _CHAPTER_TITLES.get(chapter or "", None) if chapter else None
            section = (
                f"{prose_rule_number} {prose_rule_title}".strip()
                if prose_rule_number
                else (ch_title or "Policy Section")
            )
            chunks.append(
                PolicyDocChunk(
                    chunk_index=chunk_idx,
                    content=part,
                    chunk_type=chunk_type,
                    chapter=chapter,
                    chapter_title=ch_title,
                    rule_number=prose_rule_number,
                    rule_title=prose_rule_title,
                    applies_to=applies,
                    oo_references=oo_refs,
                    section_title=section,
                    page_number=prose_page_start,
                    metadata={"strategy": "structured_pdf", "source_type": chunk_type},
                )
            )
            chunk_idx += 1

        prose_buffer = []
        prose_rule_number = None
        prose_rule_title = None

    for idx, page_data in enumerate(raw_pages):
        page_num = page_data["page"]
        page_text = page_data["text"]
        page_tables = page_data["tables"]
        ch = page_chapter[idx]

        # --- Chapter summary chunk (once per chapter) ---
        if ch and ch not in seen_chapter_summaries:
            seen_chapter_summaries.add(ch)
            flush_prose_buffer()
            prose_chapter = ch
            ch_title = _CHAPTER_TITLES.get(ch, f"Chapter {ch}")
            summary_text = _extract_chapter_intro(page_text, max_chars=600)
            if summary_text and len(summary_text) >= min_chunk_chars:
                chunks.append(
                    PolicyDocChunk(
                        chunk_index=chunk_idx,
                        content=summary_text,
                        chunk_type=CHUNK_TYPE_CHAPTER_SUMMARY,
                        chapter=ch,
                        chapter_title=ch_title,
                        applies_to=_extract_applies_to(summary_text),
                        oo_references=[],
                        section_title=f"Chapter {ch}: {ch_title}",
                        page_number=page_num,
                        metadata={"strategy": "structured_pdf", "source_type": CHUNK_TYPE_CHAPTER_SUMMARY},
                    )
                )
                chunk_idx += 1

        # --- Table chunks ---
        for tbl in page_tables:
            flush_prose_buffer()
            tbl_json = json.dumps(tbl, ensure_ascii=False)
            tbl_prose = _table_to_prose(tbl)
            content = f"[TABLE from page {page_num}]\n{tbl_prose}\n\nRaw: {tbl_json}"
            if len(content) < min_chunk_chars:
                continue
            ch_title = _CHAPTER_TITLES.get(ch or "", None) if ch else None
            oo_refs = _extract_oo_refs(tbl_prose)
            applies = _extract_applies_to(tbl_prose)
            chunks.append(
                PolicyDocChunk(
                    chunk_index=chunk_idx,
                    content=content,
                    chunk_type=CHUNK_TYPE_TABLE,
                    chapter=ch,
                    chapter_title=ch_title,
                    applies_to=applies,
                    oo_references=oo_refs,
                    section_title=f"Table — {ch_title or 'Policy'} (page {page_num})",
                    page_number=page_num,
                    metadata={"strategy": "structured_pdf", "source_type": CHUNK_TYPE_TABLE},
                )
            )
            chunk_idx += 1

        # --- Parse prose lines for rule blocks, authority, OO refs, cross-refs ---
        lines = page_text.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue

            # Detect a new rule block heading (e.g. "3.1 CASUAL LEAVE")
            rm = _RE_RULE_NUMBER.match(line)
            if rm:
                flush_prose_buffer()
                prose_chapter = ch
                prose_page_start = page_num
                prose_rule_number = rm.group(1)
                prose_rule_title = _clean_text(rm.group(2))
                prose_buffer.append(line)
                i += 1
                continue

            # Detect chapter boundary mid-page — flush and reset
            cm = _RE_CHAPTER.match(line)
            if cm:
                flush_prose_buffer()
                prose_chapter = ch
                prose_page_start = page_num
                i += 1
                continue

            # Add line to prose buffer
            if prose_chapter != ch:
                flush_prose_buffer()
                prose_chapter = ch
                prose_page_start = page_num

            prose_buffer.append(line)

            # Auto-flush when buffer gets large enough to split
            if sum(len(l) for l in prose_buffer) >= chunk_size_chars * 2:
                flush_prose_buffer()
                prose_chapter = ch
                prose_page_start = page_num

            i += 1

    flush_prose_buffer()

    # ---- Pass 4: promote authority and cross-ref chunks ----
    for c in chunks:
        if c.chunk_type == CHUNK_TYPE_RULE:
            if _RE_AUTHORITY.search(c.content):
                c.chunk_type = CHUNK_TYPE_AUTHORITY
                if c.metadata:
                    c.metadata["source_type"] = CHUNK_TYPE_AUTHORITY
            elif _RE_CROSS_REF.search(c.content) and not _RE_RULE_NUMBER.search(c.content):
                c.chunk_type = CHUNK_TYPE_CROSS_REF
                if c.metadata:
                    c.metadata["source_type"] = CHUNK_TYPE_CROSS_REF

    # Re-index after all mutations
    for new_idx, c in enumerate(chunks):
        c.chunk_index = new_idx

    logger.info(
        "PDF structured ingestion: %s total chunks from %s pages",
        len(chunks),
        len(raw_pages),
    )
    _log_chunk_type_summary(chunks)
    return chunks


# ---------------------------------------------------------------------------
# PDF helper functions
# ---------------------------------------------------------------------------

def _clean_pdf_table(raw_table: list[list[Any]]) -> list[list[str]]:
    """Normalise a pdfplumber raw table (lists of Any) to lists of str, drop empty rows."""
    cleaned: list[list[str]] = []
    for row in raw_table:
        cells = [str(c).strip() if c is not None else "" for c in row]
        if any(cells):
            cleaned.append(cells)
    return cleaned


def _table_to_prose(table: list[list[str]]) -> str:
    """Convert a 2-D table to a readable prose representation for embedding."""
    if not table:
        return ""
    header = table[0] if table else []
    lines: list[str] = []
    for row in table[1:]:
        parts = []
        for col_idx, cell in enumerate(row):
            if not cell:
                continue
            col_name = header[col_idx] if col_idx < len(header) else f"Col{col_idx}"
            parts.append(f"{col_name}: {cell}")
        if parts:
            lines.append("; ".join(parts))
    return "\n".join(lines)


def _extract_chapter_intro(page_text: str, *, max_chars: int = 600) -> str:
    """Return the opening prose of a chapter page, skipping the heading line."""
    lines = [l.strip() for l in page_text.splitlines() if l.strip()]
    # Skip lines that are purely the chapter heading
    start = 0
    for i, line in enumerate(lines):
        if _RE_CHAPTER.search(line):
            start = i + 1
            break
    intro_lines = lines[start:]
    combined = " ".join(intro_lines)
    return combined[:max_chars].strip()


def _extract_oo_refs(text: str) -> list[str]:
    return list(dict.fromkeys(_RE_OO_REF.findall(text)))


def _extract_applies_to(text: str) -> list[str]:
    found = [m.lower().replace(" ", "-") for m in _RE_APPLIES_TO.findall(text)]
    # Normalise
    norm: list[str] = []
    seen: set[str] = set()
    mapping = {"non-executive": "non-executive", "nonexecutive": "non-executive"}
    for f in found:
        key = mapping.get(f, f)
        if key not in seen:
            norm.append(key)
            seen.add(key)
    return norm


def _classify_prose_chunk(text: str, oo_refs: list[str]) -> str:
    """Classify a prose chunk into a CHUNK_TYPE_* constant."""
    if oo_refs:
        return CHUNK_TYPE_OO_INDEX
    if _RE_AUTHORITY.search(text):
        return CHUNK_TYPE_AUTHORITY
    if _RE_RATE_TABLE.search(text):
        return CHUNK_TYPE_RULE  # rate info in prose → keep as rule_chunk so it's searchable
    return CHUNK_TYPE_RULE


def _split_text_into_chunks(
    text: str,
    *,
    chunk_size_chars: int,
    chunk_overlap_chars: int,
    min_chunk_chars: int,
) -> list[str]:
    """Split a block of text into overlapping chunks, breaking on sentence/word boundaries."""
    parts: list[str] = []
    text_len = len(text)
    cursor = 0
    overlap = max(0, min(chunk_overlap_chars, chunk_size_chars - 50))

    while cursor < text_len:
        end = min(text_len, cursor + chunk_size_chars)
        if end < text_len:
            split = text.rfind(". ", cursor, end)
            if split > cursor + min_chunk_chars:
                end = split + 1
            else:
                split = text.rfind(" ", cursor, end)
                if split > cursor + min_chunk_chars:
                    end = split

        part = text[cursor:end].strip()
        if len(part) >= min_chunk_chars or (end >= text_len and part):
            parts.append(part)

        if end >= text_len:
            break
        cursor = max(cursor + 1, end - overlap)

    return parts


def _log_chunk_type_summary(chunks: list[PolicyDocChunk]) -> None:
    from collections import Counter
    counts: Counter[str] = Counter(c.chunk_type for c in chunks)
    chapter_counts: Counter[str] = Counter(c.chapter for c in chunks if c.chapter)
    logger.info("Chunk type distribution: %s", dict(counts))
    logger.info("Chunks per chapter: %s", dict(sorted(chapter_counts.items())))


# ---------------------------------------------------------------------------
# Structured JSON Knowledge Base ingestion
# ---------------------------------------------------------------------------

def read_policy_kb_json_chunks(file_path: Path) -> list[PolicyDocChunk]:
    """
    Parse a pre-built structured JSON knowledge base (DMRC HR Compendium format)
    and return fully typed PolicyDocChunk objects ready for pgvector ingestion.

    Expected JSON schema (top-level keys):
        metadata, chapters, master_authority_index,
        master_oo_index, master_cross_reference, leave_types_complete (optional)

    Each chapter contains:
        summary_chunk        → 1 × chapter_summary chunk
        rules[]              → 1 × rule_chunk per rule
        tables[]             → 1 × table_chunk per table
        authority_index[]    → authority_chunk (grouped per chapter)
        office_order_index[] → oo_index chunk (grouped per chapter)
        cross_references[]   → cross_ref chunk (grouped per chapter)

    Master-level indexes produce additional cross-chapter chunks.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Knowledge-base JSON not found: {file_path}")

    with file_path.open("r", encoding="utf-8") as fh:
        kb: dict[str, Any] = json.load(fh)

    chunks: list[PolicyDocChunk] = []
    idx = 0

    chapters: dict[str, Any] = kb.get("chapters", {})

    # Update the internal chapter-title map from the loaded KB
    for ch_letter, ch_data in chapters.items():
        title = ch_data.get("chapter_title", "")
        if title:
            _CHAPTER_TITLES[ch_letter] = title

    # ── Per-chapter chunks ──────────────────────────────────────────────────
    for ch_letter, ch_data in chapters.items():
        ch_title = ch_data.get("chapter_title", _CHAPTER_TITLES.get(ch_letter, f"Chapter {ch_letter}"))
        page_range = ch_data.get("page_range", "")

        # 1. Chapter summary
        summary_text = ch_data.get("summary_chunk", "") or ch_data.get("summary", "")
        if summary_text:
            chunks.append(PolicyDocChunk(
                chunk_index=idx,
                content=summary_text.strip(),
                chunk_type=CHUNK_TYPE_CHAPTER_SUMMARY,
                chapter=ch_letter,
                chapter_title=ch_title,
                applies_to=[],
                oo_references=[],
                section_title=f"Chapter {ch_letter}: {ch_title}",
                page_number=_parse_page_start(page_range),
                metadata={"strategy": "structured_kb_json", "source_type": CHUNK_TYPE_CHAPTER_SUMMARY,
                          "page_range": page_range, "key_topics": ch_data.get("key_topics", [])},
            ))
            idx += 1

        # 2. Rule chunks
        for rule in ch_data.get("rules", []):
            rule_content = _build_rule_content(rule)
            if not rule_content:
                continue
            oo_refs = [_normalise_oo(o) for o in rule.get("office_orders", []) if o]
            applies = rule.get("applies_to", [])
            chunks.append(PolicyDocChunk(
                chunk_index=idx,
                content=rule_content,
                chunk_type=CHUNK_TYPE_RULE,
                chapter=ch_letter,
                chapter_title=ch_title,
                rule_number=rule.get("rule_id", ""),
                rule_title=rule.get("rule_title", ""),
                applies_to=applies,
                oo_references=oo_refs,
                section_title=f"{rule.get('rule_id','')} {rule.get('rule_title','')}".strip(),
                page_number=_parse_page_start(page_range),
                metadata={"strategy": "structured_kb_json", "source_type": CHUNK_TYPE_RULE,
                          "approval_authority": rule.get("approval_authority", ""),
                          "amounts_or_limits": rule.get("amounts_or_limits", ""),
                          "key_points": rule.get("key_points", [])},
            ))
            idx += 1

        # 3. Table chunks
        for table in ch_data.get("tables", []):
            table_content = _build_table_content(table, ch_letter, ch_title)
            if not table_content:
                continue
            chunks.append(PolicyDocChunk(
                chunk_index=idx,
                content=table_content,
                chunk_type=CHUNK_TYPE_TABLE,
                chapter=ch_letter,
                chapter_title=ch_title,
                section_title=f"Table: {table.get('table_title', '')}",
                page_number=_parse_page_start(page_range),
                metadata={"strategy": "structured_kb_json", "source_type": CHUNK_TYPE_TABLE,
                          "table_id": table.get("table_id", ""),
                          "table_title": table.get("table_title", "")},
            ))
            idx += 1

        # 4. Authority index chunk (one chunk per chapter grouping all entries)
        auth_entries = ch_data.get("authority_index", [])
        if auth_entries:
            auth_content = _build_authority_content(auth_entries, ch_letter, ch_title)
            chunks.append(PolicyDocChunk(
                chunk_index=idx,
                content=auth_content,
                chunk_type=CHUNK_TYPE_AUTHORITY,
                chapter=ch_letter,
                chapter_title=ch_title,
                section_title=f"Approval Authority Index — Chapter {ch_letter}: {ch_title}",
                page_number=_parse_page_start(page_range),
                metadata={"strategy": "structured_kb_json", "source_type": CHUNK_TYPE_AUTHORITY},
            ))
            idx += 1

        # 5. Office Order index chunk (one chunk per chapter)
        oo_entries = ch_data.get("office_order_index", [])
        if oo_entries:
            oo_content = _build_oo_index_content(oo_entries, ch_letter, ch_title)
            oo_refs = [_normalise_oo(e.get("oo_number", "")) for e in oo_entries if e.get("oo_number")]
            chunks.append(PolicyDocChunk(
                chunk_index=idx,
                content=oo_content,
                chunk_type=CHUNK_TYPE_OO_INDEX,
                chapter=ch_letter,
                chapter_title=ch_title,
                oo_references=oo_refs,
                section_title=f"Office Order Index — Chapter {ch_letter}: {ch_title}",
                page_number=_parse_page_start(page_range),
                metadata={"strategy": "structured_kb_json", "source_type": CHUNK_TYPE_OO_INDEX},
            ))
            idx += 1

        # 6. Cross-reference chunk (one chunk per chapter)
        xrefs = ch_data.get("cross_references", [])
        if xrefs:
            xref_content = _build_xref_content(xrefs, ch_letter, ch_title)
            chunks.append(PolicyDocChunk(
                chunk_index=idx,
                content=xref_content,
                chunk_type=CHUNK_TYPE_CROSS_REF,
                chapter=ch_letter,
                chapter_title=ch_title,
                section_title=f"Cross-References — Chapter {ch_letter}: {ch_title}",
                page_number=_parse_page_start(page_range),
                metadata={"strategy": "structured_kb_json", "source_type": CHUNK_TYPE_CROSS_REF},
            ))
            idx += 1

    # ── Master index chunks ─────────────────────────────────────────────────

    # Master authority index — consolidated across all chapters
    master_auth = kb.get("master_authority_index", [])
    if master_auth:
        lines = ["DMRC HR Compendium — Master Approval Authority Index (all chapters)\n"]
        for entry in master_auth:
            chapters_str = entry.get("chapters", entry.get("chapter", ""))
            if isinstance(chapters_str, list):
                chapters_str = ", ".join(chapters_str)
            lines.append(f"Action: {entry.get('action','')}")
            lines.append(f"  Authority: {entry.get('authority','')}")
            lines.append(f"  Chapters: {chapters_str}\n")
        chunks.append(PolicyDocChunk(
            chunk_index=idx,
            content="\n".join(lines).strip(),
            chunk_type=CHUNK_TYPE_AUTHORITY,
            section_title="Master Approval Authority Index",
            metadata={"strategy": "structured_kb_json", "source_type": CHUNK_TYPE_AUTHORITY, "scope": "master"},
        ))
        idx += 1

    # Master OO index — all office orders in one searchable chunk
    master_oo = kb.get("master_oo_index", [])
    if master_oo:
        lines = ["DMRC HR Compendium — Master Office Order Index\n"]
        for entry in master_oo:
            lines.append(
                f"OO: {entry.get('oo_number','')}  Date: {entry.get('date','')}  "
                f"Chapter: {entry.get('chapter','')}  Subject: {entry.get('subject','')}  "
                f"Rule: {entry.get('rule_ref','')}"
            )
        oo_refs = [_normalise_oo(e.get("oo_number", "")) for e in master_oo if e.get("oo_number")]
        chunks.append(PolicyDocChunk(
            chunk_index=idx,
            content="\n".join(lines).strip(),
            chunk_type=CHUNK_TYPE_OO_INDEX,
            oo_references=oo_refs,
            section_title="Master Office Order Index",
            metadata={"strategy": "structured_kb_json", "source_type": CHUNK_TYPE_OO_INDEX, "scope": "master"},
        ))
        idx += 1

    # Master cross-reference index
    master_xref = kb.get("master_cross_reference", [])
    if master_xref:
        lines = ["DMRC HR Compendium — Master Cross-Reference Index\n"]
        for entry in master_xref:
            lines.append(
                f"Rule {entry.get('from_rule','')} (Ch.{entry.get('source_chapter','')}) → "
                f"Chapter {entry.get('to_chapter','')} Rule {entry.get('to_rule','')}: "
                f"{entry.get('relationship','')}"
            )
        chunks.append(PolicyDocChunk(
            chunk_index=idx,
            content="\n".join(lines).strip(),
            chunk_type=CHUNK_TYPE_CROSS_REF,
            section_title="Master Cross-Reference Index",
            metadata={"strategy": "structured_kb_json", "source_type": CHUNK_TYPE_CROSS_REF, "scope": "master"},
        ))
        idx += 1

    # Special consolidated leave chunk (if present)
    leave_block = kb.get("leave_types_complete", {})
    if leave_block:
        summary_for_bot = leave_block.get("summary_for_chatbot", "")
        if summary_for_bot:
            chunks.append(PolicyDocChunk(
                chunk_index=idx,
                content=summary_for_bot.strip(),
                chunk_type=CHUNK_TYPE_CHAPTER_SUMMARY,
                chapter="F",
                chapter_title=_CHAPTER_TITLES.get("F", "Leave Rules"),
                section_title="All DMRC Leave Types — Quick Reference",
                metadata={"strategy": "structured_kb_json", "source_type": CHUNK_TYPE_CHAPTER_SUMMARY,
                          "scope": "leave_types_complete",
                          "leave_count": leave_block.get("count", 0),
                          "leave_types": leave_block.get("types", [])},
            ))
            idx += 1

    # Re-index to be safe
    for new_idx, chunk in enumerate(chunks):
        chunk.chunk_index = new_idx

    logger.info("JSON KB structured ingestion: %s total chunks", len(chunks))
    _log_chunk_type_summary(chunks)
    return chunks


def read_dmrc_hr_rag_chunks_json(file_path: Path) -> list[PolicyDocChunk]:
    """
    Parse `dmrc_hr_chunks.json` — pre-split RAG chunks (rule, table, indexes, etc.).

    Chunk `chunk_type` values match the HR Compendium README (e.g. ``rule``,
    ``leave_types_index``), not the legacy PDF/KB labels (``rule_chunk``).
    """
    if not file_path.exists():
        raise FileNotFoundError(f"RAG chunks JSON not found: {file_path}")

    with file_path.open("r", encoding="utf-8") as fh:
        data: dict[str, Any] = json.load(fh)

    raw_chunks = data.get("chunks") or []
    out: list[PolicyDocChunk] = []

    for idx, item in enumerate(raw_chunks):
        content = str(item.get("content", "")).strip()
        if not content:
            continue
        meta = dict(item.get("metadata") or {})
        chunk_id = item.get("chunk_id")
        if chunk_id:
            meta["chunk_id"] = str(chunk_id)
        ctype = str(item.get("chunk_type", "rule")).strip() or "rule"
        rule_id = meta.get("rule_id")
        if rule_id:
            rule_id = str(rule_id)
        page_range = meta.get("page_range")
        page_num: int | None = None
        if isinstance(page_range, str) and page_range.strip():
            page_num = _parse_page_start(page_range)

        chapter = item.get("chapter")
        chapter = str(chapter).strip() if chapter not in (None, "") else None

        out.append(
            PolicyDocChunk(
                chunk_index=idx,
                content=content,
                chunk_type=ctype,
                chapter=chapter,
                chapter_title=item.get("chapter_title"),
                rule_number=rule_id or None,
                rule_title=None,
                applies_to=list(meta.get("applies_to") or []),
                oo_references=list(meta.get("office_orders") or []),
                section_title=item.get("title"),
                page_number=page_num,
                metadata=meta,
            )
        )

    for new_idx, chunk in enumerate(out):
        chunk.chunk_index = new_idx

    logger.info("RAG chunks JSON ingestion: %s total chunks from %s", len(out), file_path)
    _log_chunk_type_summary(out)
    return out


# ---------------------------------------------------------------------------
# JSON KB helper functions
# ---------------------------------------------------------------------------

def _build_rule_content(rule: dict[str, Any]) -> str:
    """Assemble rich text content for a rule chunk."""
    parts: list[str] = []
    rule_id = rule.get("rule_id", "")
    rule_title = rule.get("rule_title", "")
    if rule_id or rule_title:
        parts.append(f"Rule {rule_id} — {rule_title}".strip(" —"))

    applies_to = rule.get("applies_to", [])
    if applies_to:
        parts.append(f"Applies to: {', '.join(applies_to)}")

    authority = rule.get("approval_authority", "")
    if authority:
        parts.append(f"Approval Authority: {authority}")

    amounts = rule.get("amounts_or_limits", "")
    if amounts:
        parts.append(f"Amounts/Limits: {amounts}")

    content = (rule.get("content", "") or "").strip()
    if content:
        parts.append(content)

    key_points = rule.get("key_points", [])
    if key_points:
        parts.append("Key Points:")
        for pt in key_points:
            parts.append(f"  • {pt}")

    oo_list = rule.get("office_orders", [])
    if oo_list:
        parts.append(f"Office Orders: {'; '.join(oo_list)}")

    return "\n".join(parts).strip()


def _build_table_content(table: dict[str, Any], ch_letter: str, ch_title: str) -> str:
    """Assemble rich text + JSON for a table chunk."""
    parts: list[str] = []
    tid = table.get("table_id", "")
    ttitle = table.get("table_title", "")
    desc = table.get("description", "")
    data = table.get("data", [])

    header = f"Table {tid} — {ttitle}" if tid else ttitle
    parts.append(f"{header}\nChapter {ch_letter}: {ch_title}")
    if desc:
        parts.append(desc)

    # Prose representation (rows as key: value)
    if data and isinstance(data, list) and isinstance(data[0], dict):
        for row in data:
            row_parts = [f"{k}: {v}" for k, v in row.items() if v not in (None, "", [])]
            if row_parts:
                parts.append("; ".join(row_parts))

    # Raw JSON for exact-match retrieval
    parts.append(f"\nRaw data: {json.dumps(data, ensure_ascii=False)}")
    return "\n".join(parts).strip()


def _build_authority_content(entries: list[dict[str, Any]], ch_letter: str, ch_title: str) -> str:
    """Assemble authority index chunk content."""
    lines = [f"Approval Authority Index — Chapter {ch_letter}: {ch_title}\n"]
    for entry in entries:
        lines.append(f"Action: {entry.get('action', '')}")
        lines.append(f"  Sanctioning Authority: {entry.get('authority', '')}")
        rule_ref = entry.get("rule_ref", "")
        if rule_ref:
            lines.append(f"  Rule Reference: {rule_ref}")
        lines.append("")
    return "\n".join(lines).strip()


def _build_oo_index_content(entries: list[dict[str, Any]], ch_letter: str, ch_title: str) -> str:
    """Assemble office order index chunk content."""
    lines = [f"Office Order Index — Chapter {ch_letter}: {ch_title}\n"]
    for entry in entries:
        oo = entry.get("oo_number", "")
        date = entry.get("date", "")
        subject = entry.get("subject", "")
        rule_ref = entry.get("rule_ref", "")
        lines.append(f"{oo}  [{date}]  Subject: {subject}  Rule: {rule_ref}")
    return "\n".join(lines).strip()


def _build_xref_content(entries: list[dict[str, Any]], ch_letter: str, ch_title: str) -> str:
    """Assemble cross-reference chunk content."""
    lines = [f"Cross-References — Chapter {ch_letter}: {ch_title}\n"]
    for entry in entries:
        from_rule = entry.get("from_rule", "")
        to_ch = entry.get("to_chapter", "")
        to_rule = entry.get("to_rule", "")
        rel = entry.get("relationship", "")
        lines.append(f"Rule {from_rule} → Chapter {to_ch}, Rule {to_rule}: {rel}")
    return "\n".join(lines).strip()


def _parse_page_start(page_range: str) -> int | None:
    """Extract start page number from a range like '165-186'."""
    if not page_range:
        return None
    m = re.match(r"(\d+)", page_range.strip())
    return int(m.group(1)) if m else None


def _normalise_oo(oo_string: str) -> str:
    """Strip 'O.O. No. ' prefix for compact storage, keeping the number."""
    return re.sub(r"^O\.O\.\s*No\.\s*", "", (oo_string or "").strip())
