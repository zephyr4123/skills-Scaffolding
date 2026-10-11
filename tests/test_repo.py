"""仓库完整性门禁：CI 上跑，机器能查的规矩不留给人查。"""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import common  # noqa: E402

MEMORY_TYPES = {"user", "feedback", "project", "reference"}
# 重构时删掉的东西：任何地方再提到它们，就是过期文档
RETIRED = [
    "zephyr-coding-standards", "zephyr-quality-discipline", "superpowers",
    "scaffold/", "GUIDE.md", "HABITS.md", "build-agents-md", "build-codex-manifest",
    "preflight.sh", "install.sh", ".codex-plugin",
]


class SkillsTest(unittest.TestCase):
    def test_every_skill_declares_valid_engines(self):
        for name, skill in common.repo_skills().items():
            text = (skill / "SKILL.md").read_text(encoding="utf-8")
            self.assertRegex(text, r"(?m)^engines:\s*\[.+\]\s*$", f"{name} 缺 engines 字段")
            self.assertLessEqual(common.skill_engines(skill), set(common.ENGINES), f"{name} 的 engines 有未知取值")


class SeedTest(unittest.TestCase):
    seed_mem = common.SEED_DIR / "memory"

    def test_seed_memories_have_claude_format(self):
        files = [p for p in self.seed_mem.glob("*.md") if p.name != "MEMORY.md"]
        self.assertTrue(files)
        for p in files:
            fields, body = common.split_frontmatter(p.read_text(encoding="utf-8"))
            self.assertEqual(fields.get("name"), p.stem, p.name)
            self.assertTrue(fields.get("description"), p.name)
            self.assertIn(fields.get("metadata", {}).get("type"), MEMORY_TYPES, p.name)
            self.assertTrue(body.strip(), p.name)

    def test_index_and_files_match_one_to_one(self):
        index = (self.seed_mem / "MEMORY.md").read_text(encoding="utf-8")
        linked = set(re.findall(r"\(([^)]+\.md)\)", index))
        files = {p.name for p in self.seed_mem.glob("*.md") if p.name != "MEMORY.md"}
        self.assertEqual(linked, files)

    def test_redlines_fit_the_entry_file_budget(self):
        # Claude 官方建议入口文件 200 行以内，太长遵守度下降
        lines = (common.SEED_DIR / "redlines.md").read_text(encoding="utf-8").splitlines()
        self.assertLessEqual(len(lines), 200)


class NoStaleReferencesTest(unittest.TestCase):
    def test_retired_names_are_gone(self):
        hits = []
        for p in common.REPO.rglob("*"):
            rel = p.relative_to(common.REPO)
            if not p.is_file() or rel.parts[0] in (".git", "tests") or p.suffix in (".pyc", ".png", ".svg"):
                continue
            text = p.read_text(encoding="utf-8", errors="ignore")
            hits += [f"{rel}: {word}" for word in RETIRED if word in text]
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
