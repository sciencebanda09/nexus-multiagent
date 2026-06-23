"""
NEXUS Web UI — Streamlit interface
Run: streamlit run ui/app.py
"""

import sys
import time
import sqlite3
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NEXUS Multi-Agent",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
body { background: #0d1117; }
.stApp { background: #0d1117; }
.agent-box {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 12px 16px;
    margin: 6px 0;
    font-family: monospace;
    font-size: 13px;
}
.agent-orchestrator { border-left: 3px solid #58a6ff; }
.agent-researcher   { border-left: 3px solid #3fb950; }
.agent-analyst      { border-left: 3px solid #d29922; }
.agent-coder        { border-left: 3px solid #bc8cff; }
.agent-writer       { border-left: 3px solid #f78166; }
.agent-critic       { border-left: 3px solid #ff7b72; }
.status-running  { color: #d29922; font-weight: bold; }
.status-complete { color: #3fb950; font-weight: bold; }
.status-failed   { color: #f85149; font-weight: bold; }
.metric-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 16px;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)


# ── Helper: load from DB ──────────────────────────────────────────────────────
def get_history():
    try:
        from core.config import DB_PATH
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute(
            "SELECT id, goal, status, created_at, finished_at, result FROM jobs ORDER BY id DESC LIMIT 20"
        ).fetchall()
        conn.close()
        return rows
    except Exception:
        return []


def get_memory_stats():
    try:
        from memory.memory import memory_stats
        return memory_stats()
    except Exception:
        return {}


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚡ NEXUS")
    st.markdown("**Multi-Agent AI System**")
    st.divider()

    st.markdown("### Models")
    st.info("🟢 qwen2.5:3b — Primary\n🟡 qwen2.5:0.5b — Fast")

    st.markdown("### Agents")
    agents_info = [
        ("🔵", "Orchestrator", "Plans & delegates"),
        ("🟢", "Researcher",   "Web search & fetch"),
        ("🟡", "Analyst",      "Data & math"),
        ("🟣", "Coder",        "Python execution"),
        ("🔴", "Writer",       "Reports & docs"),
        ("⚪", "Critic",       "Quality review"),
    ]
    for icon, name, desc in agents_info:
        st.markdown(f"{icon} **{name}** — {desc}")

    st.divider()
    st.markdown("### Tools (12)")
    tools = ["web_search", "url_fetch", "run_python", "write_file",
             "read_file", "math_engine", "analyze_text", "query_json",
             "system_info", "recall_memory", "plan_subtasks", "summarize"]
    for t in tools:
        st.markdown(f"  `{t}`")

    st.divider()
    mem_stats = get_memory_stats()
    if mem_stats:
        st.markdown("### Memory")
        st.metric("Stored Memories", mem_stats.get("total", 0))
        by_agent = mem_stats.get("by_agent", {})
        for agent, count in by_agent.items():
            st.markdown(f"  {agent}: {count}")


# ── Main UI ───────────────────────────────────────────────────────────────────
st.title("⚡ NEXUS Multi-Agent System")
st.markdown("*Local AI · No API · No Cost · Full Power*")

tab_run, tab_history, tab_memory, tab_docs = st.tabs([
    "🚀 Run", "📋 History", "🧠 Memory", "📖 Docs"
])

# ── TAB 1: RUN ────────────────────────────────────────────────────────────────
with tab_run:
    col1, col2 = st.columns([3, 1])
    with col1:
        goal = st.text_area(
            "Enter your goal",
            placeholder=(
                "Examples:\n"
                "• Research Python async patterns and write a working async web scraper\n"
                "• Analyze pros/cons of solar energy and write a detailed report\n"
                "• Write a Python function to find prime numbers up to N, test it\n"
                "• Calculate the integral of x^3 from 0 to 5 and explain the result\n"
                "• Find the top 3 open source LLM projects and compare them"
            ),
            height=120,
        )
    with col2:
        st.markdown("### Quick Goals")
        quick_goals = [
            "What is quantum computing?",
            "Write a Python fibonacci function",
            "Calculate derivative of x^3 + 2x",
            "Analyze: AI is transforming every industry",
            "Get system CPU and RAM stats",
        ]
        for qg in quick_goals:
            if st.button(qg[:35] + "...", key=f"qg_{qg[:10]}"):
                goal = qg
                st.rerun()

    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 4])
    with col_btn1:
        run_btn = st.button("⚡ Run", type="primary", disabled=not goal)
    with col_btn2:
        verbose = st.checkbox("Verbose", value=True)

    if run_btn and goal:
        st.session_state["running"] = True
        st.session_state["current_goal"] = goal

        log_container = st.container()
        result_container = st.empty()

        with st.spinner(f"Running: {goal[:60]}..."):
            start = time.time()
            try:
                from main import run as nexus_run
                result = nexus_run(goal, verbose=verbose)
                duration = round(time.time() - start, 1)

                if result["success"]:
                    st.success(f"✅ Completed in {duration}s (Job #{result['job_id']})")
                    st.markdown("### Result")
                    st.markdown(str(result["result"])[:4000])

                    # Show saved report if exists
                    rp = Path("./outputs/report.md")
                    if rp.exists():
                        with st.expander("📄 View Full Report"):
                            st.markdown(rp.read_text())
                        with open(rp, "rb") as f:
                            st.download_button(
                                "⬇ Download Report",
                                f,
                                file_name="nexus_report.md",
                                mime="text/markdown",
                            )
                else:
                    st.error(f"❌ Failed: {result.get('error', 'Unknown error')}")

            except Exception as e:
                st.error(f"Error: {e}")
                import traceback
                st.code(traceback.format_exc())


# ── TAB 2: HISTORY ────────────────────────────────────────────────────────────
with tab_history:
    st.markdown("### Job History")
    if st.button("🔄 Refresh"):
        st.rerun()

    rows = get_history()
    if not rows:
        st.info("No jobs yet. Run a goal first!")
    else:
        for row in rows:
            jid, goal_text, status, created, finished, result_text = row
            dur = f"{round(finished-created,1)}s" if finished else "—"
            ts = datetime.fromtimestamp(created).strftime("%H:%M:%S %d/%m") if created else "—"
            status_icon = "✅" if status=="completed" else ("❌" if status=="failed" else "⏳")

            with st.expander(f"{status_icon} [{jid}] {goal_text[:70]} — {dur} @ {ts}"):
                st.markdown(f"**Status:** {status} | **Duration:** {dur}")
                if result_text:
                    st.markdown("**Result:**")
                    st.markdown(result_text[:2000])


# ── TAB 3: MEMORY ────────────────────────────────────────────────────────────
with tab_memory:
    st.markdown("### Long-Term Memory")

    col_m1, col_m2 = st.columns([3, 1])
    with col_m1:
        mem_query = st.text_input("Search memory", placeholder="Enter query to recall relevant memories...")
    with col_m2:
        mem_agent = st.selectbox("Filter by agent", ["All", "orchestrator", "researcher", "analyst", "coder", "writer"])

    if st.button("🔍 Search Memory") and mem_query:
        try:
            from memory.memory import recall_memory
            agent_filter = None if mem_agent == "All" else mem_agent
            results = recall_memory(mem_query, agent_name=agent_filter)
            st.markdown("**Recalled:**")
            st.text(results)
        except Exception as e:
            st.error(f"Memory error: {e}")

    st.divider()
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        if st.button("📊 Show Stats"):
            stats = get_memory_stats()
            st.json(stats)
    with col_s2:
        if st.button("🗑️ Clear All Memory", type="secondary"):
            try:
                from memory.memory import clear_memories
                clear_memories()
                st.success("Memory cleared.")
            except Exception as e:
                st.error(f"Error: {e}")

    # List recent memories
    st.markdown("### Recent Memories")
    try:
        from memory.memory import list_memories
        mems = list_memories(limit=15)
        for m in mems:
            with st.expander(f"[{m['meta'].get('agent','?')}] {m['doc'][:80]}"):
                st.json(m['meta'])
                st.text(m['doc'])
    except Exception as e:
        st.info(f"Load memory: {e}")


# ── TAB 4: DOCS ───────────────────────────────────────────────────────────────
with tab_docs:
    st.markdown("""
## NEXUS Architecture

### Agents
| Agent | Model | Tools | Role |
|-------|-------|-------|------|
| Orchestrator | qwen2.5:3b | planner, memory | Decomposes goals, delegates |
| Researcher | qwen2.5:3b | web_search, url_fetch | Finds real information |
| Analyst | qwen2.5:3b | math, text_analyze, json | Patterns & insights |
| Coder | qwen2.5:3b | run_python, file_write | Writes & tests code |
| Writer | qwen2.5:3b | file_write, summarizer | Final reports |
| Critic | qwen2.5:0.5b | text_analyze | Quality review |

### Tools (12)
| Tool | Purpose |
|------|---------|
| `web_search` | DuckDuckGo search (no API key) |
| `url_fetch` | Fetch + parse any webpage |
| `run_python` | Execute Python (sandboxed) |
| `write_file` / `read_file` | File I/O in workspace |
| `math_engine` | SymPy: algebra, calculus, stats |
| `analyze_text` | Readability, keywords, sentiment |
| `query_json` | Dot-notation JSON queries |
| `system_info` | CPU, RAM, disk, platform |
| `recall_memory` | ChromaDB semantic recall |
| `plan_subtasks` | LLM-powered task decomposition |
| `summarize` | Fast text compression |

### Memory
- **ChromaDB** with sentence-transformers embeddings
- Persists across sessions in `./nexus_memory_db/`
- Per-agent namespacing + semantic search
- Auto-saved by tools after each action

### Error Handling
- Circuit breakers per tool (opens after 3 failures)
- Retry with exponential backoff
- Job history in SQLite `./nexus_jobs.db`
- Full logs in `./nexus_logs/nexus.log`

### Run Commands
```bash
# Install
pip install -r requirements.txt

# CLI interactive
python main.py

# CLI one-shot
python main.py "Research async Python and write a scraper"

# Web UI
streamlit run ui/app.py
```
    """)
