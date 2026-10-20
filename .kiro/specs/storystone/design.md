# StoryStone — Design

## Pattern: #policy  (investigation verdict)

The decider reads the assembled evidence text — observations, candidate identifications, and
retrieved references — and classifies whether the evidence is strong enough to present a story,
needs more research, needs a visual detail, or must acknowledge uncertainty.
This is a language judgement: code cannot do it with an `if` statement.

## State text layout

```
=== TEMPLE CONTEXT ===
Temple: {temple_name}, {temple_city}
Background: {temple_summary}

=== SCULPTURE OBSERVATIONS ===
{observations}   (posture, mudras, attributes, companions, animals, ornaments)

=== CANDIDATE IDENTIFICATION ===
{candidate}      (e.g. "Nataraja — Shiva as Lord of Dance")

=== RETRIEVED HERITAGE REFERENCES ===
{references}     (text snippets + source URLs from web search)

=== INVESTIGATION QUESTION ===
{user_question or "Who is this figure and what is the story behind it?"}
```

## Typed questions (QUESTIONS in decision.py)

```python
"verdict": Decider.choice(
    "What is the appropriate next step given the evidence assembled?",
    {
        "answer":                  "the observations match the references well enough to present a sourced story with reasonable confidence",
        "investigate_further":     "the evidence is suggestive but thin; another search with different terms may strengthen or refute the identification",
        "request_closeup":         "a specific visual detail (object held, hand gesture, inscription) is unclear and would materially change the identification",
        "acknowledge_uncertainty": "conflicting or absent references mean no reliable identification can be made; present what is observable with explicit uncertainty",
    }
)

"evidence_quality": Decider.noul(
    "Is the assembled evidence sufficient and internally consistent to support the candidate identification?",
    {
        "true":  "at least two independent references match the key visual observations without contradiction",
        "false": "references are absent, contradictory, or match only superficial details",
    }
)

"needs_visual_detail": Decider.noul(
    "Is there a specific visual detail in the sculpture that is ambiguous and critical to distinguishing between interpretations?",
    {
        "true":  "a key attribute (weapon, vehicle, mudra, number of arms) is unclear in the photo and changes the identification",
        "false": "the observable details are sufficient or the missing detail would not change the conclusion",
    }
)
```

## Thresholds and actions (in InvestigationPolicy.decide())

```
verdict confidence >= 0.55  → use the verdict label
verdict confidence <  0.55  → default to "answer" but add a low-confidence note
evidence_quality p_yes < 0.4 AND verdict == "answer" → override to "acknowledge_uncertainty"
needs_visual_detail p_yes > 0.65 AND verdict != "answer" → override to "request_closeup"
```

## Seam (where the decider sits)

`InvestigationPolicy` is called from `HackathonAgent.chat()` directly after
`evaluate_evidence` assembles the state text. It is NOT an InterventionHandler — it runs
between tool calls, not before a specific tool. The agent calls tools, then `chat()` calls
the policy, inspects the verdict, and decides whether to call `search_heritage_references`
again or ask the tourist for a close-up.

```
chat(message, images)
  → Agent runs: research_temple / analyze_sculpture / search_heritage_references / evaluate_evidence
  → InvestigationPolicy.check(evidence_state, images=images) → Verdict
  → if "investigate_further": Agent runs search_heritage_references again → re-evaluate → check again (once)
  → if "request_closeup":     return reply asking for close-up
  → if "answer" / "acknowledge_uncertainty": Agent composes final story
  → return {reply, decisions, ...}
```

## Tools

| Tool | Input | Output | Data source |
|---|---|---|---|
| `research_temple` | name, city | history, legends, highlights, sources[] | DuckDuckGo HTML scrape |
| `analyze_sculpture` | image_description, temple_context | observations, candidate, ambiguities | Mock (sculptures.json lookup + LLM description) |
| `search_heritage_references` | candidate, clues, temple_context | references[], source_urls[] | DuckDuckGo HTML scrape |
| `evaluate_evidence` | observations, candidate, references, temple_context, question | state_text (the decider's input) | Assembles text locally |

## Eval-case plan (24 cases)

Split: 12 tune / 12 test, covering:
- Strong match (Nataraja, Ganesha, Murugan) → "answer"
- Thin references → "investigate_further"
- Blurry key attribute → "request_closeup"
- Contradictory/absent references → "acknowledge_uncertainty"
- Near-miss: good observations but only 1 source → "investigate_further" not "answer"
- Near-miss: clear image but no references found → "acknowledge_uncertainty"
- Ambiguous figure (Vishnu vs Murugan with missing attribute) → "request_closeup"

## AgentCore features
Runtime only. Memory and Gateway both disabled.
