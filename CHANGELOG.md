# Changelog

All notable changes to NEXUS are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [v1.0.0] — 2026-06-23

### Added
- 6-agent hierarchical system: Orchestrator, Researcher, Analyst, Coder, Writer, Critic
- 12 custom tools: web_search, url_fetch, run_python, write_file, read_file, math_engine, analyze_text, query_json, system_info, recall_memory, plan_subtasks, summarize
- ChromaDB persistent vector memory with sentence-transformer embeddings (`all-MiniLM-L6-v2`)
- SQLite job history with per-job logging
- Circuit breaker pattern per tool (auto-disables after 3 failures)
- Retry decorator with exponential backoff
- Dynamic task pipeline — auto-detects goal type (research / code / analyze / math / system)
- Streamlit web UI (`ui/app.py`) with job history, memory browser, docs tab
- Rich CLI with interactive mode and one-shot mode
- YAML-based configuration (`config.yaml`)
- Dual-model setup: `qwen2.5:3b` primary + `qwen2.5:0.5b` fast fallback
- Full project structure with `core/`, `agents/`, `tools/`, `memory/`, `tasks/`, `ui/`

### Notes
- Designed for 8GB RAM systems with local Ollama
- No API keys required — 100% free and offline-capable
