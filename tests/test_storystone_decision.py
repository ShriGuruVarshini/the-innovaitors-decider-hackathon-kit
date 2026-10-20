"""Tests for StoryStone's InvestigationPolicy wiring."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fakes import FakeDecider

from agent.decision import InvestigationPolicy, PATTERN_TAG, QUESTIONS


def _make_policy(verdict_label: str, evidence_yes: float = 0.8, visual_yes: float = 0.1) -> InvestigationPolicy:
    """Build an InvestigationPolicy backed by a FakeDecider that returns preset answers."""
    def rule(state: str, name: str, q: dict) -> object:
        if name == "verdict":
            return verdict_label
        if name == "evidence_quality":
            return evidence_yes  # p(yes)
        if name == "needs_visual_detail":
            return visual_yes   # p(yes)
        return 0.9

    return InvestigationPolicy(FakeDecider(rule))


STATE = (
    "=== TEMPLE CONTEXT ===\nTemple: Brihadeeswarar Temple, Thanjavur\n\n"
    "=== SCULPTURE OBSERVATIONS ===\nFour-armed dancing figure with damaru and flame.\n\n"
    "=== CANDIDATE IDENTIFICATION ===\nNataraja — Shiva as Lord of Dance\n\n"
    "=== RETRIEVED HERITAGE REFERENCES ===\nhttps://en.wikipedia.org/wiki/Nataraja: canonical four arms.\n\n"
    "=== INVESTIGATION QUESTION ===\nWho is this dancing figure?"
)


def test_pattern_tag():
    assert PATTERN_TAG == "#policy"


def test_questions_structure():
    assert set(QUESTIONS.keys()) == {"verdict", "evidence_quality", "needs_visual_detail"}
    assert QUESTIONS["verdict"]["type"] == "choice"
    assert QUESTIONS["evidence_quality"]["type"] == "noul"
    assert QUESTIONS["needs_visual_detail"]["type"] == "noul"
    assert "answer" in QUESTIONS["verdict"]["criteria"]
    assert "investigate_further" in QUESTIONS["verdict"]["criteria"]
    assert "request_closeup" in QUESTIONS["verdict"]["criteria"]
    assert "acknowledge_uncertainty" in QUESTIONS["verdict"]["criteria"]


def test_answer_verdict():
    policy = _make_policy("answer", evidence_yes=0.85)
    v = policy.check(STATE)
    assert v.action == "answer"
    assert not v.low_confidence
    assert len(policy.log) == 1
    assert policy.log[0]["verdict"] == "answer"
    assert policy.log[0]["pattern"] == "#policy"
    assert "decider_ms" in policy.log[0]


def test_investigate_further_verdict():
    policy = _make_policy("investigate_further", evidence_yes=0.3)
    v = policy.check(STATE)
    assert v.action == "investigate_further"


def test_request_closeup_verdict():
    policy = _make_policy("request_closeup", evidence_yes=0.3, visual_yes=0.8)
    v = policy.check(STATE)
    assert v.action == "request_closeup"


def test_acknowledge_uncertainty_verdict():
    policy = _make_policy("acknowledge_uncertainty", evidence_yes=0.1)
    v = policy.check(STATE)
    assert v.action == "acknowledge_uncertainty"


def test_override_answer_when_evidence_too_thin():
    """If decider says 'answer' but evidence quality is very low, override to acknowledge_uncertainty."""
    policy = _make_policy("answer", evidence_yes=0.2)
    v = policy.check(STATE)
    assert v.action == "acknowledge_uncertainty"


def test_override_to_closeup_when_visual_needed():
    """If needs_visual_detail is high and verdict is not 'answer', prefer request_closeup."""
    policy = _make_policy("investigate_further", evidence_yes=0.3, visual_yes=0.9)
    v = policy.check(STATE)
    assert v.action == "request_closeup"


def test_log_record_has_probabilities():
    policy = _make_policy("answer", evidence_yes=0.85)
    v = policy.check(STATE)
    rec = policy.log[0]
    assert "probabilities" in rec
    assert "verdict" in rec["probabilities"]


def test_multiple_checks_appended_to_log():
    policy = _make_policy("answer", evidence_yes=0.85)
    policy.check(STATE)
    policy.check(STATE)
    assert len(policy.log) == 2


def test_low_confidence_flag():
    """With a fake decider returning low confidence (0.4), low_confidence should be True."""
    # FakeDecider returns 0.85 confidence by default; simulate low confidence
    # by using a real low p_yes for the noul (confidence comes from choice confidence)
    # We test the flag path: when verdict confidence < 0.55 via a custom rule
    from decider_kit.client import Decision

    class LowConfDecider:
        last_latency_ms = 10.0
        def ask(self, state, questions, images=None):
            out = {}
            for name, q in questions.items():
                if q["type"] == "choice":
                    opts = list(q["criteria"])
                    probs = {o: (1.0 / len(opts)) for o in opts}  # uniform = low confidence
                    out[name] = Decision.parse({"type": "choice", "choice": opts[0],
                                                "probabilities": probs, "confidence": 0.3})
                else:
                    out[name] = Decision.parse({"type": "noul", "noul": 0.8})
            return out

    policy = InvestigationPolicy(LowConfDecider())
    v = policy.check(STATE)
    assert v.low_confidence is True
