import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agent.tools import research_temple, analyze_sculpture, search_heritage_references, evaluate_evidence
print("tool type:", type(research_temple))
print("has func:", hasattr(research_temple, 'func'))
print("callable direct:", callable(research_temple))
# Check what attrs exist
attrs = [a for a in dir(research_temple) if not a.startswith('__')]
print("attrs:", attrs[:20])
# Try calling directly
result = research_temple("Meenakshi Amman Temple", "Madurai")
print("direct call result type:", type(result))
print("keys:", list(result.keys()) if isinstance(result, dict) else "not dict")
