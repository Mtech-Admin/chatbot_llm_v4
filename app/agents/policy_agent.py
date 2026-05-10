"""
Policy FAQ Agent - Retrieves answers from internal policy Q&A knowledge base.
"""

import logging
import re

from app.agents.base import BaseAgent
from app.config import get_llm_client, get_model_name, settings
from app.knowledge.ingest import (
    CHUNK_TYPE_AUTHORITY,
    CHUNK_TYPE_CHAPTER_SUMMARY,
    CHUNK_TYPE_OO_INDEX,
    CHUNK_TYPE_RULE,
    CHUNK_TYPE_TABLE,
)
from app.knowledge.store import PolicyChunkMatch, policy_store
from app.orchestrator.state import OrchestratorState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Query-type classification patterns
# Each entry: (compiled_regex, chunk_type_to_target)
# Evaluated in order — first match wins.
# ---------------------------------------------------------------------------
_QUERY_TYPE_RULES: list[tuple[re.Pattern[str], str]] = [
    # Rate / amount / allowance tables
    (
        re.compile(
            r"\b(how\s+much|rate|amount|per\s+day|per\s+month|ceiling|limit|"
            r"da\s+rate|daily\s+allowance|slab|rupee|rs\.?|inr|tariff|"
            r"quantum|entitlement|entitled\s+to)\b",
            re.IGNORECASE,
        ),
        CHUNK_TYPE_TABLE,
    ),
    # Approval / sanction authority
    (
        re.compile(
            r"\b(who\s+(?:can\s+)?(?:approve|sanction|grant|authoris|authorize)|"
            r"approval\s+authority|sanctioning\s+authority|competent\s+authority|"
            r"who\s+is\s+(?:the\s+)?authority|power\s+to\s+(?:grant|sanction|approve)|"
            r"delegat(?:ion|ed)\s+of\s+power)\b",
            re.IGNORECASE,
        ),
        CHUNK_TYPE_AUTHORITY,
    ),
    # O.O. / Office Order lookups
    (
        re.compile(
            r"(?:O\.O\.|office\s+order|OO\s+no\.?|PP/\d|order\s+no\.?\s*PP)",
            re.IGNORECASE,
        ),
        CHUNK_TYPE_OO_INDEX,
    ),
    # Overview / chapter summary
    (
        re.compile(
            r"\b(what\s+is|overview|introduce|introduction|explain\s+chapter|"
            r"summarize|summary|about\s+chapter|tell\s+me\s+about\s+chapter|"
            r"what\s+does\s+chapter)\b",
            re.IGNORECASE,
        ),
        CHUNK_TYPE_CHAPTER_SUMMARY,
    ),
]

POLICY_AGENT_PROMPT = """You answer HR policy questions using the internal policy document knowledge base.

Grounding rules:
- Use only retrieved policy evidence when answering policy questions.
- If policy evidence is weak/unclear, say you are not confident and provide a concise fallback guidance.
- Do not invent policy clauses or section references."""

class PolicyAgent(BaseAgent):
    def __init__(self):
        super().__init__("policy_agent", POLICY_AGENT_PROMPT)

    async def process(self, state: OrchestratorState) -> OrchestratorState:
        try:
            kb_stats = policy_store.stats()
            logger.info(
                "Policy agent KB stats for employee %s: %s",
                state.employee_id,
                kb_stats,
            )
            has_doc_index = kb_stats.get("policy_chunk_count", 0) > 0
            has_faq_index = kb_stats.get("rows", 0) > 0
            if not has_doc_index and not has_faq_index:
                state.response_message = (
                    "I am unable to find policy information right now. "
                    "Please try again in a little while or contact HR."
                )
                state.sources = [{"type": "policy_kb", "kb_stats": kb_stats}]
                return state

            doc_matches = []
            if settings.POLICY_RAG_ENABLED and has_doc_index:
                retrieval_query = self._normalize_policy_query(state.user_message)
                top_k_final = max(1, settings.POLICY_RAG_TOP_K)
                # Pin to a specific document when configured (prevents stale docs polluting results).
                doc_key_filter: str | None = settings.POLICY_RAG_DOCUMENT_KEY.strip() or None

                # Step 1: classify query type and attempt targeted chunk-type retrieval.
                query_type = self._classify_query_type(retrieval_query)
                logger.info(
                    "RAG query classification for employee %s: query_type=%s doc_key=%s",
                    state.employee_id,
                    query_type,
                    doc_key_filter or "all",
                )

                targeted_matches: list[PolicyChunkMatch] = []
                if query_type != CHUNK_TYPE_RULE:
                    # Targeted retrieval for non-default query types
                    targeted_matches = policy_store.search_chunks_by_type(
                        retrieval_query,
                        chunk_type=query_type,
                        top_k=top_k_final,
                        fallback_if_few=2,
                        document_key=doc_key_filter,
                    )
                    logger.info(
                        "RAG targeted retrieval employee=%s type=%s found=%s",
                        state.employee_id,
                        query_type,
                        len(targeted_matches),
                    )

                # Step 2: hybrid vector+lexical broad search (always run for completeness).
                raw_doc_matches = policy_store.search_chunks(
                    retrieval_query,
                    top_k=max(top_k_final * 4, 20),
                    document_key=doc_key_filter,
                )

                # Step 3: extract rare/specific terms and do a guaranteed DB lookup.
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
                        "RAG exact-term lookup for employee %s terms=%s found=%s",
                        state.employee_id,
                        specific_terms,
                        len(exact_matches),
                    )

                # Step 4: merge — targeted hits first, then exact-term, then hybrid.
                seen_chunk_ids: set[tuple[str, int]] = set()
                merged: list[PolicyChunkMatch] = []
                for m in targeted_matches:
                    key = (m.source_file, m.chunk_index)
                    if key not in seen_chunk_ids:
                        seen_chunk_ids.add(key)
                        merged.append(m)
                for m in exact_matches:
                    key = (m.source_file, m.chunk_index)
                    if key not in seen_chunk_ids:
                        seen_chunk_ids.add(key)
                        merged.append(m)
                for m in raw_doc_matches:
                    key = (m.source_file, m.chunk_index)
                    if key not in seen_chunk_ids:
                        seen_chunk_ids.add(key)
                        merged.append(m)

                doc_matches = self._select_relevant_doc_matches(
                    query=retrieval_query,
                    matches=merged,
                    top_k=top_k_final,
                )
                self._log_doc_retrieval(state.employee_id, retrieval_query, doc_matches)

            ranked_faq = []
            if has_faq_index:
                faq_matches = policy_store.search(state.user_message, top_k=10)
                if faq_matches:
                    ranked_faq = self._rank_faq_matches(state.user_message, faq_matches)

            best_doc_score = doc_matches[0].combined_score if doc_matches else 0.0
            best_faq_score = ranked_faq[0]["combined"] if ranked_faq else 0.0
            logger.info(
                "Policy merged retrieval for employee %s: best_doc=%.4f best_faq=%.4f",
                state.employee_id,
                best_doc_score,
                best_faq_score,
            )

            # Use doc path when best chunk score clears the configured threshold.
            # Default threshold is 0.20 — low enough for semantic-adjacent topics,
            # high enough to reject total misses.
            doc_floor = max(0.15, settings.POLICY_RAG_DOC_CONFIDENCE_THRESHOLD)
            if doc_matches and best_doc_score >= doc_floor:
                state.response_message = await self._build_grounded_policy_answer(state, doc_matches)
                sources = [
                    {
                        "type": "policy_doc_chunk",
                        "document_key": m.document_key,
                        "document_title": m.document_title,
                        "source_file": m.source_file,
                        "chunk_index": m.chunk_index,
                        "section_title": m.section_title,
                        "page_number": m.page_number,
                        "chunk_type": (m.metadata or {}).get("chunk_type"),
                        "chapter": (m.metadata or {}).get("chapter"),
                        "rule_number": (m.metadata or {}).get("rule_number"),
                        "vector_score": round(m.vector_score, 4),
                        "keyword_score": round(m.keyword_score, 4),
                        "combined_score": round(m.combined_score, 4),
                    }
                    for m in doc_matches[:3]
                ]
                if ranked_faq:
                    faq_best = ranked_faq[0]
                    sources.append(
                        {
                            "type": "policy_qa_support",
                            "question": faq_best["match"].question,
                            "vector_score": round(faq_best["vector"], 4),
                            "keyword_score": round(faq_best["keyword"], 4),
                            "combined_score": round(faq_best["combined"], 4),
                            "source_file": faq_best["match"].source_file,
                            "row_number": faq_best["match"].row_number,
                        }
                    )
                state.sources = sources + [{"type": "policy_kb_stats", "kb_stats": kb_stats}]
                state.routing_agent = "policy_agent"
                logger.info(
                    "Policy agent selected document path for employee %s doc_score=%.4f faq_score=%.4f",
                    state.employee_id,
                    best_doc_score,
                    best_faq_score,
                )
                return state

            if ranked_faq and best_faq_score >= settings.POLICY_RAG_FAQ_CONFIDENCE_THRESHOLD:
                best = ranked_faq[0]
                state.response_message = best["match"].answer
                state.sources = [
                    {
                        "type": "policy_qa",
                        "question": best["match"].question,
                        "vector_score": round(best["vector"], 4),
                        "keyword_score": round(best["keyword"], 4),
                        "combined_score": round(best["combined"], 4),
                        "source_file": best["match"].source_file,
                        "row_number": best["match"].row_number,
                        "kb_stats": kb_stats,
                    }
                ]
                state.routing_agent = "policy_agent"
                logger.info(
                    "Policy agent selected FAQ fallback for employee %s combined=%.4f",
                    state.employee_id,
                    best["combined"],
                )
                return state

            state.response_message = self._general_fallback_response()
            state.sources = [{"type": "policy_kb_stats", "kb_stats": kb_stats}]
            return state
        except Exception as exc:
            logger.error("Policy agent error for employee %s: %s", state.employee_id, str(exc), exc_info=True)
            state.response_message = (
                "I am unable to retrieve policy details at the moment. "
                "Please try again shortly."
            )
            return state

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return set(re.findall(r"[a-zA-Z0-9]+", text.lower()))

    def _keyword_overlap(self, query: str, question: str) -> float:
        q_tokens = self._tokenize(query)
        d_tokens = self._tokenize(question)
        if not q_tokens or not d_tokens:
            return 0.0
        inter = len(q_tokens & d_tokens)
        union = len(q_tokens | d_tokens) or 1
        return inter / union

    def _rank_faq_matches(self, query: str, matches):
        ranked = []
        for m in matches:
            kw = self._keyword_overlap(query, m.question)
            combined = 0.85 * float(m.score) + 0.15 * float(kw)
            ranked.append({"match": m, "vector": float(m.score), "keyword": float(kw), "combined": combined})
        ranked.sort(key=lambda x: x["combined"], reverse=True)
        return ranked

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
            logger.info(
                (
                    "RAG chunk[%s] employee=%s doc=%s chunk=%s section=%r "
                    "vector=%.4f keyword=%.4f combined=%.4f preview=%r"
                ),
                idx,
                employee_id,
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
        # Remove common greeting prefixes that dilute retrieval (e.g. "Hello. Tell me ...").
        text = re.sub(
            r"^(?:\s*(?:hi|hello|hey|good\s+morning|good\s+afternoon|good\s+evening|namaste)[\s\.,!;:-]*)+",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()
        return text or query

    @staticmethod
    def _classify_query_type(query: str) -> str:
        """
        Classify the query into a chunk_type using fast regex heuristics.

        Returns one of the CHUNK_TYPE_* constants from app.knowledge.ingest.
        The default return value is CHUNK_TYPE_RULE (general rule/clause lookup).
        """
        for pattern, chunk_type in _QUERY_TYPE_RULES:
            if pattern.search(query):
                return chunk_type
        return CHUNK_TYPE_RULE

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

        # Score each candidate by how many unique query terms appear in its text,
        # then by combined_score. This surfaces rare-term chunks (e.g. "paternity")
        # above generic-term chunks (e.g. "leave") even if the latter rank higher
        # on vector score alone.
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
        """
        Extract rare/discriminating terms from the query by stripping both generic
        stopwords AND common HR domain words that appear in nearly every chunk.
        Whatever remains (e.g. 'paternity', 'maternity', 'ltc', 'vpf', 'noc') is
        used for a guaranteed direct DB lookup.
        """
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
        for idx, m in enumerate(matches[:3], start=1):
            section = m.section_title or "Policy section"
            page_label = f" | page={m.page_number}" if m.page_number else ""
            meta = m.metadata or {}
            chapter_label = f" | chapter={meta['chapter']}" if meta.get("chapter") else ""
            rule_label = f" | rule={meta['rule_number']}" if meta.get("rule_number") else ""
            type_label = f" | type={meta['chunk_type']}" if meta.get("chunk_type") else ""
            context_blocks.append(
                f"[{idx}] {section}{page_label}{chapter_label}{rule_label}{type_label}\n"
                f"source={m.source_file} chunk={m.chunk_index} score={m.combined_score:.3f}\n"
                f"{m.content}"
            )
        evidence = "\n\n".join(context_blocks)

        prompt = (
            "Answer the user question using only the retrieved policy excerpts below.\n"
            "Rules:\n"
            "- Keep it concise and actionable.\n"
            "- If evidence is partial, mention the uncertainty explicitly.\n"
            "- End with a short 'Source:' line citing excerpt numbers used (example: Source: [1], [2]).\n"
            "- Do not mention internal systems, embeddings, or retrieval.\n\n"
            f"User question: {state.user_message}\n\n"
            f"Policy excerpts:\n{evidence}"
        )

        try:
            client = get_llm_client()
            model = get_model_name()
            response = await client.chat.completions.create(
                model=model,
                max_tokens=420,
                messages=[
                    {"role": "system", "content": self._build_context_prompt(state)},
                    {"role": "user", "content": prompt},
                ],
            )
            content = (response.choices[0].message.content or "").strip()
            if content:
                return content
        except Exception as exc:
            logger.warning("Grounded policy answer generation failed: %s", str(exc))

        best = matches[0]
        excerpt = best.content[:420].strip()
        suffix = "..." if len(best.content) > 420 else ""
        section = best.section_title or "policy section"
        return (
            f"Based on the policy document ({section}), here is the closest guidance:\n"
            f"{excerpt}{suffix}\n\n"
            "Source: [1]"
        )

    @staticmethod
    def _general_fallback_response() -> str:
        return (
            "I could not find a confident policy-grounded answer for that query. "
            "Please rephrase with more specifics (policy topic, rule, or clause). "
            "I can also help with attendance, leave, profile, NOC, and VPF queries."
        )
