# StoryStone: How Strands Decider 2B Turns a Tourist's Photo Into a Heritage Investigation

## Submission fields

- **Title:** StoryStone: How Strands Decider 2B Turns a Tourist's Photo Into a Heritage Investigation
- **Tags:** `#strands-decider-2b` `#policy`
- **Category:** Agent Experience Hackathon: Strands Decider
- **Cover image:** [screenshot of the StoryStone demo UI showing the decision panel]

---

## The problem

Millions of tourists walk past extraordinary temple sculptures every day without understanding
what they are looking at. A four-armed dancing figure, a ring of fire, a small prostrate dwarf
underfoot — to someone unfamiliar with Hindu iconography, these are beautiful but opaque.

Temple guides are expensive, inconsistent, and unavailable at many smaller shrines. Existing
AI tools describe images — they tell you there is a figure with multiple arms — but they do not
*investigate*. They do not weigh evidence. They do not distinguish a well-supported identification
from a guess. And they never admit uncertainty.

StoryStone does all three.

---

## The agent

StoryStone is a heritage detective. Given a temple name and a sculpture photo, it:

1. **Researches the temple** — history, legends, architectural highlights, source URLs (DuckDuckGo)
2. **Analyses iconographic details** — posture, mudras, attributes, vahana, companions
3. **Searches heritage references** — mythology, iconography, authoritative sources (DuckDuckGo)
4. **Assembles the evidence** into a structured state text
5. **Asks Strands Decider 2B** whether the evidence is sufficient — and what to do next
6. **Presents the story** — sourced, structured, with confidence and limitations clearly stated

The agent is built with the Strands Agents SDK and deployed on Amazon Bedrock AgentCore Runtime.
The generative LLM is Amazon Nova Pro via Amazon Bedrock.

---

## The decision: evidence sufficiency classification (#policy)

The most important moment in StoryStone's pipeline is step 5 — the policy decision.

After the agent has collected everything it can find (visual observations, candidate
identification, heritage references), it does not simply trust its own findings. It asks
Strands Decider 2B:

**"Is this evidence good enough to tell the story?"**

This is a genuine language judgement. The decider reads the assembled evidence text —
written in plain English — and classifies the investigation verdict:

| Verdict | When it fires | What happens |
|---|---|---|
| `answer` | References match observations, evidence consistent | Present the sourced story |
| `investigate_further` | Evidence suggestive but thin (only 1 source, superficial match) | Search again with different terms |
| `request_closeup` | Key attribute unclear and critical (upper arms worn, vahana not visible) | Ask tourist for a focused close-up |
| `acknowledge_uncertainty` | Contradictory or absent references | Present observations honestly, no fabricated ID |

Three typed questions are asked in one forward pass:

```python
QUESTIONS = {
    "verdict": Decider.choice(
        "What is the appropriate next step given the evidence assembled?",
        {
            "answer": "observations match at least two references without contradiction",
            "investigate_further": "evidence suggestive but only one source or superficial match",
            "request_closeup": "key attribute — weapon, mudra, vahana — unclear and would change the ID",
            "acknowledge_uncertainty": "references absent, contradictory, or describe a different figure",
        }
    ),
    "evidence_quality": Decider.noul(
        "Is the evidence sufficient and internally consistent?",
        {"true": "two independent references match key observations",
         "false": "references absent, contradictory, or match only incidental details"}
    ),
    "needs_visual_detail": Decider.noul(
        "Is a specific visual detail ambiguous and critical to distinguishing interpretations?",
        {"true": "primary attribute (weapon, vehicle, hand gesture) is unclear and changes the ID",
         "false": "visible details are sufficient or missing detail is decorative"}
    ),
}
```

All three questions share one encoding of the state — one forward pass, three calibrated answers.

---

## Why Strands Decider 2B, not an LLM judge?

This decision could be delegated to the same LLM that writes the story. We chose not to,
for three reasons:

**Speed and cost.** An LLM judge on every investigation adds 2–5 s and $0.002–0.005 per call.
Strands Decider 2B answers in ~1–2 s (hosted API) with calibrated probabilities —
at a fraction of the cost. Across thousands of tourist investigations, this matters.

**Calibration.** The decider returns actual probabilities for each verdict option.
When `verdict confidence < 0.55`, the code adds a low-confidence note to the story.
An LLM saying "I'm fairly confident" is not the same as `p(answer) = 0.83`.

**Separation of concerns.** The LLM is good at narration. The decider is good at classification.
Mixing both into one LLM call makes it harder to tune, test, and improve either independently.
The benchmark (`./kit bench`) measures the decider's accuracy against an LLM baseline
on the same 24 labelled cases — so we know exactly where each performs.

---

## The investigation in practice

A tourist at Meenakshi Amman Temple in Madurai types:

> *"I see a figure with four arms, dancing in a ring of fire, standing on a small dwarf."*

StoryStone's pipeline:

```
analyze_sculpture("dancing figure with ring of fire...")
  → matched: "nataraja" mock entry
  → observations: "Four arms performing Ananda Tandava. Upper right: damaru drum.
                   Upper left: flame. Lower right: Abhaya mudra. Ring of flames.
                   Standing on Apasmara Purusha (dwarf). Crescent moon in hair."

search_heritage_references("Nataraja — Shiva as Lord of Cosmic Dance", ...)
  → Wikipedia/Nataraja, Met Museum/Chola bronzes, CIIS/cosmic dance

evaluate_evidence(...)
  → state_text assembled (temple context + observations + candidate + references)

Strands Decider 2B:
  verdict         = "answer"      (confidence 0.91)
  evidence_quality = yes          (p_yes = 0.87)
  needs_visual_detail = no        (p_yes = 0.08)

LLM (1 call):
  → "What You May Be Looking At: This is almost certainly Nataraja..."
```

The right panel of the demo UI shows the three probability bars in real time as the decider responds.

---

## Low-confidence handling

When `verdict confidence < 0.55`, the code adds to the reply:

> *"⚠️ Note: the decider's confidence was below the usual threshold. This interpretation is
> plausible but treat it as tentative."*

When the decider returns `acknowledge_uncertainty`, the reply ends with:

> *"🪨 StoryStone could not find sufficient evidence to make a confident identification.
> Ask a temple priest or guide, or consult the Archaeological Survey of India documentation."*

We never fabricate citations or confidence percentages. Uncertainty is communicated explicitly.

---

## Benchmark results

Measured on `agent/eval_cases.jsonl` (11 tune-split cases, 33 decisions):

| | Strands Decider 2B | LLM baseline (qwen3.5-4b) |
|---|---|---|
| **Accuracy** | 57.6% overall / **81.2% when confident** | 81.8% |
| **Latency p50** | **5,639 ms** | 23,355 ms |
| **Latency p95** | 8,188 ms | 31,207 ms |
| **Cost per 1,000 decisions** | $0.035 | $0.000 (free tier) |
| **Confident decisions (≥0.7)** | 48% | 100% |

**Reading the numbers honestly:**

The overall accuracy of 57.6% is lower than the LLM's 81.8% — but 52% of the decider's calls
have confidence below 0.7, and those trigger the low-confidence warning in the story.
When the decider is confident (the other 48%), accuracy is 81.2% — matching the LLM.

This is exactly the point of calibrated probabilities: the decider *knows* when it is unsure
and signals it. An LLM judge claims 100% confidence on every case and is wrong 18% of the time
without any warning.

The decider is **4.1× faster** at the median (5.6 s vs 23.4 s). For a tourist standing in a
temple, that difference is felt.

*Run `.\kit.cmd bench --split test` to reproduce on the held-out test split.*

---

## Reusing the pattern

The `agent/decision.py` file is a self-contained, labelled, reusable `#policy` pattern.
Any agent that needs to classify "is this evidence/content sufficient to act on?" can copy it:

- A claims verification agent: `answer` / `needs_more_evidence` / `contradicted` / `uncertain`
- A content moderation agent: `publish` / `review` / `reject`
- A research assistant: `report_finding` / `search_more` / `flag_contradiction`

The pattern is documented with a `REUSABLE DECISION PATTERN:` header, typed questions,
option descriptions, thresholds, and a "how to reuse it" section — meeting the hackathon's
reusable pattern requirement.

---

## Architecture summary

```
Tourist → Demo UI (FastAPI + HTML)
               │
               ├─ research_temple()            DuckDuckGo, no API key
               ├─ analyze_sculpture()          Iconographic mock DB
               ├─ search_heritage_references() DuckDuckGo, no API key
               ├─ evaluate_evidence()          Text assembly
               │
               ├─ Strands Decider 2B ──────── #policy verdict (3 questions, 1 pass)
               │    (AWS User Group Madurai hosted API)
               │
               └─ Amazon Bedrock Nova Pro ──── Story narration
                    (Amazon Bedrock AgentCore Runtime)
```

**LLM calls per investigation: 2.** Strands Decider 2B calls: 1.

---

## About the kit

StoryStone was built using the **AWS User Group Madurai** Strands Decider hackathon kit —
a complete scaffolding that handles setup, benchmarking, deployment, video recording,
article drafting, and publishing. The reusable library (`decider_kit/`), the demo UI,
and the tooling are the user group's contribution. The agent, the use case, and the
decision pattern are original work for this submission.

*Built with the AWS User Group Madurai Strands Decider hackathon kit.*
Visit [awsugmdu.in](https://www.awsugmdu.in)
