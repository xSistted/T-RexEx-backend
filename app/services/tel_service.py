import re
phoneNumRegEx = re.compile(r'\d{3}-\d{3}-\d{4}')

def detect(string: str):
    output = {}
    matches = re.finditer(phoneNumRegEx, string)
    for match in matches:
        output[match.group()] = match.span()
    return output

def censor(string: str):
    founds = detect(string)
    temp = string
    for key in founds.keys():
        temp = temp.replace(key[:7], "XXX-XXX")
    return temp