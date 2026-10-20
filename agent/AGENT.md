# Use case

- **Pitch:** StoryStone — Every sculpture has a story. StoryStone investigates the clues and discovers it.
- **Who it is for:** Tourists visiting Indian temples who want to understand the mythological and
  historical stories behind sculptures they photograph, without needing a guide or specialist knowledge.
- **Features:**
  - Dynamic temple introduction with history, legends, and source links from web research;
  - Iconographic sculpture analysis — posture, mudras, attributes, companions, ornaments;
  - Adaptive investigation loop: the decider decides whether to present the story, dig deeper,
    ask for a close-up, or acknowledge uncertainty;
  - Evidence-backed story with sourced references, confidence notes, and "explore further" prompts;
  - Follow-up question support on the same sculpture without re-running the full investigation.
- **The decision handed to Strands Decider 2B:** after assembling temple context, visual
  observations, candidate identification, and retrieved heritage references, the decider reads
  the evidence text and classifies the investigation verdict: answer / investigate_further /
  request_closeup / acknowledge_uncertainty. (`#policy`)
- **Why a decision model:** the verdict requires reading and weighing prose evidence — whether
  references actually match visual observations, whether an ambiguity is critical, whether sources
  contradict each other. An `if` statement on counts or confidence numbers cannot make this
  judgement reliably.
- **Amazon Bedrock:** the conversation, temple research synthesis, and story composition
  (Amazon Nova Pro by default). The deployed agent runs on Amazon Bedrock AgentCore Runtime.
