import re
dobRegEx = re.compile(r'(DOB:\s*)\d{2}/\d{2}/(\d{2})\d{2}(?!\d)')

def detect(string: str):
    output = []
    matches = re.finditer(dobRegEx, string)
    for match in matches:
        output.append({
                    "position": (match.start(), match.end()),
                    "keyword": match.group(0),
                })
    return output

def censor(string: str):
    return dobRegEx.sub(lambda match: match.group(1) + "XX/XX/" + match.group(2) + "XX", string)

