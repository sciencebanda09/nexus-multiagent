"""
NEXUS Core Configuration
Loads YAML config, initializes LLM with fallback, sets up logging.
"""

import yaml
import logging
import time
import sqlite3
from pathlib import Path
from functools import wraps
from typing import Optional

# ── Load YAML ──────────────────────────────────────────────────────────────
CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"
with open(CONFIG_PATH) as f:
    CFG = yaml.safe_load(f)

# ── Directories ─────────────────────────────────────────────────────────────
for d in ["./workspace", "./outputs", "./nexus_logs", "./nexus_memory_db"]:
    Path(d).mkdir(parents=True, exist_ok=True)

# ── Logging ─────────────────────────────────────────────────────────────────
log_cfg = CFG["logging"]
logging.basicConfig(
    level=getattr(logging, log_cfg["level"]),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.FileHandler(log_cfg["file"]),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("nexus.config")


# ── LLM Factory ─────────────────────────────────────────────────────────────
def _make_llm(model: str, temperature: float = None):
    from crewai import LLM
    oc = CFG["ollama"]
    return LLM(
        model=f"ollama/{model}",
        base_url=oc["base_url"],
        temperature=temperature if temperature is not None else oc["temperature"],
    )

def get_llm(fast: bool = False):
    """Return primary or fast LLM; fallback to other if first fails."""
    oc = CFG["ollama"]
    primary = oc["fast_model"] if fast else oc["primary_model"]
    fallback = oc["primary_model"] if fast else oc["fast_model"]
    try:
        llm = _make_llm(primary)
        logger.info(f"LLM loaded: {primary}")
        return llm
    except Exception as e:
        logger.warning(f"Primary LLM {primary} failed ({e}), trying {fallback}")
        return _make_llm(fallback)


# Singletons
llm = get_llm(fast=False)
fast_llm = get_llm(fast=True)


# ── SQLite Job History ───────────────────────────────────────────────────────
def init_db():
    db_path = CFG["database"]["path"]
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goal TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            result TEXT,
            error TEXT,
            created_at REAL,
            finished_at REAL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS agent_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER,
            agent TEXT,
            action TEXT,
            content TEXT,
            timestamp REAL,
            FOREIGN KEY(job_id) REFERENCES jobs(id)
        )
    """)
    conn.commit()
    conn.close()
    return db_path


DB_PATH = init_db()


def save_job(goal: str) -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "INSERT INTO jobs (goal, status, created_at) VALUES (?, 'running', ?)",
        (goal, time.time())
    )
    job_id = cur.lastrowid
    conn.commit()
    conn.close()
    return job_id


def finish_job(job_id: int, result: str = None, error: str = None):
    status = "failed" if error else "completed"
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE jobs SET status=?, result=?, error=?, finished_at=? WHERE id=?",
        (status, result, error, time.time(), job_id)
    )
    conn.commit()
    conn.close()


def log_agent_action(job_id: int, agent: str, action: str, content: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO agent_logs (job_id, agent, action, content, timestamp) VALUES (?,?,?,?,?)",
        (job_id, agent, action, content[:2000], time.time())
    )
    conn.commit()
    conn.close()


def get_job_history(limit: int = 20):
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT id, goal, status, created_at, finished_at FROM jobs ORDER BY id DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return rows


# ── Circuit Breaker ──────────────────────────────────────────────────────────
class CircuitBreaker:
    """Stops calling a tool after N consecutive failures."""

    def __init__(self, name: str, max_failures: int = 3, reset_after: int = 60):
        self.name = name
        self.max_failures = max_failures
        self.reset_after = reset_after
        self._failures = 0
        self._last_failure_time: Optional[float] = None
        self._open = False

    def call(self, fn, *args, **kwargs):
        if self._open:
            if time.time() - self._last_failure_time > self.reset_after:
                logger.info(f"Circuit {self.name}: resetting after cooldown")
                self._open = False
                self._failures = 0
            else:
                return f"[CircuitBreaker] {self.name} is open — too many failures. Try again in {self.reset_after}s."
        try:
            result = fn(*args, **kwargs)
            self._failures = 0
            return result
        except Exception as e:
            self._failures += 1
            self._last_failure_time = time.time()
            logger.error(f"Circuit {self.name}: failure {self._failures}/{self.max_failures} — {e}")
            if self._failures >= self.max_failures:
                self._open = True
                logger.error(f"Circuit {self.name}: OPEN — disabling tool")
            return f"Tool error ({self.name}): {e}"


# ── Retry Decorator ──────────────────────────────────────────────────────────
def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            attempt = 0
            wait = delay
            while attempt < max_attempts:
                try:
                    return fn(*args, **kwargs)
                except Exception as e:
                    attempt += 1
                    if attempt == max_attempts:
                        raise
                    logger.warning(f"Retry {attempt}/{max_attempts} for {fn.__name__}: {e}")
                    time.sleep(wait)
                    wait *= backoff
        return wrapper
    return decorator

