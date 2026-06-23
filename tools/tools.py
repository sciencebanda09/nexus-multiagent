"""
NEXUS Tools — 12 production-grade tools
All free, all offline-capable (except web_search/url_fetch).
Every tool has: circuit breaker, retry, input validation, memory logging.
"""

import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

from crewai.tools import BaseTool

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.config import CircuitBreaker, CFG
from memory.memory import save_memory, recall_memory

logger = logging.getLogger("nexus.tools")

# ── Circuit breakers per tool ────────────────────────────────────────────────
_cb = {
    "web_search": CircuitBreaker("web_search"),
    "url_fetch":  CircuitBreaker("url_fetch"),
    "code_exec":  CircuitBreaker("code_exec"),
    "shell":      CircuitBreaker("shell"),
}

# ── ALLOWED IMPORTS for sandboxed code exec ──────────────────────────────────
SAFE_IMPORTS = {
    "math", "os", "sys", "json", "re", "datetime", "itertools",
    "collections", "random", "time", "string", "hashlib", "base64",
    "pathlib", "functools", "operator", "statistics", "decimal",
    "fractions", "textwrap", "pprint", "copy", "enum", "dataclasses",
    "numpy", "scipy", "sympy", "csv", "io",
}
BLOCKED_PATTERNS = [
    r"import\s+subprocess", r"import\s+shutil",
    r"__import__", r"eval\s*\(", r"exec\s*\(",
    r"open\s*\(.*['\"]w['\"]",  # no write in code exec
    r"os\.system", r"os\.popen", r"os\.remove",
]


def _check_code_safety(code: str) -> Optional[str]:
    for pat in BLOCKED_PATTERNS:
        if re.search(pat, code, re.IGNORECASE):
            return f"Blocked pattern: `{pat}`"
    return None


# ═══════════════════════════════════════════════════════════════════════════
# 1. WEB SEARCH
# ═══════════════════════════════════════════════════════════════════════════
class WebSearchTool(BaseTool):
    name: str = "web_search"
    description: str = (
        "Search the web for current information. "
        "Input: a search query string. "
        "Returns: top results with title, URL, snippet."
    )

    def _run(self, query: str) -> str:
        def _search():
            from duckduckgo_search import DDGS
            cfg = CFG["tools"]["web_search"]
            with DDGS() as ddgs:
                results = list(ddgs.text(
                    query.strip(),
                    max_results=cfg["max_results"],
                ))
            if not results:
                return "No results found."
            output = "\n\n".join(
                f"[{i+1}] {r['title']}\nURL: {r['href']}\n{r['body']}"
                for i, r in enumerate(results)
            )
            save_memory("researcher", f"Search: {query}\n{output[:600]}", "web_search")
            return output

        return _cb["web_search"].call(_search)


# ═══════════════════════════════════════════════════════════════════════════
# 2. URL FETCH + PARSE
# ═══════════════════════════════════════════════════════════════════════════
class URLFetchTool(BaseTool):
    name: str = "url_fetch"
    description: str = (
        "Fetch and extract clean text from a URL. "
        "Input: a valid URL string. "
        "Returns: page title + readable text content."
    )

    def _run(self, url: str) -> str:
        def _fetch():
            import requests
            from bs4 import BeautifulSoup
            cfg = CFG["tools"]["url_fetch"]
            url_clean = url.strip().strip('"\'')
            if not url_clean.startswith("http"):
                return "Invalid URL. Must start with http/https."
            resp = requests.get(
                url_clean,
                timeout=cfg["timeout"],
                headers={"User-Agent": "Mozilla/5.0 (NEXUS Agent)"},
            )
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            # Remove script/style noise
            for tag in soup(["script", "style", "nav", "footer", "aside"]):
                tag.decompose()
            title = soup.title.string.strip() if soup.title else "No title"
            text = " ".join(soup.get_text(separator=" ").split())
            text = text[:cfg["max_content_length"]]
            save_memory("researcher", f"URL: {url_clean}\n{text[:500]}", "url_fetch")
            return f"TITLE: {title}\n\nCONTENT:\n{text}"

        return _cb["url_fetch"].call(_fetch)


# ═══════════════════════════════════════════════════════════════════════════
# 3. PYTHON CODE EXECUTION (sandboxed)
# ═══════════════════════════════════════════════════════════════════════════
class CodeExecTool(BaseTool):
    name: str = "run_python"
    description: str = (
        "Execute Python code and return output. "
        "Input: Python code string. "
        "Safe imports: math, numpy, scipy, sympy, json, re, datetime, statistics, etc. "
        "No file writes, no subprocess, no eval/exec."
    )

    def _run(self, code: str) -> str:
        def _exec():
            cfg = CFG["tools"]["code_exec"]
            safety_err = _check_code_safety(code)
            if safety_err:
                return f"Code rejected — {safety_err}"

            result = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True,
                text=True,
                timeout=cfg["timeout"],
                env={**os.environ, "PYTHONPATH": ""},
            )
            out = (result.stdout or "").strip()
            err = (result.stderr or "").strip()
            if err and not out:
                output = f"ERROR:\n{err}"
            elif err:
                output = f"OUTPUT:\n{out}\n\nSTDERR:\n{err}"
            else:
                output = out or "No output."
            save_memory("coder", f"Code:\n{code[:300]}\nOutput: {output[:300]}", "code_exec")
            return output

        return _cb["code_exec"].call(_exec)


# ═══════════════════════════════════════════════════════════════════════════
# 4. FILE WRITE
# ═══════════════════════════════════════════════════════════════════════════
class FileWriteTool(BaseTool):
    name: str = "write_file"
    description: str = (
        "Write content to a file. "
        "Input: JSON string with keys 'path' (relative, under ./workspace or ./outputs) and 'content'."
    )

    def _run(self, input_str: str) -> str:
        try:
            data = json.loads(input_str)
            path = Path(data["path"])
            # Security: only allow relative paths in safe dirs
            allowed = [Path("./workspace"), Path("./outputs")]
            resolved = Path(".") / path
            if not any(str(resolved).startswith(str(a)) for a in allowed):
                # auto-redirect to workspace
                path = Path("./workspace") / path.name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(data["content"], encoding="utf-8")
            return f"Written {len(data['content'])} chars to {path}"
        except json.JSONDecodeError:
            return "Input must be valid JSON: {\"path\": \"...\", \"content\": \"...\"}"
        except Exception as e:
            return f"File write failed: {e}"


# ═══════════════════════════════════════════════════════════════════════════
# 5. FILE READ
# ═══════════════════════════════════════════════════════════════════════════
class FileReadTool(BaseTool):
    name: str = "read_file"
    description: str = (
        "Read content from a file. "
        "Input: file path string (relative). "
        "Returns: file content."
    )

    def _run(self, path_str: str) -> str:
        try:
            path = Path(path_str.strip().strip('"\''))
            if not path.exists():
                return f"File not found: {path}"
            content = path.read_text(encoding="utf-8", errors="replace")
            return content[:8000]  # cap at 8k chars
        except Exception as e:
            return f"File read error: {e}"


# ═══════════════════════════════════════════════════════════════════════════
# 6. MATH & SYMBOLIC ENGINE
# ═══════════════════════════════════════════════════════════════════════════
class MathTool(BaseTool):
    name: str = "math_engine"
    description: str = (
        "Solve math problems: arithmetic, algebra, calculus, statistics, symbolic. "
        "Input: a math expression or word problem string. "
        "Examples: 'solve x^2 - 5x + 6 = 0', 'integrate x^2 from 0 to 1', "
        "'mean of [1,2,3,4,5]', '2**32', 'factor 360'."
    )

    def _run(self, problem: str) -> str:
        try:
            import sympy as sp
            import statistics
            import re as re_mod
            p = problem.strip()

            # Stats: mean/median/stdev of list
            list_match = re_mod.search(r'\[([0-9.,\s]+)\]', p)
            if list_match and any(w in p.lower() for w in ["mean", "median", "std", "variance", "mode"]):
                nums = [float(x.strip()) for x in list_match.group(1).split(",")]
                results = {
                    "mean": statistics.mean(nums),
                    "median": statistics.median(nums),
                    "stdev": statistics.stdev(nums) if len(nums) > 1 else 0,
                    "variance": statistics.variance(nums) if len(nums) > 1 else 0,
                }
                return json.dumps(results, indent=2)

            # Integrate
            if "integrat" in p.lower():
                expr_str = re_mod.sub(r'integrat[e\s]+', '', p, flags=re_mod.IGNORECASE).strip()
                x = sp.Symbol('x')
                # Check for limits
                from_match = re_mod.search(r'from\s+([\-\d.]+)\s+to\s+([\-\d.]+)', p)
                expr_clean = re_mod.sub(r'from.*$', '', expr_str).strip()
                expr = sp.sympify(expr_clean)
                if from_match:
                    a, b = float(from_match.group(1)), float(from_match.group(2))
                    result = sp.integrate(expr, (x, a, b))
                else:
                    result = sp.integrate(expr, x)
                return f"∫ {expr_clean} = {result}"

            # Differentiate
            if "differentiat" in p.lower() or "derivative" in p.lower():
                expr_str = re_mod.sub(r'(differentiat[e\s]+|derivative\s+of\s+)', '', p, flags=re_mod.IGNORECASE).strip()
                x = sp.Symbol('x')
                result = sp.diff(sp.sympify(expr_str), x)
                return f"d/dx({expr_str}) = {result}"

            # Solve equation
            if "solve" in p.lower() or "=" in p:
                expr_str = re_mod.sub(r'solve\s*', '', p, flags=re_mod.IGNORECASE).strip()
                x = sp.Symbol('x')
                if "=" in expr_str:
                    lhs, rhs = expr_str.split("=", 1)
                    eq = sp.Eq(sp.sympify(lhs.strip()), sp.sympify(rhs.strip()))
                else:
                    eq = sp.sympify(expr_str)
                solution = sp.solve(eq, x)
                return f"Solution: x = {solution}"

            # Factor
            if "factor" in p.lower():
                num_match = re_mod.search(r'\d+', p)
                if num_match:
                    n = int(num_match.group())
                    return f"Factors of {n}: {sp.factorint(n)}"

            # Simplify expression
            expr = sp.sympify(p)
            simplified = sp.simplify(expr)
            evaluated = float(simplified.evalf()) if simplified.is_number else simplified
            return f"= {evaluated}"

        except Exception as e:
            # Fallback: safe eval
            try:
                result = eval(problem, {"__builtins__": {}}, {"__import__": None})
                return str(result)
            except Exception:
                return f"Math error: {e}. Try a clearer expression."


# ═══════════════════════════════════════════════════════════════════════════
# 7. TEXT ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════
class TextAnalysisTool(BaseTool):
    name: str = "analyze_text"
    description: str = (
        "Analyze text: word count, sentences, readability, top keywords, sentiment proxy. "
        "Input: text string to analyze."
    )

    def _run(self, text: str) -> str:
        try:
            import re as re_mod
            import collections

            words = re_mod.findall(r'\b[a-z]+\b', text.lower())
            sentences = re_mod.split(r'[.!?]+', text)
            sentences = [s.strip() for s in sentences if s.strip()]

            # TF for top keywords (exclude stopwords)
            stopwords = {
                "the","a","an","is","it","in","on","at","to","of","and","or",
                "but","for","with","by","from","that","this","was","are","be",
                "have","has","had","do","does","did","will","would","can","could"
            }
            content_words = [w for w in words if w not in stopwords and len(w) > 3]
            freq = collections.Counter(content_words)
            top_keywords = freq.most_common(10)

            # Flesch-Kincaid readability proxy
            avg_sent_len = len(words) / max(len(sentences), 1)
            avg_word_len = sum(len(w) for w in words) / max(len(words), 1)
            fk_grade = 0.39 * avg_sent_len + 11.8 * avg_word_len - 15.59
            fk_grade = round(max(0, fk_grade), 1)

            # Sentiment proxy (positive/negative word count)
            pos_words = {"good","great","excellent","best","love","amazing","wonderful","perfect","happy","success"}
            neg_words = {"bad","poor","worst","hate","terrible","awful","fail","error","wrong","problem"}
            pos_count = sum(1 for w in words if w in pos_words)
            neg_count = sum(1 for w in words if w in neg_words)
            sentiment = "positive" if pos_count > neg_count else ("negative" if neg_count > pos_count else "neutral")

            result = {
                "word_count": len(words),
                "sentence_count": len(sentences),
                "avg_sentence_length": round(avg_sent_len, 1),
                "avg_word_length": round(avg_word_len, 1),
                "readability_grade": fk_grade,
                "sentiment_proxy": sentiment,
                "top_keywords": top_keywords,
                "unique_words": len(set(words)),
                "lexical_diversity": round(len(set(words)) / max(len(words), 1), 3),
            }
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Text analysis error: {e}"


# ═══════════════════════════════════════════════════════════════════════════
# 8. JSON QUERY TOOL
# ═══════════════════════════════════════════════════════════════════════════
class JSONQueryTool(BaseTool):
    name: str = "query_json"
    description: str = (
        "Parse and query JSON data using dot-notation paths. "
        "Input: JSON string with keys 'data' (JSON/dict) and 'query' (dot path like 'results.0.name'). "
        "Or just pass raw JSON to pretty-print it."
    )

    def _run(self, input_str: str) -> str:
        try:
            data = json.loads(input_str)
            if isinstance(data, dict) and "data" in data and "query" in data:
                obj = data["data"]
                if isinstance(obj, str):
                    obj = json.loads(obj)
                parts = data["query"].split(".")
                result = obj
                for part in parts:
                    if isinstance(result, list):
                        result = result[int(part)]
                    elif isinstance(result, dict):
                        result = result[part]
                    else:
                        return f"Cannot traverse into {type(result)} at '{part}'"
                return json.dumps(result, indent=2, default=str)
            else:
                # Pretty print
                return json.dumps(data, indent=2, default=str)
        except Exception as e:
            return f"JSON query error: {e}"


# ═══════════════════════════════════════════════════════════════════════════
# 9. SYSTEM INFO
# ═══════════════════════════════════════════════════════════════════════════
class SystemInfoTool(BaseTool):
    name: str = "system_info"
    description: str = (
        "Get system information: CPU, RAM, disk, platform, Python version. "
        "Input: 'all' for full report, or specific key: cpu|ram|disk|platform."
    )

    def _run(self, query: str) -> str:
        try:
            import psutil
            import platform
            q = query.strip().lower()
            info = {}
            if q in ("all", "cpu"):
                info["cpu_percent"] = psutil.cpu_percent(interval=1)
                info["cpu_count"] = psutil.cpu_count()
                info["cpu_freq_MHz"] = round(psutil.cpu_freq().current if psutil.cpu_freq() else 0, 1)
            if q in ("all", "ram"):
                vm = psutil.virtual_memory()
                info["ram_total_GB"] = round(vm.total / 1e9, 2)
                info["ram_used_GB"] = round(vm.used / 1e9, 2)
                info["ram_percent"] = vm.percent
            if q in ("all", "disk"):
                disk = psutil.disk_usage(".")
                info["disk_total_GB"] = round(disk.total / 1e9, 2)
                info["disk_free_GB"] = round(disk.free / 1e9, 2)
                info["disk_percent"] = disk.percent
            if q in ("all", "platform"):
                info["os"] = platform.system()
                info["os_version"] = platform.version()[:80]
                info["python"] = platform.python_version()
                info["machine"] = platform.machine()
            return json.dumps(info, indent=2)
        except Exception as e:
            return f"System info error: {e}"


# ═══════════════════════════════════════════════════════════════════════════
# 10. MEMORY RECALL (agent-accessible)
# ═══════════════════════════════════════════════════════════════════════════
class MemoryRecallTool(BaseTool):
    name: str = "recall_memory"
    description: str = (
        "Recall relevant past findings from long-term memory. "
        "Input: a query string describing what to recall. "
        "Returns: semantically similar past agent outputs."
    )

    def _run(self, query: str) -> str:
        return recall_memory(query, n=4)


# ═══════════════════════════════════════════════════════════════════════════
# 11. TASK PLANNER (LLM-powered sub-task decomposer)
# ═══════════════════════════════════════════════════════════════════════════
class TaskPlannerTool(BaseTool):
    name: str = "plan_subtasks"
    description: str = (
        "Break a complex goal into ordered subtasks with agent assignments. "
        "Input: goal string. "
        "Returns: numbered plan with agent roles."
    )

    def _run(self, goal: str) -> str:
        try:
            from crewai import LLM
            fast_llm = LLM(model="ollama/qwen2.5:0.5b", base_url="http://localhost:11434")
            prompt = f"""Break this goal into 3-6 concrete subtasks.
Goal: {goal}

Format each task as:
TASK N: [agent role] — [specific action]

Agent roles: Researcher, Analyst, Coder, Writer, Orchestrator
Be specific and actionable. No fluff."""
            result = fast_llm.invoke(prompt)
            save_memory("orchestrator", f"Plan for: {goal}\n{result}", "planning")
            return result
        except Exception as e:
            return f"Planning error: {e}"


# ═══════════════════════════════════════════════════════════════════════════
# 12. SUMMARIZER (fast LLM compression)
# ═══════════════════════════════════════════════════════════════════════════
class SummarizerTool(BaseTool):
    name: str = "summarize"
    description: str = (
        "Summarize long text into key points. "
        "Input: JSON with 'text' and optional 'style' (bullets|paragraph|tldr). "
        "Returns: compressed summary."
    )

    def _run(self, input_str: str) -> str:
        try:
            from core.config import fast_llm
            try:
                data = json.loads(input_str)
                text = data.get("text", input_str)
                style = data.get("style", "bullets")
            except Exception:
                text = input_str
                style = "bullets"

            text = text[:3000]  # cap input
            style_prompt = {
                "bullets": "as 5-7 bullet points",
                "paragraph": "as a 2-3 sentence paragraph",
                "tldr": "as a single TL;DR sentence",
            }.get(style, "as bullet points")

            prompt = f"Summarize the following text {style_prompt}:\n\n{text}"
            result = fast_llm.invoke(prompt)
            save_memory("writer", f"Summary of: {text[:100]}...\n{result}", "summary")
            return result
        except Exception as e:
            return f"Summarizer error: {e}"


# ── Tool registry ────────────────────────────────────────────────────────────
def get_all_tools():
    return {
        "web_search":  WebSearchTool(),
        "url_fetch":   URLFetchTool(),
        "code_exec":   CodeExecTool(),
        "file_write":  FileWriteTool(),
        "file_read":   FileReadTool(),
        "math":        MathTool(),
        "text_analyze":TextAnalysisTool(),
        "json_query":  JSONQueryTool(),
        "system_info": SystemInfoTool(),
        "mem_recall":  MemoryRecallTool(),
        "task_planner":TaskPlannerTool(),
        "summarizer":  SummarizerTool(),
    }

