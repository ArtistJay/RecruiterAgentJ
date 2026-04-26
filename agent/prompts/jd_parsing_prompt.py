JD_PARSING_PROMPT = """You are an expert HR analyst. Parse the following Job Description and extract structured information.

JOB DESCRIPTION:
{jd_text}

Return ONLY a valid JSON object with EXACTLY these fields:
{{
    "job_title": "extracted role title",
    "company": "company name if mentioned, else 'Not specified'",
    "must_have_skills": ["skill1", "skill2", "skill3"],
    "nice_to_have_skills": ["skill1", "skill2"],
    "min_experience_years": 3,
    "max_experience_years": 7,
    "education_required": "degree requirement",
    "location": "location or Remote",
    "remote_ok": true,
    "salary_range": "if mentioned, else 'Not specified'",
    "key_responsibilities": ["resp1", "resp2", "resp3"],
    "seniority_level": "Junior/Mid/Senior/Lead/Principal",
    "industry_domain": "e.g., FinTech, HealthTech, etc."
}}

Be precise. If something is not mentioned in the JD, make a reasonable inference based on the role.
Extract ALL technical skills mentioned — separate must-haves from nice-to-haves.
"""
