"""
Policy FAQ Agent - Retrieves answers from internal policy Q&A knowledge base.
"""

import logging
import re

from app.agents.base import BaseAgent
from app.knowledge.store import policy_store
from app.orchestrator.state import OrchestratorState

logger = logging.getLogger(__name__)

POLICY_AGENT_PROMPT = """You answer HR policy questions using the internal policy Q&A knowledge base."""


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
            if kb_stats.get("rows", 0) == 0:
                state.response_message = (
                    "I am unable to find policy information right now. "
                    "Please try again in a little while or contact HR."
                )
                state.sources = [{"type": "policy_qa", "kb_stats": kb_stats}]
                return state

            matches = policy_store.search(state.user_message, top_k=10)
            if not matches:
                state.response_message = (
                    "I could not find a matching policy answer right now. "
                    "Please try rephrasing your question."
                )
                state.sources = [{"type": "policy_qa", "kb_stats": kb_stats}]
                return state

            ranked = self._rank_matches(state.user_message, matches)
            best = ranked[0]
            if best["combined"] < 0.25:
                state.response_message = (
                    "I found related policy topics, but I am not fully confident about the exact answer. "
                    "Please share a bit more detail in your question."
                )
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
                return state

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
                "Policy agent matched question for employee %s combined=%.4f vector=%.4f keyword=%.4f",
                state.employee_id,
                best["combined"],
                best["vector"],
                best["keyword"],
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

    def _rank_matches(self, query: str, matches):
        ranked = []
        for m in matches:
            kw = self._keyword_overlap(query, m.question)
            combined = 0.85 * float(m.score) + 0.15 * float(kw)
            ranked.append({"match": m, "vector": float(m.score), "keyword": float(kw), "combined": combined})
        ranked.sort(key=lambda x: x["combined"], reverse=True)
        return ranked
