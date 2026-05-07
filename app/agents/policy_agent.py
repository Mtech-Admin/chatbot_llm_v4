"""
Policy FAQ Agent - Retrieves answers from internal policy Q&A knowledge base.
"""

import logging
import re

from app.agents.base import BaseAgent
from app.config import get_llm_client, get_model_name, settings
from app.knowledge.store import PolicyChunkMatch, policy_store
from app.orchestrator.state import OrchestratorState

logger = logging.getLogger(__name__)

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
                doc_matches = policy_store.search_chunks(
                    state.user_message,
                    top_k=max(1, settings.POLICY_RAG_TOP_K),
                )

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

            # Unified policy behavior:
            # - Prefer document chunks whenever confidence is reasonable.
            # - FAQ remains supplementary/fallback, not the default winner over docs.
            doc_floor = max(0.18, settings.POLICY_RAG_DOC_CONFIDENCE_THRESHOLD - 0.08)
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

    async def _build_grounded_policy_answer(
        self,
        state: OrchestratorState,
        matches: list[PolicyChunkMatch],
    ) -> str:
        context_blocks = []
        for idx, m in enumerate(matches[:3], start=1):
            section = m.section_title or "Policy section"
            page_label = f" | page={m.page_number}" if m.page_number else ""
            context_blocks.append(
                f"[{idx}] {section}{page_label}\n"
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
