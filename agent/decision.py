"""REUSABLE DECISION PATTERN: heritage investigation verdict  (#policy)

What it does
    After StoryStone assembles temple context, visual observations, a candidate identification,
    and retrieved heritage references, Strands Decider 2B reads the full evidence text and
    classifies the appropriate investigation verdict:

        answer               — evidence is sufficient; present the sourced story
        investigate_further  — evidence is thin; another search may help
        request_closeup      — a specific visual detail is unclear and critical
        acknowledge_uncertainty — contradictory or absent references; be honest

    Two supporting yes/no questions travel with the verdict:
        evidence_quality     — are the references sufficient and non-contradictory?
        needs_visual_detail  — is a key attribute unclear and would it change the identification?

    These three questions are asked in one decider call on the assembled state, so the model
    encodes the evidence once and all three answers share that encoding.

Typed questions and options
    verdict (choice):
        answer                  — observations match references well enough for a sourced story
        investigate_further     — evidence is suggestive but thin; a different search may help
        request_closeup         — a key attribute (weapon, mudra, vahana) is unclear in the photo
        acknowledge_uncertainty — references are absent or contradictory; cannot commit

    evidence_quality (noul):
        true  — at least two independent references match the key visual observations without contradiction
        false — references are absent, contradictory, or match only superficial details

    needs_visual_detail (noul):
        true  — a key attribute (weapon, vehicle, hand gesture, inscription) is unclear and changes the identification
        false — observable details are sufficient or the missing detail would not change the conclusion

Wiring
    `InvestigationPolicy` is called from `HackathonAgent.chat()` after the agent has run
    tools and `evaluate_evidence` has assembled the state text:

        policy = InvestigationPolicy(decider)
        verdict = policy.check(state_text, images=photos)
        # verdict.action in ("answer", "investigate_further", "request_closeup", "acknowledge_uncertainty")

    It is NOT a Strands InterventionHandler — it runs between agent tool calls, not before a
    specific tool. The caller decides the next action based on `verdict.action`.

    One log record is appended per call: probabilities, verdict, decider_ms.

How to reuse it
    Copy this file, rewrite the four verdict option descriptions for your domain,
    and adjust the thresholds in `InvestigationPolicy.decide()`.
    The wiring is a direct `.check()` call wherever you need a content/evidence verdict
    before acting — before publishing, before answering, before filing a report.
    The pattern fits any "is this evidence good enough?" decision written in prose.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from decider_kit import Decider, Decision

PATTERN_TAG = "#policy"

QUESTIONS: dict[str, dict[str, Any]] = {
    "verdict": Decider.choice(
        "What is the appropriate next step given the evidence assembled about this sculpture?",
        {
            "answer": (
                "the visual observations match at least two independent heritage references; "
                "a sourced story with reasonable confidence can be presented"
            ),
            "investigate_further": (
                "the evidence is suggestive but thin — only one source, or sources match only "
                "superficial features; a different search query may find stronger support"
            ),
            "request_closeup": (
                "a specific key attribute (weapon, hand gesture, vahana, inscription, number of arms) "
                "is unclear or damaged in the photograph and would materially change the identification"
            ),
            "acknowledge_uncertainty": (
                "available references are absent, contradictory, or describe an entirely different "
                "figure; no reliable identification can be made from this evidence"
            ),
        },
    ),
    "evidence_quality": Decider.noul(
        "Is the assembled evidence sufficient and internally consistent to support the candidate identification?",
        {
            "true": (
                "at least two independent references match the key visual observations (posture, "
                "primary attribute, vahana) without contradiction"
            ),
            "false": (
                "references are absent, contradict each other, or match only incidental details "
                "such as jewellery style rather than the identifying iconographic attributes"
            ),
        },
    ),
    "needs_visual_detail": Decider.noul(
        "Is there a specific visual detail in the sculpture that is ambiguous or unclear and critical to distinguishing between candidate identifications?",
        {
            "true": (
                "a primary identifying attribute — the weapon held, the vahana at the base, "
                "the number of arms, a hand mudra, or an inscription — is damaged, blurry, "
                "or obscured, and knowing it would change or confirm the identification"
            ),
            "false": (
                "the visible details are sufficient for a confident identification, or the "
                "missing detail is decorative and would not change the conclusion"
            ),
        },
    ),
}


@dataclass
class InvestigationVerdict:
    action: str          # answer | investigate_further | request_closeup | acknowledge_uncertainty
    p_evidence_quality: float
    p_needs_visual:     float
    verdict_confidence: float
    low_confidence:     bool
    answers:            dict[str, Decision] = field(repr=False, default_factory=dict)
    decider_ms:         float = 0.0

    @property
    def log_record(self) -> dict[str, Any]:
        return {
            "pattern": PATTERN_TAG,
            "verdict": self.action,
            "verdict_confidence": round(self.verdict_confidence, 3),
            "p_evidence_quality": round(self.p_evidence_quality, 3),
            "p_needs_visual": round(self.p_needs_visual, 3),
            "low_confidence": self.low_confidence,
            "decider_ms": round(self.decider_ms),
            "probabilities": {
                k: {o: round(p, 3) for o, p in v.probabilities.items()}
                for k, v in self.answers.items()
                if hasattr(v, "probabilities") and v.probabilities
            },
        }


class InvestigationPolicy:
    """Wraps a Strands Decider call that classifies the investigation verdict.

    Call `.check(state_text)` after the agent has assembled evidence.
    The log list grows by one record per call; HackathonAgent.chat() merges it into `decisions`.
    """

    # Confidence below which we add a low-confidence note to the story
    LOW_CONFIDENCE = 0.55
    # If evidence quality p_yes is below this AND verdict is "answer", override to "acknowledge_uncertainty"
    MIN_EVIDENCE_FOR_ANSWER = 0.40
    # If needs_visual p_yes is above this AND verdict is NOT "answer", prefer "request_closeup"
    CLOSEUP_THRESHOLD = 0.65

    def __init__(self, decider: Decider):
        self.decider = decider
        self.log: list[dict[str, Any]] = []

    def check(self, state_text: str, images: Any = None) -> InvestigationVerdict:
        """Run the policy check. Pass `images` when the photo is available (vision decider)."""
        a = self.decider.ask(state_text, QUESTIONS, images=images)
        ms = self.decider.last_latency_ms or 0.0
        v = self._decide(a, ms)
        self.log.append(v.log_record)
        return v

    def _decide(self, a: dict[str, Decision], ms: float) -> InvestigationVerdict:
        verdict_ans = a["verdict"]
        action = verdict_ans.label or "acknowledge_uncertainty"
        verdict_conf = verdict_ans.confidence or 0.0
        p_eq = a["evidence_quality"].p_yes or 0.0
        p_nv = a["needs_visual_detail"].p_yes or 0.0

        low_confidence = verdict_conf < self.LOW_CONFIDENCE

        # Override: if evidence is too thin, don't claim an answer
        if action == "answer" and p_eq < self.MIN_EVIDENCE_FOR_ANSWER:
            action = "acknowledge_uncertainty"

        # Override: if a critical visual detail is missing and we're not already answering
        if action != "answer" and p_nv > self.CLOSEUP_THRESHOLD:
            action = "request_closeup"

        # Low confidence fallback: default to answer but flag it
        if low_confidence and action not in ("answer", "acknowledge_uncertainty"):
            action = "answer"

        return InvestigationVerdict(
            action=action,
            p_evidence_quality=p_eq,
            p_needs_visual=p_nv,
            verdict_confidence=verdict_conf,
            low_confidence=low_confidence,
            answers=a,
            decider_ms=ms,
        )
