"""Email generator — drafts personalized hiring emails using LLM."""

import logging
from agent.llm_config import get_llm
from agent.tools.retry import safe_llm_call

logger = logging.getLogger(__name__)

EMAIL_PROMPT = """You are a senior recruiter at a top tech company. Draft a professional, warm, and exciting offer/interview-invitation email.

DETAILS:
- Candidate Name: {name}
- Current Role: {current_role} at {company}
- Role Offered: {job_title}
- Combined Score: {combined_score}/100
- Key Strengths Noted: {strengths}
- Conversation Summary: {conversation_summary}
- Suggested Next Steps: {next_steps}

REQUIREMENTS:
1. Address the candidate by first name
2. Reference specific strengths from their evaluation (show you did your homework)
3. Mention the role and why they stood out
4. Propose a next step (interview call, technical discussion, etc.)
5. Keep it warm, professional, and under 200 words
6. Include a subject line at the top

Return the email in this format:
Subject: [subject line]

[email body]
"""


def draft_hiring_email(candidate: dict, job_title: str) -> str:
    """Generate a personalized outreach/offer email for a candidate."""
    llm = get_llm("ranking")  # Use cheap model — simple text generation

    strengths = candidate.get("strengths", [])
    strengths_str = ", ".join(strengths[:4]) if strengths else "Strong overall profile"

    prompt = EMAIL_PROMPT.format(
        name=candidate.get("name", "Candidate"),
        current_role=candidate.get("current_role", "Professional"),
        company=candidate.get("company", "their current company"),
        job_title=job_title or "the open position",
        combined_score=candidate.get("combined_score", "N/A"),
        strengths=strengths_str,
        conversation_summary=candidate.get("conversation_summary", "Positive engagement overall.")[:300],
        next_steps=candidate.get("next_steps", "Schedule an interview"),
    )

    try:
        response = safe_llm_call(llm, prompt)
        return response.content.strip()
    except Exception as e:
        logger.error(f"Email generation failed: {e}")
        return (
            f"Subject: Exciting Opportunity — {job_title}\n\n"
            f"Dear {candidate.get('name', 'Candidate').split()[0]},\n\n"
            f"We were impressed by your profile and would love to discuss "
            f"the {job_title} role with you. Your experience in "
            f"{strengths_str} stood out to our team.\n\n"
            f"Would you be available for a brief call this week?\n\n"
            f"Best regards,\nThe Recruiting Team"
        )
