"""Full pipeline test — all 4 agents end-to-end."""

import json
from agent.graph import graph

# Load sample JD
with open("data/sample_jds/ml_engineer.txt", "r") as f:
    jd_text = f.read()

# Initial state
initial_state = {
    "raw_jd": jd_text,
    "parsed_jd": {},
    "matched_candidates": [],
    "engaged_candidates": [],
    "final_shortlist": [],
    "logs": []
}

print("🚀 AgentJ — Full Pipeline Test")
print("=" * 70)

# Run the full graph
result = graph.invoke(initial_state)

# Display final results
print("\n" + "=" * 70)
print("🏆 FINAL RANKED SHORTLIST")
print("=" * 70)

for c in result["final_shortlist"]:
    print(f"\n  #{c['rank']} {c['name']}")
    print(f"     Role: {c['current_role']} at {c['company']}")
    print(f"     📈 Match: {c['match_score']} | 💬 Interest: {c['interest_score']} | 🎯 Combined: {c['combined_score']}")
    print(f"     📋 Recommendation: {c['recommendation']}")
    print(f"     ✅ Strengths: {', '.join(c['strengths'][:3])}")
    print(f"     ❌ Gaps: {', '.join(c['gaps'][:3])}")
    print(f"     💡 Signals: {', '.join(c['key_signals'][:3])}")
    print(f"     📝 {c.get('conversation_summary', 'N/A')[:120]}...")
    if c.get('final_reasoning'):
        print(f"     🎯 Reasoning: {c['final_reasoning'][:120]}...")

print(f"\n📝 Full Logs:")
for log in result["logs"]:
    print(f"   → {log}")

# Save full output for submission
output_path = "docs/sample_outputs/full_pipeline_output.json"
with open(output_path, "w") as f:
    json.dump(result, f, indent=2, default=str)
print(f"\n💾 Full output saved to {output_path}")
