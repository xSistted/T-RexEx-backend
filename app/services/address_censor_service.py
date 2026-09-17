import re
dobRegEx = re.compile(r'Address: \s*(\d+)')

def detect(string: str):
    output = {}
    matches = re.finditer(dobRegEx, string)
    for match in matches:
        output[match.group()] = match.span()
    return output

def censor(string: str):
    founds = detect(string)
    temp = string
    for key in founds.keys():
        num = key[9:]
        temp = temp.replace(key, "Address: " + "X" * len(num))
    return temp