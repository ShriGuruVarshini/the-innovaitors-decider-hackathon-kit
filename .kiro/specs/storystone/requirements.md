# StoryStone — Requirements

## Who it is for
Tourists visiting Indian temples who want to understand the stories behind sculptures they
photograph, without needing a guide or prior knowledge of Hindu iconography.

## User stories

### US-1 Temple introduction
WHEN a tourist provides a temple name and city,
THE agent SHALL call `research_temple` to retrieve historical background, legends, and
architectural highlights with source URLs,
AND SHALL present a structured introduction before asking for a sculpture photo.

### US-2 Sculpture investigation
WHEN a tourist uploads a sculpture photo (with optional question),
THE agent SHALL call `analyze_sculpture` to extract visible iconographic details (posture,
mudras, attributes, animals, companions),
AND SHALL call `search_heritage_references` to find matching mythology and iconography sources,
AND SHALL call `evaluate_evidence` to assemble the full evidence text,
AND SHALL ask Strands Decider 2B the investigation verdict BEFORE presenting any story.

### US-3 Policy decision — investigation verdict
WHEN the evidence text is assembled,
THE system SHALL ask Strands Decider 2B:
  - verdict (choice): answer | investigate_further | request_closeup | acknowledge_uncertainty
  - evidence_quality (noul): is the evidence sufficient and non-contradictory?
  - needs_visual_detail (noul): is a specific visual detail unclear and important to the interpretation?
PAIRED WITH the hosted Strands Decider 2B API (AWS User Group Madurai).

### US-4 Verdict actions
WHEN verdict == "answer":
  THE agent SHALL present the full structured story (identification, clues, narrative, significance,
  sources, confidence, explore further).
WHEN verdict == "investigate_further":
  THE agent SHALL call `search_heritage_references` with different search terms (once more only),
  THEN SHALL re-evaluate and present the best-supported story.
WHEN verdict == "request_closeup":
  THE agent SHALL ask the tourist for a close-up photo of the specific unclear detail.
WHEN verdict == "acknowledge_uncertainty":
  THE agent SHALL present what is known with explicit uncertainty, and SHALL NOT fabricate
  citations or identifications.

### US-5 Low-confidence handling
WHEN the decider's confidence on `verdict` is below 0.55,
THE agent SHALL present the story with an added note that the identification is tentative,
AND SHALL suggest follow-up questions.

### US-6 Follow-up interaction
WHEN the tourist asks a follow-up question on the same sculpture,
THE agent SHALL answer using the already-assembled context without repeating the full
investigation.

### US-7 Graceful failure
WHEN web search returns no results or an error,
THE agent SHALL fall back to mock data in `agent/data/sculptures.json`,
AND SHALL note that references are from built-in heritage knowledge.

### US-8 Amazon Bedrock (deployment)
The deployed agent SHALL run on Amazon Bedrock AgentCore Runtime with Amazon Bedrock
(Amazon Nova Pro by default) as the generative model.
During local development it runs on the AWS User Group Madurai cloud (qwen3.5-4b).
