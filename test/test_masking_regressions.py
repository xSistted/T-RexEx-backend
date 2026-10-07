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
    from app.api.v1.routes.detect import detect
    from app.schemas.detect import DetectRequest

ROOT = Path(__file__).resolve().parents[1]


class MaskingRegressions(unittest.TestCase):
    def test_additional_numeric_formats(self):
        cases = {
            "1234567890123456": ("XXXXXXXXXXXX3456", "credit_card"),
            "1234 5678 9012 3456": ("XXXX XXXX XXXX 3456", "credit_card"),
            "0932457894": ("XXXXXX7894", "phone"),
            "093 245 7894": ("XXX XXX 7894", "phone"),
            "+66-93-245-7894": ("+66-XX-XXX-7894", "phone"),
        }
        for text, (expected, rule_id) in cases.items():
            with self.subTest(text=text):
                response = mask(MaskRequest(text=text))
                self.assertEqual(response.masked_text, expected)
                self.assertEqual(response.summary.by_type, {rule_id: 1})
                self.assertEqual(detect(DetectRequest(text=text)).summary.by_type, {rule_id: 1})
                self.assertEqual(mask(MaskRequest(text=expected)).masked_text, expected)
                for neighbor in "0123456789-":
                    for invalid in [neighbor + text, text + neighbor]:
                        self.assertEqual(mask(MaskRequest(text=invalid)).masked_text, invalid)
        text = " | ".join(cases)
        self.assertEqual(mask(MaskRequest(text=text)).masked_text, " | ".join(v[0] for v in cases.values()))
        for rule in get_rules().rules:
            for text in cases:
                self.assertEqual([d["position"] for d in RULE_MODULES[rule.id][0].detect(text)],
                                 [(m.start(), m.end()) for m in re.finditer(rule.pattern, text)])

    def test_overlapping_masks_are_order_independent(self):
        cases = {
            "DOB:25/12/2549@mail.com": "DOB:XX/XX/2**X@mail.com",
            "093-245-7894@sms.bank.co.th": "0**********4@sms.bank.co.th",
            "Address: 093-245-7894": "Address: XXX-XXX-7894",
        }
        for text, expected in cases.items():
            for order in itertools.permutations(RULE_MODULES):
                with self.subTest(text=text, order=order):
                    response = mask(MaskRequest(text=text, enabled_rules=list(order)))
                    detected = detect(DetectRequest(text=text, enabled_rules=list(order)))
                    self.assertEqual(response.masked_text, expected)
                    self.assertEqual(response.summary.model_dump(), detected.summary.model_dump())
                    self.assertEqual([m.model_dump() for m in response.matches], [m.model_dump() for m in detected.matches])
                    self.assertEqual(mask(MaskRequest(text=expected)).masked_text, expected)

    def test_email_takes_priority_over_contained_phone(self):
        text = "093-245-7894@sms.bank.co.th | 093-245-7894"
        expected = "0**********4@sms.bank.co.th | XXX-XXX-7894"
        response = mask(MaskRequest(text=text))
        self.assertEqual(response.masked_text, expected)
        self.assertEqual(response.summary.by_type, {"email": 1, "phone": 1})
        self.assertEqual(detect(DetectRequest(text=text)).summary.by_type, {"email": 1, "phone": 1})
        self.assertEqual(mask(MaskRequest(text=text, enabled_rules=["phone"])).masked_text,
                         "XXX-XXX-7894@sms.bank.co.th | XXX-XXX-7894")

    def test_rule_selection_and_malformed_email(self):
        text = "093-245-7894"
        response = mask(MaskRequest(text=text, enabled_rules=[]))
        self.assertEqual(response.masked_text, text)
        self.assertEqual(response.summary.total, 0)
        self.assertEqual(detect(DetectRequest(text=text, enabled_rules=[])).summary.total, 0)
        for selected in [["phone", "phone"], ["unknown", "phone"], None]:
            with self.subTest(selected=selected):
                self.assertEqual(mask(MaskRequest(text=text, enabled_rules=selected)).summary.total, 1)
                self.assertEqual(detect(DetectRequest(text=text, enabled_rules=selected)).summary.total, 1)
        self.assertEqual(mask(MaskRequest(text="@abc@mail.com")).masked_text, "@abc@mail.com")

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
