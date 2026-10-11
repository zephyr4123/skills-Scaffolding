"""common.py 单测：frontmatter 读写、内容指纹、受管区块、skill 的 engines 解析。"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import common  # noqa: E402

MEMORY = """---
name: deploy
description: 部署命令: make ship
metadata:
  node_type: memory
  type: project
  modified: 2026-10-11T03:14:55.852Z
---

部署到 stg 用 `make ship ENV=stg`。
"""


class FrontmatterTest(unittest.TestCase):
    def test_parses_top_level_and_metadata(self):
        fields, body = common.split_frontmatter(MEMORY)
        self.assertEqual(fields["name"], "deploy")
        self.assertEqual(fields["description"], "部署命令: make ship")  # 值里的冒号不能截断
        self.assertEqual(fields["metadata"]["type"], "project")
        self.assertEqual(body.strip(), "部署到 stg 用 `make ship ENV=stg`。")

    def test_roundtrip_is_lossless(self):
        fields, body = common.split_frontmatter(MEMORY)
        self.assertEqual(common.render_frontmatter(fields, body), MEMORY)

    def test_text_without_frontmatter(self):
        self.assertEqual(common.split_frontmatter("hello\n"), ({}, "hello\n"))


class FingerprintTest(unittest.TestCase):
    def test_tool_maintained_metadata_is_ignored(self):
        # Claude 改时间戳、我们写 scaffold_sha，都不算改了内容
        fields, body = common.split_frontmatter(MEMORY)
        before = common.fingerprint(fields, body)
        fields["metadata"]["modified"] = "2030-01-01T00:00:00Z"
        fields["metadata"]["scaffold_sha"] = "abc"
        self.assertEqual(common.fingerprint(fields, body), before)

    def test_body_description_and_type_count(self):
        fields, body = common.split_frontmatter(MEMORY)
        base = common.fingerprint(fields, body)
        self.assertNotEqual(common.fingerprint(fields, body + "补一句\n"), base)
        self.assertNotEqual(common.fingerprint({**fields, "description": "x"}, body), base)
        self.assertNotEqual(common.fingerprint({**fields, "metadata": {"type": "feedback"}}, body), base)


class BlockTest(unittest.TestCase):
    def test_upsert_appends_then_replaces_in_place(self):
        text = "# 项目说明\n\n原有内容\n"
        once = common.upsert_block(text, "demo", "第一版", sha="111")
        self.assertTrue(once.startswith(text.rstrip("\n")))
        twice = common.upsert_block(once + "\n区块后的用户内容\n", "demo", "第二版", sha="222")
        self.assertEqual(twice.count("<!-- demo "), 1)
        self.assertIn("第二版", twice)
        self.assertNotIn("第一版", twice)
        self.assertIn("区块后的用户内容", twice)

    def test_read_block_returns_inner_and_sha(self):
        text = common.upsert_block("", "demo", "内容\n第二行", sha="abc123")
        inner, sha = common.read_block(text, "demo")
        self.assertEqual(inner, "内容\n第二行")
        self.assertEqual(sha, "abc123")
        self.assertIsNone(common.read_block("无区块", "demo"))

    def test_remove_block_restores_original(self):
        original = "# 标题\n\n正文\n"
        self.assertEqual(common.remove_block(common.upsert_block(original, "demo", "x"), "demo"), original)


class SkillEnginesTest(unittest.TestCase):
    def test_reads_engines_list(self):
        with tempfile.TemporaryDirectory() as d:
            skill = Path(d)
            (skill / "SKILL.md").write_text("---\nname: a\nengines: [claude-code]\n---\nbody\n", encoding="utf-8")
            self.assertEqual(common.skill_engines(skill), {"claude-code"})

    def test_missing_field_means_both(self):
        with tempfile.TemporaryDirectory() as d:
            skill = Path(d)
            (skill / "SKILL.md").write_text("---\nname: a\n---\nbody\n", encoding="utf-8")
            self.assertEqual(common.skill_engines(skill), {"claude-code", "codex"})


if __name__ == "__main__":
    unittest.main()
