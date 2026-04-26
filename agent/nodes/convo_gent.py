"""
ConvoGent — Agent 3: Conversational Outreach Simulation

Simulates multi-turn recruiter-candidate conversations.
Uses ADAPTIVE turn count — the agent evaluates after each turn
whether enough information has been gathered, and may stop early.
"""

import json
import logging
from agent.state import AgentState
from agent.llm_config import get_llm
from agent.tools.scoring import calculate_interest_score
from agent.tools.retry import safe_llm_call
from agent.prompts.engagement_prompt import (
    RECRUITER_PROMPT,
    CANDIDATE_PERSONA_PROMPT,
    INTEREST_ANALYSIS_PROMPT,
    TURN_INSTRUCTIONS,
)

logger = logging.getLogger(__name__)

# Prompt for the agent to evaluate whether to continue
CONTINUE_EVALUATION_PROMPT = """You are an expert recruiter analyst. After each conversation turn, you must decide whether to continue the conversation or stop.

CONVERSATION SO FAR:
{conversation_so_far}

INFORMATION WE NEED TO ASSESS:
1. Candidate's genuine interest level in the role
2. Salary expectations vs what's offered
3. Notice period / availability
4. Skill gaps and how candidate feels about them
5. Any red flags (competing offers, reluctance, etc.)

Answer these TWO questions:
1. Has the candidate provided enough information to assess their interest level? (yes/no)
2. Do we have enough conversation data to produce a reliable Interest Score? (yes/no)

Current turn: {current_turn} of {max_turns}

Return ONLY a valid JSON:
{{
    "has_enough_info": true,
    "has_enough_for_scoring": true,
    "missing_info": ["what's still unknown"],
    "reasoning": "1 sentence explaining decision",
    "recommendation": "continue or stop"
}}
"""


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


def simulate_conversation(candidate: dict, parsed_jd: dict, max_turns: int = 4) -> dict:
    """
    Simulate a multi-turn recruiter-candidate conversation.
    ADAPTIVE: After each turn (from turn 2 onwards), the agent evaluates
    whether enough information has been gathered. May stop early.
    """

    convo_llm = get_llm("convo")
    scoring_llm = get_llm("scoring")

    transcript = []
    conversation_text = ""
    actual_turns = 0

    skills = candidate.get("skills", [])
    skills_str = ", ".join(skills) if isinstance(skills, list) else str(skills)

    edu = candidate.get("education", {})
    if isinstance(edu, dict):
        edu_str = f"{edu.get('degree', '')} in {edu.get('field', '')} from {edu.get('university', '')}"
    else:
        edu_str = str(edu)

    gaps_str = ", ".join(candidate.get("gaps", ["No specific gaps identified"]))
    strengths_str = ", ".join(candidate.get("strengths", ["Relevant experience"]))

    for turn in range(1, max_turns + 1):
        actual_turns = turn

        # --- RECRUITER TURN ---
        turn_instruction = TURN_INSTRUCTIONS.get(turn, TURN_INSTRUCTIONS[5])
        if "{gaps}" in turn_instruction:
            turn_instruction = turn_instruction.format(gaps=gaps_str)

        recruiter_prompt = RECRUITER_PROMPT.format(
            job_title=parsed_jd.get("job_title", ""),
            company=parsed_jd.get("company", "the company"),
            location=parsed_jd.get("location", ""),
            salary_range=parsed_jd.get("salary_range", "Competitive"),
            cand_name=candidate.get("name", ""),
            cand_role=candidate.get("current_role", ""),
            cand_company=candidate.get("company", ""),
            cand_exp=candidate.get("years_experience", 0),
            gaps=gaps_str,
            strengths=strengths_str,
            turn_number=turn,
            conversation_so_far=conversation_text if conversation_text else "This is the start of the conversation.",
            turn_instruction=turn_instruction,
        )

        recruiter_response = safe_llm_call(convo_llm, recruiter_prompt)
        recruiter_msg = recruiter_response.content.strip()

        transcript.append({"role": "recruiter", "turn": turn, "message": recruiter_msg})
        conversation_text += f"\nRecruiter: {recruiter_msg}"

        # --- CANDIDATE TURN ---
        candidate_prompt = CANDIDATE_PERSONA_PROMPT.format(
            cand_name=candidate.get("name", ""),
            cand_role=candidate.get("current_role", ""),
            cand_company=candidate.get("company", ""),
            cand_exp=candidate.get("years_experience", 0),
            cand_skills=skills_str,
            cand_education=edu_str,
            current_salary=candidate.get("current_salary_lpa", "Not disclosed"),
            expected_salary=candidate.get("expected_salary_lpa", "Not disclosed"),
            notice_period=candidate.get("notice_period", "Unknown"),
            cand_location=candidate.get("preferred_location", ""),
            open_to_remote=candidate.get("open_to_remote", "Unknown"),
            willing_to_relocate=candidate.get("willingness_to_relocate", "Unknown"),
            career_goals=candidate.get("career_goals", ""),
            personality=", ".join(candidate.get("personality_traits", ["professional"])),
            conversation_so_far=conversation_text,
            recruiter_message=recruiter_msg,
        )

        candidate_response = safe_llm_call(convo_llm, candidate_prompt)
        candidate_msg = candidate_response.content.strip()

        transcript.append({"role": "candidate", "turn": turn, "message": candidate_msg})
        conversation_text += f"\nCandidate: {candidate_msg}"

        # --- ADAPTIVE STOP: Evaluate after turn 2+ (need at least 2 turns for context) ---
        if turn >= 2 and turn < max_turns:
            try:
                eval_prompt = CONTINUE_EVALUATION_PROMPT.format(
                    conversation_so_far=conversation_text,
                    current_turn=turn,
                    max_turns=max_turns,
                )
                eval_response = safe_llm_call(scoring_llm, eval_prompt)
                evaluation = _extract_json(eval_response.content)

                should_stop = (
                    evaluation.get("has_enough_info", False) and
                    evaluation.get("has_enough_for_scoring", False)
                )

                if evaluation.get("recommendation", "").lower() == "stop":
                    should_stop = True

                if should_stop:
                    reason = evaluation.get("reasoning", "Sufficient information gathered")
                    print(f" [stopped at turn {turn}/{max_turns}: {reason}]", end="")
                    break

            except Exception as e:
                # If evaluation fails, just continue the conversation
                logger.warning(f"Turn evaluation failed: {e}")
                continue

    # --- ANALYZE CONVERSATION ---
    analysis_prompt = INTEREST_ANALYSIS_PROMPT.format(
        full_transcript=conversation_text,
        expected_salary=candidate.get("expected_salary_lpa", "Unknown"),
        offered_salary=parsed_jd.get("salary_range", "Unknown"),
        notice_period=candidate.get("notice_period", "Unknown"),
        career_goals=candidate.get("career_goals", "Unknown"),
    )

    try:
        analysis_response = safe_llm_call(scoring_llm, analysis_prompt)
        analysis = _extract_json(analysis_response.content)
    except Exception as e:
        logger.error(f"Conversation analysis failed: {e}")
        analysis = {
            "enthusiasm": 50, "availability": 50,
            "salary_alignment": 50, "role_fit_perception": 50,
            "red_flags": 20, "key_signals": ["Analysis failed"],
            "conversation_summary": f"Error analyzing: {e}",
            "enthusiasm_explanation": "", "availability_explanation": "",
            "salary_explanation": "", "role_fit_explanation": "",
            "red_flags_explanation": "",
        }

    interest_score = calculate_interest_score(
        enthusiasm=analysis.get("enthusiasm", 50),
        availability=analysis.get("availability", 50),
        salary_align=analysis.get("salary_alignment", 50),
        role_fit=analysis.get("role_fit_perception", 50),
        red_flags=analysis.get("red_flags", 20),
    )

    return {
        "transcript": transcript,
        "conversation_text": conversation_text,
        "interest_score": interest_score,
        "actual_turns": actual_turns,
        "max_turns": max_turns,
        "interest_breakdown": {
            "enthusiasm": analysis.get("enthusiasm", 0),
            "availability": analysis.get("availability", 0),
            "salary_alignment": analysis.get("salary_alignment", 0),
            "role_fit_perception": analysis.get("role_fit_perception", 0),
            "red_flags": analysis.get("red_flags", 0),
        },
        "interest_explanations": {
            "enthusiasm": analysis.get("enthusiasm_explanation", ""),
            "availability": analysis.get("availability_explanation", ""),
            "salary": analysis.get("salary_explanation", ""),
            "role_fit": analysis.get("role_fit_explanation", ""),
            "red_flags": analysis.get("red_flags_explanation", ""),
        },
        "key_signals": analysis.get("key_signals", []),
        "conversation_summary": analysis.get("conversation_summary", ""),
    }


def convo_gent(state: AgentState) -> dict:
    """Run conversational outreach for top matched candidates."""

    matched = state["matched_candidates"]
    parsed_jd = state["parsed_jd"]
    max_turns = state.get("max_turns", 4)

    # Only engage candidates above minimum match threshold
    candidates_to_engage = [c for c in matched if c.get("match_score", 0) >= 25][:7]

    if not candidates_to_engage:
        print("⚠️ ConvoGent: No candidates above engagement threshold")
        return {
            "engaged_candidates": [],
            "logs": ["ConvoGent: No candidates above match threshold for engagement"]
        }

    print(f"💬 ConvoGent: Engaging {len(candidates_to_engage)} candidates (max {max_turns} turns, adaptive)...\n")

    engaged = []

    for i, cand in enumerate(candidates_to_engage):
        name = cand.get("name", "Unknown")
        print(f"   [{i+1}/{len(candidates_to_engage)}] Chatting with {name}...", end=" ")

        try:
            result = simulate_conversation(cand, parsed_jd, max_turns=max_turns)

            engaged_candidate = {**cand}
            engaged_candidate["interest_score"] = result["interest_score"]
            engaged_candidate["interest_breakdown"] = result["interest_breakdown"]
            engaged_candidate["interest_explanations"] = result["interest_explanations"]
            engaged_candidate["key_signals"] = result["key_signals"]
            engaged_candidate["conversation_summary"] = result["conversation_summary"]
            engaged_candidate["transcript"] = result["transcript"]
            engaged_candidate["conversation_text"] = result["conversation_text"]
            engaged_candidate["actual_turns"] = result["actual_turns"]
            engaged_candidate["max_turns_allowed"] = result["max_turns"]

            engaged.append(engaged_candidate)
            turns_info = f"{result['actual_turns']}/{max_turns} turns"
            print(f"✅ Interest: {result['interest_score']} ({turns_info})")

        except Exception as e:
            print(f"❌ Error: {e}")
            logger.error(f"Conversation failed for {name}: {e}")
            engaged_candidate = {**cand}
            engaged_candidate["interest_score"] = 50
            engaged_candidate["interest_breakdown"] = {}
            engaged_candidate["interest_explanations"] = {}
            engaged_candidate["key_signals"] = [f"Conversation failed: {e}"]
            engaged_candidate["conversation_summary"] = "Conversation could not be completed."
            engaged_candidate["transcript"] = []
            engaged_candidate["conversation_text"] = ""
            engaged_candidate["actual_turns"] = 0
            engaged_candidate["max_turns_allowed"] = max_turns
            engaged.append(engaged_candidate)

    print(f"\n💬 ConvoGent: {len(engaged)} candidates engaged")

    return {
        "engaged_candidates": engaged,
        "logs": [f"ConvoGent: Engaged {len(engaged)} candidates (adaptive, max {max_turns} turns)"]
    }
