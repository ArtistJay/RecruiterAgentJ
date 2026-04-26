"""
ScoutGent — Agent 2: Candidate Discovery & Matching
Searches ChromaDB for candidates, scores each with LLM explainability.
"""

import json
import logging
from agent.state import AgentState
from agent.llm_config import get_llm
from agent.tools.vector_search import search_candidates
from agent.tools.scoring import calculate_match_score
from agent.tools.retry import safe_llm_call
from agent.prompts.matching_prompt import MATCHING_PROMPT

logger = logging.getLogger(__name__)


def _extract_json(content: str) -> dict:
    """Robustly extract JSON from LLM response."""
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]

    start = content.find("{")
    end = content.rfind("}") + 1
    if start != -1 and end > start:
        return json.loads(content[start:end])
    return json.loads(content.strip())


def scout_gent(state: AgentState) -> dict:
    """Discover and score matching candidates."""
    parsed_jd = state["parsed_jd"]

    # Fail gracefully if InParseGent errored
    if parsed_jd.get("error"):
        logger.error(f"ScoutGent received errored JD: {parsed_jd['error']}")
        print(f"⚠️ ScoutGent: JD parsing had errors, proceeding with best effort...")

    llm = get_llm("scout")

    # Step 1: Vector search
    print("🔎 ScoutGent: Searching candidate pool...")
    raw_candidates = search_candidates(parsed_jd, top_k=15)
    print(f"   Found {len(raw_candidates)} potential matches\n")

    if not raw_candidates:
        print("⚠️ ScoutGent: No candidates found in vector DB!")
        return {
            "matched_candidates": [],
            "logs": ["ScoutGent: No candidates found in vector search"]
        }

    # Step 2: LLM scoring
    matched = []

    for i, cand in enumerate(raw_candidates):
        name = cand.get("name", "Unknown")
        print(f"   Evaluating {i+1}/{len(raw_candidates)}: {name}...", end=" ")

        skills = cand.get("skills", [])
        skills_str = ", ".join(skills) if isinstance(skills, list) else str(skills)

        edu = cand.get("education", {})
        if isinstance(edu, dict):
            edu_str = f"{edu.get('degree', '')} in {edu.get('field', '')} from {edu.get('university', '')}"
        else:
            edu_str = str(edu)

        prompt = MATCHING_PROMPT.format(
            job_title=parsed_jd.get("job_title", ""),
            must_have_skills=", ".join(parsed_jd.get("must_have_skills", [])),
            nice_to_have_skills=", ".join(parsed_jd.get("nice_to_have_skills", [])),
            min_exp=parsed_jd.get("min_experience_years", 0),
            max_exp=parsed_jd.get("max_experience_years", 10),
            education=parsed_jd.get("education_required", ""),
            location=parsed_jd.get("location", ""),
            domain=parsed_jd.get("industry_domain", ""),
            cand_name=name,
            cand_role=cand.get("current_role", "Unknown"),
            cand_company=cand.get("company", "Unknown"),
            cand_skills=skills_str,
            cand_exp=cand.get("years_experience", 0),
            cand_education=edu_str,
            cand_summary=cand.get("experience_summary", ""),
            cand_location=cand.get("preferred_location", "Unknown"),
            cand_remote=cand.get("open_to_remote", "Unknown"),
        )

        try:
            response = safe_llm_call(llm, prompt)
            evaluation = _extract_json(response.content)

            match_score = calculate_match_score(
                skills_val=evaluation.get("skills_score", 50),
                exp_val=evaluation.get("experience_score", 50),
                edu_val=evaluation.get("education_score", 50),
                loc_val=evaluation.get("location_score", 50),
                bonus_val=evaluation.get("bonus_score", 50),
            )

            matched_candidate = {
                "candidate_id": cand.get("candidate_id", f"CAND-{i}"),
                "name": name,
                "current_role": cand.get("current_role", "Unknown"),
                "company": cand.get("company", "Unknown"),
                "skills": cand.get("skills", []),
                "years_experience": cand.get("years_experience", 0),
                "education": cand.get("education", {}),
                "preferred_location": cand.get("preferred_location", ""),
                "notice_period": cand.get("notice_period", "Unknown"),
                "expected_salary_lpa": cand.get("expected_salary_lpa", 0),
                "current_salary_lpa": cand.get("current_salary_lpa", 0),
                "career_goals": cand.get("career_goals", ""),
                "personality_traits": cand.get("personality_traits", []),
                "open_to_remote": cand.get("open_to_remote", False),
                "experience_summary": cand.get("experience_summary", ""),
                "willingness_to_relocate": cand.get("willingness_to_relocate", False),
                "match_score": match_score,
                "score_breakdown": {
                    "skills": evaluation.get("skills_score", 0),
                    "experience": evaluation.get("experience_score", 0),
                    "education": evaluation.get("education_score", 0),
                    "location": evaluation.get("location_score", 0),
                    "bonus": evaluation.get("bonus_score", 0),
                },
                "strengths": evaluation.get("strengths", []),
                "gaps": evaluation.get("gaps", []),
                "overall_assessment": evaluation.get("overall_assessment", ""),
                "explanations": {
                    "skills": evaluation.get("skills_explanation", ""),
                    "experience": evaluation.get("experience_explanation", ""),
                    "education": evaluation.get("education_explanation", ""),
                    "location": evaluation.get("location_explanation", ""),
                    "bonus": evaluation.get("bonus_explanation", ""),
                },
            }

            matched.append(matched_candidate)
            print(f"✅ Match: {match_score}")

        except Exception as e:
            print(f"❌ Error: {e}")
            logger.error(f"Failed to evaluate {name}: {e}")
            continue

    # Sort by match score, keep top 10
    matched.sort(key=lambda x: x["match_score"], reverse=True)
    top_candidates = matched[:10]

    print(f"\n🏆 ScoutGent: {len(matched)} scored, top {len(top_candidates)} selected")

    log_msg = (
        f"ScoutGent: Scored {len(matched)} candidates. "
        f"Top: {top_candidates[0]['name']} ({top_candidates[0]['match_score']})"
    ) if top_candidates else "ScoutGent: No matches found"

    return {
        "matched_candidates": top_candidates,
        "logs": [log_msg]
    }
