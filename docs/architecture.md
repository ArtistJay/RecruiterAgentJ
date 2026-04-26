# agentJ: Architectural Deep Dive and Trade-offs

## 1. Multi-Agent Orchestration (LangGraph)
Unlike standard linear RAG pipelines, agentJ uses a Directed Acyclic Graph (DAG) approach via LangGraph. This architecture provides:
- State Management: A persistent AgentState object that serves as a shared memory for all four agents.
- Modular Logic: Each Gent (InParse, Scout, Convo, Final) operates independently, allowing for specialized prompts and targeted model selection.

## 2. Multi-Model Smart Budget Strategy
To maximize quality while staying within Groq Free Tier rate limits, we implemented a strategic routing layer:
- Llama 3.1 8B-Instant: Used for InParseGent. High RPD (14.4K) allows for frequent JD parsing without burning budget.
- Llama 4 Scout 17B: Used for ScoutGent. Optimized for technical evaluation and logical reasoning.
- Llama 3.3 70B-Versatile: Reserved for ConvoGent. High-IQ model needed for natural dialogue and probing candidate motivations.
- Qwen3 32B: Used for scoring transcripts due to high RPM (60) and structured output reliability.

## 3. Hybrid Scoring Framework
The system uses a two-stage scoring mechanism to ensure high-quality recommendations:
- Match Score: Evaluated against the JD. Weights: 40% Skills, 25% Exp, 15% Edu, 10% Loc, 10% Bonus.
- Interest Score: Evaluated via ConvoGent simulation. Weights: 30% Enthusiasm, 25% Availability, 20% Salary, 15% Fit, -10% Red Flags.
- Combined Final Score: (0.6 * Match Score) + (0.4 * Interest Score).

## 4. Technical Innovations and Trade-offs
- Local Inference for Embeddings: By running sentence-transformers locally on an NVIDIA RTX 3060 Ti, we achieved zero-latency, zero-cost embedding generation while keeping candidate data private.
- Semantic Mapping: By using vector search, the system can identify Transferable Skills (e.g., matching a Physics PhD with CFD expertise to an ML role), which traditional keyword-based ATS systems fail to do.
- Simulated Engagement: Before the recruiter spends time on a call, AgentJ probes for Red Flags like notice period conflicts or salary misalignment through the ConvoGent simulation.
