MATCHING_PROMPT = """You are an expert technical recruiter. Evaluate how well this candidate matches the job requirements.

JOB REQUIREMENTS:
- Title: {job_title}
- Must-have skills: {must_have_skills}
- Nice-to-have skills: {nice_to_have_skills}
- Experience needed: {min_exp}-{max_exp} years
- Education: {education}
- Location: {location}
- Domain: {domain}

CANDIDATE PROFILE:
- Name: {cand_name}
- Current Role: {cand_role}
- Company: {cand_company}
- Skills: {cand_skills}
- Experience: {cand_exp} years
- Education: {cand_education}
- Summary: {cand_summary}
- Location: {cand_location}
- Open to remote: {cand_remote}

Score this candidate on each dimension (0-100) and provide brief explanations.

Return ONLY a valid JSON object:
{{
    "skills_score": 0,
    "skills_explanation": "which skills match, which are missing",
    "experience_score": 0,
    "experience_explanation": "how experience aligns",
    "education_score": 0,
    "education_explanation": "education fit",
    "location_score": 0,
    "location_explanation": "location compatibility",
    "bonus_score": 0,
    "bonus_explanation": "nice-to-have skills, transferable skills, domain overlap",
    "strengths": ["strength1", "strength2"],
    "gaps": ["gap1", "gap2"],
    "overall_assessment": "2-3 sentence summary of fit"
}}

Be fair and precise. A candidate with 3/6 must-have skills should score ~50 on skills, not 80.
"""
