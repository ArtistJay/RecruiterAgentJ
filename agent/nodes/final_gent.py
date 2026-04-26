"""
FinalGent — Agent 4: Ranking & Final Output

Combines Match Score + Interest Score, produces final
ranked shortlist with recommendations.
"""

import json
from agent.state import AgentState
from agent.llm_config import get_llm
from agent.tools.scoring import calculate_combined_score, get_recommendation
from agent.prompts.ranking_prompt import RANKING_PROMPT


def _extract_json_array(content: str) -> list:
    """Extract JSON array from LLM response."""
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]
    
    start = content.find("[")
    end = content.rfind("]") + 1
    if start != -1 and end > start:
        return json.loads(content[start:end])
    return json.loads(content.strip())


def final_gent(state: AgentState) -> dict:
    """Combine scores, rank candidates, produce final output."""
    
    engaged = state["engaged_candidates"]
    parsed_jd = state["parsed_jd"]
    llm = get_llm("ranking")
    
    print(f"📊 FinalGent: Ranking {len(engaged)} candidates...\n")
    
    # Step 1: Calculate combined scores
    for cand in engaged:
        match_s = cand.get("match_score", 0)
        interest_s = cand.get("interest_score", 0)
        combined = calculate_combined_score(match_s, interest_s)
        cand["combined_score"] = combined
        cand["recommendation"] = get_recommendation(combined)
    
    # Sort by combined score
    engaged.sort(key=lambda x: x["combined_score"], reverse=True)
    
    # Step 2: LLM final assessment
    candidates_summary = ""
    for c in engaged:
        candidates_summary += (
            f"\n- {c['name']} (ID: {c.get('candidate_id', 'N/A')})\n"
            f"  Match Score: {c.get('match_score', 0)}, "
            f"Interest Score: {c.get('interest_score', 0)}, "
            f"Combined: {c['combined_score']}\n"
            f"  Strengths: {', '.join(c.get('strengths', []))}\n"
            f"  Gaps: {', '.join(c.get('gaps', []))}\n"
            f"  Conversation: {c.get('conversation_summary', 'N/A')}\n"
        )
    
    prompt = RANKING_PROMPT.format(
        num_candidates=len(engaged),
        job_title=parsed_jd.get("job_title", ""),
        candidates_summary=candidates_summary,
    )
    
    try:
        response = llm.invoke(prompt)
        llm_rankings = _extract_json_array(response.content)
        
        # Merge LLM insights into candidate records
        llm_map = {r.get("candidate_id", r.get("name", "")): r for r in llm_rankings}
        
        for cand in engaged:
            cid = cand.get("candidate_id", "")
            cname = cand.get("name", "")
            llm_rec = llm_map.get(cid, llm_map.get(cname, {}))
            
            if llm_rec:
                cand["final_reasoning"] = llm_rec.get("reasoning", "")
                cand["risk_factors"] = llm_rec.get("risk_factors", [])
                cand["next_steps"] = llm_rec.get("next_steps", "")
                # Override recommendation with LLM's if available
                if llm_rec.get("recommendation"):
                    cand["recommendation"] = llm_rec["recommendation"]
    except Exception as e:
        print(f"   ⚠️ LLM ranking enhancement failed: {e}")
        for cand in engaged:
            cand["final_reasoning"] = "Based on combined match and interest scores."
            cand["risk_factors"] = []
            cand["next_steps"] = "Schedule interview"
    
    # Build final shortlist
    final = []
    for rank, cand in enumerate(engaged, 1):
        final.append({
            "rank": rank,
            "candidate_id": cand.get("candidate_id", ""),
            "name": cand.get("name", ""),
            "current_role": cand.get("current_role", ""),
            "company": cand.get("company", ""),
            "match_score": cand.get("match_score", 0),
            "interest_score": cand.get("interest_score", 0),
            "combined_score": cand.get("combined_score", 0),
            "recommendation": cand.get("recommendation", ""),
            "strengths": cand.get("strengths", []),
            "gaps": cand.get("gaps", []),
            "score_breakdown": cand.get("score_breakdown", {}),
            "interest_breakdown": cand.get("interest_breakdown", {}),
            "conversation_summary": cand.get("conversation_summary", ""),
            "key_signals": cand.get("key_signals", []),
            "transcript": cand.get("transcript", []),
            "final_reasoning": cand.get("final_reasoning", ""),
            "risk_factors": cand.get("risk_factors", []),
            "next_steps": cand.get("next_steps", ""),
            "explanations": cand.get("explanations", {}),
            "interest_explanations": cand.get("interest_explanations", {}),
            "actual_turns": cand.get("actual_turns", 0),
            "max_turns_allowed": cand.get("max_turns_allowed", 0),
        })
    
    print(f"📊 FinalGent: Ranking complete!")
    
    return {
        "final_shortlist": final,
        "logs": [f"FinalGent: Final ranking of {len(final)} candidates complete. Top: {final[0]['name']} ({final[0]['combined_score']})"]
    }
