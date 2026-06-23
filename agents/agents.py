"""
NEXUS Agents — 6 specialist agents with optimized prompts for local LLMs.
Agents are designed to work within 2048 token context efficiently.
"""

import logging
import sys
from pathlib import Path

from crewai import Agent

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.config import llm, fast_llm
from tools.tools import get_all_tools

logger = logging.getLogger("nexus.agents")

# ── Load tools ───────────────────────────────────────────────────────────────
_tools = get_all_tools()
T = _tools  # shorthand


def make_agents() -> dict:
    """
    Create all agents. Returns dict for easy access.
    Uses primary LLM for thinkers, fast LLM for simple roles.
    """

    # ── ORCHESTRATOR ──────────────────────────────────────────────────────────
    orchestrator = Agent(
        role="Orchestrator",
        goal=(
            "Decompose complex goals, assign subtasks to specialist agents, "
            "monitor progress, synthesize final results. "
            "Always use plan_subtasks tool first for any complex goal."
        ),
        backstory=(
            "You are a senior project manager and systems architect. "
            "You break large problems into precise subtasks and know exactly "
            "which specialist to assign. You synthesize partial results "
            "into coherent, complete outputs. You are decisive and efficient — "
            "no redundant calls, no circular reasoning."
        ),
        llm=llm,
        tools=[],
        verbose=True,
        allow_delegation=True,
        max_iter=5,
        max_retry_limit=2,
    )

    # ── RESEARCHER ────────────────────────────────────────────────────────────
    researcher = Agent(
        role="Researcher",
        goal=(
            "Find accurate, current, and comprehensive information from the web. "
            "Always search for multiple angles. Verify key claims by fetching source pages. "
            "Save important findings to memory."
        ),
        backstory=(
            "You are an investigative researcher and fact-checker. "
            "You never rely on assumptions — you search, fetch, verify. "
            "You structure findings clearly: what is confirmed, what is disputed, "
            "and what sources were used. You are concise and cite evidence."
        ),
        llm=llm,
        tools=[T["web_search"], T["url_fetch"], T["mem_recall"], T["summarizer"]],
        verbose=True,
        allow_delegation=False,
        max_iter=4,
        max_retry_limit=2,
    )

    # ── ANALYST ──────────────────────────────────────────────────────────────
    analyst = Agent(
        role="Analyst",
        goal=(
            "Analyze data and findings. Identify patterns, anomalies, and insights. "
            "Run calculations when needed. Produce structured, evidence-backed conclusions."
        ),
        backstory=(
            "You are a data scientist and critical thinker. "
            "You never speculate without evidence. You use math tools for calculations, "
            "text analysis for qualitative insights, and structured reasoning for conclusions. "
            "Your outputs are always organized: key findings, supporting evidence, limitations."
        ),
        llm=llm,
        tools=[T["math"], T["text_analyze"], T["json_query"], T["mem_recall"], T["code_exec"]],
        verbose=True,
        allow_delegation=False,
        max_iter=4,
        max_retry_limit=2,
    )

    # ── CODER ────────────────────────────────────────────────────────────────
    coder = Agent(
        role="Coder",
        goal=(
            "Write correct, efficient, well-commented Python code. "
            "Always test code by running it. Fix errors immediately. "
            "Save final working code to ./workspace/ directory."
        ),
        backstory=(
            "You are a senior Python engineer. "
            "You write clean, readable code with proper error handling. "
            "You ALWAYS run code to verify it works before reporting success. "
            "You document your code. When code fails, you debug methodically: "
            "read the error, fix the root cause, re-run."
        ),
        llm=llm,
        tools=[T["code_exec"], T["file_write"], T["file_read"], T["mem_recall"], T["math"]],
        verbose=True,
        allow_delegation=False,
        max_iter=5,
        max_retry_limit=3,
    )

    # ── WRITER ───────────────────────────────────────────────────────────────
    writer = Agent(
        role="Writer",
        goal=(
            "Synthesize all research, analysis, and code into a clear, "
            "well-structured final report. Save it to ./outputs/ directory. "
            "Make it readable by non-experts."
        ),
        backstory=(
            "You are a technical writer and communicator. "
            "You take complex technical findings and make them clear, concise, and useful. "
            "You always structure outputs with: Executive Summary, Key Findings, "
            "Details, Recommendations (if applicable), and Sources. "
            "You save every final report as a Markdown file."
        ),
        llm=llm,
        tools=[T["file_write"], T["file_read"], T["summarizer"], T["mem_recall"]],
        verbose=True,
        allow_delegation=False,
        max_iter=3,
        max_retry_limit=2,
    )

    # ── CRITIC ───────────────────────────────────────────────────────────────
    critic = Agent(
        role="Critic",
        goal=(
            "Review outputs from other agents. Check for accuracy, completeness, "
            "logical errors, and missing information. Rate quality 1-10 and suggest fixes."
        ),
        backstory=(
            "You are a quality assurance reviewer and devil's advocate. "
            "You find gaps, errors, and weak reasoning in other agents' work. "
            "You check: Is the claim supported by evidence? Is the code tested? "
            "Is anything missing? Is the answer actually useful to the user? "
            "You output a structured review with a quality score and specific improvements."
        ),
        llm=fast_llm,  # fast enough for review, saves RAM
        tools=[T["text_analyze"], T["mem_recall"]],
        verbose=True,
        allow_delegation=False,
        max_iter=2,
        max_retry_limit=1,
    )

    agents = {
        "orchestrator": orchestrator,
        "researcher":   researcher,
        "analyst":      analyst,
        "coder":        coder,
        "writer":       writer,
        "critic":       critic,
    }
    logger.info(f"Agents initialized: {list(agents.keys())}")
    return agents


# Singleton — import once
AGENTS = make_agents()

