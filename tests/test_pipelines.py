"""Pipeline streaming test — all 4 agents end-to-end."""

import json
import os
from agent.graph import graph

# Load sample JD
jd_path = "data/sample_jds/ml_engineer.txt"
with open(jd_path, "r") as f:
    jd_text = f.read()

# Initialize State
initial_state = {
    "raw_jd": jd_text,
    "parsed_jd": {},
    "matched_candidates": [],
    "engaged_candidates": [],
    "final_shortlist": [],
    "logs": []
}

print("🚀 Starting AgentJ Pipeline: InParseGent -> ScoutGent -> ConvoGent -> FinalGent")
print("-" * 60)

# Run the graph
for output in graph.stream(initial_state):
    for node, data in output.items():
        print(f"\n✅ Node [{node}] finished.")
        if "logs" in data:
            for log in data["logs"]:
                print(f"   📜 {log}")

        if node == "scout_gent":
            print("\n🏆 RANKED CANDIDATES:")
            for i, cand in enumerate(data["matched_candidates"], 1):
                print(f"   {i}. {cand['name']:20} | Match: {cand['match_score']}% | Role: {cand['current_role']}")

print("\n✨ Pipeline Test Complete.")
