from __future__ import annotations

import asyncio
import json
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from secure_code_eval.datasets import normalize_cwe, slugify
from secure_code_eval.extract import extract_python_code
from secure_code_eval.pipeline import finding_model_alias
from secure_code_eval.rate_limit import AsyncStartRateLimiter
from secure_code_eval.sarif import Finding, parse_sarif


class CoreTests(unittest.TestCase):
    def test_normalize_cwe(self):
        self.assertEqual(normalize_cwe("CWE-020_author_1.py"), "CWE-20")
        self.assertEqual(normalize_cwe("external/cwe/cwe-079"), "CWE-79")
        self.assertEqual(normalize_cwe("CWE_502"), "CWE-502")

    def test_slugify(self):
        self.assertEqual(slugify("CWE-020_author_1.py"), "CWE-020_author_1")
        self.assertEqual(slugify("nested/path/CWE-079_codeql_1.py"), "CWE-079_codeql_1")

    def test_extract_python_fence(self):
        text = "Here is code:\n```python\nimport os\n\ndef f():\n    return os.getcwd()\n```"
        self.assertEqual(extract_python_code(text), "import os\n\ndef f():\n    return os.getcwd()")

    def test_extract_plain_text(self):
        text = "Sure.\n\nfrom pathlib import Path\n\ndef f():\n    return Path('.')"
        self.assertEqual(extract_python_code(text), "from pathlib import Path\n\ndef f():\n    return Path('.')")

    def test_parse_sarif_cwes(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "results.sarif"
            path.write_text(
                json.dumps(
                    {
                        "runs": [
                            {
                                "tool": {
                                    "driver": {
                                        "rules": [
                                            {
                                                "id": "py/path-injection",
                                                "properties": {"tags": ["external/cwe/cwe-022"]},
                                            }
                                        ]
                                    }
                                },
                                "results": [
                                    {
                                        "ruleId": "py/path-injection",
                                        "message": {"text": "Path injection"},
                                        "locations": [
                                            {
                                                "physicalLocation": {
                                                    "artifactLocation": {"uri": "CWE-022_author_1.py"},
                                                    "region": {"startLine": 10, "startColumn": 5},
                                                }
                                            }
                                        ],
                                    }
                                ],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            findings = parse_sarif(path)
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0].sample_slug, "CWE-022_author_1")
            self.assertEqual(findings[0].cwes, frozenset({"CWE-22"}))

    def test_finding_model_alias_for_combined_scan(self):
        finding = Finding(
            sample_slug="CWE-020_author_1",
            file="gemma/CWE-020_author_1.py",
            rule_id="x",
            message="",
            cwes=frozenset(),
        )
        self.assertEqual(finding_model_alias(finding), "gemma")

    def test_limiter_allows_parallel_but_spaces_starts(self):
        async def run():
            limiter = AsyncStartRateLimiter(rpm=600)
            starts = []

            async def task():
                await limiter.wait()
                starts.append(time.monotonic())
                await asyncio.sleep(0.02)

            await asyncio.gather(task(), task(), task())
            return starts

        starts = asyncio.run(run())
        self.assertEqual(len(starts), 3)
        self.assertGreaterEqual(starts[1] - starts[0], 0.09)
        self.assertGreaterEqual(starts[2] - starts[1], 0.09)


if __name__ == "__main__":
    unittest.main()
