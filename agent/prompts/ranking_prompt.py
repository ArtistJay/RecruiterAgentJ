RANKING_PROMPT = """You are a senior hiring manager making final recommendations.

You have {num_candidates} candidates evaluated for the role: {job_title}

For each candidate below, you have their Match Score (skills/experience fit) and Interest Score (from conversation).

CANDIDATES:
{candidates_summary}

For each candidate, provide a final recommendation.

Return ONLY a valid JSON array:
[
    {{
        "candidate_id": "CAND-001",
        "name": "Name",
        "combined_score": 75.5,
        "recommendation": "Strong Yes / Yes / Maybe / No",
        "reasoning": "1-2 sentence justification",
        "risk_factors": ["risk1"],
        "next_steps": "Suggested action for recruiter"
    }}
]

Sort by combined_score descending. Be decisive and practical.
"""
