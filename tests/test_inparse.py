"""Quick test — run InParseGent on sample JD."""

import json
from agent.nodes.inparse_gent import inparse_gent

with open("data/sample_jds/ml_engineer.txt", "r") as f:
    jd_text = f.read()

state = {
    "raw_jd": jd_text,
    "parsed_jd": {},
    "matched_candidates": [],
    "engaged_candidates": [],
    "final_shortlist": [],
    "logs": []
}

print("🧠 Running InParseGent...\n")
result = inparse_gent(state)

print("📋 Parsed JD:")
print(json.dumps(result["parsed_jd"], indent=2))
print(f"\n📝 Log: {result['logs']}")
