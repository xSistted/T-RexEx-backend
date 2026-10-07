import re
phoneNumRegEx = re.compile(r'(?<![\d+-])(?:\+66-\d{2}-\d{3}-\d{4}|\d{3}-\d{3}-\d{4}|\d{3} \d{3} \d{4}|\d{10})(?![\d-])')

def detect(string: str):
    output = []
    matches = re.finditer(phoneNumRegEx, string)
    for match in matches:
        output.append({
            "position": (match.start(), match.end()),
            "keyword": match.group(0),
        })
    return output

def censor(string: str):
    def replace(match):
        key = match.group(0)
        prefix = key[:4] if key.startswith("+66-") else ""
        return prefix + re.sub(r'\d', 'X', key[len(prefix):-4]) + key[-4:]
    return phoneNumRegEx.sub(replace, string)

