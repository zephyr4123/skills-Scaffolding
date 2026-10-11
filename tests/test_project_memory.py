"""project_memory hook 单测：项目根定位、注入内容、失败放行。"""

import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path

HOOK_PATH = Path(__file__).resolve().parents[1] / "engines" / "codex" / "project_memory.py"
_spec = importlib.util.spec_from_file_location("project_memory", HOOK_PATH)
pm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pm)


class TempHomeCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve()
        self.home = self.root / "home"
        self.home.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def mkdir(self, rel: str) -> Path:
        d = self.root / rel
        d.mkdir(parents=True, exist_ok=True)
        return d


class FindProjectRootTest(TempHomeCase):
    def test_git_root_found_from_subdir(self):
        repo = self.mkdir("home/repo")
        (repo / ".git").mkdir()
        sub = self.mkdir("home/repo/a/b")
        self.assertEqual(pm.find_project_root(sub, self.home), repo)

    def test_git_file_counts_as_marker(self):
        # submodule / worktree 的 .git 是文件而不是目录
        repo = self.mkdir("home/sub-module")
        (repo / ".git").write_text("gitdir: ../.git/modules/x\n")
        self.assertEqual(pm.find_project_root(self.mkdir("home/sub-module/lib"), self.home), repo)

    def test_nearest_nested_repo_wins(self):
        outer = self.mkdir("home/outer")
        (outer / ".git").mkdir()
        inner = self.mkdir("home/outer/inner")
        (inner / ".git").mkdir()
        self.assertEqual(pm.find_project_root(self.mkdir("home/outer/inner/x"), self.home), inner)

    def test_memory_dir_marks_root_without_git(self):
        proj = self.mkdir("home/notes")
        (proj / ".memory").mkdir()
        self.assertEqual(pm.find_project_root(self.mkdir("home/notes/sub"), self.home), proj)

    def test_no_marker_falls_back_to_cwd(self):
        cwd = self.mkdir("home/plain/sub")
        self.assertEqual(pm.find_project_root(cwd, self.home), cwd)

    def test_home_memory_is_not_shared_with_unmarked_dirs(self):
        (self.home / ".memory").mkdir()
        cwd = self.mkdir("home/plain")
        self.assertEqual(pm.find_project_root(cwd, self.home), cwd)

    def test_cwd_equal_home_uses_home(self):
        self.assertEqual(pm.find_project_root(self.home, self.home), self.home)

    def test_outside_home_without_marker_uses_cwd(self):
        cwd = self.mkdir("elsewhere/x")
        self.assertEqual(pm.find_project_root(cwd, self.home), cwd)


class BuildContextTest(TempHomeCase):
    def test_without_index_tells_where_to_write(self):
        proj = self.mkdir("home/p")
        ctx = pm.build_context(proj)
        self.assertIn(str(proj / ".memory"), ctx)
        self.assertIn("还没有记忆", ctx)

    def test_index_content_is_injected(self):
        proj = self.mkdir("home/p")
        (proj / ".memory").mkdir()
        (proj / ".memory" / "MEMORY.md").write_text("- [部署](deploy.md) — 用 make deploy\n", encoding="utf-8")
        ctx = pm.build_context(proj)
        self.assertIn("- [部署](deploy.md) — 用 make deploy", ctx)
        self.assertNotIn("还没有记忆", ctx)

    def test_long_index_is_truncated_with_notice(self):
        proj = self.mkdir("home/p")
        (proj / ".memory").mkdir()
        lines = [f"- [m{i}](m{i}.md) — x" for i in range(pm.MAX_INDEX_LINES + 50)]
        (proj / ".memory" / "MEMORY.md").write_text("\n".join(lines), encoding="utf-8")
        ctx = pm.build_context(proj)
        self.assertIn(f"m{pm.MAX_INDEX_LINES - 1}.md", ctx)
        self.assertNotIn(f"m{pm.MAX_INDEX_LINES}.md", ctx)
        self.assertIn(f"共 {pm.MAX_INDEX_LINES + 50} 行", ctx)


class MainTest(TempHomeCase):
    def run_main(self, stdin_text: str):
        out, err = io.StringIO(), io.StringIO()
        code = pm.main(io.StringIO(stdin_text), out, err, self.home)
        return code, out.getvalue(), err.getvalue()

    def test_emits_session_start_additional_context(self):
        repo = self.mkdir("home/repo")
        (repo / ".git").mkdir()
        (repo / ".memory").mkdir()
        (repo / ".memory" / "MEMORY.md").write_text("- [x](x.md) — 暗号青柠\n", encoding="utf-8")
        sub = self.mkdir("home/repo/src")
        code, out, _ = self.run_main(json.dumps({"cwd": str(sub), "source": "startup"}))
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["hookSpecificOutput"]["hookEventName"], "SessionStart")
        self.assertIn("暗号青柠", payload["hookSpecificOutput"]["additionalContext"])

    def test_malformed_stdin_falls_back_to_process_cwd(self):
        proj = self.mkdir("home/proc-cwd")
        old = os.getcwd()
        os.chdir(proj)
        try:
            code, out, _ = self.run_main("not json")
        finally:
            os.chdir(old)
        self.assertEqual(code, 0)
        self.assertIn(str(proj / ".memory"), json.loads(out)["hookSpecificOutput"]["additionalContext"])

    def test_unreadable_index_fails_open(self):
        proj = self.mkdir("home/locked")
        (proj / ".memory").mkdir()
        index = proj / ".memory" / "MEMORY.md"
        index.write_text("secret", encoding="utf-8")
        index.chmod(0)
        try:
            code, out, err = self.run_main(json.dumps({"cwd": str(proj)}))
        finally:
            index.chmod(0o644)
        # hook 出错不能阻断会话：退出码 0、不输出半截上下文、stderr 留下可定位的信息
        self.assertEqual(code, 0)
        self.assertEqual(out, "")
        self.assertIn(str(proj), err)


if __name__ == "__main__":
    unittest.main()
