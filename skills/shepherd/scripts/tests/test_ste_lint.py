import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import ste_lint


def rules(text):
    return [message.split(":")[0].split(" (")[0] for _, message in ste_lint.lint(text)]


class SteLintTests(unittest.TestCase):
    def test_authored_prose_follows_ste(self):
        findings = [f"{p.relative_to(ste_lint.REPO)}:{n}: {m}"
                    for p in ste_lint.authored_files() for n, m in ste_lint.lint(p.read_text())]
        self.assertEqual(findings, [])

    def test_each_rule_fires(self):
        text = (
            "Run the tests; read the log.\n\n"
            "Don't skip it.\n\n"
            "The agent has changed the file.\n\n"
            "The hook is running now.\n\n"
            "Utilize the cache.\n\n"
            + "word " * 26 + "end.\n\n"
            + "One. Two. Three. Four. Five. Six. Seven.\n"
        )
        self.assertEqual(rules(text), ["semicolon", "contraction", "perfect", "progressive",
                                       "plain word", "long sentence", "long paragraph"])

    def test_skips_code_tables_quotes_and_nouns(self):
        text = (
            "---\nname: x\ndescription: Use it when you write code.\n---\n\n"
            "# Don't; a heading\n\n"
            "```\nlet x = 1; // don't\n```\n\n"
            "| Cue | Skill |\n|---|---|\n| don't; is running | x |\n\n"
            "Run `a; b` and say \"don't\". The value is nothing.\n\n"
            "- One item. Two. Three. Four. Five. Six. Seven.\n"
        )
        self.assertEqual(ste_lint.lint(text), [])

    def test_checks_the_frontmatter_description(self):
        text = "---\nname: x\ndescription: Don't use it.\n---\n\nBody.\n"
        self.assertEqual(ste_lint.lint(text), [(3, 'contraction: "Don\'t"')])


if __name__ == "__main__":
    unittest.main()
