from bisect import bisect_right

from app.services import email, credit, tel_censor_service, dob_censor_service, address_censor_service
from app.services.types import Detection

RULE_MODULES = {
    "email": (email, "อีเมล"),
    "credit_card": (credit, "เลขบัตรเครดิต"),
    "phone": (tel_censor_service, "เบอร์โทรศัพท์"),
    "dob": (dob_censor_service, "วันเกิด"),
    "address": (address_censor_service, "ที่อยู่"),
}


def detect(text: str, enabled_rules: list[str] | None = None) -> list[tuple[str, str, Detection]]:
    enabled = set(RULE_MODULES if enabled_rules is None else enabled_rules)
    found = [
        (rule_id, label, detection)
        for rule_id, (module, label) in RULE_MODULES.items() if rule_id in enabled
        for detection in module.detect(text)
    ]
    email_spans = [d["position"] for rule_id, _, d in found if rule_id == "email"]
    email_starts = [start for start, _ in email_spans]
    selected = []
    for rule_id, label, detection in found:
        start, end = detection["position"]
        index = bisect_right(email_starts, start) - 1
        if rule_id == "phone" and index >= 0 and end <= email_spans[index][1]:
            continue
        selected.append((rule_id, label, detection))
    return sorted(selected, key=lambda item: item[2]["position"][0])


def censor(text: str, detections: list[tuple[str, str, Detection]]) -> str:
    output = list(text)
    for rule_id, _, detection in detections:
        keyword = detection["keyword"]
        replacement = RULE_MODULES[rule_id][0].censor(keyword)

        if len(replacement) != len(keyword):
            raise ValueError("Mask replacements must preserve length")
        start, _ = detection["position"]
        for offset, (original, masked) in enumerate(zip(keyword, replacement)):
            if original != masked:
                index = start + offset

                output[index] = "*" if masked == "*" or output[index] == "*" else masked
    return "".join(output)
