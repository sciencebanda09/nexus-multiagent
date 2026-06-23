"""
NEXUS Tasks — Dynamic task builder with goal-type detection.
Automatically selects task pipeline based on what the user wants.
"""

import logging
import sys
from pathlib import Path
from crewai import Task

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.agents import AGENTS

logger = logging.getLogger("nexus.tasks")

A = AGENTS  # shorthand


def detect_goal_type(goal: str) -> list:
    g = goal.lower()
    tags = []
    if any(w in g for w in ["search","find","research","look up","what is","who is","news","latest","current"]):
        tags.append("research")
    if any(w in g for w in ["code","write","script","program","function","implement","build","create","debug","fix"]):
        tags.append("code")
    if any(w in g for w in ["analyze","analysis","compare","pattern","insight","data","statistics","trend"]):
        tags.append("analyze")
    if any(w in g for w in ["report","summarize","explain","write","document","essay","article","draft"]):
        tags.append("write")
    if any(w in g for w in ["calculate","math","solve","equation","integral","derivative","factor","formula"]):
        tags.append("math")
    if any(w in g for w in ["system","cpu","ram","disk","memory","performance","benchmark"]):
        tags.append("system")
    if not tags:
        tags = ["research", "analyze", "write"]
    return tags


def build_tasks(goal: str, job_id: int = None) -> list:
    tags = detect_goal_type(goal)
    logger.info(f"Goal type detected: {tags} for: {goal[:80]}")
    tasks = []

    plan_task = Task(
        description=(
            f"USER GOAL: {goal}\n\n"
            "1. Use the plan_subtasks tool to decompose this goal.\n"
            "2. Identify which agents should handle each part.\n"
            "3. List any prerequisites or dependencies between subtasks.\n"
            "4. Check memory for any relevant past work on similar tasks.\n"
            "Output: A numbered execution plan with agent assignments."
        ),
        expected_output=(
            "A structured execution plan with:\n"
            "- Numbered subtasks (1-6 max)\n"
            "- Agent assigned to each\n"
            "- Dependencies noted\n"
            "- Any relevant prior context from memory"
        ),
        agent=A["orchestrator"],
    )
    tasks.append(plan_task)

    if "research" in tags or "code" in tags:
        research_task = Task(
            description=(
                f"Research the following goal thoroughly: {goal}\n\n"
                "Steps:\n"
                "1. Search web for key information (3+ searches with different angles).\n"
                "2. Fetch 1-2 most relevant URLs for deeper content.\n"
                "3. Check memory for prior related findings.\n"
                "4. Organize findings into: Facts, Context, Key Sources.\n"
                "If no internet or search fails: use recalled memory and state limitations."
            ),
            expected_output=(
                "Structured research notes with:\n"
                "- Key facts found\n"
                "- Source URLs\n"
                "- Context and background\n"
                "- Any conflicting information noted"
            ),
            agent=A["researcher"],
            context=[plan_task],
        )
        tasks.append(research_task)
        prev_tasks = [plan_task, research_task]
    else:
        prev_tasks = [plan_task]

    if "analyze" in tags or "math" in tags or "code" in tags:
        analyze_task = Task(
            description=(
                f"Analyze all available information related to: {goal}\n\n"
                "Steps:\n"
                "1. Review findings from prior tasks.\n"
                "2. If math/calculations needed: use math_engine tool.\n"
                "3. If text data available: use analyze_text tool.\n"
                "4. If structured data: use query_json tool.\n"
                "5. If system metrics needed: use system_info tool.\n"
                "6. Identify: key patterns, gaps, insights, risks.\n"
                "Output structured analysis with evidence for each point."
            ),
            expected_output=(
                "Analysis report with:\n"
                "- Key Findings (numbered)\n"
                "- Supporting Evidence for each\n"
                "- Patterns or Anomalies\n"
                "- Confidence level (High/Medium/Low) per finding\n"
                "- Limitations of the analysis"
            ),
            agent=A["analyst"],
            context=prev_tasks,
        )
        tasks.append(analyze_task)
        prev_tasks = prev_tasks + [analyze_task]

    if "code" in tags:
        code_task = Task(
            description=(
                f"Implement code for: {goal}\n\n"
                "Steps:\n"
                "1. Read analysis/research context carefully.\n"
                "2. Write clean, well-commented Python code.\n"
                "3. ALWAYS run the code using run_python tool to verify it works.\n"
                "4. If it fails: read error, fix, re-run. Repeat until working.\n"
                "5. Save final working code to ./workspace/ using write_file.\n"
                "   Format: {\"path\": \"./workspace/solution.py\", \"content\": \"<code>\"}\n"
                "6. Include usage example in comments.\n"
                "Do NOT report success without actually running the code."
            ),
            expected_output=(
                "Working code with:\n"
                "- The complete, tested code\n"
                "- Actual run output/results\n"
                "- File path where it was saved\n"
                "- Usage instructions"
            ),
            agent=A["coder"],
            context=prev_tasks,
        )
        tasks.append(code_task)
        prev_tasks = prev_tasks + [code_task]

    write_task = Task(
        description=(
            f"Create a comprehensive final answer for: {goal}\n\n"
            "Steps:\n"
            "1. Read all context from prior tasks.\n"
            "2. Summarize key findings clearly.\n"
            "3. Structure the report:\n"
            "   # Executive Summary (2-3 sentences)\n"
            "   # Key Findings\n"
            "   # Details\n"
            "   # Code/Examples (if applicable)\n"
            "   # Recommendations\n"
            "   # Sources\n"
            "4. Save the report using write_file: {\"path\": \"./outputs/report.md\", \"content\": \"<report>\"}\n"
            "5. Return the full report text."
        ),
        expected_output=(
            "Complete, well-structured Markdown report saved to ./outputs/report.md. "
            "Should be immediately useful to a non-expert reader."
        ),
        agent=A["writer"],
        context=prev_tasks,
    )
    tasks.append(write_task)

    critique_task = Task(
        description=(
            "Review the final report and all agent outputs critically.\n\n"
            "Check for:\n"
            "1. Accuracy — are claims supported by evidence?\n"
            "2. Completeness — does it fully answer the user's goal?\n"
            "3. Code — was it actually tested and working?\n"
            "4. Clarity — is it understandable?\n"
            "5. Gaps — what's missing?\n\n"
            f"Original user goal: {goal}\n\n"
            "Rate the output 1-10 with justification. "
            "If score < 7, list specific fixes needed."
        ),
        expected_output=(
            "Quality review with:\n"
            "- Score: X/10\n"
            "- Strengths\n"
            "- Weaknesses/Gaps\n"
            "- Specific fixes if score < 7\n"
            "- Final verdict: PASS or NEEDS_REVISION"
        ),
        agent=A["critic"],
        context=[write_task] + prev_tasks[-2:],
    )
    tasks.append(critique_task)

    logger.info(f"Built {len(tasks)} tasks: {[t.agent.role for t in tasks]}")
    return tasks
