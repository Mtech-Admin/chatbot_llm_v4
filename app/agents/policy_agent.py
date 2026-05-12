"""
Policy FAQ Agent — DMRC HR Compendium RAG with query routing (README flow).

Retrieval: classify intent → pin index chunks when useful → hybrid vector+lexical
search (sentence-transformers / hash fallback in store) → rerank by preferred
chunk types → optional exact-term pass → LLM with citations.
"""

from __future__ import annotations

import logging
import re

from app.agents.base import BaseAgent
from app.config import get_llm_client, get_model_name, settings
from app.knowledge.ingest import CHUNK_TYPE_FAQ
from app.knowledge.store import PolicyChunkMatch, policy_store
from app.orchestrator.state import OrchestratorState

logger = logging.getLogger(__name__)

# Intent labels align with files/README.md — "Query Routing Logic"
ROUTING_INTENT_CITATION = "citation"
ROUTING_INTENT_LISTING = "listing"
ROUTING_INTENT_COMPLEX = "complex"
ROUTING_INTENT_AUTHORITY = "authority"
ROUTING_INTENT_RATE = "rate"
ROUTING_INTENT_OVERVIEW = "overview"
ROUTING_INTENT_SPECIFIC = "specific"

QUERY_ROUTING: dict[str, list[str]] = {
    ROUTING_INTENT_LISTING: [
        "leave_types_index",
        "financial_limits_index",
        "chapter_summary",
        "document_summary",
    ],
    ROUTING_INTENT_SPECIFIC: ["rule", "table", "chapter_authority", "cross_reference"],
    ROUTING_INTENT_AUTHORITY: ["authority_index", "chapter_authority", "rule"],
    ROUTING_INTENT_RATE: ["table", "financial_limits_index", "rule"],
    ROUTING_INTENT_COMPLEX: ["cross_reference", "rule", "chapter_summary"],
    ROUTING_INTENT_CITATION: ["oo_index", "rule"],
    ROUTING_INTENT_OVERVIEW: ["chapter_summary", "document_summary"],
}

_ROUTING_INTENT_RULES: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"(?:O\.O\.|office\s+order|OO\s+no\.?|PP/\d|PP-\d|order\s+no\.?\s*PP|"
            r"circular\s+no)",
            re.IGNORECASE,
        ),
        ROUTING_INTENT_CITATION,
    ),
    (
        re.compile(
            r"\b("
            r"how\s+many\s+types|how\s+many\s+kinds|types\s+of|kinds\s+of|"
            r"list\s+(?:all\s+)?(?:the\s+)?(?:types|kinds|leave|advances?)|"
            r"what\s+are\s+(?:all\s+)?(?:the\s+)?(?:types|kinds)|enumerate"
            r")\b",
            re.IGNORECASE,
        ),
        ROUTING_INTENT_LISTING,
    ),
    (
        re.compile(
            r"\b(compare|difference\s+between|vs\.?|versus|either\s+or|\band\b.+\band\b)\b",
            re.IGNORECASE,
        ),
        ROUTING_INTENT_COMPLEX,
    ),
    (
        re.compile(
            r"\b(who\s+(?:can\s+)?(?:approve|sanction|grant|authoris|authorize)|"
            r"approval\s+authority|sanctioning\s+authority|competent\s+authority|"
            r"who\s+is\s+(?:the\s+)?authority|power\s+to\s+(?:grant|sanction|approve)|"
            r"delegat(?:ion|ed)\s+of\s+power)\b",
            re.IGNORECASE,
        ),
        ROUTING_INTENT_AUTHORITY,
    ),
    (
        re.compile(
            r"\b(how\s+much|rate|amount|per\s+day|per\s+month|ceiling|limit|"
            r"da\s+rate|daily\s+allowance|slab|rupee|rs\.?|inr|tariff|"
            r"quantum|entitlement|entitled\s+to)\b",
            re.IGNORECASE,
        ),
        ROUTING_INTENT_RATE,
    ),
    (
        re.compile(
            r"\b(what\s+is\s+chapter|overview|introduce|introduction|explain\s+chapter|"
            r"summarize|summary|about\s+chapter|tell\s+me\s+about\s+chapter|"
            r"what\s+does\s+chapter|chapters?\s+in\s+(?:the\s+)?(?:document|compendium)|"
            r"what\s+does\s+(?:the\s+)?(?:hr\s+)?compendium)"
            r"\b",
            re.IGNORECASE,
        ),
        ROUTING_INTENT_OVERVIEW,
    ),
]

POLICY_AGENT_PROMPT = """You are an HR Policy Assistant for Delhi Metro Rail Corporation (DMRC).
Answer using ONLY the DMRC HR Compendium excerpts in the user message (November 2023 edition).
Rules:
1. If the answer is in the context, state it accurately and cite rule id / chapter / page range when present in the excerpt metadata lines.
2. If you are unsure or the information is not in the context, say it is not covered in the provided sections and suggest contacting HR.
3. For listing questions (e.g. types of leave), give a complete numbered list when the context lists items.
4. For eligibility, mention conditions or exceptions shown in the context.
5. For amounts and limits, note if the context says figures are subject to revision.
6. End with a Reference line when possible, e.g. Reference: Rule F.3.10, Chapter F, pages 165-186 (from context).
7. If an "Official HR Compendium PDF" URL appears in the user message, end your answer with a final line:
   Full document: <that exact URL> (so users can open the PDF)."""


class PolicyAgent(BaseAgent):
    def __init__(self):
        super().__init__("policy_agent", POLICY_AGENT_PROMPT)

    @staticmethod
    def _reference_pdf_url() -> str:
        return (settings.HR_COMPENDIUM_PDF_URL or "").strip()

    @staticmethod
    def _append_reference_document_link(message: str) -> str:
        url = PolicyAgent._reference_pdf_url()
        if not url:
            return message
        if url in message:
            return message
        return f"{message.rstrip()}\n\nFull document: {url}"

    @staticmethod
    def _kb_stats_source(kb_stats: dict) -> dict:
        row: dict = {"type": "policy_kb_stats", "kb_stats": kb_stats}
        url = PolicyAgent._reference_pdf_url()
        if url:
            row["reference_document_url"] = url
            row["reference_document_label"] = "DMRC HR Compendium (PDF, Nov 2023)"
        return row

    async def process(self, state: OrchestratorState) -> OrchestratorState:
        try:
            kb_stats = policy_store.stats()
            logger.info(
                "Policy agent KB stats for employee %s: %s",
                state.employee_id,
                kb_stats,
            )
            has_chunks = kb_stats.get("policy_chunk_count", 0) > 0
            if not has_chunks:
                state.response_message = (
                    "I am unable to find policy information right now. "
                    "Please try again in a little while or contact HR."
                )
                state.sources = [{"type": "policy_kb", "kb_stats": kb_stats}]
                return state

            if not settings.POLICY_RAG_ENABLED:
                state.response_message = self._general_fallback_response()
                state.sources = [{"type": "policy_kb_stats", "kb_stats": kb_stats}]
                return state

            retrieval_query = self._normalize_policy_query(state.user_message)
            top_k_final = max(1, settings.POLICY_RAG_TOP_K)
            doc_key_filter: str | None = settings.POLICY_RAG_DOCUMENT_KEY.strip() or None

            routing_intent = self._classify_routing_intent(retrieval_query)
            preferred_types = QUERY_ROUTING.get(routing_intent, QUERY_ROUTING[ROUTING_INTENT_SPECIFIC])
            logger.info(
                "Policy RAG routing employee=%s intent=%s preferred_types=%s doc_key=%s",
                state.employee_id,
                routing_intent,
                preferred_types,
                doc_key_filter or "all",
            )

            pool_k = max(50, top_k_final * 10)
            pinned = self._pinned_index_matches(
                routing_intent,
                retrieval_query,
                document_key=doc_key_filter,
            )
            broad_matches = policy_store.search_chunks(
                retrieval_query,
                top_k=pool_k,
                document_key=doc_key_filter,
            )
            merged = self._dedupe_chunk_matches([*pinned, *broad_matches])
            reranked = self._rerank_by_preferred_types(merged, preferred_types)

            specific_terms = self._specific_query_terms(retrieval_query)
            exact_matches: list[PolicyChunkMatch] = []
            if specific_terms:
                exact_matches = policy_store.search_chunks_by_exact_terms(
                    retrieval_query,
                    specific_terms,
                    top_k=top_k_final,
                    document_key=doc_key_filter,
                )
                logger.info(
                    "RAG exact-term lookup employee=%s terms=%s found=%s",
                    state.employee_id,
                    specific_terms,
                    len(exact_matches),
                )

            seen: set[str] = set()
            ordered: list[PolicyChunkMatch] = []
            for m in (*pinned, *exact_matches, *reranked):
                key = self._chunk_dedupe_key(m)
                if key in seen:
                    continue
                seen.add(key)
                ordered.append(m)

            all_matches = self._select_relevant_doc_matches(
                query=retrieval_query,
                matches=ordered,
                top_k=top_k_final,
            )
            self._log_doc_retrieval(state.employee_id, retrieval_query, all_matches)

            confidence_floor = max(0.15, settings.POLICY_RAG_DOC_CONFIDENCE_THRESHOLD)
            best_score = all_matches[0].combined_score if all_matches else 0.0
            logger.info(
                "Policy unified retrieval for employee %s: best_score=%.4f threshold=%.4f",
                state.employee_id,
                best_score,
                confidence_floor,
            )

            if not all_matches or best_score < confidence_floor:
                state.response_message = self._general_fallback_response()
                state.sources = [{"type": "policy_kb_stats", "kb_stats": kb_stats}]
                return state

            top = all_matches[0]
            top_chunk_type = (top.metadata or {}).get("chunk_type", "")

            if top_chunk_type == CHUNK_TYPE_FAQ:
                faq_question = (top.metadata or {}).get("question", top.section_title or "")
                q_similarity = self._question_similarity(retrieval_query, faq_question)
                logger.info(
                    "FAQ question similarity for employee %s: user_q=%r faq_q=%r similarity=%.4f",
                    state.employee_id,
                    retrieval_query,
                    faq_question,
                    q_similarity,
                )
                if q_similarity >= 0.72:
                    answer = self._extract_faq_answer(top.content)
                    state.response_message = self._append_reference_document_link(answer)
                    state.sources = [
                        {
                            "type": "policy_faq_chunk",
                            "document_key": top.document_key,
                            "section_title": top.section_title,
                            "chunk_index": top.chunk_index,
                            "chunk_id": (top.metadata or {}).get("chunk_id"),
                            "vector_score": round(top.vector_score, 4),
                            "keyword_score": round(top.keyword_score, 4),
                            "combined_score": round(top.combined_score, 4),
                            "question_similarity": round(q_similarity, 4),
                            "source_file": (top.metadata or {}).get("source_file", top.source_file),
                            "row_number": (top.metadata or {}).get("row_number"),
                            "kb_stats": kb_stats,
                        },
                        self._kb_stats_source(kb_stats),
                    ]
                    state.routing_agent = "policy_agent"
                    return state

            state.response_message = await self._build_grounded_policy_answer(state, all_matches)
            state.sources = [
                {
                    "type": "policy_doc_chunk",
                    "document_key": m.document_key,
                    "document_title": m.document_title,
                    "source_file": m.source_file,
                    "chunk_index": m.chunk_index,
                    "chunk_id": (m.metadata or {}).get("chunk_id"),
                    "section_title": m.section_title,
                    "page_number": m.page_number,
                    "chunk_type": (m.metadata or {}).get("chunk_type"),
                    "chapter": (m.metadata or {}).get("chapter"),
                    "rule_number": (m.metadata or {}).get("rule_id")
                    or (m.metadata or {}).get("rule_number"),
                    "page_range": (m.metadata or {}).get("page_range"),
                    "vector_score": round(m.vector_score, 4),
                    "keyword_score": round(m.keyword_score, 4),
                    "combined_score": round(m.combined_score, 4),
                }
                for m in all_matches[:5]
            ] + [self._kb_stats_source(kb_stats)]
            state.routing_agent = "policy_agent"
            logger.info(
                "Policy agent used LLM grounding for employee %s score=%.4f intent=%s",
                state.employee_id,
                best_score,
                routing_intent,
            )
            return state

        except Exception as exc:
            logger.error("Policy agent error for employee %s: %s", state.employee_id, str(exc), exc_info=True)
            state.response_message = (
                "I am unable to retrieve policy details at the moment. "
                "Please try again shortly."
            )
            return state

    @staticmethod
    def _classify_routing_intent(query: str) -> str:
        for pattern, intent in _ROUTING_INTENT_RULES:
            if pattern.search(query):
                return intent
        return ROUTING_INTENT_SPECIFIC

    @staticmethod
    def _chunk_dedupe_key(m: PolicyChunkMatch) -> str:
        meta = m.metadata or {}
        cid = meta.get("chunk_id")
        if cid:
            return f"id:{cid}"
        return f"{m.document_key}:{m.chunk_index}"

    @staticmethod
    def _dedupe_chunk_matches(matches: list[PolicyChunkMatch]) -> list[PolicyChunkMatch]:
        seen: set[str] = set()
        out: list[PolicyChunkMatch] = []
        for m in matches:
            key = PolicyAgent._chunk_dedupe_key(m)
            if key in seen:
                continue
            seen.add(key)
            out.append(m)
        return out

    @staticmethod
    def _rerank_by_preferred_types(
        matches: list[PolicyChunkMatch],
        preferred_types: list[str],
    ) -> list[PolicyChunkMatch]:
        order = {t: i for i, t in enumerate(preferred_types)}

        def sort_key(m: PolicyChunkMatch) -> tuple[int, float]:
            ct = (m.metadata or {}).get("chunk_type") or ""
            tier = order.get(ct, 1_000)
            return tier, -m.combined_score

        return sorted(matches, key=sort_key)

    def _pinned_index_matches(
        self,
        intent: str,
        query: str,
        *,
        document_key: str | None,
    ) -> list[PolicyChunkMatch]:
        """Fetch high-value index chunks for intents where vector search can miss a single mega-chunk."""
        q = query.lower()
        out: list[PolicyChunkMatch] = []

        def grab(chunk_type: str, k: int) -> None:
            out.extend(
                policy_store.search_chunks(
                    query,
                    top_k=k,
                    document_key=document_key,
                    chunk_type=chunk_type,
                )
            )

        if intent == ROUTING_INTENT_CITATION:
            grab("oo_index", 4)
        elif intent == ROUTING_INTENT_AUTHORITY:
            grab("authority_index", 4)
        elif intent == ROUTING_INTENT_OVERVIEW:
            grab("document_summary", 2)
        elif intent == ROUTING_INTENT_LISTING:
            if re.search(
                r"\b(leave|leaves|casual|earned|eol|maternity|paternity|scl|hpl|hpl/|ccl|quarantine|wriil)\b",
                q,
            ):
                grab("leave_types_index", 3)
            if re.search(
                r"\b(hba|advance|advances|mpa|motor|wheeler|lakh|crore|financial|"
                r"ceiling|encashment|ctg)\b",
                q,
            ):
                grab("financial_limits_index", 3)
        elif intent == ROUTING_INTENT_RATE:
            grab("financial_limits_index", 3)

        return self._dedupe_chunk_matches(out)

    @staticmethod
    def _extract_faq_answer(content: str) -> str:
        m = re.search(r"(?i)^Answer:\s*(.+)", content, re.MULTILINE | re.DOTALL)
        if m:
            return m.group(1).strip()
        return content

    @staticmethod
    def _question_similarity(user_query: str, faq_question: str) -> float:
        stop = {
            "a", "an", "the", "is", "are", "was", "were", "be", "been",
            "what", "when", "where", "which", "who", "how", "why",
            "me", "my", "i", "tell", "give", "please", "about", "for",
            "in", "on", "of", "to", "and", "or", "do", "does", "can",
        }

        def _tokens(text: str) -> set[str]:
            return {
                t for t in re.findall(r"[a-zA-Z0-9]+", text.lower())
                if len(t) >= 3 and t not in stop
            }

        q = _tokens(user_query)
        f = _tokens(faq_question)
        if not q or not f:
            return 0.0
        inter = len(q & f)
        union = len(q | f)
        return inter / union if union else 0.0

    def _log_doc_retrieval(
        self,
        employee_id: str,
        query: str,
        matches: list[PolicyChunkMatch],
        *,
        limit: int = 3,
    ) -> None:
        if not matches:
            logger.info("RAG retrieval for employee %s returned no document chunks", employee_id)
            return

        logger.info(
            "RAG retrieval summary for employee %s: query=%r total_matches=%s",
            employee_id,
            query,
            len(matches),
        )
        for idx, match in enumerate(matches[:limit], start=1):
            preview = re.sub(r"\s+", " ", (match.content or "")).strip()[:260]
            cid = (match.metadata or {}).get("chunk_id", "")
            logger.info(
                (
                    "RAG chunk[%s] employee=%s chunk_id=%s doc=%s chunk=%s section=%r "
                    "vector=%.4f keyword=%.4f combined=%.4f preview=%r"
                ),
                idx,
                employee_id,
                cid,
                match.source_file,
                match.chunk_index,
                match.section_title,
                match.vector_score,
                match.keyword_score,
                match.combined_score,
                preview,
            )

    def _normalize_policy_query(self, query: str) -> str:
        text = (query or "").strip()
        if not text:
            return text
        text = re.sub(
            r"^(?:\s*(?:hi|hello|hey|good\s+morning|good\s+afternoon|good\s+evening|namaste)[\s\.,!;:-]*)+",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()
        return text or query

    def _select_relevant_doc_matches(
        self,
        *,
        query: str,
        matches: list[PolicyChunkMatch],
        top_k: int,
    ) -> list[PolicyChunkMatch]:
        if not matches:
            return []
        terms = self._query_terms(query)
        if not terms:
            return matches[:top_k]

        scored: list[tuple[int, float, PolicyChunkMatch]] = []
        for m in matches:
            hay = f"{m.section_title or ''} {m.content or ''}".lower()
            hit_count = sum(1 for t in terms if t in hay)
            scored.append((hit_count, m.combined_score, m))

        scored.sort(key=lambda x: (x[0], x[1]), reverse=True)

        hits = [m for hits, _, m in scored if hits > 0]
        if hits:
            return hits[:top_k]
        return matches[:top_k]

    @staticmethod
    def _specific_query_terms(query: str) -> list[str]:
        hr_common = {
            "leave",
            "employee",
            "employees",
            "dmrc",
            "office",
            "order",
            "ref",
            "department",
            "rules",
            "rule",
            "regulation",
            "regulations",
            "shall",
            "date",
            "dated",
            "number",
            "may",
            "will",
            "pay",
            "allowance",
            "service",
            "work",
            "period",
            "days",
            "months",
            "year",
            "salary",
            "grant",
            "benefit",
            "benefits",
            "account",
            "officer",
            "authority",
            "circular",
            "applicable",
            "subject",
            "request",
            "approval",
            "approved",
            "apply",
            "application",
            "eligible",
            "eligibility",
            "provide",
            "provided",
        }
        generic = {
            "about",
            "allow",
            "any",
            "can",
            "detail",
            "details",
            "for",
            "give",
            "hello",
            "hey",
            "hi",
            "how",
            "info",
            "information",
            "is",
            "me",
            "of",
            "on",
            "please",
            "policy",
            "tell",
            "the",
            "what",
        }
        stop_all = generic | hr_common
        out: list[str] = []
        for tok in re.findall(r"[a-zA-Z0-9]+", (query or "").lower()):
            if len(tok) < 4 or tok in stop_all:
                continue
            if tok not in out:
                out.append(tok)
        return out

    @staticmethod
    def _query_terms(query: str) -> list[str]:
        stop = {
            "about",
            "allow",
            "any",
            "can",
            "detail",
            "details",
            "for",
            "give",
            "hello",
            "hey",
            "hi",
            "how",
            "i",
            "info",
            "information",
            "is",
            "me",
            "of",
            "on",
            "please",
            "policy",
            "tell",
            "the",
            "what",
        }
        out = []
        for tok in re.findall(r"[a-zA-Z0-9]+", (query or "").lower()):
            if len(tok) < 3 or tok in stop:
                continue
            if tok not in out:
                out.append(tok)
        return out

    async def _build_grounded_policy_answer(
        self,
        state: OrchestratorState,
        matches: list[PolicyChunkMatch],
    ) -> str:
        context_blocks = []
        for idx, m in enumerate(matches[:5], start=1):
            section = m.section_title or "Policy section"
            meta = m.metadata or {}
            ref_parts = []
            if meta.get("rule_id") or meta.get("rule_number"):
                ref_parts.append(f"rule={meta.get('rule_id') or meta.get('rule_number')}")
            if meta.get("chapter"):
                ref_parts.append(f"chapter={meta['chapter']}")
            if meta.get("page_range"):
                ref_parts.append(f"pages={meta['page_range']}")
            elif m.page_number is not None:
                ref_parts.append(f"page={m.page_number}")
            if meta.get("chunk_id"):
                ref_parts.append(f"chunk_id={meta['chunk_id']}")
            meta_line = (" | ".join(ref_parts)) if ref_parts else ""
            chunk_type = meta.get("chunk_type", "")
            context_blocks.append(
                f"[{idx}] {section}"
                + (f" | {meta_line}" if meta_line else "")
                + (f" | type={chunk_type}" if chunk_type else "")
                + f"\n{m.content}"
            )
        evidence = "\n\n".join(context_blocks)

        pdf_url = self._reference_pdf_url()
        pdf_block = (
            f"\n\nOfficial HR Compendium PDF (November 2023 — use this exact link in your answer):\n{pdf_url}"
            if pdf_url
            else ""
        )

        prompt = (
            "Answer the user question using only the policy excerpts below.\n"
            "Follow the system rules on citations, uncertainty, and the full-document link.\n\n"
            f"User question: {state.user_message}\n\n"
            f"Policy excerpts:\n{evidence}"
            f"{pdf_block}"
        )

        try:
            client = get_llm_client()
            model = get_model_name()
            response = await client.chat.completions.create(
                model=model,
                max_tokens=620,
                messages=[
                    {"role": "system", "content": self._build_context_prompt(state)},
                    {"role": "user", "content": prompt},
                ],
            )
            content = (response.choices[0].message.content or "").strip()
            if content:
                return self._append_reference_document_link(content)
        except Exception as exc:
            logger.warning("Grounded policy answer generation failed: %s", str(exc))

        best = matches[0]
        excerpt = best.content[:420].strip()
        suffix = "..." if len(best.content) > 420 else ""
        section = best.section_title or "policy section"
        fallback = (
            f"Based on the policy document ({section}), here is the closest guidance:\n"
            f"{excerpt}{suffix}\n\n"
            "Reference: see excerpt [1] above."
        )
        return self._append_reference_document_link(fallback)

    @staticmethod
    def _general_fallback_response() -> str:
        return (
            "I could not find a confident policy-grounded answer for that query. "
            "Please rephrase with more specifics (policy topic, rule, or clause). "
            "I can also help with attendance, leave, profile, NOC, and VPF queries."
        )
