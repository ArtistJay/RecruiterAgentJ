import os
import json
import time
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

ROLES = [
    "Machine Learning Engineer", "Senior Python Developer",
    "Frontend React Developer", "Data Scientist",
    "DevOps Engineer", "AI Research Scientist",
    "Full Stack Developer", "Cloud Architect",
    "Backend Java Developer", "NLP Engineer",
    "CFD Simulation Specialist", "Embedded Systems Engineer"
]

SENIORITY = ["Junior", "Mid-Level", "Senior", "Lead", "Principal"]

def fix_candidate(data):
    """Normalize field names — LLM might use different keys."""
    for key in ["full_name", "Full Name", "Full_Name", "candidate_name"]:
        if key in data and "name" not in data:
            data["name"] = data.pop(key)
    for key in ["role", "job_title", "title", "current_job_title"]:
        if key in data and "current_role" not in data:
            data["current_role"] = data.pop(key)
    for key in ["technical_skills", "key_skills", "core_skills"]:
        if key in data and "skills" not in data:
            data["skills"] = data.pop(key)
    
    # Defaults
    data.setdefault("name", "Unknown Candidate")
    data.setdefault("current_role", "Software Engineer")
    data.setdefault("skills", ["Python"])
    data.setdefault("years_experience", 3)
    data.setdefault("experience_summary", "Experienced professional.")
    return data

def generate_candidate(role, seniority, index):
    prompt = f"""Generate a realistic Indian tech professional profile for {seniority} {role}.
    Return ONLY a valid JSON with these fields: name, current_role, company, years_experience, skills, education, experience_summary, personality_traits, notice_period, expected_salary_lpa, current_salary_lpa, preferred_location, open_to_remote, career_goals, willingness_to_relocate.
    """
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        raw = json.loads(response.choices[0].message.content)
        candidate = fix_candidate(raw)
        candidate["candidate_id"] = f"CAND-{index:03d}"
        return candidate
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    os.makedirs("data/candidates", exist_ok=True)
    print("🚀 Generating 20 candidates...")
    for i in range(20):
        c = generate_candidate(ROLES[i % len(ROLES)], SENIORITY[i % len(SENIORITY)], i + 1)
        if c:
            with open(f"data/candidates/candidate_{i+1:03d}.json", "w") as f:
                json.dump(c, f, indent=2)
            print(f"✅ Created {c['name']}")
        if (i + 1) % 5 == 0: time.sleep(3)