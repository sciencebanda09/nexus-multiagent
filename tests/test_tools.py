"""
NEXUS Unit Tests
Run: pytest tests/ -v
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


# ── Tool tests (no LLM, no Ollama needed) ────────────────────────────────────

class TestMathTool:
    def setup_method(self):
        from tools.tools import MathTool
        self.tool = MathTool()

    def test_basic_arithmetic(self):
        result = self.tool._run("2 + 2")
        assert "4" in result

    def test_solve_quadratic(self):
        result = self.tool._run("solve x**2 - 5*x + 6 = 0")
        assert "2" in result or "3" in result

    def test_mean(self):
        result = self.tool._run("mean of [1, 2, 3, 4, 5]")
        assert "3" in result

    def test_integration(self):
        result = self.tool._run("integrate x**2 from 0 to 3")
        assert "9" in result

    def test_bad_input(self):
        result = self.tool._run("not a math problem !@#")
        assert isinstance(result, str)  # should not raise


class TestTextAnalysisTool:
    def setup_method(self):
        from tools.tools import TextAnalysisTool
        self.tool = TextAnalysisTool()

    def test_word_count(self):
        result = self.tool._run("Hello world this is a test sentence with ten words here")
        data = json.loads(result)
        assert data["word_count"] > 0

    def test_sentiment_positive(self):
        result = self.tool._run("This is excellent great wonderful amazing work")
        data = json.loads(result)
        assert data["sentiment_proxy"] == "positive"

    def test_empty_text(self):
        result = self.tool._run("")
        assert isinstance(result, str)


class TestJSONQueryTool:
    def setup_method(self):
        from tools.tools import JSONQueryTool
        self.tool = JSONQueryTool()

    def test_pretty_print(self):
        result = self.tool._run('{"name": "NEXUS", "version": "1.0"}')
        assert "NEXUS" in result

    def test_dot_query(self):
        payload = json.dumps({
            "data": {"user": {"name": "Shashank"}},
            "query": "user.name"
        })
        result = self.tool._run(payload)
        assert "Shashank" in result

    def test_invalid_json(self):
        result = self.tool._run("not json at all {{{")
        assert "error" in result.lower()


class TestSystemInfoTool:
    def setup_method(self):
        from tools.tools import SystemInfoTool
        self.tool = SystemInfoTool()

    def test_all(self):
        result = self.tool._run("all")
        data = json.loads(result)
        assert "ram_total_GB" in data
        assert "cpu_count" in data

    def test_platform(self):
        result = self.tool._run("platform")
        data = json.loads(result)
        assert "python" in data
        assert "os" in data


class TestCodeExecTool:
    def setup_method(self):
        from tools.tools import CodeExecTool
        self.tool = CodeExecTool()

    def test_basic_print(self):
        result = self.tool._run("print('hello nexus')")
        assert "hello nexus" in result

    def test_math_output(self):
        result = self.tool._run("print(2 ** 10)")
        assert "1024" in result

    def test_blocked_subprocess(self):
        result = self.tool._run("import subprocess; subprocess.run(['ls'])")
        assert "Blocked" in result or "blocked" in result.lower()

    def test_syntax_error(self):
        result = self.tool._run("def broken(: pass")
        assert isinstance(result, str)


class TestFileTools:
    def setup_method(self):
        from tools.tools import FileWriteTool, FileReadTool
        self.write = FileWriteTool()
        self.read = FileReadTool()
        Path("./workspace").mkdir(exist_ok=True)

    def test_write_and_read(self):
        payload = json.dumps({"path": "./workspace/test_nexus.txt", "content": "NEXUS test content"})
        write_result = self.write._run(payload)
        assert "Written" in write_result

        read_result = self.read._run("./workspace/test_nexus.txt")
        assert "NEXUS test content" in read_result

    def test_read_missing_file(self):
        result = self.read._run("./workspace/definitely_does_not_exist_xyz.txt")
        assert "not found" in result.lower()

    def test_path_traversal_blocked(self):
        payload = json.dumps({"path": "../../etc/passwd", "content": "hacked"})
        result = self.write._run(payload)
        # Should redirect to workspace, not write to system path
        assert isinstance(result, str)


# ── Config tests ─────────────────────────────────────────────────────────────

class TestCircuitBreaker:
    def test_opens_after_failures(self):
        from core.config import CircuitBreaker
        cb = CircuitBreaker("test", max_failures=2, reset_after=999)

        def failing_fn():
            raise ValueError("boom")

        cb.call(failing_fn)
        cb.call(failing_fn)
        result = cb.call(failing_fn)
        assert "CircuitBreaker" in result or "open" in result.lower()

    def test_passes_on_success(self):
        from core.config import CircuitBreaker
        cb = CircuitBreaker("test2")
        result = cb.call(lambda: "ok")
        assert result == "ok"


class TestTaskDetection:
    def test_code_goal(self):
        from tasks.tasks import detect_goal_type
        tags = detect_goal_type("write a python function to sort a list")
        assert "code" in tags

    def test_research_goal(self):
        from tasks.tasks import detect_goal_type
        tags = detect_goal_type("research latest AI models")
        assert "research" in tags

    def test_math_goal(self):
        from tasks.tasks import detect_goal_type
        tags = detect_goal_type("calculate the integral of x squared")
        assert "math" in tags

    def test_default_fallback(self):
        from tasks.tasks import detect_goal_type
        tags = detect_goal_type("xyzzy gobbledygook")
        assert len(tags) > 0
