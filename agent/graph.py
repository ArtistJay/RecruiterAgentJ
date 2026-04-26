"""agentJ — LangGraph pipeline with conditional routing."""

from langgraph.graph import StateGraph, START, END
from agent.state import AgentState
from agent.nodes.inparse_gent import inparse_gent
from agent.nodes.scout_gent import scout_gent
from agent.nodes.convo_gent import convo_gent
from agent.nodes.final_gent import final_gent


def should_engage(state: AgentState) -> str:
    """
    Conditional routing after ScoutGent:
    - If no viable candidates found (or all scores < 25), skip conversations
    - Otherwise, proceed to conversational engagement
    """
    matched = state.get("matched_candidates", [])

    if not matched:
        return "skip_to_final"

    top_score = matched[0]["match_score"]  # Already sorted descending
    viable_count = sum(1 for c in matched if c["match_score"] >= 25)

    if viable_count == 0 or top_score < 25:
        return "skip_to_final"

    return "engage"


def passthrough_to_final(state: AgentState) -> dict:
    """
    When ConvoGent is skipped, pass matched candidates to FinalGent
    with default interest scores.
    """
    matched = state.get("matched_candidates", [])
    engaged = []

    for cand in matched:
        engaged_cand = {**cand}
        engaged_cand["interest_score"] = 0
        engaged_cand["interest_breakdown"] = {
            "enthusiasm": 0, "availability": 0,
            "salary_alignment": 0, "role_fit_perception": 0, "red_flags": 0,
        }
        engaged_cand["interest_explanations"] = {}
        engaged_cand["key_signals"] = ["Conversation skipped — low match score"]
        engaged_cand["conversation_summary"] = "Not engaged — match score below threshold."
        engaged_cand["transcript"] = []
        engaged_cand["conversation_text"] = ""
        engaged.append(engaged_cand)

    print(f"⏭️  SkipGent: Skipped conversations for {len(engaged)} low-match candidates")

    return {
        "engaged_candidates": engaged,
        "logs": [f"SkipGent: Skipped ConvoGent — no candidates above match threshold"]
    }


# Build the workflow
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("inparse_gent", inparse_gent)
workflow.add_node("scout_gent", scout_gent)
workflow.add_node("convo_gent", convo_gent)
workflow.add_node("skip_gent", passthrough_to_final)
workflow.add_node("final_gent", final_gent)

# Define flow
workflow.add_edge(START, "inparse_gent")
workflow.add_edge("inparse_gent", "scout_gent")

# Conditional routing: engage or skip based on match quality
workflow.add_conditional_edges(
    "scout_gent",
    should_engage,
    {
        "engage": "convo_gent",
        "skip_to_final": "skip_gent",
    }
)

workflow.add_edge("convo_gent", "final_gent")
workflow.add_edge("skip_gent", "final_gent")
workflow.add_edge("final_gent", END)

# Compile
graph = workflow.compile()

if __name__ == "__main__":
    print("✅ AgentJ LangGraph compiled!")
    print("   Pipeline: InParseGent → ScoutGent → [ConvoGent | SkipGent] → FinalGent → END")
