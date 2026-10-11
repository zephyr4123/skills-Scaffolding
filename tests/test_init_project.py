"""init_project.py 单测：在临时 git 项目上验证播种、红线区块、Claude 接入、同步规则、老注入清理与记忆迁移。"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import common  # noqa: E402
import init_project as ip  # noqa: E402

BOTH = ["claude-code", "codex"]


class ProjectCase(unittest.TestCase):
    def setUp(self):
        # 隔离本机全局 git 配置（比如全局 excludes 早就忽略了 settings.local.json），否则会掩盖问题
        patcher = unittest.mock.patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"})
        patcher.start()
        self.addCleanup(patcher.stop)
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name).resolve()
        self.claude_home = base / "home" / ".claude"
        self.root = base / "proj"
        self.root.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        # 每个用例一份可改的种子副本，用来模拟「脚手架发了新版」
        self.seed = base / "seed"
        shutil.copytree(common.SEED_DIR, self.seed)

    def tearDown(self):
        self._tmp.cleanup()

    def init(self, engines=BOTH, apply=True):
        return ip.init_project(self.root, engines, self.claude_home, apply=apply, seed=self.seed)

    def fixes(self, results):
        return [msg for level, msg in results if level == common.FIX]

    def skips(self, results):
        return [msg for level, msg in results if level == common.SKIP]

    def mem(self, name):
        return common.split_frontmatter((self.root / ".memory" / name).read_text(encoding="utf-8"))

    def seed_names(self):
        return sorted(p.name for p in (self.seed / "memory").glob("*.md") if p.name != "MEMORY.md")


class FreshProjectTest(ProjectCase):
    def test_everything_lands_where_expected(self):
        self.init()
        for name in self.seed_names():
            fields, body = self.mem(name)
            self.assertEqual(fields["metadata"]["origin"], common.ORIGIN)
            self.assertEqual(fields["metadata"]["scaffold_sha"], common.fingerprint(fields, body))
            self.assertIn(f"({name})", (self.root / ".memory" / "MEMORY.md").read_text(encoding="utf-8"))

        inner, sha = common.read_block((self.root / "AGENTS.md").read_text(encoding="utf-8"), ip.REDLINES_TAG)
        self.assertEqual(inner, (self.seed / "redlines.md").read_text(encoding="utf-8").strip())
        self.assertEqual(sha, common.text_sha(inner))

        self.assertEqual((self.root / "CLAUDE.md").read_text(encoding="utf-8"), "@AGENTS.md\n")
        settings = json.loads((self.root / ".claude" / "settings.local.json").read_text(encoding="utf-8"))
        self.assertEqual(settings["autoMemoryDirectory"], str(self.root / ".memory"))
        self.assertIn(".claude/settings.local.json", (self.root / ".gitignore").read_text(encoding="utf-8").splitlines())

    def test_second_run_is_noop(self):
        self.init()
        self.assertEqual(self.fixes(self.init()), [])

    def test_check_mode_writes_nothing(self):
        results = self.init(apply=False)
        self.assertTrue(self.fixes(results))
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), [".git"])

    def test_codex_only_machine_gets_no_claude_files(self):
        self.init(engines=["codex"])
        self.assertTrue((self.root / "AGENTS.md").exists())
        self.assertFalse((self.root / "CLAUDE.md").exists())
        self.assertFalse((self.root / ".claude").exists())


class ExistingFilesTest(ProjectCase):
    def test_project_content_is_preserved(self):
        (self.root / "AGENTS.md").write_text("# 项目说明\n\n别动这段。\n", encoding="utf-8")
        (self.root / "CLAUDE.md").write_text("# Claude 说明\n\n项目约定。\n", encoding="utf-8")
        (self.root / ".claude").mkdir()
        (self.root / ".claude" / "settings.local.json").write_text('{"permissions": {"allow": ["Bash(ls)"]}}')
        self.init()
        self.assertTrue((self.root / "AGENTS.md").read_text(encoding="utf-8").startswith("# 项目说明\n\n别动这段。\n"))
        claude = (self.root / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertTrue(claude.startswith("# Claude 说明\n\n项目约定。\n"))
        self.assertEqual(claude.count("@AGENTS.md"), 1)
        settings = json.loads((self.root / ".claude" / "settings.local.json").read_text(encoding="utf-8"))
        self.assertEqual(settings["permissions"], {"allow": ["Bash(ls)"]})

    def test_existing_agents_import_is_not_duplicated(self):
        (self.root / "CLAUDE.md").write_text("@AGENTS.md\n\n其他内容\n", encoding="utf-8")
        self.init()
        self.assertEqual((self.root / "CLAUDE.md").read_text(encoding="utf-8").count("@AGENTS.md"), 1)

    def test_invalid_settings_json_is_not_overwritten(self):
        (self.root / ".claude").mkdir()
        (self.root / ".claude" / "settings.local.json").write_text("{坏的 json")
        results = self.init()
        self.assertTrue([m for lvl, m in results if lvl == common.FAIL])
        self.assertEqual((self.root / ".claude" / "settings.local.json").read_text(), "{坏的 json")


class SyncTest(ProjectCase):
    """脚手架发新版后重跑：没改过的跟着更新，改过的跳过，撤掉的种子跟着撤。"""

    def edit_seed(self, name, old, new):
        p = self.seed / "memory" / name
        p.write_text(p.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")

    def test_untouched_memory_follows_upstream(self):
        self.init()
        name = self.seed_names()[0]
        self.edit_seed(name, "---\n\n", "---\n\n新版补充一句。\n")
        self.assertTrue(self.fixes(self.init()))
        self.assertIn("新版补充一句。", self.mem(name)[1])

    def test_project_edited_memory_is_skipped(self):
        self.init()
        name = self.seed_names()[0]
        p = self.root / ".memory" / name
        p.write_text(p.read_text(encoding="utf-8") + "\n项目自己的补充。\n", encoding="utf-8")
        self.edit_seed(name, "---\n\n", "---\n\n新版补充一句。\n")
        results = self.init()
        self.assertTrue(any(name in s for s in self.skips(results)))
        self.assertIn("项目自己的补充。", p.read_text(encoding="utf-8"))
        self.assertNotIn("新版补充一句。", p.read_text(encoding="utf-8"))

    def test_claude_rewriting_metadata_does_not_count_as_edit(self):
        self.init()
        name = self.seed_names()[0]
        p = self.root / ".memory" / name
        fields, body = common.split_frontmatter(p.read_text(encoding="utf-8"))
        fields["metadata"]["modified"] = "2030-01-01T00:00:00Z"
        p.write_text(common.render_frontmatter(fields, body), encoding="utf-8")
        self.edit_seed(name, "---\n\n", "---\n\n新版补充一句。\n")
        self.init()
        self.assertIn("新版补充一句。", p.read_text(encoding="utf-8"))

    def test_same_name_file_owned_by_project_is_skipped(self):
        name = self.seed_names()[0]
        (self.root / ".memory").mkdir()
        (self.root / ".memory" / name).write_text("---\nname: x\n---\n项目自己的\n", encoding="utf-8")
        self.init()
        self.assertEqual((self.root / ".memory" / name).read_text(encoding="utf-8"), "---\nname: x\n---\n项目自己的\n")

    def test_retired_seed_is_removed_with_its_index_line(self):
        self.init()
        name = self.seed_names()[0]
        (self.seed / "memory" / name).unlink()
        self.init()
        self.assertFalse((self.root / ".memory" / name).exists())
        self.assertNotIn(f"({name})", (self.root / ".memory" / "MEMORY.md").read_text(encoding="utf-8"))

    def test_redlines_follow_upstream_unless_edited(self):
        self.init()
        (self.seed / "redlines.md").write_text("# 新版红线\n", encoding="utf-8")
        self.init()
        self.assertIn("# 新版红线", (self.root / "AGENTS.md").read_text(encoding="utf-8"))

        agents = self.root / "AGENTS.md"
        agents.write_text(agents.read_text(encoding="utf-8").replace("# 新版红线", "# 项目定制红线"), encoding="utf-8")
        (self.seed / "redlines.md").write_text("# 再新一版\n", encoding="utf-8")
        results = self.init()
        self.assertTrue(any("红线" in s for s in self.skips(results)))
        self.assertIn("# 项目定制红线", agents.read_text(encoding="utf-8"))


class LegacyAndMigrationTest(ProjectCase):
    def test_old_injection_is_cleaned(self):
        legacy = Path(self._tmp.name) / "skills-scaffolding" / "scaffold" / "AGENTS.md"
        (self.root / "CLAUDE.local.md").symlink_to(legacy)
        (self.root / "AGENTS.md").symlink_to(legacy)
        (self.root / ".gitignore").write_text("node_modules/\nCLAUDE.local.md\nAGENTS.md\n", encoding="utf-8")
        (self.root / "CLAUDE.md").write_text(
            "# 项目\n\n约定。\n\n## Skill 脚手架\n@.claude/skills-guide.md\n@.claude/habits.md\n", encoding="utf-8")
        self.init()
        self.assertFalse((self.root / "CLAUDE.local.md").is_symlink())
        self.assertFalse((self.root / "AGENTS.md").is_symlink())
        self.assertTrue((self.root / "AGENTS.md").is_file())
        gitignore = (self.root / ".gitignore").read_text(encoding="utf-8")
        self.assertNotIn("\nAGENTS.md\n", "\n" + gitignore)  # AGENTS.md 现在要进 git
        self.assertIn("node_modules/", gitignore)
        claude = (self.root / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertNotIn("skills-guide", claude)
        self.assertIn("约定。", claude)

    def test_foreign_agents_symlink_is_left_alone(self):
        other = Path(self._tmp.name) / "elsewhere.md"
        other.write_text("别人的", encoding="utf-8")
        (self.root / "AGENTS.md").symlink_to(other)
        results = self.init()
        self.assertTrue((self.root / "AGENTS.md").is_symlink())
        self.assertTrue(any("AGENTS.md" in s for s in self.skips(results)))

    def test_codex_variant_of_old_injection_in_agents_md_is_cleaned(self):
        # 更早期有一版把 .claude 批量替换成了 .Codex，留下了这种从来没生效过的 AGENTS.md
        (self.root / "AGENTS.md").write_text("## Skill 脚手架\n@.Codex/skills-guide.md\n@.Codex/habits.md\n", encoding="utf-8")
        self.init()
        text = (self.root / "AGENTS.md").read_text(encoding="utf-8")
        self.assertNotIn("skills-guide", text)
        self.assertIsNotNone(common.read_block(text, ip.REDLINES_TAG))

    def test_agents_md_symlinked_to_claude_md_is_one_entry(self):
        # 常见写法：AGENTS.md -> CLAUDE.md，两个引擎读同一个文件。红线写进 CLAUDE.md 本体，不加自引用
        (self.root / "CLAUDE.md").write_text("# 项目约定\n\n原有内容。\n", encoding="utf-8")
        (self.root / "AGENTS.md").symlink_to("CLAUDE.md")
        results = self.init()
        self.assertEqual(os.readlink(self.root / "AGENTS.md"), "CLAUDE.md")
        text = (self.root / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("# 项目约定\n\n原有内容。\n"))
        self.assertIsNotNone(common.read_block(text, ip.REDLINES_TAG))
        self.assertNotIn("@AGENTS.md", text)
        self.assertFalse([m for lvl, m in results if lvl == common.FAIL])
        self.assertEqual(self.fixes(self.init()), [])

    def test_claude_md_symlinked_to_agents_md_is_one_entry(self):
        (self.root / "AGENTS.md").write_text("# 项目约定\n", encoding="utf-8")
        (self.root / "CLAUDE.md").symlink_to("AGENTS.md")
        self.init()
        self.assertTrue((self.root / "CLAUDE.md").is_symlink())
        text = (self.root / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIsNotNone(common.read_block(text, ip.REDLINES_TAG))
        self.assertNotIn("@AGENTS.md", text)

    def test_tracked_settings_local_json_gets_a_warning(self):
        (self.root / ".claude").mkdir()
        (self.root / ".claude" / "settings.local.json").write_text("{}\n", encoding="utf-8")
        subprocess.run(["git", "add", "-f", ".claude/settings.local.json"], cwd=self.root, check=True)
        results = self.init()
        self.assertTrue(any("git rm --cached" in s for s in self.skips(results)))

    def test_claude_auto_memory_is_moved_into_project(self):
        old = self.claude_home / "projects" / ip.claude_project_key(self.root) / "memory"
        old.mkdir(parents=True)
        (old / "MEMORY.md").write_text("- [朋友的数据](friend.md) — 追踪的是朋友不是用户\n", encoding="utf-8")
        (old / "friend.md").write_text("---\nname: friend\ndescription: d\nmetadata:\n  type: project\n---\n内容\n")
        self.init()
        self.assertEqual((self.root / ".memory" / "friend.md").read_text(), "---\nname: friend\ndescription: d\nmetadata:\n  type: project\n---\n内容\n")
        self.assertIn("(friend.md)", (self.root / ".memory" / "MEMORY.md").read_text(encoding="utf-8"))
        self.assertFalse(old.exists())


if __name__ == "__main__":
    unittest.main()
