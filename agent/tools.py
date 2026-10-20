"""StoryStone tools: temple research, sculpture analysis, heritage reference search, evidence assembly.

Four tools the heritage detective uses in sequence:
  1. research_temple        — web search for temple history, legends, highlights and sources
  2. analyze_sculpture      — mock iconographic analysis (observations, candidate, ambiguities)
  3. search_heritage_references — web search for mythology, iconography and heritage evidence
  4. evaluate_evidence      — assembles the state text passed to Strands Decider 2B

All web search uses DuckDuckGo's free HTML endpoint (no API key). Falls back to
agent/data/sculptures.json when search fails or returns nothing.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from strands import tool

_DATA_FILE = Path(__file__).parent / "data" / "sculptures.json"
_cache: dict[str, Any] | None = None


def _data() -> dict[str, Any]:
    global _cache
    if _cache is None:
        _cache = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
    return _cache


# ---------------------------------------------------------------------------
# DuckDuckGo HTML scrape — no API key, free, rate-limited
# ---------------------------------------------------------------------------

def _ddg_search(query: str, max_results: int = 4) -> list[dict[str, str]]:
    """Search DuckDuckGo and return a list of {title, url, snippet} dicts.

    Uses the lite HTML interface which works without JavaScript and without an API key.
    Returns [] on any network or parse error (caller falls back to mock data).
    """
    try:
        import urllib.parse
        import urllib.request

        encoded = urllib.parse.quote_plus(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (StoryStone heritage research bot)",
                "Accept": "text/html",
            },
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        # Parse result blocks: DDG lite uses <div class="result"> with <a class="result__a">
        results: list[dict[str, str]] = []
        # Match result links
        link_pattern = re.compile(
            r'<a[^>]+class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.S
        )
        snippet_pattern = re.compile(
            r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>', re.S
        )
        links = link_pattern.findall(html)
        snippets = [re.sub(r"<[^>]+>", "", s) for s in snippet_pattern.findall(html)]
        for i, (href, title_html) in enumerate(links[:max_results]):
            title = re.sub(r"<[^>]+>", "", title_html).strip()
            snippet = snippets[i].strip() if i < len(snippets) else ""
            # DDG lite wraps URLs in a redirect; extract the real URL
            real_url = href
            if "uddg=" in href:
                m = re.search(r"uddg=([^&]+)", href)
                if m:
                    import urllib.parse as up
                    real_url = up.unquote(m.group(1))
            if title and real_url.startswith("http"):
                results.append({"title": title, "url": real_url, "snippet": snippet})
        return results
    except Exception:
        return []


def _clean_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


# ---------------------------------------------------------------------------
# Tool 1: Temple research
# ---------------------------------------------------------------------------

@tool
def research_temple(temple_name: str, city: str) -> dict[str, Any]:
    """Research a temple's history, legends, highlights and source URLs using web search.

    Returns a dict with keys: name, city, summary, highlights (list), sources (list of URLs).
    Falls back to built-in heritage knowledge when search is unavailable.
    """
    # Try web search first
    query = f"{temple_name} {city} temple history legend significance"
    results = _ddg_search(query, max_results=5)

    # Also try to find the template key in local data (case-insensitive)
    key = temple_name.lower().strip()
    local = _data().get("temples", {}).get(key)

    if results:
        # Build a summary from search snippets
        snippets = [r["snippet"] for r in results if r["snippet"]]
        sources = [r["url"] for r in results]
        summary_parts = snippets[:3]
        summary = " ".join(summary_parts) if summary_parts else (
            local["summary"] if local else f"{temple_name} is a significant temple in {city}."
        )
        highlights = local["highlights"] if local else []
        # Add local sources if available
        if local:
            for s in local.get("sources", []):
                if s not in sources:
                    sources.append(s)
        return {
            "name": temple_name,
            "city": city,
            "summary": summary[:1200],
            "highlights": highlights,
            "sources": sources[:6],
            "source": "web_search",
        }

    # Fallback: local mock data
    if local:
        return {**local, "source": "built_in_knowledge"}

    # Generic fallback
    return {
        "name": temple_name,
        "city": city,
        "summary": (
            f"{temple_name} in {city} is a Hindu temple of historical and religious significance. "
            "Detailed information was not available at this time."
        ),
        "highlights": [],
        "sources": [],
        "source": "fallback",
    }


# ---------------------------------------------------------------------------
# Tool 2: Sculpture image analysis (mock)
# ---------------------------------------------------------------------------

_MOCK_DESCRIPTIONS = {
    "dancing figure": "nataraja",
    "dance": "nataraja",
    "ring of fire": "nataraja",
    "elephant": "ganesha",
    "elephant head": "ganesha",
    "trunk": "ganesha",
    "mouse": "ganesha",
    "spear": "murugan",
    "vel": "murugan",
    "peacock": "murugan",
    "rooster": "murugan",
    "teacher": "dakshinamurthy",
    "banyan": "dakshinamurthy",
    "seated sage": "dakshinamurthy",
    "chin mudra": "dakshinamurthy",
    "damaged": "ambiguous_figure",
    "unclear": "ambiguous_figure",
    "blurry": "ambiguous_figure",
    "worn": "ambiguous_figure",
    "hard to see": "ambiguous_figure",
}


@tool
def analyze_sculpture(image_description: str, temple_context: str) -> dict[str, Any]:
    """Analyze a sculpture's visible iconographic details and generate candidate identifications.

    In production this uses a multimodal model; currently returns rich mock observations
    drawn from the heritage knowledge base. The image_description (from the user or from
    earlier multimodal analysis) is used to select the best-matching mock entry.

    Returns: observations (str), candidate (str), ambiguities (list[str]), needs_closeup (bool).
    """
    desc_lower = image_description.lower()
    matched_key = None
    for keyword, sculpture_key in _MOCK_DESCRIPTIONS.items():
        if keyword in desc_lower:
            matched_key = sculpture_key
            break

    sculptures = _data().get("sculptures", {})
    if matched_key and matched_key in sculptures:
        s = sculptures[matched_key]
        needs_closeup = matched_key == "ambiguous_figure"
        ambiguities: list[str] = []
        if needs_closeup:
            ambiguities = [
                "The primary attribute in the upper hands is damaged or worn — cannot distinguish chakra (Vishnu) from vel (Murugan)",
                "No vahana (vehicle) is clearly visible at the base",
            ]
        return {
            "observations": s["observations"],
            "candidate": s["candidate"],
            "iconographic_notes": s["iconography"],
            "ambiguities": ambiguities,
            "needs_closeup": needs_closeup,
            "matched_sculpture": matched_key,
        }

    # Generic fallback for unrecognised descriptions
    return {
        "observations": (
            f"The sculpture shows a figure with ornate jewellery and traditional attire. "
            f"Based on the temple context ({temple_context[:120]}...), this may depict a deity "
            f"associated with this temple's primary tradition. Visible details: {image_description[:300]}."
        ),
        "candidate": "Unidentified deity — further iconographic analysis needed",
        "iconographic_notes": "Insufficient distinguishing features observed for confident identification.",
        "ambiguities": ["Primary attribute unclear", "Posture and mudra not definitively identified"],
        "needs_closeup": True,
        "matched_sculpture": None,
    }


# ---------------------------------------------------------------------------
# Tool 3: Heritage reference search
# ---------------------------------------------------------------------------

@tool
def search_heritage_references(
    candidate: str, clues: str, temple_context: str, search_attempt: int = 1
) -> dict[str, Any]:
    """Search for heritage references, mythology, and iconography supporting a candidate identification.

    Uses DuckDuckGo web search. Falls back to built-in reference data.
    Returns: references (list of {url, text}), found (bool), search_terms (str).
    """
    # Vary the query on the second attempt to find different sources
    if search_attempt == 1:
        search_terms = f"{candidate} iconography mythology significance Hindu temple"
    else:
        candidate_short = candidate.split("—")[0].strip().split("(")[0].strip()
        search_terms = f"{candidate_short} sculpture symbolism attributes meaning Agama Shastra"

    results = _ddg_search(search_terms, max_results=5)

    if results:
        refs = [{"url": r["url"], "text": r["snippet"]} for r in results if r["snippet"]]
        return {
            "references": refs[:4],
            "found": len(refs) > 0,
            "search_terms": search_terms,
            "source": "web_search",
        }

    # Fallback: look up the matching sculpture in local data
    sculptures = _data().get("sculptures", {})
    for key, s in sculptures.items():
        if key in candidate.lower() or any(
            k in candidate.lower() for k in [key, s["candidate"].split("—")[0].strip().lower()]
        ):
            return {
                "references": s.get("sources", []),
                "found": True,
                "search_terms": search_terms,
                "source": "built_in_knowledge",
            }

    return {
        "references": [],
        "found": False,
        "search_terms": search_terms,
        "source": "fallback",
    }


# ---------------------------------------------------------------------------
# Tool 4: Evidence assembly (builds the state text for the decider)
# ---------------------------------------------------------------------------

@tool
def evaluate_evidence(
    temple_name: str,
    temple_city: str,
    temple_summary: str,
    observations: str,
    candidate: str,
    references: str,
    user_question: str = "",
) -> dict[str, str]:
    """Assemble all evidence into the structured state text that Strands Decider 2B reads.

    The state text layout matches exactly what the decider expects (see design.md).
    Returns: state_text (str) — the complete evidence package ready for the policy check.
    """
    question = user_question or "Who is this figure, and what is the story behind it?"
    state = (
        "=== TEMPLE CONTEXT ===\n"
        f"Temple: {temple_name}, {temple_city}\n"
        f"Background: {temple_summary[:600]}\n\n"
        "=== SCULPTURE OBSERVATIONS ===\n"
        f"{observations}\n\n"
        "=== CANDIDATE IDENTIFICATION ===\n"
        f"{candidate}\n\n"
        "=== RETRIEVED HERITAGE REFERENCES ===\n"
        f"{references}\n\n"
        "=== INVESTIGATION QUESTION ===\n"
        f"{question}"
    )
    return {"state_text": state}


TOOLS = [research_temple, analyze_sculpture, search_heritage_references, evaluate_evidence]
