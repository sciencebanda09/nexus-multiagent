# ⚡ NEXUS Multi-Agent AI System

**6 Agents · 12 Tools · Vector Memory · 100% Local · Zero Cost**

---

## Requirements
- Windows/Linux/Mac
- Python 3.10+
- Ollama with `qwen2.5:3b` and `qwen2.5:0.5b`
- 8GB+ RAM (6GB usable)

---

## Setup (one time)

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Make sure Ollama is running with your models
ollama serve                    # Terminal 1
ollama list                     # Verify qwen2.5:3b and qwen2.5:0.5b exist
```

---

## Run

### Option A — Interactive CLI
```bash
python main.py
```

### Option B — One-shot CLI
```bash
python main.py "Research async Python and write a working web scraper"
python main.py "Calculate the integral of x^3 - 2x from 0 to 4"
python main.py "Write a Python quicksort implementation and test it"
python main.py "Find top 3 open source LLMs and compare them"
```

### Option C — Web UI (Streamlit)
```bash
streamlit run ui/app.py
# Open: http://localhost:8501
```

---

## Architecture

```
nexus/
├── main.py              ← CLI entry point
├── config.yaml          ← All settings (models, memory, tools)
├── requirements.txt
│
├── core/
│   └── config.py        ← LLM setup, SQLite DB, circuit breaker, retry
│
├── agents/
│   └── agents.py        ← 6 agents with specialized prompts
│
├── tools/
│   └── tools.py         ← 12 tools with error handling
│
├── memory/
│   └── memory.py        ← ChromaDB vector memory
│
├── tasks/
│   └── tasks.py         ← Dynamic task pipeline builder
│
├── ui/
│   └── app.py           ← Streamlit web interface
│
├── workspace/           ← Coder saves files here
├── outputs/             ← Writer saves reports here
└── nexus_logs/          ← Log files
```

---

## Agents

| Agent | LLM | Tools | Role |
|-------|-----|-------|------|
| Orchestrator | 3b | planner, memory | Decomposes & delegates |
| Researcher | 3b | web_search, url_fetch, memory | Finds real info |
| Analyst | 3b | math, text_analyze, json, code | Data & insights |
| Coder | 3b | run_python, file_write, math | Writes & tests code |
| Writer | 3b | file_write, summarizer | Final reports |
| Critic | 0.5b | text_analyze | Quality review |

---

## Tools (12)

| Tool | Description |
|------|-------------|
| `web_search` | DuckDuckGo (no API key needed) |
| `url_fetch` | Fetch + parse any webpage |
| `run_python` | Execute Python (sandboxed, 20s timeout) |
| `write_file` | Save files to ./workspace or ./outputs |
| `read_file` | Read any file |
| `math_engine` | SymPy: solve, integrate, differentiate, stats |
| `analyze_text` | Readability, keywords, sentiment |
| `query_json` | Dot-notation JSON traversal |
| `system_info` | CPU, RAM, disk, platform |
| `recall_memory` | Semantic search over past agent work |
| `plan_subtasks` | LLM-powered goal decomposition |
| `summarize` | Fast text compression (uses 0.5b) |

---

## Memory System

- **Backend**: ChromaDB (persistent, local)
- **Embeddings**: sentence-transformers `all-MiniLM-L6-v2` (~80MB, offline)
- **Persists**: across all sessions in `./nexus_memory_db/`
- **Namespacing**: per-agent + per-category
- **Recall**: semantic similarity search

---

## Error Handling

- **Circuit Breaker**: disables a tool after 3 consecutive failures, auto-resets after 60s
- **Retry**: 3 attempts with exponential backoff on LLM calls
- **Job DB**: every run saved in `./nexus_jobs.db` (SQLite)
- **Logs**: `./nexus_logs/nexus.log`

---

## RAM Tuning (8GB system)

In `config.yaml`:
```yaml
ollama:
  num_ctx: 2048      # Keep this — prevents OOM
  num_predict: 512   # Keep this
crew:
  max_rpm: 8         # Limits parallel LLM calls
```

If you hit OOM, reduce `num_ctx` to `1024`.

---

## Example Goals

```
Research Python async patterns and write a working async web scraper
Analyze the pros and cons of solar vs wind energy
Write and test a Python implementation of merge sort
Calculate the derivative and integral of x^4 - 3x^2 + 2
Find 3 open source robotics frameworks and compare their GitHub activity
Explain how transformers work and write a simple attention mechanism
Get my system stats and analyze performance
```

---

## CLI Commands

Inside `python main.py` interactive mode:
- Type any goal and press Enter
- `history` — show past jobs
- `quit` / `exit` — exit
