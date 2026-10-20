"""One-off live test: two-turn StoryStone conversation against the user group cloud."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.agent import HackathonAgent

a = HackathonAgent()

print("=" * 60)
print("TURN 1 — Temple introduction")
print("=" * 60)
r1 = a.chat("I'm visiting Meenakshi Amman Temple in Madurai. Tell me about this temple.")
print(r1["reply"])
print(f"\n[latency: {r1['latency_ms']} ms | decisions: {len(r1['decisions'])}]")

print()
print("=" * 60)
print("TURN 2 — Sculpture investigation")
print("=" * 60)
r2 = a.chat(
    "I found a beautiful figure with four arms, a ring of fire around it, "
    "standing on a small dwarf. It looks like it is dancing. Who is this?"
)
print(r2["reply"])
print(f"\n[latency: {r2['latency_ms']} ms | decisions: {len(r2['decisions'])}]")

if r2["decisions"]:
    print()
    print("DECIDER RECORD:")
    print(json.dumps(r2["decisions"][0], indent=2))
