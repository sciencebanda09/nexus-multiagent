# ⚡ NEXUS Multi-Agent AI System

<div align="center">

[![CI](https://github.com/sciencebanda09/nexus-multiagent/actions/workflows/ci.yml/badge.svg)](https://github.com/sciencebanda09/nexus-multiagent/actions/workflows/ci.yml)
[![CodeQL](https://github.com/sciencebanda09/nexus-multiagent/actions/workflows/codeql.yml/badge.svg)](https://github.com/sciencebanda09/nexus-multiagent/actions/workflows/codeql.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue)](https://www.python.org/)
[![Ollama](https://img.shields.io/badge/LLM-Ollama%20local-green)](https://ollama.ai)
[![No API Key](https://img.shields.io/badge/API%20Key-None%20Required-brightgreen)](https://github.com/sciencebanda09/nexus-multiagent)

**Production-grade multi-agent AI system — runs 100% locally, zero cost, zero API keys.**

[Quickstart](#quickstart) · [Architecture](#architecture) · [Tools](#tools-12) · [Contributing](CONTRIBUTING.md) · [Changelog](CHANGELOG.md)

</div>

---

## What is NEXUS?

NEXUS is a local multi-agent orchestration system built on [CrewAI](https://github.com/crewAIInc/crewAI) and [Ollama](https://ollama.ai). Six specialized AI agents collaborate to research, analyze, code, and write — all running on your own hardware with `qwen2.5:3b`.

**No OpenAI. No Anthropic. No monthly bill.**

```
nexus> Research async Python patterns and write a working web scraper
```

→ Orchestrator plans → Researcher searches the web → Analyst finds patterns  
→ Coder writes + tests the scraper → Writer produces a report → Critic reviews quality

---

## Features

- **6 Specialist Agents** — Orchestrator, Researcher, Analyst, Coder, Writer, Critic
- **12 Custom Tools** — web search, URL fetch, Python execution, math engine, file I/O, text analysis, JSON query, system info, vector memory recall, task planner, summarizer
- **Persistent Vector Memory** — ChromaDB + sentence-transformers, survives restarts
- **Smart Task Routing** — auto-detects goal type (research / code / math / analyze) and builds the right pipeline
- **Production Error Handling** — circuit breakers, retry with backoff, SQLite job history
- **Streamlit Web UI** — browser-based interface with memory browser and job history
- **8GB RAM compatible** — tuned for `qwen2.5:3b` on consumer hardware

---

## Quickstart

### Prerequisites

- Python 3.11 or 3.12
- [Ollama](https://ollama.ai) installed
- 8GB+ RAM

```bash
# Pull required models
ollama pull qwen2.5:3b
ollama pull qwen2.5:0.5b
```

### Install

```bash
git clone https://github.com/sciencebanda09/nexus-multiagent.git
cd nexus-multiagent

# Create venv (Python 3.11 recommended)
py -3.11 -m venv nexus_env
nexus_env\Scripts\activate        # Windows
source nexus_env/bin/activate     # Linux/Mac

pip install -r requirements.txt
```

### Run

```bash
# Terminal 1 — start Ollama
ollama serve

# Terminal 2 — start NEXUS
python main.py
```

**Or with Streamlit UI:**
```bash
streamlit run ui/app.py
# Open http://localhost:8501
```

**Or one-shot from CLI:**
```bash
python main.py "Research Python async patterns and write a web scraper"
```

---

## Architecture

```
nexus-multiagent/
├── main.py                  ← CLI entry point (interactive + one-shot)
├── config.yaml              ← All settings (models, memory, tools)
├── requirements.txt
│
├── core/
│   └── config.py            ← LLM factory, SQLite DB, circuit breaker, retry
│
├── agents/
│   └── agents.py            ← 6 agents with tuned prompts
│
├── tools/
│   └── tools.py             ← 12 tools with error handling
│
├── memory/
│   └── memory.py            ← ChromaDB vector memory
│
├── tasks/
│   └── tasks.py             ← Dynamic task pipeline builder
│
├── ui/
│   └── app.py               ← Streamlit web UI
│
├── tests/                   ← pytest unit tests
├── workspace/               ← Coder saves files here
└── outputs/                 ← Writer saves reports here
```

### Agent Pipeline

```
User Goal
    │
    ▼
Orchestrator ──── plan_subtasks ──► execution plan
    │
    ├──► Researcher ──── web_search, url_fetch ──► research notes
    │
    ├──► Analyst ──── math_engine, analyze_text ──► insights
    │
    ├──► Coder ──── run_python, write_file ──► tested code
    │
    ├──► Writer ──── summarize, write_file ──► final report
    │
    └──► Critic ──── text_analyze ──► quality score
```

---

## Tools (12)

| Tool | Description |
|------|-------------|
| `web_search` | DuckDuckGo search — no API key |
| `url_fetch` | Fetch + parse any webpage (BeautifulSoup) |
| `run_python` | Sandboxed Python execution (20s timeout) |
| `write_file` | Save to `./workspace` or `./outputs` |
| `read_file` | Read any local file |
| `math_engine` | SymPy: solve, integrate, differentiate, stats |
| `analyze_text` | Readability, keywords, sentiment proxy |
| `query_json` | Dot-notation JSON traversal |
| `system_info` | CPU, RAM, disk, platform (psutil) |
| `recall_memory` | Semantic search over past agent work |
| `plan_subtasks` | LLM-powered goal decomposition |
| `summarize` | Fast text compression (uses 0.5b model) |

---

## RAM Tuning

Configured by default for 8GB systems. In `config.yaml`:

```yaml
ollama:
  num_ctx: 2048      # Keep — prevents OOM
  num_predict: 512   # Keep
crew:
  max_rpm: 8         # Limits parallel LLM calls
```

If you hit OOM: set `num_ctx: 1024`.

---

## Example Goals

```
Research Python async patterns and write a working async web scraper
Analyze the pros and cons of solar vs wind energy
Write and test a Python quicksort implementation
Calculate the derivative and integral of x^4 - 3x^2 + 2
Find the top 3 open source robotics frameworks and compare them
Get my system stats and analyze performance bottlenecks
Explain how transformers work and write a simple attention layer
```

---

## Development

```bash
pip install pytest pytest-cov ruff
pytest tests/ -v
ruff check .
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide.

---

## Built By

**Shashank Dev** — Founder & CEO, [D-MechatronicX](https://github.com/sciencebanda09)  
World Champion FPV Drone Rescue · ISRO BAH2026 · iDEX DISC14

---

## License

[MIT](LICENSE) © 2026 Shashank Dev
