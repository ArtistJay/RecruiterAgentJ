# agentJ: AI-Powered Talent Scouting and Engagement Agent

**agentJ** is an industrial-grade, multi-agent recruitment system designed to automate the end-to-end talent acquisition funnel. It replaces manual screening with semantic search, multi-turn conversational simulations, and qualitative interest analysis to find not just the best "resume," but the best "person" for the role.

Built for the **Deccan AI Catalyst Hackathon 2026**.

---

## 🏗️ Core Architecture: The Stateful Multi-Agent Pipeline

agentJ is built on **LangGraph**, utilizing a Directed Acyclic Graph (DAG) with persistent state management and intelligent conditional routing.

### The Workflow Logic
START → InParseGent → ScoutGent → [ConvoGent | SkipGent] → FinalGent → END

| Agent | Responsibility | Intelligence Layering (Groq / OpenAI) |
| :--- | :--- | :--- |
| **InParseGent** | **The Analyst:** Extracts structured DNA from messy Job Descriptions. Includes a self-correction retry loop to ensure no mandatory fields are missed. | Llama 3.1-8B / GPT-4.1-nano | (Extraction efficiency)
| **ScoutGent** | **The Matcher:** Executes semantic search across ChromaDB. Scores candidates using a strict 5-factor weighted matrix with human-readable explanations. | Llama 4 Scout 17B / GPT-4.1-mini | (Reasoning smart)
| **ConvoGent** | **The Interviewer:** Simulates natural, 4-turn recruiter-candidate conversations to probe for red flags, salary alignment, and genuine interest. | Llama 3.3-70B / GPT-4.1 | (Convo smart)
| **SkipGent** | **The Optimizer:** Triggered when all candidates score below 25/100 on Match Score, preventing wasteful API spend on clearly unqualified profiles. | Logic-based (Fast & Free) | (Deterministic logic)
| **FinalGent** | **The Ranker:** Synthesizes Match + Interest scores into a final recommendation. Drafts personalized "You are Hired" emails based on candidate strengths. | Llama 3.1-8B / GPT-4.1-nano | (Synthesis smart)

---

## 🧠 Advanced Technical Features

### 1. Self-Healing PDF Ingestion (OCR Fallback)
The system handles real-world, messy documents through a multi-stage extraction pipeline:
* **Phase 1 (Fast):** Attempts digital text extraction via PyMuPDF.
* **Phase 2 (Deep):** If the PDF is a scanned image or lacks a text layer, the system triggers OCRmyPDF to perform OCR and deskewing.
* **Phase 3 (Structure):** A dedicated 8B model (ResuParse) maps unstructured OCR text into a standardized JSON schema.

### 2. Smart LLM Routing & Multi-Provider Support
* **Intelligence Tiering:** Tasks are routed to specific models based on complexity (e.g., 70B for nuance, 8B for parsing).
* **Provider Switch:** Seamlessly toggle between Groq (Free Tier/High Speed) and OpenAI (Paid/High Reliability) via environment variables.
* **Smart Error Handling:** Fatal errors (quota exhausted, bad API key) → fails immediately with actionable message. Transient errors (timeout, RPM throttle) → retries once with backoff. Never retries pointlessly.

### 3. Local Embedding Privacy & Performance
By running sentence-transformers (all-MiniLM-L6-v2) locally on an NVIDIA RTX 3060 Ti, agentJ achieves:
* **Zero token cost** for vector generation.
* **Zero latency** for candidate indexing.
* **Data Privacy:** Resumes are vectorized locally before any data hits the cloud.

---

## 📊 The Scoring Engine

Dynamic Score Weighting: agentJ uses a hybrid mathematical model to provide transparent, explainable rankings. Recruiters can adjust the Match vs. Interest weight ratio in real-time via the sidebar slider.

### Match Score (60% Weight)
* **40% Skills:** Direct match of Must-haves vs. Nice-to-haves.
* **25% Experience:** Seniority and years-of-experience alignment.
* **15% Education:** Degree and major relevance.
* **10% Location:** Remote compatibility or relocation willingness.
* **10% Bonus:** Domain expertise and transferable skills.

### Interest Score (40% Weight)
* **30% Enthusiasm:** Qualitative sentiment analysis from the conversation.
* **25% Availability:** Readiness to start and notice period constraints.
* **20% Salary Fit:** Alignment between candidate expectations and role budget.
* **15% Role Fit:** How the candidate perceives the job responsibilities.
* **-10% Red Flags:** Automated penalty for inconsistencies or hesitations.

---

## 🛠️ Tech Stack
* Orchestration: LangGraph (Stateful Workflows)
* Vector DB: ChromaDB (Local Persistence)
* Extraction: PyMuPDF + OCRmyPDF (Tesseract Engine)
* LLMs: Groq (Llama 3.3-70B, Llama 4-Scout, Qwen3) / OpenAI (GPT-4.1)
* UI: Streamlit + Plotly (Interactive Radar Charts)

---

## 🚀 Setup & Execution

### 1. Installation
Step 1: Set up environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

Step 2: Ensure Tesseract is installed on your OS
Ubuntu: sudo apt install tesseract-ocr
Mac: brew install tesseract

### 2. Configuration
Create a .env file in the root directory:
LLM_PROVIDER=groq
GROQ_API_KEY=your_key_here
OPENAI_API_KEY=optional_key_here
MODE=cloud

### 3. Data Ingestion
Populate your candidate pool by placing PDFs in data/J_dataset/ and running:
# Process PDFs and generate JSONs
python scripts/ingest_resumes.py

# Index JSONs into the Vector Database
python scripts/seed_vectordb.py

### 4. Run Application
export PYTHONPATH="${PWD}:${PYTHONPATH}"
streamlit run app.py

---

## 🧪 Testing Suite
* python tests/test_scoring.py: Validates weighted math logic.
* python tests/test_inparse.py: Validates JD parsing and self-correction.
* python tests/test_full_pipeline.py: End-to-end simulation test.

---
**Built with ❤️ by Jay Patel (PhD Scholar, IIT Hyderabad)**