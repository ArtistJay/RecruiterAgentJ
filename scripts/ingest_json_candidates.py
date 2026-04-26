"""
Ingest pre-structured JSON candidate files into the data/candidates folder.
Use this when candidate data comes from online forms, APIs, or other structured sources.
"""

import os
import json
import shutil


def ingest_json_folder(source_folder: str, output_folder: str = "data/candidates"):
    """
    Copy and validate JSON candidate files from source into the candidate pool.
    Assigns candidate_id if missing. Validates required fields.
    """
    os.makedirs(output_folder, exist_ok=True)

    REQUIRED_FIELDS = ["name", "skills"]

    files = [f for f in os.listdir(source_folder) if f.endswith(".json")]
    if not files:
        print(f"❌ No JSON files found in {source_folder}")
        return 0

    print(f"📦 Found {len(files)} JSON files in {source_folder}")

    ingested = 0
    for i, filename in enumerate(files):
        src_path = os.path.join(source_folder, filename)
        try:
            with open(src_path, "r") as f:
                data = json.load(f)

            # Validate
            missing = [field for field in REQUIRED_FIELDS if not data.get(field)]
            if missing:
                print(f"  ⚠️ {filename}: Missing {missing} — skipping")
                continue

            # Set defaults
            data.setdefault("candidate_id", f"JSON-{i+1:04d}")
            data.setdefault("current_role", "Not specified")
            data.setdefault("company", "Not specified")
            data.setdefault("years_experience", 0)
            data.setdefault("education", {})
            data.setdefault("experience_summary", "")
            data.setdefault("personality_traits", [])
            data.setdefault("notice_period", "Unknown")
            data.setdefault("expected_salary_lpa", 0)
            data.setdefault("current_salary_lpa", 0)
            data.setdefault("preferred_location", "Unknown")
            data.setdefault("open_to_remote", True)
            data.setdefault("career_goals", "")
            data.setdefault("willingness_to_relocate", True)

            # Save to output
            dest_path = os.path.join(output_folder, filename)
            with open(dest_path, "w") as f:
                json.dump(data, f, indent=2)

            print(f"  ✅ {data['name']}")
            ingested += 1

        except Exception as e:
            print(f"  ❌ {filename}: {e}")

    print(f"\n📦 {ingested}/{len(files)} candidates ingested to {output_folder}")
    return ingested


if __name__ == "__main__":
    import sys
    source = sys.argv[1] if len(sys.argv) > 1 else "data/json_candidates"
    ingest_json_folder(source)
