# Project Brief: StoryStone — The Curious Heritage Detective

## 1. Project Overview

Build **StoryStone**, an AI-powered heritage discovery application that helps tourists understand the stories, mythology, symbolism, and cultural significance behind sculptures found in Indian temples.

The core concept is:

**“Every sculpture has a story. Let AI investigate the clues and discover it.”**

StoryStone should not behave like a generic image-captioning chatbot. It should behave like a curious heritage detective that analyzes a sculpture, researches possible interpretations, evaluates supporting evidence, decides whether further investigation is necessary, and explains the most plausible story with references.

Prioritize a working, impressive end-to-end demonstration over excessive features.

## 2. Technology Constraints

Important constraints:
- Keep the architecture simple.
- Do not introduce a complex multi-agent architecture unless clearly necessary.
- Avoid unnecessary databases, vector stores, microservices, queues, and cloud infrastructure.
- Prefer a minimal local implementation for the first working version.
- Do not hardcode API keys or expose secrets in the frontend.
- Verify current SDK interfaces, model compatibility, and tool APIs against their official documentation rather than inventing methods or assuming compatibility.
- If an external model or search provider is needed, isolate it behind a simple configurable interface.
- Do not assume Kiro itself is the runtime agent. Strands Agents must implement the actual agent behavior.

## 3. User Journey

### Step 1: Select a Temple

The landing page should contain only two mandatory fields:

1. Temple name
2. City

Example:
- Temple name: Meenakshi Amman Temple
- City: Madurai

The user clicks **Discover This Temple**.

### Step 2: Generate the Temple Story

The application researches the selected temple and presents a short introduction containing:

- Historical background
- Important religious and cultural significance
- Major traditional legends
- Architectural or sculptural highlights
- Reliable sources and reference links

This should be generated dynamically using research and AI, not from a hardcoded response.

Store the current temple context in the user's active session so that the user does not need to re-enter the temple details when uploading sculpture photographs.

If the temple identity is ambiguous, ask the user to confirm it.

### Step 3: Upload a Sculpture Photograph

Provide an image upload area with a clear call to action:

**“Found a sculpture that caught your eye? Discover its story.”**

The user uploads a photograph taken at the selected temple.

The application passes the following information to the Strands agent:

- Temple name
- City
- Previously researched temple context
- Uploaded photograph
- Optional user question

Example question: “Who is this figure, and what is the story behind it?”

### Step 4: Investigate the Sculpture

The agent should:

1. Analyze the image using a multimodal model.
2. Describe observable visual details, such as posture, hand gestures, objects, animals, clothing, ornaments, and nearby figures.
3. Generate one or more plausible interpretations.
4. Research relevant mythology, temple history, iconography, and heritage references.
5. Compare the visual clues with information found in reliable sources.
6. Decide whether sufficient evidence exists to present an interpretation.
7. If a critical visual detail is unclear, ask the user for a targeted close-up.
8. If the evidence remains insufficient, communicate uncertainty instead of inventing an answer.
9. Generate a visitor-friendly explanation supported by sources.

The agent must be allowed to choose the next action based on the available evidence. It should not execute every tool in a fixed sequence when some steps are unnecessary.

### Step 5: Present the Story

Display the final result in a visually appealing format with these sections:

- **What You May Be Looking At:** The most plausible identification.
- **Clues in the Sculpture:** The visible features that support the interpretation.
- **The Story Behind It:** The associated mythological or historical narrative.
- **Why It Matters:** Cultural, symbolic, or religious significance.
- **Evidence and Sources:** Links to the references used.
- **Confidence and Limitations:** Explain what is well-supported and what remains uncertain.
- **Explore Further:** Suggested questions or an option to investigate another sculpture.

Clearly distinguish direct visual observations from historical claims and AI-generated hypotheses. Never fabricate citations, historical facts, or confidence percentages.

## 4. Core Feature: The Curious Detective Agent

Implement one Strands agent that can reason about the task and invoke tools when needed.

Suggested tools:

### Tool A: Temple Context Research
Input: Temple name and city.

Purpose:
- Find reliable information about the temple.
- Identify relevant historical, cultural, and mythological context.
- Return concise findings and source URLs.

### Tool B: Sculpture Image Analysis
Input: Image and temple context.

Purpose:
- Identify visible features and potential iconographic clues.
- Describe ambiguities and missing visual information.
- Suggest plausible interpretations without treating them as confirmed facts.

Use a multimodal model through a compatible Strands integration. Avoid building a separate image-analysis service unless necessary.

### Tool C: Heritage Reference Search
Input: Candidate identification, observed clues, and temple context.

Purpose:
- Search for relevant mythology, iconography, historical references, and descriptions of the sculpture or associated narrative.
- Prefer authoritative temple publications, government heritage resources, museums, academic sources, and credible cultural institutions.
- Return source URLs and relevant findings.

### Tool D: Evidence Evaluation
Input: Visual observations, candidate interpretations, and retrieved references.

Purpose:
- Check whether the sources actually support the proposed identification.
- Identify contradictions and alternative interpretations.
- Decide whether to answer, investigate further, request a close-up, or acknowledge uncertainty.

This can be implemented as a dedicated tool or as part of the agent's reasoning. Do not create unnecessary abstractions if a simpler implementation works.

## 5. Agent Decision-Making Requirements

The agent should follow an adaptive investigation loop:

1. Observe the uploaded sculpture.
2. Form plausible hypotheses.
3. Determine which evidence is needed.
4. Use the appropriate tool.
5. Evaluate the returned evidence.
6. Decide whether further investigation is necessary.
7. Repeat within a reasonable tool-call limit.
8. Present the best-supported explanation or acknowledge uncertainty.

Example scenario:

A tourist uploads a sculpture that might depict Murugan and Avvaiyar in the traditional story associated with the fruit of wisdom.

The agent must not assume this interpretation merely because the tourist is visiting a Tamil Nadu temple.

Instead, it should:
- Identify visible figures and objects.
- Check whether the sculpture's composition supports that hypothesis.
- Research the traditional story and search for evidence connecting it to the sculpture.
- Consider alternative interpretations if the visual clues do not match.
- Present the interpretation only with appropriate qualification and supporting references.

If the object held by a figure is too blurry to identify and that detail is important, the agent may ask the tourist to upload a closer photograph of that particular area.

If a close-up is unnecessary, the agent should answer immediately.

Avoid endless research loops. Limit repeated searches and additional image requests.

## 6. Architecture Expectations

Use a straightforward architecture:

- Frontend: Temple selection, temple story, image upload, investigation status, results, and follow-up questions.
- Application backend: Input validation, image handling, session context, and invocation of the Strands agent.
- Strands agent: Reasoning, tool selection, evidence gathering, and investigation decisions.
- Tools: Temple research, image analysis, and heritage reference search.
- External capabilities: Compatible multimodal model and web search or reference retrieval.

Keep the temple context and conversation state available across successive interactions in the same session.

Do not send unnecessary copies of large images or duplicate context to the model. Apply reasonable upload limits and validate file types.

## 7. Suggested User Interface

Design a clean, modern heritage-exploration experience.

The interface should include:

1. A welcome screen with the StoryStone name and tagline.
2. Two mandatory temple fields: temple name and city.
3. A temple discovery card with a sourced introduction.
4. A photograph upload area.
5. A visible investigation status showing stages such as:
   - Observing sculpture
   - Researching possible interpretations
   - Checking historical references
   - Preparing the story
6. A structured story result with sources and uncertainty indicators.
7. Follow-up question input.
8. An option to upload another sculpture from the same temple.

Investigation status must reflect actual backend activity; do not display fabricated progress.

Make the experience mobile-friendly because tourists may use it while walking around a temple.

## 8. Hackathon Scope and Priorities

### Priority 1: Must work
- Temple name and city input.
- Dynamic temple research.
- Image upload.
- Multimodal sculpture analysis.
- Strands agent with tool calling.
- Evidence-backed story generation.
- Source links and uncertainty handling.
- Basic follow-up interaction.

### Priority 2: High-impact enhancement
- Adaptive decision to request a close-up.
- Comparison of multiple plausible interpretations.
- Visible explanation of why the agent selected an interpretation.

### Priority 3: Optional stretch feature
- Upload a second sculpture and explore possible narrative connections.
- Build a small connected-story view.

Do not implement the stretch feature until the complete core journey works.

## 9. Reliability, Safety, and Evaluation

- Treat image interpretations as hypotheses unless supported by adequate evidence.
- Respect that religious imagery can have multiple regional or sectarian interpretations.
- Do not invent the temple's history or attribute a legend to a sculpture without supporting evidence.
- Preserve uncertainty when reliable information cannot be found.
- Cite the actual sources used for factual claims.
- Keep API keys in environment variables.
- Handle invalid images, search failures, unavailable model responses, and ambiguous temple names gracefully.

Create a few test scenarios:

1. A recognizable sculpture with strong supporting references.
2. An ambiguous sculpture with multiple possible interpretations.
3. A blurry photograph requiring a close-up.
4. A sculpture for which no reliable identification can be found.
5. A temple name that matches multiple locations.
6. A search failure that requires a graceful fallback.

## 10. How I Want You to Work

Before writing the full implementation:

1. Inspect the available project files and identify the current state of the repository.
2. Check official Strands Agents documentation and relevant model/tool integrations.
3. Propose a minimal architecture and file structure.
4. Identify required dependencies, environment variables, and external API requirements.
5. Explain any assumptions or blockers.

Then implement the project incrementally.

Start with a working end-to-end vertical slice: temple input → research → image upload → Strands investigation → sourced explanation.

After that, improve the interface and add adaptive evidence gathering.

Create a README containing setup instructions, environment configuration, architecture, and instructions to run the app locally.

Do not stop after producing a design document or code snippets. Implement and test the actual application wherever the environment permits. Report clearly what works, what requires API credentials, and what remains incomplete.

**Final success criterion:** A tourist can enter “Meenakshi Amman Temple” and “Madurai,” receive a researched temple introduction, upload a sculpture photo, and watch StoryStone investigate its possible meaning before presenting an understandable, evidence-backed story. The demonstration must show genuine agent decision-making rather than merely wrapping a single image prompt in a chatbot.