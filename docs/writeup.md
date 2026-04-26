# agentJ: One-Page Architecture & Trade-offs

## What It Does
agentJ takes a raw Job Description, parses it into structured requirements, discovers matching candidates via semantic search, simulates recruiter-candidate conversations to gauge interest, and outputs a ranked shortlist with explainable scores.

## Architecture
A 4-agent LangGraph pipeline with **conditional routing**:

InParseGent → ScoutGent → [ConvoGent | SkipGent] → FinalGent → Ranked Output

text


- **InParseGent** (Llama 3.1-8B): Extracts structured JD fields with self-correction retry loop.
- **ScoutGent** (Llama 4 Scout 17B): GPU-accelerated semantic search via ChromaDB + LLM-scored 5-factor evaluation.
- **ConvoGent** (Llama 3.3-70B + Qwen3-32B): Simulates 4-turn conversations; analyzes transcripts for interest signals.
- **Conditional Router**: Skips ConvoGent for candidates below match threshold (saves tokens, shows agentic decision-making).
- **FinalGent** (Llama 3.1-8B): Combines Match + Interest scores, produces ranked recommendations.

## Scoring
- **Match Score** = 40% Skills + 25% Experience + 15% Education + 10% Location + 10% Bonus
- **Interest Score** = 30% Enthusiasm + 25% Availability + 20% Salary Fit + 15% Role Fit - 10% Red Flags
- **Combined** = 60% Match + 40% Interest (adjustable via UI slider)

## Key Trade-offs
| Decision | Why |
|----------|-----|
| Multi-model routing | Optimizes Groq free tier: cheap models for simple tasks, powerful models for conversations |
| Local embeddings (GPU) | Zero token cost, zero latency, full data privacy |
| Simulated conversations | Surfaces red flags (salary mismatch, notice period) before real recruiter outreach |
| Self-correction in parsing | Handles messy/incomplete JDs gracefully without human intervention |
| Conditional routing | Avoids wasting expensive conversation tokens on poor-fit candidates |

## What I'd Improve With More Time
- Parallel conversation fan-out (currently sequential due to rate limits)
- Real candidate database integration (LinkedIn API, etc.)
- Human-in-the-loop review step before final ranking
- A/B testing different conversation strategies
- Fine-tuned scoring weights based on historical hiring data

## Tech Stack
LangGraph · Groq (4 models) · ChromaDB · Sentence-Transformers (CUDA) · Streamlit · Plotly

---
Built by **Jaykumar Patel** (PhD Scholar, IIT Hyderabad) for Deccan AI Catalyst Hackathon 2026
