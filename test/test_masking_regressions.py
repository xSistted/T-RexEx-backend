"""Run with: python -X utf8 -m unittest discover -s test -p test_masking_regressions.py"""

import contextlib
import csv
import io
import itertools
from pathlib import Path
import re
import unittest

with contextlib.redirect_stdout(io.StringIO()):
    from app.api.v1.routes.mask import mask, RULE_MODULES
    from app.schemas.mask import MaskRequest
    from app.services.rule_service import get_rules

ROOT = Path(__file__).resolve().parents[1]


class MaskingRegressions(unittest.TestCase):
    def test_existing_csv(self):
        with (ROOT / "test/data/pdpa_masking_test_cases.csv").open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                with self.subTest(case=row["id"]):
                    accepted = [row["expected_output"]]
                    if row["alt_expected_output"]:
                        accepted.append(row["alt_expected_output"])
                    self.assertIn(mask(MaskRequest(text=row["input"])).masked_text, accepted)

    def test_prefix_collisions_and_whitespace(self):
        for houses in itertools.permutations(["1", "12", "123/45"]):
            text = " | ".join("Address: " + house + " Road 9" for house in houses)
            expected = " | ".join("Address: " + re.sub(r"\d", "X", house) + " Road 9" for house in houses)
            with self.subTest(houses=houses):
                response = mask(MaskRequest(text=text))
                self.assertEqual(response.masked_text, expected)
                self.assertEqual(response.summary.by_type, {"address": 3})
        for whitespace in ["", " ", "  ", "\t", "\n", "\r\n"]:
            with self.subTest(whitespace=repr(whitespace)):
                text = f"DOB:{whitespace}25/12/2549 | Address:{whitespace}123/45 Road 9"
                expected = f"DOB:{whitespace}XX/XX/25XX | Address:{whitespace}XXX/XX Road 9"
                self.assertEqual(mask(MaskRequest(text=text)).masked_text, expected)

    def test_email_domain_boundaries(self):
        for suffix in [".", ",", ";", ")", ". Next sentence"]:
            with self.subTest(suffix=suffix):
                self.assertEqual(mask(MaskRequest(text="abc@mail.co.th" + suffix)).masked_text, "a*c@mail.co.th" + suffix)
        for text in ["abc@mail.com-", "abc@mail.com_", "abc@mail.com.123", "abc@mail..com", "abc@-mail.com"]:
            with self.subTest(invalid=text):
                self.assertEqual(mask(MaskRequest(text=text)).masked_text, text)

    def test_advertised_patterns_and_examples(self):
        for rule in get_rules().rules:
            module = RULE_MODULES[rule.id][0]
            self.assertEqual(module.censor(rule.example_before), rule.example_after)
            for text in [rule.example_before, "Address:689", "Address:\t123/45", "DOB: 25/12/25490",
                         "1093-245-7894", "abc@mail.com.", "a..bc@mail.com", "abc@-mail.com"]:
                with self.subTest(rule=rule.id, text=text):
                    self.assertEqual([d["position"] for d in module.detect(text)],
                                     [(m.start(), m.end()) for m in re.finditer(rule.pattern, text)])


if __name__ == "__main__":
    unittest.main()
