import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR / "scripts"))

import deep_paper  # noqa: E402


class GitHubRepositoryExtractionTests(unittest.TestCase):
    def test_extracts_normalizes_and_deduplicates_repository_urls(self):
        text = """
        Code: https://github.com/ruc-datalab/EvoOntology.
        README: https://github.com/ruc-datalab/EvoOntology/blob/main/README.md
        Clone: https://github.com/ruc-datalab/EvoOntology.git
        Issue: https://github.com/ruc-datalab/EvoOntology/issues/12
        Full-width punctuation: https://github.com/ruc-datalab/EvoOntology；
        Not a repository: https://github.com/topics/agents
        """

        self.assertEqual(
            deep_paper.extract_github_repository_urls(text),
            ["https://github.com/ruc-datalab/EvoOntology"],
        )

    def test_returns_empty_list_when_no_repository_is_present(self):
        self.assertEqual(
            deep_paper.extract_github_repository_urls("No source repository is linked."),
            [],
        )


class RepositoryManifestTests(unittest.TestCase):
    def test_builds_manifest_without_executing_repository_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "ExampleRepo"
            (repo / "src").mkdir(parents=True)
            (repo / "README.md").write_text("# Example\n", encoding="utf-8")
            (repo / "pyproject.toml").write_text("[project]\nname='example'\n", encoding="utf-8")
            (repo / "src" / "main.py").write_text("print('hello')\n", encoding="utf-8")
            subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
            subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-m", "initial"], check=True, capture_output=True)

            manifest = deep_paper.build_repository_manifest(
                "https://github.com/example/ExampleRepo", repo
            )

            self.assertEqual(manifest["status"], "cloned")
            self.assertEqual(manifest["default_branch"], "main")
            self.assertEqual(len(manifest["commit"]), 40)
            self.assertIn("README.md", manifest["readme_files"])
            self.assertIn("pyproject.toml", manifest["key_files"])
            self.assertIn("src/main.py", manifest["key_files"])
            self.assertEqual(manifest["languages"]["Python"], 1)
            self.assertTrue(Path(manifest["tree_path"]).exists())
            self.assertTrue(Path(manifest["manifest_path"]).exists())

            saved = json.loads(Path(manifest["manifest_path"]).read_text(encoding="utf-8"))
            self.assertEqual(saved["url"], "https://github.com/example/ExampleRepo")

    @mock.patch("deep_paper.subprocess.run")
    def test_clone_failure_is_recorded_without_aborting(self, run):
        run.return_value = subprocess.CompletedProcess(
            args=["git", "clone"], returncode=128, stdout="", stderr="network unavailable"
        )
        with tempfile.TemporaryDirectory() as tmp:
            repositories = deep_paper.prepare_code_repositories(
                "Source: https://github.com/example/missing",
                Path(tmp),
            )

        self.assertEqual(len(repositories), 1)
        self.assertEqual(repositories[0]["status"], "error")
        self.assertIn("network unavailable", repositories[0]["error"])
        clone_command = run.call_args.args[0]
        self.assertEqual(clone_command[:4], ["git", "clone", "--depth", "1"])
        self.assertIn("--filter=blob:none", clone_command)
        self.assertEqual(run.call_args.kwargs["env"]["GIT_TERMINAL_PROMPT"], "0")
        self.assertEqual(run.call_args.kwargs["env"]["GIT_LFS_SKIP_SMUDGE"], "1")


class PromptLayoutTests(unittest.TestCase):
    def test_code_section_is_conditional_and_precedes_personal_thoughts(self):
        prompt = (SKILL_DIR / "prompts" / "analyze_paper.md").read_text(encoding="utf-8")

        self.assertIn('"关联代码解读"是条件章节', prompt)
        self.assertLess(prompt.index("## 关联代码解读"), prompt.index("## 我的思考"))


if __name__ == "__main__":
    unittest.main()
