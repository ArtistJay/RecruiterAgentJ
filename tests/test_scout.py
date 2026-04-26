"""Test InParseGent + ScoutGent together."""

import json
from agent.nodes.inparse_gent import inparse_gent
from agent.nodes.scout_gent import scout_gent

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

# Agent 1
print("=" * 60)
print("🧠 AGENT 1: InParseGent")
print("=" * 60)
result1 = inparse_gent(state)
state["parsed_jd"] = result1["parsed_jd"]
state["logs"] += result1["logs"]
print(f"   Role: {state['parsed_jd'].get('job_title')}")
print(f"   Must-have: {state['parsed_jd'].get('must_have_skills')}")

# Agent 2
print("\n" + "=" * 60)
print("🔍 AGENT 2: ScoutGent")
print("=" * 60)
result2 = scout_gent(state)
state["matched_candidates"] = result2["matched_candidates"]
state["logs"] += result2["logs"]

# Results
print("\n" + "=" * 60)
print("📊 TOP CANDIDATES BY MATCH SCORE")
print("=" * 60)
for i, c in enumerate(state["matched_candidates"], 1):
    print(f"\n  #{i} {c['name']}")
    print(f"     Role: {c['current_role']} at {c['company']}")
    print(f"     Match Score: {c['match_score']}")
    bd = c['score_breakdown']
    print(f"     Skills: {bd['skills']} | Exp: {bd['experience']} | Edu: {bd['education']} | Loc: {bd['location']} | Bonus: {bd['bonus']}")
    print(f"     Strengths: {', '.join(c['strengths'][:3])}")
    print(f"     Gaps: {', '.join(c['gaps'][:3])}")
    print(f"     Assessment: {c['overall_assessment'][:120]}...")

print(f"\n📝 Logs: {state['logs']}")
