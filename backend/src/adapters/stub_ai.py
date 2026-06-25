"""GenAI explainer — stub until ANTHROPIC_API_KEY is set."""

from __future__ import annotations

from typing import Any

from domain.ports import IAIExplainer


class StubAIExplainer(IAIExplainer):
    async def explain_subdimension(
        self,
        *,
        product_id: str,
        subdimension_id: str,
        user_question: str | None,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        q = user_question or "What should we improve first?"
        ctx_bits = []
        if context.get("guide_overview"):
            ctx_bits.append(f"Guide: {context.get('guide_overview')}")
        if context.get("importance"):
            ctx_bits.append(f"Importance: {context.get('importance')}")
        if context.get("weight_rationale"):
            ctx_bits.append(f"Weight rationale: {context.get('weight_rationale')}")
        if context.get("tradeoff"):
            ctx_bits.append(f"Trade-offs: {context.get('tradeoff')}")
        if context.get("non_negotiable") is not None:
            ctx_bits.append(f"Non-negotiable: {context.get('non_negotiable')}")
        ctx = "\n".join(ctx_bits) if ctx_bits else "(no extra context provided)"

        return {
            "mode": "stub",
            "answer": (
                f"[Stub GenAI] Sub-dimension `{subdimension_id}` on `{product_id}`.\n\n"
                f"{ctx}\n\n"
                f"Question: {q!r}\n\n"
                "What this stub is doing: echoing your structured context so the real integration can pass the same "
                "redacted bundle to a live model once `ANTHROPIC_API_KEY` is configured. "
                "For now: prioritize non‑negotiable gaps, validate evidence sources, then tune trade-offs."
            ),
            "context_echo_keys": list(context.keys()),
        }
