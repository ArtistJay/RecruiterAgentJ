import os
import json
import time
from agent.tools.pdf_utils import extract_text_with_ocr_fallback
from agent.prompts.resume_parsing_prompt import RESUME_PARSING_PROMPT
from agent.llm_config import get_llm

def process_kaggle_dataset(input_folder, output_folder):
    os.makedirs(output_folder, exist_ok=True)
    llm = get_llm("inparse") # Routes to Llama-3.1-8B-Instant

    files = [f for f in os.listdir(input_folder) if f.endswith(".pdf")]
    print(f"🚀 Found {len(files)} resumes. Starting extraction...")

    for i, filename in enumerate(files):
        pdf_path = os.path.join(input_folder, filename)
        print(f"[{i+1}/{len(files)}] Processing {filename}...")

        try:
            # 1. Extraction with OCR Fallback
            raw_text = extract_text_with_ocr_fallback(pdf_path)
            
            # 2. Parse with 8B Model (Truncate text to fit context if needed)
            prompt = RESUME_PARSING_PROMPT.format(resume_text=raw_text[:6000])
            response = llm.invoke(prompt)
            
            # Clean response (LLMs sometimes wrap JSON in code blocks)
            content = response.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            candidate_data = json.loads(content)
            
            # Add file reference for your ChromaDB metadata
            candidate_data["candidate_id"] = f"CAND-{i+1:04d}"
            candidate_data["resume_filename"] = filename

            # 3. Save JSON
            json_filename = filename.replace(".pdf", ".json")
            with open(os.path.join(output_folder, json_filename), "w") as f:
                json.dump(candidate_data, f, indent=2)
            
            display_name = candidate_data.get("name")
            if not display_name or display_name in ["None", "null", "Unknown"]:
                display_name = f"Anonymous ({filename})"
            print(f"✅ Successfully parsed: {display_name}")

        except Exception as e:
            print(f"❌ Critical error processing {filename}: {e}")
        
        # Small sleep to respect Groq Free Tier RPM limits
        time.sleep(2)

if __name__ == "__main__":
    # Change these paths to your Kaggle dataset location
    # KAGGLE_PDF_DIR = "data/kaggle_resumes"
    J_DATASET_DIR = "data/J_dataset"
    CANDIDATE_JSON_DIR = "data/candidates"
    
    process_kaggle_dataset(J_DATASET_DIR, CANDIDATE_JSON_DIR)