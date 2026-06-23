# Contributing to NEXUS

Thanks for wanting to contribute. NEXUS is built for developers who want powerful local AI without paying for APIs.

---

## Setup for Development

```bash
# 1. Fork and clone
git clone https://github.com/YOUR_USERNAME/nexus-multiagent.git
cd nexus-multiagent

# 2. Create Python 3.11 venv
py -3.11 -m venv nexus_env
nexus_env\Scripts\activate     # Windows
source nexus_env/bin/activate  # Linux/Mac

# 3. Install with dev deps
pip install -r requirements.txt
pip install pytest pytest-cov ruff

# 4. Run tests
pytest tests/ -v

# 5. Lint
ruff check .
```

---

## Branch Strategy

| Branch | Purpose |
|--------|---------|
| `main` | Stable releases only |
| `dev` | Active development |
| `feat/your-feature` | New features |
| `fix/issue-number` | Bug fixes |

Always branch from `dev`, PR back to `dev`. `dev` → `main` only on releases.

---

## Adding a New Tool

1. Open `tools/tools.py`
2. Create a class inheriting `BaseTool`:

```python
class MyNewTool(BaseTool):
    name: str = "my_tool"
    description: str = "What it does and what input format it expects."

    def _run(self, input_str: str) -> str:
        try:
            # your logic
            return result
        except Exception as e:
            return f"Tool error: {e}"
```

3. Add it to `get_all_tools()` at the bottom of the file
4. Assign it to relevant agents in `agents/agents.py`
5. Write a test in `tests/test_tools.py`

---

## Adding a New Agent

1. Open `agents/agents.py`
2. Follow the existing pattern — give it a clear `role`, `goal`, `backstory`
3. Assign only tools it actually needs
4. Add to the `agents` dict in `make_agents()`
5. Update `tasks/tasks.py` if the agent needs its own task type

---

## Commit Style

```
feat: add SQL query tool
fix: circuit breaker reset timer off by one
perf: reduce num_ctx to 1024 for 0.5b model
docs: add tool authoring guide to CONTRIBUTING
chore: update requirements.txt
```

---

## PR Checklist

- [ ] Tested end-to-end with `python main.py`
- [ ] `pytest tests/` passes
- [ ] `ruff check .` clean
- [ ] PR description filled out
- [ ] Linked to relevant issue

---

## Reporting Bugs

Use the [Bug Report](.github/ISSUE_TEMPLATE/bug_report.yml) template. Include your OS, Python version, Ollama model, and full traceback.
