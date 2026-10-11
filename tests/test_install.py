"""install.py 单测：全部跑在临时家目录上，验证可重复执行、保留用户已有配置、能撤销。"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import common  # noqa: E402
import install  # noqa: E402

USER_HOOKS = {
    "hooks": {
        "PostToolUse": [{"matcher": "", "hooks": [{"type": "command", "command": "python3 /x/collect.py"}]}],
        "SessionStart": [{"matcher": "startup", "hooks": [{"type": "command", "command": "bash /x/update.sh"}]}],
    }
}
USER_TOML = """model = "gpt-6-astra"
model_reasoning_effort = "low"
model_context_window = 272000

[features]
js_repl = false
memories = true

[mcp_servers.node_repl]
command = "node"
"""
LEGACY_RULES = "<!-- codex-memory:begin 旧的研究版 -->\n## 项目记忆\n旧规则\n<!-- codex-memory:end -->\n"


def changed(results):
    return [msg for level, msg in results if level == install.FIX]


class MachineCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.m = install.Machine(home=Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()


class LinkSkillsTest(MachineCase):
    def expected(self, engine):
        return {n for n, d in common.repo_skills().items() if engine in common.skill_engines(d)}

    def test_links_only_skills_for_that_engine(self):
        install.link_skills(self.m, "codex", apply=True)
        linked = {p.name for p in self.m.skill_root("codex").iterdir() if p.is_symlink()}
        self.assertEqual(linked, self.expected("codex"))
        self.assertLess(len(linked), len(common.repo_skills()))  # 确有 Claude 专属 skill 被过滤

    def test_check_mode_changes_nothing(self):
        results = install.link_skills(self.m, "claude-code", apply=False)
        self.assertTrue(changed(results))
        self.assertFalse(self.m.skill_root("claude-code").exists())

    def test_real_dir_and_foreign_links_are_left_alone(self):
        root = self.m.skill_root("claude-code")
        name = sorted(self.expected("claude-code"))[0]
        (root / name).mkdir(parents=True)
        (root / "someone-else").symlink_to(self.m.home)
        install.link_skills(self.m, "claude-code", apply=True)
        self.assertFalse((root / name).is_symlink())
        self.assertEqual(os.readlink(root / "someone-else"), str(self.m.home))

    def test_links_to_removed_skills_are_cleaned(self):
        root = self.m.skill_root("claude-code")
        root.mkdir(parents=True)
        (root / "zephyr-coding-standards").symlink_to(common.SKILLS_DIR / "general" / "zephyr-coding-standards")
        install.link_skills(self.m, "claude-code", apply=True)
        self.assertFalse((root / "zephyr-coding-standards").is_symlink())

    def test_second_run_is_noop(self):
        install.link_skills(self.m, "claude-code", apply=True)
        self.assertEqual(changed(install.link_skills(self.m, "claude-code", apply=True)), [])


class CodexConfigTest(MachineCase):
    def config(self):
        return (self.m.codex_home / "config.toml").read_text(encoding="utf-8")

    def test_sets_context_window_and_disables_memories_keeping_the_rest(self):
        self.m.codex_home.mkdir()
        (self.m.codex_home / "config.toml").write_text(USER_TOML, encoding="utf-8")
        install.codex_config(self.m, apply=True)
        text = self.config()
        self.assertIn("model_context_window = 1000000\n", text)
        self.assertNotIn("272000", text)
        self.assertIn("memories = false\n", text)
        self.assertIn("js_repl = false", text)
        self.assertIn('[mcp_servers.node_repl]\ncommand = "node"', text)
        # 顶层键必须仍在第一个表头之前，否则 TOML 会把它归进 [features]
        self.assertLess(text.index("model_context_window"), text.index("[features]"))

    def test_missing_keys_and_tables_are_added(self):
        self.m.codex_home.mkdir()
        (self.m.codex_home / "config.toml").write_text('model = "x"\n\n[tui]\ntheme = "dark"\n', encoding="utf-8")
        install.codex_config(self.m, apply=True)
        text = self.config()
        self.assertLess(text.index("model_context_window = 1000000"), text.index("[tui]"))
        self.assertIn("[features]\nmemories = false\n", text)

    def test_second_run_is_noop(self):
        install.codex_config(self.m, apply=True)
        self.assertEqual(changed(install.codex_config(self.m, apply=True)), [])


class CodexMemoryTest(MachineCase):
    def seed_user_files(self):
        self.m.codex_home.mkdir()
        (self.m.codex_home / "hooks.json").write_text(json.dumps(USER_HOOKS, indent=2), encoding="utf-8")
        (self.m.codex_home / "AGENTS.md").write_text("# 全局备忘\n\n回复用中文。\n\n" + LEGACY_RULES, encoding="utf-8")

    def hooks(self):
        return json.loads((self.m.codex_home / "hooks.json").read_text(encoding="utf-8"))["hooks"]

    def agents(self):
        return (self.m.codex_home / "AGENTS.md").read_text(encoding="utf-8")

    def test_installs_hook_script_entry_and_rules(self):
        self.seed_user_files()
        install.codex_memory(self.m, apply=True)
        script = self.m.codex_home / "hooks" / install.HOOK_FILENAME
        self.assertTrue(script.is_file())
        hooks = self.hooks()
        self.assertEqual(hooks["PostToolUse"], USER_HOOKS["hooks"]["PostToolUse"])
        # 用户原有组保持第 0 位：Codex 的 hook 信任记录按位置索引
        self.assertEqual(hooks["SessionStart"][0], USER_HOOKS["hooks"]["SessionStart"][0])
        ours = [h for g in hooks["SessionStart"] for h in g["hooks"] if install.HOOK_FILENAME in h["command"]]
        self.assertEqual(len(ours), 1)
        self.assertIn(str(script), ours[0]["command"])
        text = self.agents()
        self.assertTrue(text.startswith("# 全局备忘\n\n回复用中文。\n"))
        self.assertIn("## 项目记忆（Codex 读写规则）", text)
        self.assertNotIn("codex-memory:begin", text)  # 研究版遗留区块被清掉

    def test_second_run_is_noop(self):
        self.seed_user_files()
        install.codex_memory(self.m, apply=True)
        self.assertEqual(changed(install.codex_memory(self.m, apply=True)), [])

    def test_uninstall_restores_user_files(self):
        self.seed_user_files()
        install.codex_memory(self.m, apply=True)
        install.uninstall_codex_memory(self.m)
        self.assertEqual(self.hooks(), USER_HOOKS["hooks"])
        self.assertEqual(self.agents(), "# 全局备忘\n\n回复用中文。\n")
        self.assertFalse((self.m.codex_home / "hooks" / install.HOOK_FILENAME).exists())


class PluginStatusTest(unittest.TestCase):
    CLAUDE_LIST = (
        "Installed plugins:\n\n  ❯ swiftui-pro@swiftui-agent-skill\n    Version: 1.0.0\n    Status: ✔ enabled\n"
    )
    CODEX_LIST = (
        "PLUGIN                           STATUS              VERSION  SOURCE\n"
        "swiftui-pro@swiftui-agent-skill  installed, enabled  2.0.0    /x\n"
        "superpowers@claude-plugins-official  not installed           /y\n"
    )

    def test_claude_installed(self):
        self.assertTrue(install.plugin_installed("claude-code", self.CLAUDE_LIST, "swiftui-pro@swiftui-agent-skill"))
        self.assertFalse(install.plugin_installed("claude-code", self.CLAUDE_LIST, "swiftui@swiftui-agent-skill"))

    def test_codex_not_installed_row_is_not_a_match(self):
        self.assertTrue(install.plugin_installed("codex", self.CODEX_LIST, "swiftui-pro@swiftui-agent-skill"))
        self.assertFalse(install.plugin_installed("codex", self.CODEX_LIST, "superpowers@claude-plugins-official"))


if __name__ == "__main__":
    unittest.main()
