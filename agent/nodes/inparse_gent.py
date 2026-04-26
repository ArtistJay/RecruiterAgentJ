"""
InParseGent — Agent 1: Job Description Parser
Takes raw JD text, extracts structured requirements using LLM.
Includes self-correction: retries with stricter prompt if output is invalid.
"""

import json
import logging
from agent.state import AgentState
from agent.llm_config import get_llm
from agent.tools.retry import safe_llm_call
from agent.prompts.jd_parsing_prompt import JD_PARSING_PROMPT

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = [
    "job_title", "must_have_skills", "min_experience_years",
    "max_experience_years", "education_required", "location"
]

CORRECTION_PROMPT = """Your previous response was missing required fields. 
The following fields are MANDATORY and must be present in your JSON output:
{missing_fields}

Original JD:
{jd_text}

Return a COMPLETE valid JSON with ALL required fields. Do NOT skip any field.
Previous (incomplete) response for reference:
{previous_response}

Return ONLY the corrected JSON object.
"""


def _extract_json(content: str) -> dict:
    """Robustly extract JSON from LLM response."""
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]

    try:
        return json.loads(content.strip())
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(content[start:end])
        raise


def _validate_parsed_jd(parsed: dict) -> list:
    """Return list of missing required fields."""
    missing = []
    for field in REQUIRED_FIELDS:
        val = parsed.get(field)
        if val is None or val == "" or val == []:
            missing.append(field)
    return missing


def inparse_gent(state: AgentState) -> dict:
    """Parse raw JD into structured requirements.
    Includes self-correction: if critical fields are missing, retries with a stricter prompt.
    """
    raw_jd = state["raw_jd"]
    llm = get_llm("inparse")

    # --- Attempt 1: Standard parse ---
    prompt = JD_PARSING_PROMPT.format(jd_text=raw_jd)
    response = safe_llm_call(llm, prompt)

    try:
        parsed_jd = _extract_json(response.content)
    except (json.JSONDecodeError, Exception) as e:
        logger.error(f"Initial JSON extraction failed: {e}")
        parsed_jd = {}

    # --- Self-correction: check for missing fields ---
    missing = _validate_parsed_jd(parsed_jd)

    if missing and parsed_jd.get("job_title"):  # Partial success — try to fix
        logger.info(f"Self-correcting: missing fields {missing}")
        print(f"🔄 InParseGent: Self-correcting — missing {missing}...")

        correction_prompt = CORRECTION_PROMPT.format(
            missing_fields=", ".join(missing),
            jd_text=raw_jd,
            previous_response=json.dumps(parsed_jd, indent=2),
        )

        try:
            correction_response = safe_llm_call(llm, correction_prompt)
            corrected = _extract_json(correction_response.content)

            # Merge: corrected values fill gaps, keep original where valid
            for field in missing:
                if field in corrected and corrected[field]:
                    parsed_jd[field] = corrected[field]

            print(f"✅ InParseGent: Self-correction applied")
        except Exception as e:
            logger.warning(f"Self-correction failed: {e}")
            print(f"⚠️ InParseGent: Self-correction failed, proceeding with partial data")

    elif not parsed_jd or "error" in parsed_jd:
        # Total failure — try once more with original prompt
        print(f"🔄 InParseGent: First attempt failed, retrying...")
        try:
            response = safe_llm_call(llm, prompt)
            parsed_jd = _extract_json(response.content)
        except Exception as e:
            parsed_jd = {
                "error": f"Failed to parse JD after retries: {e}",
                "job_title": "Unknown",
                "must_have_skills": [],
                "nice_to_have_skills": [],
                "min_experience_years": 0,
                "max_experience_years": 10,
                "education_required": "Not specified",
                "location": "Not specified",
            }

    # Set defaults for any still-missing optional fields
    parsed_jd.setdefault("nice_to_have_skills", [])
    parsed_jd.setdefault("salary_range", "Not specified")
    parsed_jd.setdefault("remote_ok", False)
    parsed_jd.setdefault("key_responsibilities", [])
    parsed_jd.setdefault("seniority_level", "Mid")
    parsed_jd.setdefault("industry_domain", "Technology")
    parsed_jd.setdefault("company", "Not specified")

    title = parsed_jd.get("job_title", "Unknown")
    print(f"🧠 InParseGent: Parsed JD for '{title}'")

    return {
        "parsed_jd": parsed_jd,
        "logs": [f"InParseGent: Parsed JD for role '{title}' (self-correction: {'applied' if missing else 'not needed'})"]
    }
