"""Verify the assignment and API without modifying application code or result.csv.

Run from the repository root: python -X utf8 test/verify_assignment.py
Requires the existing development dependency httpx. Exits 1 on any failed check.
The finite generated domains are documented in docs/assignment-verification.md.
"""

import contextlib
import csv
import io
import itertools
import json
from pathlib import Path
import re
import sys
import time
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

with contextlib.redirect_stdout(io.StringIO()) as import_output:
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api.v1.routes.mask import RULE_MODULES
    from app.services import email, credit, tel_censor_service, dob_censor_service, address_censor_service

counts = Counter()
failures = []


def check(group, name, actual, expected, text=None):
    counts[group + ":total"] += 1
    if actual == expected:
        counts[group + ":passed"] += 1
    else:
        failures.append(dict(group=group, name=name, input=text, expected=expected, actual=actual))
        counts[group + ":failed"] += 1


def service_case(group, name, module, text, expected):
    try:
        actual = module.censor(text)
        check(group, name, actual, expected, text)
        found = module.detect(text)
        valid = all(0 <= d["position"][0] < d["position"][1] <= len(text)
                    and text[slice(*d["position"])] == d["keyword"] for d in found)
        check("service-invariants", name + ":spans", valid, True)
        check("service-invariants", name + ":idempotent", module.censor(actual), actual, text)
    except Exception as exc:
        check(group, name, type(exc).__name__ + ": " + str(exc), expected, text)


def response_invariants(name, text, data, include=True):
    summary = data["summary"]
    check("http-invariants", name + ":total", summary["total"], sum(summary["by_type"].values()))
    check("http-invariants", name + ":positive-counts", all(v > 0 for v in summary["by_type"].values()), True)
    check("http-invariants", name + ":time", data["processing_time_ms"] >= 0, True)
    if not include:
        check("http-invariants", name + ":matches-disabled", data["matches"], None)
        return
    matches = data["matches"]
    check("http-invariants", name + ":match-count", len(matches), summary["total"])
    check("http-invariants", name + ":sorted", [m["start"] for m in matches], sorted(m["start"] for m in matches))
    check("http-invariants", name + ":counts", dict(Counter(m["rule_id"] for m in matches)), summary["by_type"])
    valid = all(any(d["position"] == (m["start"], m["end"])
                    for d in RULE_MODULES[m["rule_id"]][0].detect(text)) for m in matches)
    check("http-invariants", name + ":original-spans", valid, True)
    check("http-invariants", name + ":no-raw-fields", all(set(m) == {"rule_id", "label", "start", "end", "masked_value"}
          and m["masked_value"] is None for m in matches), True)


started = time.perf_counter()
with TestClient(app) as client:
    for path in ["/", "/docs", "/redoc", "/openapi.json", "/api/v1/health", "/api/v1/rules"]:
        check("http-smoke", path, client.get(path).status_code, 200)
    check("http-smoke", "health", client.get("/api/v1/health").json()["status"], "ok")
    rules = client.get("/api/v1/rules").json()["rules"]
    check("metadata", "five unique rules", sorted(r["id"] for r in rules), sorted(RULE_MODULES))
    for rule in rules:
        module = RULE_MODULES[rule["id"]][0]
        check("metadata", rule["id"] + ":example", module.censor(rule["example_before"]), rule["example_after"])
        probes = [rule["example_before"], "DOB:25/12/2549", "Address: 689", "093-245-7894",
                  "a..bc@mail.com", "abc@-mail.com", "abc@mail.com", "abc@mail.com."]
        for text in probes:
            advertised = [(m.start(), m.end()) for m in re.finditer(rule["pattern"], text)]
            implemented = [d["position"] for d in module.detect(text)]
            check("metadata", rule["id"] + ":regex:" + text, implemented, advertised)

    with (ROOT / "test/data/pdpa_masking_test_cases.csv").open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            text = row["input"]
            response = client.post("/api/v1/mask", json={"text": text})
            group = "csv-" + row["status"] + "-" + row["category"]
            check("http-status", row["id"], response.status_code, 200)
            data = response.json()
            accepted = [row["expected_output"]]
            if row["alt_expected_output"]:
                accepted.append(row["alt_expected_output"])
            actual = data["masked_text"]
            check(group, row["id"] + ":" + row["description"], actual if actual not in accepted else accepted[0], accepted[0], text)
            response_invariants(row["id"], text, data)
            detected = client.post("/api/v1/detect", json={"text": text}).json()
            check("http-invariants", row["id"] + ":detect-summary", detected["summary"], data["summary"])
            check("http-invariants", row["id"] + ":detect-matches", detected["matches"], data["matches"])

    originals = {"email": "somchai.d@company.com", "credit_card": "1234-5678-9012-3456",
                 "phone": "093-245-7894", "dob": "DOB:25/12/2549", "address": "Address: 689 ถนนพระราม 9"}
    replacements = {"email": "s*******d@company.com", "credit_card": "XXXX-XXXX-XXXX-3456",
                    "phone": "XXX-XXX-7894", "dob": "DOB:XX/XX/25XX", "address": "Address: XXX ถนนพระราม 9"}
    text = " | ".join(originals.values())
    ids = list(originals)
    for size in range(6):
        for selected in itertools.combinations(ids, size):
            for include in [True, False]:
                for endpoint in ["mask", "detect"]:
                    data = client.post("/api/v1/" + endpoint, json={"text": text, "enabled_rules": list(selected), "include_matches": include}).json()
                    name = endpoint + ":" + repr(selected) + ":" + str(include)
                    check("rule-subsets", name + ":summary", data["summary"], {"total": len(selected), "by_type": {k: 1 for k in selected}})
                    if endpoint == "mask":
                        expected = " | ".join(replacements[k] if k in selected else v for k, v in originals.items())
                        check("rule-subsets", name + ":output", data["masked_text"], expected, text)
                    response_invariants(name, text, data, include)
    for endpoint in ["mask", "detect"]:
        for selection in [None, ids, ["unknown"], ["unknown", "phone"], ["phone", "phone"]]:
            data = client.post("/api/v1/" + endpoint, json={"text": "093-245-7894", "enabled_rules": selection}).json()
            expected = 0 if selection == ["unknown"] else 1
            check("rule-selection", endpoint + ":" + repr(selection), data["summary"]["total"], expected)
        for index, body in enumerate([{}, {"text": None}, {"text": 1}, {"text": True}, {"text": []}, {"text": {}},
                                     {"text": "a" * 50001}, {"text": "abc", "enabled_rules": "phone"},
                                     {"text": "abc", "enabled_rules": [None]}, {"text": "abc", "include_matches": None},
                                     {"text": "abc", "include_matches": "invalid"}]):
            check("http-validation", endpoint + ":invalid:" + str(index), client.post("/api/v1/" + endpoint, json=body).status_code, 422)
        check("http-validation", endpoint + ":invalid-json", client.post("/api/v1/" + endpoint, content="{", headers={"content-type": "application/json"}).status_code, 422)
        for length in [0, 1, 49999, 50000]:
            check("http-validation", endpoint + ":length:" + str(length), client.post("/api/v1/" + endpoint, json={"text": "a" * length}).status_code, 200)
    for order in itertools.permutations(ids):
        text = " | ".join(originals.values())
        data = client.post("/api/v1/mask", json={"text": text, "enabled_rules": list(order)}).json()
        check("rule-permutations", repr(order), data["masked_text"], " | ".join(replacements.values()))
    for name, unit in [("dense-phone", "093-245-7894 "), ("dense-address", "Address: 689\n"),
                       ("dense-email", "abc@mail.com "), ("dense-card", "1234-5678-9012-3456 "),
                       ("dense-dob", "DOB:25/12/2549 "), ("nonmatch-email", "a."),
                       ("nonmatch-address", "Address: "), ("nonmatch-dob", "DOB: ")]:
        n = 50000 // len(unit)
        text = unit * n + " " * (50000 - len(unit) * n)
        expected_unit = {"dense-phone": "XXX-XXX-7894 ", "dense-address": "Address: XXX\n",
                         "dense-email": "a*c@mail.com ", "dense-card": "XXXX-XXXX-XXXX-3456 ",
                         "dense-dob": "DOB:XX/XX/25XX "}.get(name, unit)
        before = time.perf_counter()
        response = client.post("/api/v1/mask", json={"text": text, "include_matches": False})
        check("maximum-payload", name + ":status", response.status_code, 200)
        check("maximum-payload", name + ":output", response.json()["masked_text"], expected_unit * n + " " * (50000 - len(unit) * n))
        # Record measurements only; the assignment specifies no timing threshold.
        counts["timing-ms:" + name] = round((time.perf_counter() - before) * 1000, 3)
    preflight = client.options("/api/v1/mask", headers={"origin": "http://localhost:3000", "access-control-request-method": "POST", "access-control-request-headers": "content-type"})
    check("http-smoke", "cors-preflight", preflight.status_code, 200)

    for order in itertools.permutations(["email", "phone", "credit_card"]):
        text = "093-245-7894@sms.bank.co.th"
        data = client.post("/api/v1/mask", json={"text": text, "enabled_rules": list(order)}).json()
        check("overlap-robustness", "email-phone:" + repr(order), data["masked_text"], "0**********4@sms.bank.co.th", text)
    for text, expected in [("Address: 093-245-7894", "Address: XXX-XXX-7894"),
                           ("DOB:25/12/2549@mail.com", "DOB:XX/XX/2**X@mail.com")]:
        data = client.post("/api/v1/mask", json={"text": text}).json()
        spans = data["matches"]
        overlap = any(a["end"] > b["start"] for a, b in zip(spans, spans[1:]))
        # Genuine source spans can overlap; preserve both detections and mask their union.
        check("overlap-coverage", "both-detections:" + text, overlap, True, text)
        check("overlap-coverage", "all-sensitive-characters:" + text, data["masked_text"], expected, text)
    for houses in itertools.permutations(["1", "12", "123/45"]):
        text = " | ".join("Address: " + house + " ถนนพระราม 9" for house in houses)
        expected = " | ".join("Address: " + re.sub(r"\d", "X", house) + " ถนนพระราม 9" for house in houses)
        service_case("address-prefix-collisions", repr(houses), address_censor_service, text, expected)
        data = client.post("/api/v1/mask", json={"text": text}).json()
        check("address-prefix-http", repr(houses), data["masked_text"], expected, text)
        check("address-prefix-http", repr(houses) + ":count", data["summary"]["by_type"], {"address": 3})

# Exhaust all group lengths 1..6; boundary cases cover each numeric neighbor.
for lengths in itertools.product(range(1, 7), repeat=3):
    text = "-".join("1" * n for n in lengths)
    expected = "XXX-XXX-1111" if lengths == (3, 3, 4) else text
    service_case("generated-phone-shape", repr(lengths), tel_censor_service, text, expected)
for lengths in itertools.product(range(1, 7), repeat=4):
    text = "-".join("1" * n for n in lengths)
    expected = "XXXX-XXXX-XXXX-1111" if lengths == (4, 4, 4, 4) else text
    service_case("generated-card-shape", repr(lengths), credit, text, expected)
for module, token, replacement in [(tel_censor_service, "093-245-7894", "XXX-XXX-7894"),
                                    (credit, "1234-5678-9012-3456", "XXXX-XXXX-XXXX-3456")]:
    for neighbor in "0123456789-":
        for left in [True, False]:
            text = neighbor + token if left else token + neighbor
            service_case("numeric-boundaries", module.__name__ + neighbor + str(left), module, text, text)
    for prefix, suffix in [("", ""), ("(", ")"), ("ไทย", "ครับ"), ("📞 ", "."), ("\n", "\t")]:
        service_case("valid-wrappers", module.__name__ + repr((prefix, suffix)), module, prefix + token + suffix, prefix + replacement + suffix)

for whitespace in ["", " ", "  ", "\t", "\n", "\r\n"]:
    for year in ["0000", "1999", "2006", "2499", "2549", "9999"]:
        text = "DOB:" + whitespace + "25/12/" + year
        service_case("dob-whitespace", repr(whitespace) + year, dob_censor_service, text, "DOB:" + whitespace + "XX/XX/" + year[:2] + "XX")
    for house in ["1", "689", "12345", "99/12"]:
        text = "Address:" + whitespace + house + " ถนนพระราม 9 เขตลาดกระบัง 10520"
        expected = "Address:" + whitespace + re.sub(r"\d", "X", house) + " ถนนพระราม 9 เขตลาดกระบัง 10520"
        service_case("address-whitespace", repr(whitespace) + house, address_censor_service, text, expected)
for day, month, year in itertools.product(range(1, 4), range(1, 4), range(1, 7)):
    text = "DOB:" + "1" * day + "/" + "1" * month + "/" + "2" * year
    expected = "DOB:XX/XX/22XX" if (day, month, year) == (2, 2, 4) else text
    service_case("generated-dob-shape", repr((day, month, year)), dob_censor_service, text, expected)
# Exhaust each independent fixed-width date component, without calendar validation.
for year in range(10000):
    text = f"DOB:25/12/{year:04d}"
    service_case("all-four-digit-years", str(year), dob_censor_service, text, f"DOB:XX/XX/{year // 100:02d}XX")
for day, month in itertools.product(range(100), repeat=2):
    text = f"DOB:{day:02d}/{month:02d}/2549"
    service_case("all-two-digit-day-month-pairs", f"{day}/{month}", dob_censor_service, text, "DOB:XX/XX/25XX")
for local in ["a", "ab", "abc", "somchai.d", "a+b", "a_b", "a-b", "12345", "a.b.c"]:
    for domain in ["company.com", "mail.co.th", "Company.COM", "x-bank.co.th"]:
        for prefix, suffix in [("", ""), ("<", ">"), ("ไทย", "ครับ"), ("", "."), ("", ","), ("", ";")]:
            masked = local if len(local) <= 2 else local[0] + "*" * (len(local) - 2) + local[-1]
            text = prefix + local + "@" + domain + suffix
            service_case("email-wrappers", text, email, text, prefix + masked + "@" + domain + suffix)
for text in [".abc@mail.com", "abc.@mail.com", "a..bc@mail.com", "abc@-mail.com", "abc@mail-.com",
             "abc@@mail.com", "abc@mail..com", "abc@mail.com-", "abc@mail.c", "abc@mail.com_", "@abc@mail.com"]:
    service_case("email-malformed-robustness", text, email, text, text)
for module in [email, credit]:
    for text in [None, 123, [], {}]:
        for method in [module.detect, module.censor]:
            try:
                method(text)
                actual = "no error"
            except Exception as exc:
                actual = type(exc).__name__
            check("service-validation", module.__name__ + method.__name__ + repr(text), actual, "TypeError")
    for detections in [[{"position": (-1, 2), "keyword": "ab"}], [{"position": (0, 999), "keyword": "ab"}],
                       [{"position": (2, 1), "keyword": "ab"}], [{"position": (0, 2), "keyword": "zz"}]]:
        try:
            module.censor("abc@mail.com", detections)
            actual = "no error"
        except Exception as exc:
            actual = type(exc).__name__
        check("service-validation", module.__name__ + repr(detections), actual, "ValueError")

check("import-side-effects", "services print on import", bool(import_output.getvalue()), False)
report = {"elapsed_seconds": round(time.perf_counter() - started, 3), "counts": dict(sorted(counts.items())),
          "total": sum(v for k, v in counts.items() if k.endswith(":total")),
          "passed": sum(v for k, v in counts.items() if k.endswith(":passed")),
          "failed": len(failures), "failures": failures}
output = ROOT / "test/data/assignment_verification.json"
output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({k: v for k, v in report.items() if k != "failures"}, indent=2))
print("Detailed failures:", output)
sys.exit(bool(failures))
