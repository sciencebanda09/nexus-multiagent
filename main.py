"""
NEXUS Multi-Agent System — Main Entry Point
Run: python main.py
Or:  python main.py "Your goal here"
"""

import sys
import time
import traceback
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    RICH = True
except ImportError:
    RICH = False

from crewai import Crew, Process
from agents.agents import AGENTS
from tasks.tasks import build_tasks
from core.config import save_job, finish_job, get_job_history

logger = logging.getLogger("nexus.main")
console = Console() if RICH else None


def banner():
    if RICH:
        console.print(Panel.fit(
            "[bold cyan]NEXUS[/bold cyan] [white]Multi-Agent AI System[/white]\n"
            "[dim]6 Agents · 12 Tools · Vector Memory · Local LLM[/dim]",
            border_style="cyan",
        ))
    else:
        print("\n" + "="*55)
        print("  NEXUS Multi-Agent AI System")
        print("  6 Agents | 12 Tools | Vector Memory | Local LLM")
        print("="*55 + "\n")


SIMPLE_REPLIES = {
    "hi", "hello", "hey", "hiya", "howdy",
    "thanks", "thank you", "ty", "thx",
    "ok", "okay", "k", "cool", "got it",
    "bye", "goodbye", "cya", "exit", "quit",
    "yes", "no", "yep", "nope", "sure",
}

def is_simple_input(goal: str) -> bool:
    return goal.strip().lower() in SIMPLE_REPLIES or len(goal.strip()) < 4


def run(goal: str, verbose: bool = True) -> dict:
    start = time.time()

    # Short-circuit for greetings / one-word inputs
    if is_simple_input(goal):
        if RICH:
            console.print("[bold cyan]NEXUS:[/bold cyan] Hello! Give me a research goal or task and I will get to work.")
        else:
            print("NEXUS: Hello! Give me a research goal or task and I will get to work.")
        return {"success": True, "result": None, "job_id": None, "duration": 0, "error": None}

    banner()
    start = time.time()

    if RICH:
        console.print(f"\n[bold green]GOAL:[/bold green] {goal}\n")
    else:
        print(f"\nGOAL: {goal}\n")

    job_id = save_job(goal)
    logger.info(f"Job {job_id} started: {goal[:80]}")

    try:
        tasks = build_tasks(goal, job_id=job_id)

        if RICH:
            tbl = Table(show_header=True, header_style="bold magenta")
            tbl.add_column("Step", style="dim", width=4)
            tbl.add_column("Agent", style="cyan")
            tbl.add_column("Task")
            for i, t in enumerate(tasks, 1):
                tbl.add_row(str(i), t.agent.role, t.description[:70] + "...")
            console.print(tbl)

        crew = Crew(
            agents=[AGENTS["researcher"], AGENTS["analyst"], AGENTS["coder"], AGENTS["writer"], AGENTS["critic"]],
            tasks=tasks,
            process=Process.sequential,
            verbose=False,
            memory=True,
            cache=True,
            max_rpm=8,
            share_crew=False,
            embedder={
                "provider": "ollama",
                "config": {
                    "model": "nomic-embed-text",
                    "base_url": "http://localhost:11434",
                },
            },
        )

        if RICH:
            console.print("\n[yellow]Crew executing...[/yellow]\n")
        else:
            print("\n[Crew executing...]\n")

        result = crew.kickoff()
        duration = round(time.time() - start, 1)
        result_str = str(result)
        finish_job(job_id, result=result_str)

        if RICH:
            console.print(Panel(
                f"[bold green]COMPLETED[/bold green] in {duration}s\n\n{result_str[:2000]}",
                title="Result", border_style="green",
            ))
        else:
            print(f"\nCOMPLETED in {duration}s\n{result_str[:3000]}")

        report_path = Path("./outputs/report.md")
        if report_path.exists():
            print(f"\nReport saved: {report_path}")

        return {"success": True, "result": result_str, "job_id": job_id,
                "duration": duration, "error": None}

    except KeyboardInterrupt:
        finish_job(job_id, error="Interrupted")
        print("\nInterrupted.")
        return {"success": False, "result": None, "job_id": job_id, "error": "Interrupted"}

    except Exception as e:
        duration = round(time.time() - start, 1)
        err_str = traceback.format_exc()
        finish_job(job_id, error=str(e))
        logger.error(f"Job {job_id} failed: {e}\n{err_str}")
        if RICH:
            console.print(Panel(f"[bold red]FAILED[/bold red] in {duration}s\n\n{e}",
                                title="Error", border_style="red"))
        else:
            print(f"\nFAILED: {e}")
            traceback.print_exc()
        return {"success": False, "result": None, "job_id": job_id,
                "duration": duration, "error": str(e)}


def show_history():
    rows = get_job_history(limit=10)
    if RICH:
        tbl = Table(title="Job History", show_header=True, header_style="bold blue")
        tbl.add_column("ID", width=4)
        tbl.add_column("Goal")
        tbl.add_column("Status", width=10)
        tbl.add_column("Duration", width=10)
        for row in rows:
            jid, goal, status, created, finished = row
            dur = f"{round(finished-created,1)}s" if finished else "—"
            color = "green" if status=="completed" else ("red" if status=="failed" else "yellow")
            tbl.add_row(str(jid), goal[:60], f"[{color}]{status}[/{color}]", dur)
        console.print(tbl)
    else:
        print("\nJob History:")
        for row in rows:
            jid, goal, status, created, finished = row
            dur = f"{round(finished-created,1)}s" if finished else "—"
            print(f"  [{jid}] {status:10} {dur:8} {goal[:50]}")


def interactive():
    banner()
    if RICH:
        console.print("[dim]Commands: 'history', 'quit', or type your goal[/dim]\n")
    else:
        print("Commands: 'history', 'quit', or type your goal\n")

    while True:
        try:
            goal = (console.input("[bold cyan]nexus> [/bold cyan]") if RICH else input("nexus> ")).strip()
            if not goal:
                continue
            if goal.lower() in ("quit", "exit", "q"):
                print("Goodbye.")
                break
            if goal.lower() == "history":
                show_history()
                continue
            run(goal)
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye.")
            break


if __name__ == "__main__":
    if len(sys.argv) > 1:
        run(" ".join(sys.argv[1:]))
    else:
        interactive()



