import re
dobRegEx = re.compile(r'DOB:\s*(\d{2}/\d{2}/\d{4})')

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
        temp = temp.replace(key[4:6], "XX")
        temp = temp.replace(key[7:9], "XX")
        temp = temp.replace(key[12:14], "XX")
    return temp