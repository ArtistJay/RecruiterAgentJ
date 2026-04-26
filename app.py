"""
agentJ — AI-Powered Talent Scouting & Engagement Agent
Streamlit UI with streaming progress, email generation,
dual ingestion (PDF/JSON), and interactive analytics.
"""

import streamlit as st
import json
import os
import sys
import csv
import io
import shutil
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent.graph import graph
from agent.tools.scoring import calculate_combined_score, get_recommendation

# ═══════════════════════════════════════════════════════
# PAGE CONFIG
# ═══════════════════════════════════════════════════════
st.set_page_config(
    page_title="agentJ — AI Talent Scout",
    page_icon="🕵️",
    layout="wide"
)

st.title("🕵️ agentJ — AI-Powered Talent Scouting Agent")
st.markdown(
    "*Paste a Job Description → Get a ranked shortlist with Match Scores, "
    "Interest Scores, and conversation insights.*"
)
st.divider()


# ═══════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════
def _count_candidates():
    d = "data/candidates"
    if not os.path.exists(d):
        return 0
    return len([f for f in os.listdir(d) if f.endswith(".json")])


def _db_exists():
    d = "db/chroma"
    if not os.path.exists(d):
        return False
    return any(f for f in os.listdir(d) if f != ".gitkeep")


def _count_files_in_folder(folder: str, ext: str) -> int:
    """Count files with given extension in a folder. Returns -1 if folder doesn't exist."""
    if not folder or not os.path.isdir(folder):
        return -1
    return len([f for f in os.listdir(folder) if f.lower().endswith(ext)])


# ═══════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════
with st.sidebar:
    # ─── API SETUP ───
    st.header("🔑 API Setup")
    
    provider_choice = st.radio(
        "LLM Provider",
        ["Groq (Free)", "OpenAI (Paid)"],
        index=0 if os.getenv("LLM_PROVIDER", "groq").lower() == "groq" else 1,
        help="Groq: Free tier with rate limits. OpenAI: ~\$0.50/run, no rate limits.",
        horizontal=True,
    )
    
    if provider_choice.startswith("Groq"):
        api_key = st.text_input(
            "Groq API Key",
            value=os.getenv("GROQ_API_KEY", ""),
            type="password",
            help="Get your free key at console.groq.com",
        )
        if api_key:
            os.environ["GROQ_API_KEY"] = api_key
            os.environ["LLM_PROVIDER"] = "groq"
        provider = "GROQ"
    else:
        api_key = st.text_input(
            "OpenAI API Key",
            value=os.getenv("OPENAI_API_KEY", ""),
            type="password",
            help="Get your key at platform.openai.com/api-keys",
        )
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
            os.environ["LLM_PROVIDER"] = "openai"
        provider = "OPENAI"
    
    # Status indicator
    if api_key:
        key_preview = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
        if provider == "OPENAI":
            st.success(f"🔌 **{provider}** — Key set ({key_preview})")
        else:
            st.success(f"🔌 **{provider}** — Key set ({key_preview})")
    else:
        env_groq = os.getenv("GROQ_API_KEY", "")
        env_openai = os.getenv("OPENAI_API_KEY", "")
        if env_groq or env_openai:
            active = "GROQ" if env_groq else "OPENAI"
            st.info(f"🔌 **{active}** — Using key from .env file")
            provider = active
        else:
            st.warning("⚠️ No API key set! Enter a key above or add it to `.env`")

    cand_count = _count_candidates()
    db_ready = _db_exists()
    st.caption(
        f"📦 Candidates: **{cand_count}** | "
        f"🔍 ChromaDB: **{'Ready' if db_ready else 'Empty'}**"
    )


    # ─── DUAL INGESTION ───
    st.header("📂 Data Ingestion")

    ingest_mode = st.radio(
        "Source Format",
        ["📄 PDF Resumes (with OCR)", "📋 Pre-structured JSON"],
        help=(
            "**PDF:** Real CVs/resumes — text extracted automatically, "
            "OCR for scanned documents.\n\n"
            "**JSON:** Pre-structured candidate data from online forms, "
            "APIs, HR systems, or any other source."
        )
    )

    if ingest_mode.startswith("📄"):
        source_path = st.text_input(
            "PDF Folder Path",
            value="data/J_dataset",
            help="Absolute or relative path to a folder containing .pdf resume files"
        )

        # Live path validation
        pdf_count = _count_files_in_folder(source_path, ".pdf")
        if pdf_count == -1:
            st.error(f"❌ Folder not found: `{source_path}`")
        elif pdf_count == 0:
            st.warning(f"⚠️ No .pdf files found in `{source_path}`")
        else:
            st.success(f"✅ Found **{pdf_count}** PDF files ready to process")

        process_disabled = pdf_count <= 0
        if st.button("📥 Process PDFs & Index", disabled=process_disabled):
            with st.status("Processing PDFs...", expanded=True) as ingest_status:
                try:
                    st.write(f"1️⃣ Reading {pdf_count} PDFs from `{source_path}`...")
                    st.write("   (OCR will auto-trigger for scanned documents)")
                    from scripts.ingest_resumes import process_kaggle_dataset
                    process_kaggle_dataset(source_path, "data/candidates")

                    st.write("2️⃣ Indexing into ChromaDB...")
                    from scripts.seed_vectordb import seed
                    seed()

                    from agent.tools.vector_search import reset_vector_cache
                    reset_vector_cache()

                    final_count = _count_candidates()
                    st.write(f"✅ Done! **{final_count}** candidates now indexed.")
                    ingest_status.update(label="✅ PDF Ingestion Complete!", state="complete")
                except Exception as e:
                    st.error(f"❌ Failed: {e}")
                    ingest_status.update(label="❌ Failed", state="error")

    else:
        source_path = st.text_input(
            "JSON Folder Path",
            value="data/json_candidates",
            help=(
                "Absolute or relative path to a folder containing .json candidate files. "
                "Each JSON should have at least 'name' and 'skills' fields."
            )
        )

        # Live path validation
        json_count = _count_files_in_folder(source_path, ".json")
        if json_count == -1:
            st.error(f"❌ Folder not found: `{source_path}`")
        elif json_count == 0:
            st.warning(f"⚠️ No .json files found in `{source_path}`")
        else:
            st.success(f"✅ Found **{json_count}** JSON files ready to import")

        import_disabled = json_count <= 0
        if st.button("📥 Import JSONs & Index", disabled=import_disabled):
            with st.status("Importing JSONs...", expanded=True) as ingest_status:
                try:
                    st.write(f"1️⃣ Validating {json_count} JSON files from `{source_path}`...")
                    from scripts.ingest_json_candidates import ingest_json_folder
                    count = ingest_json_folder(source_path, "data/candidates")

                    st.write("2️⃣ Indexing into ChromaDB...")
                    from scripts.seed_vectordb import seed
                    seed()

                    from agent.tools.vector_search import reset_vector_cache
                    reset_vector_cache()

                    st.write(f"✅ Done! **{count}** candidates imported and indexed.")
                    ingest_status.update(label="✅ JSON Import Complete!", state="complete")
                except Exception as e:
                    st.error(f"❌ Failed: {e}")
                    ingest_status.update(label="❌ Failed", state="error")

    st.divider()

    # ─── RESET ───
    st.header("🗑️ Data Management")
    if st.button("🗑️ Reset All Data & Start Fresh", type="secondary"):
        errors = []

        # 1. Clear candidate JSONs
        cand_dir = "data/candidates"
        if os.path.exists(cand_dir):
            for fname in os.listdir(cand_dir):
                if fname.endswith(".json"):
                    try:
                        os.remove(os.path.join(cand_dir, fname))
                    except Exception as e:
                        errors.append(f"Could not delete {fname}: {e}")

        # 2. Clear ChromaDB collection (NOT the folder — it's locked by this process)
        try:
            import chromadb
            client = chromadb.PersistentClient(path="db/chroma")
            try:
                client.delete_collection("candidates")
            except Exception:
                pass  # Collection doesn't exist — that's fine
            # Reset the cached reference so next search re-creates it
            from agent.tools.vector_search import reset_vector_cache
            reset_vector_cache()
        except Exception as e:
            errors.append(f"ChromaDB reset: {e}")

        # 3. Clear cached pipeline output
        cache_file = "docs/sample_outputs/full_pipeline_output.json"
        if os.path.exists(cache_file):
            try:
                os.remove(cache_file)
            except Exception as e:
                errors.append(f"Cache: {e}")

        # 4. Clear session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]

        if errors:
            st.warning("⚠️ Reset completed with warnings:\n" + "\n".join(errors))
        else:
            st.success("✅ All data cleared! Upload new resumes to begin.")
        st.rerun()

    st.divider()

    # ─── SCORING ───
    st.header("⚙️ Scoring Weights")
    match_weight = st.slider("Match Score Weight", 0.0, 1.0, 0.6, 0.05)
    interest_weight = round(1.0 - match_weight, 2)
    st.write(f"Interest Score Weight: **{interest_weight}**")

    max_turns = st.slider(
        "Max Conversation Turns",
        min_value=2, max_value=10, value=4, step=1,
        help="Upper limit for recruiter-candidate conversation turns. "
        "The agent may stop early if it has gathered enough information."
    )
    st.caption("💡 Agent stops early when it has enough info — this is the upper limit.")
    st.divider()

    st.header("📊 Scoring Formula")
    st.markdown(f"""
    **Match Score** (0-100):
    - Skills: 40% | Experience: 25%
    - Education: 15% | Location: 10% | Bonus: 10%

    **Interest Score** (0-100):
    - Enthusiasm: 30% | Availability: 25%
    - Salary Fit: 20% | Role Fit: 15% | Red Flags: -10%

    **Combined** = {match_weight:.0%} Match + {interest_weight:.0%} Interest
    """)
    st.divider()

    st.markdown(f"**Models ({provider}):**")
    if provider == "OPENAI":
        st.markdown("- 🧠 Parsing: `gpt-4.1-nano`")
        st.markdown("- 🔍 Matching: `gpt-4.1-mini`")
        st.markdown("- 💬 Conversations: `gpt-4.1`")
        st.markdown("- 📊 Scoring: `gpt-4.1-mini`")
        st.markdown("- 📋 Ranking: `gpt-4.1-nano`")
    else:
        st.markdown("- 🧠 Parsing: `llama-3.1-8b`")
        st.markdown("- 🔍 Matching: `llama-4-scout-17b`")
        st.markdown("- 💬 Conversations: `llama-3.3-70b`")
        st.markdown("- 📊 Scoring: `qwen3-32b`")
        st.markdown("- 📋 Ranking: `llama-3.1-8b`")
    st.divider()

    st.markdown("**Tech Stack:**")
    st.markdown("LangGraph · ChromaDB · Sentence-Transformers · Groq/OpenAI")
    st.divider()
    st.markdown("Built by **Jay A. Patel** for Deccan AI Catalyst Hackathon 2026")

    st.divider()
    if st.button("⏹️ Stop Server", type="secondary", help="Stops the Streamlit server. Use Ctrl+C in terminal if tab stays open."):
        # Close the browser tab via JavaScript, then kill the server
        st.markdown(
            """<script>
            setTimeout(function(){
                window.close();
                // If window.close() is blocked by browser, show message
                document.body.innerHTML = '<h2 style="text-align:center;margin-top:40vh;color:#666">Server stopped. You can close this tab.</h2>';
            }, 500);
            </script>""",
            unsafe_allow_html=True
        )
        st.success("🛑 Server shutting down... You can close this tab.")
        import time, os, signal
        time.sleep(2)
        os.kill(os.getpid(), signal.SIGTERM)


# ═══════════════════════════════════════════════════════
# MAIN — JD INPUT
# ═══════════════════════════════════════════════════════
sample_jds = {}
sample_dir = "data/sample_jds"
if os.path.exists(sample_dir):
    for f in sorted(os.listdir(sample_dir)):
        if f.endswith(".txt"):
            name = f.replace(".txt", "").replace("_", " ").title()
            with open(os.path.join(sample_dir, f), "r") as fh:
                sample_jds[name] = fh.read()

col1, col2 = st.columns([3, 1])
with col2:
    if sample_jds:
        selected = st.selectbox(
            "📄 Load Sample JD ?",
            ["— Select —"] + list(sample_jds.keys())
        )
        if selected != "— Select —":
            st.session_state["jd_text"] = sample_jds[selected]

    cached_path = "docs/sample_outputs/full_pipeline_output.json"
    if os.path.exists(cached_path):
        st.markdown("---")
        if st.button("⚡ Load Cached Results", help="Load previously saved output — no API calls"):
            with open(cached_path, "r") as f:
                st.session_state["result"] = json.load(f)
                st.session_state["match_weight"] = match_weight
            st.toast("✅ Cached results loaded!", icon="⚡")
            st.rerun()

with col1:
    jd_text = st.text_area(
        "📋 Paste Job Description Here",
        value=st.session_state.get("jd_text", ""),
        height=250,
        placeholder="Paste a full job description here..."
    )


# ═══════════════════════════════════════════════════════
# PIPELINE — STREAMING
# ═══════════════════════════════════════════════════════
if st.button("🚀 Run AgentJ Pipeline", type="primary", disabled=not jd_text):

    if not _db_exists() or _count_candidates() == 0:
        # Check if PDFs/JSONs exist but just haven't been processed yet
        pdf_path = "data/J_dataset"
        has_pdfs = os.path.isdir(pdf_path) and any(f.endswith(".pdf") for f in os.listdir(pdf_path))
        has_jsons_raw = os.path.isdir("data/json_candidates") and any(f.endswith(".json") for f in os.listdir("data/json_candidates"))

        if has_pdfs or has_jsons_raw:
            st.info(
                "👈 **Candidates not yet indexed.** Click **📥 Process PDFs & Index** "
                "(or **📥 Import JSONs & Index**) in the sidebar first. "
                "You only need to do this **once** — after that, run multiple JDs against the same candidate pool."
            )
        else:
            st.error(
                "❌ **No candidate data found.** "
                "Place PDF resumes in a folder (e.g., `data/J_dataset/`) "
                "or JSON files in a folder (e.g., `data/json_candidates/`), "
                "set the path in **📂 Data Ingestion** (sidebar), "
                "then click **Process/Import**. This is a one-time step."
            )
    else:
        initial_state = {
            "raw_jd": jd_text,
            "parsed_jd": {},
            "matched_candidates": [],
            "engaged_candidates": [],
            "final_shortlist": [],
            "logs": [],
            "max_turns": max_turns,
        }

        status = st.status("🚀 AgentJ Pipeline Running...", expanded=True)

        with status:
            try:
                final_state = dict(initial_state)

                for output in graph.stream(initial_state):
                    for node_name, node_data in output.items():
                        for key, value in node_data.items():
                            if key == "logs" and isinstance(value, list):
                                final_state.setdefault("logs", [])
                                final_state["logs"].extend(value)
                            else:
                                final_state[key] = value

                        if node_name == "inparse_gent":
                            title = node_data.get("parsed_jd", {}).get("job_title", "Unknown")
                            sc = len(node_data.get("parsed_jd", {}).get("must_have_skills", []))
                            st.write(f"✅ **InParseGent** — Parsed: *{title}* ({sc} must-have skills)")

                        elif node_name == "scout_gent":
                            cands = node_data.get("matched_candidates", [])
                            if cands:
                                st.write(
                                    f"✅ **ScoutGent** — {len(cands)} matched. "
                                    f"Top: **{cands[0]['name']}** (Match: {cands[0]['match_score']})"
                                )
                            else:
                                st.write("⚠️ **ScoutGent** — No matching candidates")

                        elif node_name == "convo_gent":
                            eng = node_data.get("engaged_candidates", [])
                            if eng:
                                avg = round(sum(c.get("interest_score", 0) for c in eng) / len(eng), 1)
                                st.write(f"✅ **ConvoGent** — {len(eng)} conversations. Avg Interest: {avg}")
                            else:
                                st.write("⚠️ **ConvoGent** — No conversations completed")

                        elif node_name == "skip_gent":
                            st.write("⏭️ **SkipGent** — Skipped (no candidates above match threshold)")

                        elif node_name == "final_gent":
                            sl = node_data.get("final_shortlist", [])
                            if sl:
                                st.write(
                                    f"✅ **FinalGent** — {len(sl)} ranked. "
                                    f"Top: **{sl[0]['name']}** (Combined: {sl[0]['combined_score']})"
                                )
                            else:
                                st.write("✅ **FinalGent** — Ranking complete")

                st.write("---")
                st.write("🎉 **All agents completed!**")
                status.update(label="✅ Pipeline Complete!", state="complete")

                st.session_state["result"] = final_state
                st.session_state["match_weight"] = match_weight

                cache_dir = "docs/sample_outputs"
                os.makedirs(cache_dir, exist_ok=True)
                with open(os.path.join(cache_dir, "full_pipeline_output.json"), "w") as f:
                    json.dump(final_state, f, indent=2, default=str)
                st.toast("💾 Results auto-saved!", icon="💾")

            except Exception as e:
                error_msg = str(e)
                if "quota" in error_msg.lower():
                    st.error(
                        f"❌ **API Quota Exhausted**\n\n{error_msg}\n\n"
                        "Switch to OpenAI (`LLM_PROVIDER=openai` in `.env`) or load cached results."
                    )
                else:
                    st.error(f"❌ Pipeline failed: {error_msg}")
                status.update(label="❌ Failed", state="error")


# ═══════════════════════════════════════════════════════
# RESULTS
# ═══════════════════════════════════════════════════════
if "result" in st.session_state:
    result = st.session_state["result"]
    mw = st.session_state.get("match_weight", 0.6)
    iw = round(1.0 - mw, 2)

    st.divider()

    shortlist = result.get("final_shortlist", [])
    for c in shortlist:
        c["combined_score"] = calculate_combined_score(
            c.get("match_score", 0), c.get("interest_score", 0),
            match_weight=mw, interest_weight=iw
        )
        c["recommendation"] = get_recommendation(c["combined_score"])

    shortlist.sort(key=lambda x: x["combined_score"], reverse=True)
    for i, c in enumerate(shortlist, 1):
        c["rank"] = i

    # ─── EXECUTIVE SUMMARY ───
    if shortlist:
        strong_yes = [c for c in shortlist if "Strong Yes" in c.get("recommendation", "")]
        yes_list = [c for c in shortlist if c.get("recommendation", "").startswith("Yes")]
        maybe_list = [c for c in shortlist if "Maybe" in c.get("recommendation", "")]
        no_list = [c for c in shortlist if c.get("recommendation", "").startswith("No")]

        st.subheader("📊 Executive Summary")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("🟢 Strong Yes", len(strong_yes))
        m2.metric("🟡 Yes", len(yes_list))
        m3.metric("🟠 Maybe", len(maybe_list))
        m4.metric("🔴 No", len(no_list))

        top = shortlist[0]
        st.success(
            f"**🏆 Top: {top['name']}** — {top['current_role']} at {top.get('company', 'N/A')} | "
            f"Combined: **{top['combined_score']}** | "
            f"Match: {top['match_score']} | Interest: {top['interest_score']} | "
            f"{top['recommendation']}"
        )

        if len(shortlist) > 1:
            r = shortlist[1]
            st.info(f"**Runner-up: {r['name']}** — Combined: {r['combined_score']} | {r['recommendation']}")
    else:
        st.warning("No candidates found. Try a different JD or ingest more resumes.")

    # ─── PARSED JD ───
    with st.expander("📋 Parsed Job Description", expanded=False):
        pjd = result.get("parsed_jd", {})

        st.markdown(
            f"### {pjd.get('job_title', 'N/A')}\n"
            f"**{pjd.get('seniority_level', '')}** · "
            f"{pjd.get('min_experience_years', '?')}-{pjd.get('max_experience_years', '?')} years · "
            f"{pjd.get('location', 'N/A')} · "
            f"{pjd.get('industry_domain', 'N/A')}"
        )

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**💰 Salary:** {pjd.get('salary_range', 'Not specified')}")
            st.markdown(f"**🏢 Company:** {pjd.get('company', 'Not specified')}")
        with col2:
            st.markdown(f"**🎓 Education:** {pjd.get('education_required', 'Not specified')}")
            st.markdown(f"**🌐 Remote:** {'Yes' if pjd.get('remote_ok') else 'No / Not specified'}")

        st.markdown("---")
        st.markdown("**Must-have Skills:**")
        skills_html = " ".join([f'<code style="background:#e8f5e9;padding:2px 8px;border-radius:4px;margin:2px;display:inline-block">{s}</code>' for s in pjd.get("must_have_skills", [])])
        st.markdown(skills_html, unsafe_allow_html=True)

        nice_skills = pjd.get("nice_to_have_skills", [])
        if nice_skills:
            st.markdown("**Nice-to-have:**")
            nice_html = " ".join([f'<code style="background:#e3f2fd;padding:2px 8px;border-radius:4px;margin:2px;display:inline-block">{s}</code>' for s in nice_skills])
            st.markdown(nice_html, unsafe_allow_html=True)

    # ─── COMPARISON CHART ───
    if shortlist:
        st.subheader("📊 Score Comparison")
        try:
            import plotly.graph_objects as go
            n = min(len(shortlist), 8)
            names = [c["name"].split()[0] for c in shortlist[:n]]
            fig = go.Figure(data=[
                go.Bar(name="Match", x=names, y=[c["match_score"] for c in shortlist[:n]], marker_color="#4CAF50"),
                go.Bar(name="Interest", x=names, y=[c["interest_score"] for c in shortlist[:n]], marker_color="#2196F3"),
                go.Bar(name="Combined", x=names, y=[c["combined_score"] for c in shortlist[:n]], marker_color="#FF9800"),
            ])
            fig.update_layout(barmode="group", yaxis_title="Score (0-100)", height=380, template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)
        except ImportError:
            st.caption("Install plotly for charts: `pip install plotly`")

    # ─── CANDIDATE CARDS — SCORES VISIBLE + HIRE BUTTON ───
    if shortlist:
        st.subheader("📇 Candidates")
        st.caption("Scores visible below each candidate. Click **Details** to expand. Click **📧 Draft Hire Email** to generate a personalized outreach email.")

        for c in shortlist:
            rec = c["recommendation"]
            cid = c.get("candidate_id", c["name"])

            # Color bar
            if "Strong Yes" in rec:
                border = "#4CAF50"
            elif rec.startswith("Yes"):
                border = "#FFC107"
            elif "Maybe" in rec:
                border = "#FF9800"
            else:
                border = "#f44336"

            # ── CANDIDATE HEADER — name prominent ──
            st.markdown(
                f'<div style="border-left: 5px solid {border}; padding: 8px 0 8px 16px; margin-bottom: 4px;">'
                f'<span style="font-size: 1.3em; font-weight: 700;">#{c["rank"]} {c["name"]}</span>'
                f'<br><span style="color: #666; font-size: 0.95em;">{c["current_role"]} at {c.get("company", "N/A")}</span>'
                f'</div>',
                unsafe_allow_html=True
            )

            # ── SCORES ROW — balanced columns ──
            sc1, sc2, sc3, sc4, act = st.columns([1, 1, 1, 1.2, 1])
            with sc1:
                st.markdown(f"<div style='text-align:center'><span style='color:#888;font-size:0.8em'>📈 Match</span><br><span style='font-size:1.5em;font-weight:700'>{c['match_score']}</span></div>", unsafe_allow_html=True)
            with sc2:
                st.markdown(f"<div style='text-align:center'><span style='color:#888;font-size:0.8em'>💬 Interest</span><br><span style='font-size:1.5em;font-weight:700'>{c['interest_score']}</span></div>", unsafe_allow_html=True)
            with sc3:
                st.markdown(f"<div style='text-align:center'><span style='color:#888;font-size:0.8em'>🎯 Combined</span><br><span style='font-size:1.5em;font-weight:700'>{c['combined_score']}</span></div>", unsafe_allow_html=True)
            with sc4:
                st.markdown(f"<div style='padding-top:4px'><strong>{rec}</strong></div>", unsafe_allow_html=True)
                signals = c.get("key_signals", [])
                if signals:
                    preview = signals[0][:50] + ("..." if len(signals[0]) > 50 else "")
                    st.caption(f"🔹 {preview}")
            with act:
                st.write("")
                if st.button(f"📧 Hire Email", key=f"hire_{cid}"):
                    st.session_state[f"drafting_{cid}"] = True

            # ── HIRE EMAIL ──
            if st.session_state.get(f"drafting_{cid}", False):
                with st.spinner(f"✍️ Drafting email for {c['name']}..."):
                    from agent.tools.email_generator import draft_hiring_email
                    job_title = result.get("parsed_jd", {}).get("job_title", "the position")
                    email_text = draft_hiring_email(c, job_title)
                    st.session_state[f"email_{cid}"] = email_text
                    st.session_state[f"drafting_{cid}"] = False
                    st.rerun()

            if f"email_{cid}" in st.session_state:
                st.success(f"📧 Email drafted for **{c['name']}**")
                st.text_area(
                    "Generated Email",
                    value=st.session_state[f"email_{cid}"],
                    height=200,
                    key=f"email_display_{cid}"
                )
                ec1, ec2 = st.columns(2)
                with ec1:
                    st.download_button(
                        "📥 Download Email",
                        st.session_state[f"email_{cid}"],
                        file_name=f"hire_email_{c['name'].replace(' ', '_')}.txt",
                        mime="text/plain",
                        key=f"dl_email_{cid}"
                    )
                with ec2:
                    if st.button("✖ Dismiss", key=f"dismiss_{cid}"):
                        del st.session_state[f"email_{cid}"]
                        st.rerun()

            # ── EXPANDABLE DETAILS ──
            with st.expander(f"🔍 Full Details — {c['name']}"):

                try:
                    import plotly.graph_objects as go
                    bd = c.get("score_breakdown", {})
                    ib = c.get("interest_breakdown", {})
                    if bd or ib:
                        radar = go.Figure()
                        if bd:
                            cats = [k.title() for k in bd.keys()]
                            vals = [int(v) if isinstance(v, (int, float)) else 50 for v in bd.values()]
                            radar.add_trace(go.Scatterpolar(
                                r=vals + [vals[0]], theta=cats + [cats[0]],
                                fill="toself", name="Match", line_color="#4CAF50",
                            ))
                        if ib:
                            ci = [k.replace("_", " ").title() for k in ib.keys()]
                            vi = [int(v) if isinstance(v, (int, float)) else 50 for v in ib.values()]
                            radar.add_trace(go.Scatterpolar(
                                r=vi + [vi[0]], theta=ci + [ci[0]],
                                fill="toself", name="Interest", line_color="#2196F3",
                            ))
                        radar.update_layout(
                            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                            showlegend=True, height=350,
                        )
                        st.plotly_chart(radar, use_container_width=True)
                except ImportError:
                    pass

                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Match Breakdown:**")
                    bd = c.get("score_breakdown", {})
                    expl = c.get("explanations", {})
                    for k, v in bd.items():
                        val = int(v) if isinstance(v, (int, float)) else 50
                        st.progress(val / 100, text=f"{k.title()}: {val}")
                        if expl.get(k):
                            st.caption(f"  ↳ {expl[k]}")
                with col2:
                    st.markdown("**Interest Breakdown:**")
                    ib = c.get("interest_breakdown", {})
                    ie = c.get("interest_explanations", {})
                    for k, v in ib.items():
                        val = int(v) if isinstance(v, (int, float)) else 50
                        st.progress(val / 100, text=f"{k.replace('_', ' ').title()}: {val}")
                        ek = k.replace("_perception", "").replace("_alignment", "")
                        explanation = ie.get(ek, ie.get(k, ""))
                        if explanation:
                            st.caption(f"  ↳ {explanation}")

                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**✅ Strengths:**")
                    for s in c.get("strengths", []):
                        st.markdown(f"- {s}")
                with col2:
                    st.markdown("**❌ Gaps:**")
                    for g in c.get("gaps", []):
                        st.markdown(f"- {g}")

                summary = c.get("conversation_summary", "")
                if summary and summary != "N/A" and "Not engaged" not in summary:
                    actual = c.get("actual_turns", "?")
                    max_t = c.get("max_turns_allowed", "?")
                    st.markdown(f"**💬 Conversation Summary** *(completed in {actual}/{max_t} turns)*:")
                    st.info(summary)

                signals = c.get("key_signals", [])
                if signals and "skipped" not in str(signals).lower():
                    st.markdown("**🔍 Key Signals:**")
                    for sig in signals:
                        st.markdown(f"- 🔹 {sig}")

                if c.get("transcript"):
                    with st.expander("📜 Full Conversation Transcript"):
                        for msg in c["transcript"]:
                            role = msg.get("role", "unknown")
                            text = msg.get("message", "")
                            turn = msg.get("turn", "?")
                            if role == "recruiter":
                                st.markdown(f"**🧑‍💼 Recruiter (Turn {turn}):** {text}")
                            else:
                                st.markdown(f"**👤 {c['name']} (Turn {turn}):** {text}")
                            st.markdown("---")

                if c.get("final_reasoning"):
                    st.markdown("**🎯 Final Reasoning:**")
                    st.write(c["final_reasoning"])

                if c.get("risk_factors"):
                    st.markdown("**⚠️ Risk Factors:**")
                    for rf in c["risk_factors"]:
                        st.markdown(f"- ⚠️ {rf}")

                if c.get("next_steps"):
                    st.markdown(f"**📌 Next Steps:** {c['next_steps']}")

            st.markdown("---")

    # ─── LOGS ───
    with st.expander("📝 Pipeline Logs"):
        logs = result.get("logs", [])
        if logs:
            for log in logs:
                st.write(f"→ {log}")
        else:
            st.caption("No logs available.")

    # ─── EXPORT ───
    st.divider()
    st.subheader("📥 Export")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button(
            "📥 Full Report (JSON)",
            json.dumps(result, indent=2, default=str),
            file_name="agentj_report.json",
            mime="application/json"
        )
    with col2:
        if shortlist:
            buf = io.StringIO()
            w = csv.DictWriter(buf, fieldnames=["Rank", "Name", "Role", "Match", "Interest", "Combined", "Recommendation"])
            w.writeheader()
            for c in shortlist:
                w.writerow({
                    "Rank": c["rank"], "Name": c["name"], "Role": c["current_role"],
                    "Match": c["match_score"], "Interest": c["interest_score"],
                    "Combined": c["combined_score"], "Recommendation": c["recommendation"]
                })
            st.download_button("📥 Summary (CSV)", buf.getvalue(), file_name="agentj_shortlist.csv", mime="text/csv")
    with col3:
        if st.button("🔄 Clear Results"):
            for key in ["result", "match_weight", "jd_text"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
