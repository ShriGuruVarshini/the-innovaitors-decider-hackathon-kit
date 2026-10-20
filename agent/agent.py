"""StoryStone — The Curious Heritage Detective

A tourist provides a temple name and city, receives a researched temple introduction, uploads
a sculpture photo, and watches StoryStone investigate its possible meaning before presenting
an understandable, evidence-backed story.

Strands Decider 2B makes one key decision per investigation: after assembling temple context,
visual observations, a candidate identification, and retrieved heritage references, the decider
classifies the investigation verdict (answer / investigate_further / request_closeup /
acknowledge_uncertainty). The LLM narrates; the decider decides.

Architecture note (rate-limit aware):
  The user group cloud allows 10 LLM requests/minute. A Strands agentic loop with 4 tools
  consumes 5–8 requests per turn. To stay within the limit we call tools directly in Python
  (zero LLM calls) and use ONE LLM call at the end for the narrative, for a total of 2 LLM
  calls per sculpture investigation (temple intro + story narration).

    from agent.agent import HackathonAgent
    out = HackathonAgent().chat("Meenakshi Amman Temple, Madurai — who is this dancing figure?",
                                images=["agent/data/images/nataraja.jpg"])
    out["reply"], out["decisions"]
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

from decider_kit import Decider
from decider_kit.llm import agent_model, ask as llm_ask, default_model_id, image_blocks, strip_thinking

from .decision import InvestigationPolicy
from .tools import (
    analyze_sculpture as _analyze,
    evaluate_evidence as _evaluate,
    research_temple as _research,
    search_heritage_references as _search_refs,
)

NAME = "StoryStone — The Curious Heritage Detective"

# User group cloud caps output at 1,024 tokens. Bedrock/local have higher limits.
def _max_tokens(default: int) -> int:
    from decider_kit.llm import provider
    return 900 if provider() == "ugmdu" else default


# ── Ollama vision helper (used only for image summarization) ───────────────
# The main LLM stays on ugmdu. Ollama is used for ONE call per image upload.
# Model: qwen3.5:4b — vision-capable, 4 GB, runs on CPU with 8 GB+ RAM.
_OLLAMA_VISION_MODEL = os.environ.get("VISION_MODEL", "qwen3.5:4b")
_OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")


def _ollama_available() -> bool:
    """Return True if Ollama is running and the vision model is pulled."""
    try:
        import urllib.request
        with urllib.request.urlopen(f"{_OLLAMA_URL}/api/tags", timeout=2) as r:
            import json as _json
            data = _json.loads(r.read())
            models = [m.get("name", "").split(":")[0] for m in data.get("models", [])]
            return _OLLAMA_VISION_MODEL.split(":")[0] in models
    except Exception:
        return False


def _summarize_with_ollama(images: list, user_text: str) -> str:
    """Call Ollama via /api/chat (vision-capable endpoint) to describe the sculpture photo.

    Uses the chat API which correctly handles multimodal input in current Ollama versions.
    Images are passed as base64 strings in the message content.
    """
    import base64
    import json as _json
    import urllib.request

    from decider_kit.client import encode_images

    # Encode images to plain base64 (strip data: prefix if present)
    encoded = []
    for b64 in encode_images(images):
        raw = b64.split(",", 1)[1] if "," in b64 else b64
        # Ensure valid base64 padding
        padding = 4 - len(raw) % 4
        if padding != 4:
            raw += "=" * padding
        encoded.append(raw)

    if not encoded:
        return user_text

    prompt_text = (
        "You are examining a photograph of a temple sculpture. "
        "Describe ONLY what you can actually see:\n"
        "- Number of arms and what each hand holds or its gesture\n"
        "- Posture (standing, seated, dancing)\n"
        "- Animal or figure at the base\n"
        "- Crown, ornaments, clothing\n"
        "- Any inscriptions visible\n\n"
        "Be factual and specific. Do not name the deity — just observe. Under 120 words."
    )
    if user_text and user_text not in ("(analyse this sculpture)", "(photo)", ""):
        prompt_text += f"\n\nTourist also noted: {user_text}"

    # Use /api/chat with images list — correct for Ollama vision models
    # Note: images must be in the top-level message dict, NOT inside content
    payload = _json.dumps({
        "model": _OLLAMA_VISION_MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt_text,
                "images": encoded,
            }
        ],
        "stream": False,
        "options": {"num_predict": 200, "temperature": 0},
        "think": False,
    }).encode()

    req = urllib.request.Request(
        f"{_OLLAMA_URL}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    # Generous timeout: first run loads model into RAM (~60s on CPU), subsequent ~20s
    with urllib.request.urlopen(req, timeout=300) as resp:
        result = _json.loads(resp.read())
        return result.get("message", {}).get("content", "").strip()


_VISION_SYSTEM = "You are a precise iconographic observer. Describe only what is visually present."

_VISION_PROMPT = """\
You are examining a photograph of a temple sculpture. Describe ONLY what you can actually see:
- Number of arms and what each hand holds or what gesture it makes
- Posture (standing, seated, dancing)
- Any animal or smaller figure at the base or nearby
- Ornaments, crown, clothing
- Any inscriptions or background context visible

Be specific and factual. Do not identify the deity yet — just observe.
Keep the description under 150 words.
"""

# ── Prompts ────────────────────────────────────────────────────────────────

_TEMPLE_SYSTEM = """You are StoryStone, a heritage detective helping tourists discover Indian temples. Be warm, concise, and accessible."""

_TEMPLE_PROMPT = """\
Tourist is visiting {temple_name}, {city}. Write a brief temple introduction using this research:

{research}

Format:
**{temple_name}** _{city}_
[2 sentences of historical background]
**Key legends:** [1 important story, 1–2 sentences]
**Look for:** [2 sculptural highlights]
**Sources:** [URLs]

End with: "Found a sculpture? Describe it or upload a photo — I'll investigate its story."
Keep it under 300 words.
"""

_STORY_SYSTEM = """You are StoryStone, a heritage detective presenting evidence-backed sculpture stories. Be thorough but concise. Always cite sources. Never fabricate facts."""

_STORY_PROMPT = """\
Tourist at {temple_name}, {city} asked: "{question}"

Evidence assembled:
{evidence}

Write a concise story using EXACTLY these headings (keep each section brief):

**What You May Be Looking At** (1–2 sentences)
**Clues in the Sculpture** (3–4 bullet points)
**The Story Behind It** (2 short paragraphs)
**Why It Matters** (2–3 sentences)
**Sources** (URLs from the evidence)
**Confidence** (1 sentence on certainty level)
**Explore Further** (1 follow-up question)

Stay under 500 words total.
"""

_INVESTIGATE_PROMPT = """\
Tourist at {temple_name}, {city}: "{description}"

Evidence:
{evidence}

Verdict: {verdict}. {verdict_note}

Respond helpfully in under 200 words.
"""

_FOLLOWUP_SYSTEM = """You are StoryStone. Answer the follow-up question using existing context. Be concise — under 150 words."""


def _refs_to_text(refs: list[dict]) -> str:
    """Format a list of {url, text} dicts into readable reference text."""
    if not refs:
        return "(no references found)"
    parts = []
    for r in refs:
        url = r.get("url", "")
        text = r.get("snippet") or r.get("text", "")
        if text and url:
            parts.append(f"- {text[:300]}\n  Source: {url}")
        elif url:
            parts.append(f"- {url}")
    return "\n".join(parts) if parts else "(no reference text available)"


class HackathonAgent:
    """One StoryStone session per session_id. Calls tools directly to minimise LLM round-trips."""

    def __init__(
        self,
        decider: Decider | None = None,
        model_id: str | None = None,
        eager: bool | None = None,
    ):
        import os
        self.decider = decider or Decider()
        self.policy = InvestigationPolicy(self.decider)
        self.eager = eager if eager is not None else os.environ.get("DEMO_EAGER") == "1"
        self.model_id = model_id or default_model_id()
        # session_id → {temple_name, temple_city, temple_summary, last_evidence, last_candidate, history}
        self.sessions: dict[str, dict[str, Any]] = {}

    def _sess(self, session_id: str) -> dict[str, Any]:
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "temple_name": "", "temple_city": "",
                "temple_summary": "", "temple_sources": [],
                "last_evidence": "", "last_candidate": "",
                "history": [],   # list of {role, content} for follow-ups
            }
        return self.sessions[session_id]

    # ── Public interface ───────────────────────────────────────────────────

    def chat(
        self,
        message: str,
        session_id: str = "default",
        images: list[Any] | None = None,
    ) -> dict[str, Any]:
        """`images` (optional): base64 strings or file paths attached by the tourist."""
        sess = self._sess(session_id)
        policy_log_before = len(self.policy.log)
        t0 = time.perf_counter()

        # ── Detect intent ─────────────────────────────────────────────────
        msg_lower = message.lower()
        is_temple_request = any(k in msg_lower for k in [
            "tell me about", "visiting", "i am at", "i'm at", "what is this temple",
            "temple in", "about the temple", "discover this temple",
        ])
        has_sculpture_context = bool(images) or any(k in msg_lower for k in [
            "figure", "sculpture", "statue", "who is", "what is this", "dancing",
            "elephant", "spear", "peacock", "ring of fire", "four arms", "six arms",
            "mudra", "carving", "idol", "deity",
        ])
        has_temple_set = bool(sess["temple_name"])
        is_followup = has_temple_set and not is_temple_request and not has_sculpture_context and sess["last_evidence"]

        # ── Extract temple name/city from message if not set ──────────────
        if not has_temple_set or is_temple_request:
            name, city = self._extract_temple(message, sess)
        else:
            name = sess["temple_name"]
            city = sess["temple_city"]

        decisions: list[dict[str, Any]] = []
        reply = ""

        # ── Branch: temple intro ──────────────────────────────────────────
        if is_temple_request or (not has_temple_set and not has_sculpture_context):
            reply = self._temple_intro(message, name, city, sess)

        # ── Branch: follow-up question on existing investigation ──────────
        elif is_followup:
            reply = self._followup(message, sess)

        # ── Branch: sculpture investigation ───────────────────────────────
        else:
            reply, decisions = self._investigate(message, name, city, images, sess, policy_log_before)

        return {
            "reply": reply,
            "decisions": decisions,
            "model_id": self.model_id,
            "latency_ms": round((time.perf_counter() - t0) * 1000),
            "agent": NAME,
            "eager": self.eager,
        }

    # ── Image summarization (Ollama vision) ──────────────────────────────

    def _summarize_image(self, images: list[Any], user_text: str) -> str:
        """Describe the uploaded sculpture photo using Ollama (qwen3.5:4b vision).

        Flow:
        1. If Ollama is running with qwen3.5:4b → call it directly via REST (no rate limit,
           no cloud cost, full vision). This is independent of the main LLM (ugmdu).
        2. If Ollama is not running → fall back to user_text + a note so the investigation
           still proceeds with whatever description the tourist typed.

        The description is used by analyze_sculpture (keyword matching → iconographic
        observations) and by the final story prompt.
        """
        if not images:
            return user_text

        if _ollama_available():
            try:
                description = _summarize_with_ollama(images, user_text)
                if description:
                    return description
            except Exception as e:
                # Ollama call failed — log and fall back
                print(f"[StoryStone] Ollama vision error: {e}")

        # Fallback: use the tourist's text + note
        base = user_text if user_text not in ("(analyse this sculpture)", "(photo)", "") else ""
        note = (
            "📷 *Photo received. For richer visual analysis, make sure Ollama is running "
            f"with `{_OLLAMA_VISION_MODEL}` pulled (`ollama pull {_OLLAMA_VISION_MODEL}`). "
            "Investigating based on your text description.*"
        )
        return f"{base}\n{note}".strip() if base else note

    # ── Temple intro (1 LLM call) ─────────────────────────────────────────

    def _temple_intro(self, message: str, name: str, city: str, sess: dict) -> str:
        # Direct tool call — no LLM round-trip for the research
        research = _research(temple_name=name, city=city)
        sess["temple_name"] = name
        sess["temple_city"] = city
        sess["temple_summary"] = research.get("summary", "")
        sess["temple_sources"] = research.get("sources", [])

        research_text = (
            f"Summary: {research.get('summary', '')}\n"
            f"Highlights: {', '.join(research.get('highlights', []))}\n"
            f"Sources: {', '.join(research.get('sources', []))}"
        )
        prompt = _TEMPLE_PROMPT.format(
            temple_name=name, city=city, research=research_text
        )
        reply, _ = llm_ask(prompt, system=_TEMPLE_SYSTEM, model_id=self.model_id, max_tokens=_max_tokens(700))
        return strip_thinking(reply)

    # ── Sculpture investigation (tools direct + 1 LLM call) ───────────────

    def _investigate(
        self,
        message: str,
        name: str,
        city: str,
        images: list[Any] | None,
        sess: dict,
        policy_log_before: int,
    ) -> tuple[str, list[dict]]:

        temple_summary = sess.get("temple_summary") or f"{name} in {city}"

        # Step 1: summarize the uploaded image (vision LLM or text fallback)
        # This produces a text description used by analyze_sculpture and the story prompt.
        image_description = self._summarize_image(images or [], message)

        # Step 2: analyze sculpture — uses image_description (direct tool call, no LLM)
        analysis = _analyze(
            image_description=image_description,
            temple_context=temple_summary[:300],
        )
        observations = analysis.get("observations", image_description)
        candidate = analysis.get("candidate", "Unknown deity")

        # Step 3: search heritage references (direct tool call, no LLM)
        refs_result = _search_refs(
            candidate=candidate,
            clues=observations[:400],
            temple_context=temple_summary[:200],
            search_attempt=1,
        )
        references = refs_result.get("references", [])
        refs_text = _refs_to_text(references)

        # Step 4: assemble evidence (direct tool call, no LLM)
        evidence_result = _evaluate(
            temple_name=name,
            temple_city=city,
            temple_summary=temple_summary[:500],
            observations=observations,
            candidate=candidate,
            references=refs_text,
            user_question=message,
        )
        state_text = evidence_result.get("state_text", "")
        sess["last_evidence"] = state_text
        sess["last_candidate"] = candidate

        # Step 5: Strands Decider 2B — the ONE decision
        verdict = self.policy.check(state_text, images=images)
        decisions = self.policy.log[policy_log_before:]

        # Step 6: if investigate_further — one more search, re-check (no extra LLM call)
        if verdict.action == "investigate_further":
            refs2 = _search_refs(
                candidate=candidate,
                clues=observations[:400],
                temple_context=temple_summary[:200],
                search_attempt=2,
            )
            all_refs = references + refs2.get("references", [])
            refs_text2 = _refs_to_text(all_refs)
            ev2 = _evaluate(
                temple_name=name, temple_city=city,
                temple_summary=temple_summary[:500],
                observations=observations, candidate=candidate,
                references=refs_text2, user_question=message,
            )
            state_text = ev2.get("state_text", state_text)
            sess["last_evidence"] = state_text
            verdict = self.policy.check(state_text, images=images)
            decisions = self.policy.log[policy_log_before:]
            refs_text = refs_text2

        # Step 7: handle verdict without an extra LLM call where possible
        if verdict.action == "request_closeup":
            return self._closeup_reply(), decisions

        if verdict.action == "acknowledge_uncertainty":
            reply, _ = llm_ask(
                _INVESTIGATE_PROMPT.format(
                    temple_name=name, city=city,
                    description=message[:200],
                    evidence=state_text[:1500],
                    verdict="acknowledge_uncertainty",
                    verdict_note="Describe what IS observable. Do not fabricate an identification.",
                ),
                system=_STORY_SYSTEM, model_id=self.model_id, max_tokens=_max_tokens(500),
            )
            return strip_thinking(reply) + self._uncertainty_footer(), decisions

        # Step 8: compose final story (1 LLM call)
        # Use image_description (from vision or text) as the question context
        question_ctx = image_description if image_description != message else message
        story_prompt = _STORY_PROMPT.format(
            temple_name=name, city=city,
            question=question_ctx[:300],
            evidence=state_text[:1800],
        )
        reply, _ = llm_ask(story_prompt, system=_STORY_SYSTEM, model_id=self.model_id, max_tokens=_max_tokens(900))
        reply = strip_thinking(reply)

        if verdict.low_confidence:
            reply += (
                "\n\n⚠️ *Note: the decider's confidence was below the usual threshold. "
                "This interpretation is plausible but treat it as tentative.*"
            )
        return reply, decisions

    # ── Follow-up (1 LLM call) ────────────────────────────────────────────

    def _followup(self, message: str, sess: dict) -> str:
        context = (
            f"Temple: {sess['temple_name']}, {sess['temple_city']}\n"
            f"Last investigated: {sess['last_candidate']}\n\n"
            f"Evidence assembled:\n{sess['last_evidence'][:2000]}"
        )
        prompt = f"Context:\n{context}\n\nTourist's follow-up question: {message}"
        reply, _ = llm_ask(prompt, system=_FOLLOWUP_SYSTEM, model_id=self.model_id, max_tokens=_max_tokens(400))
        return strip_thinking(reply)

    # ── Helpers ───────────────────────────────────────────────────────────

    def _extract_temple(self, message: str, sess: dict) -> tuple[str, str]:
        """Best-effort extraction of temple name and city from message text."""
        import re
        # Try "X Temple in Y" or "X Temple, Y"
        m = re.search(r"([\w\s]+(?:temple|mandir|kovil|shrine)[\w\s]*?)(?:\s+in\s+|\s*,\s*)([\w\s]+)",
                      message, re.I)
        if m:
            return m.group(1).strip(), m.group(2).strip().split(".")[0].strip()
        # Fall back to stored values or generic
        return sess.get("temple_name") or "the temple", sess.get("temple_city") or "India"

    def _closeup_reply(self) -> str:
        return (
            "🔍 **StoryStone needs a closer look.**\n\n"
            "I can see some promising details, but one key attribute isn't clear enough "
            "to make a confident identification — likely the object held in the upper hands, "
            "or the animal/vehicle at the base of the sculpture.\n\n"
            "Could you take a closer photo of that specific area? A focused close-up works "
            "perfectly — no need to photograph the whole sculpture again.\n\n"
            "That one detail will help me distinguish between the possible interpretations."
        )

    def _uncertainty_footer(self) -> str:
        return (
            "\n\n---\n"
            "🪨 *StoryStone could not find sufficient evidence to make a confident "
            "identification. The observations above are accurate, but the interpretation "
            "is uncertain. Ask a temple priest or guide, or consult the Archaeological "
            "Survey of India documentation for this site.*"
        )


if __name__ == "__main__":
    import sys
    a = HackathonAgent()
    msgs = sys.argv[1:] or [
        "I'm at Meenakshi Amman Temple in Madurai. Tell me about this temple.",
        "I found a beautiful dancing figure with a ring of fire. Who is this?",
    ]
    for msg in msgs:
        print(json.dumps(a.chat(msg), indent=2, default=str))
