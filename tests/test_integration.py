"""
Integration tests — require Ollama running.
Skipped in CI (excluded in pytest call).
Run locally: pytest tests/test_integration.py -v
"""
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

pytestmark = pytest.mark.skipif(
    True, reason="Integration tests require local Ollama — run manually"
)

def test_full_math_goal():
    from main import run
    result = run("calculate 2 + 2", verbose=False)
    assert result["success"]

def test_full_code_goal():
    from main import run
    result = run("write a python hello world script", verbose=False)
    assert result["success"]
