import re
phoneNumRegEx = re.compile(r'(?<![\d+-])(?:\+66-\d{2}-\d{3}-\d{4}|\d{3}-\d{3}-\d{4}|\d{10})(?![\d-])')

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

test = """My name is Somchai. You can contact me at 093-245-7894 or 081-555-1234.
My DOB:25/12/2549 and my brother's DOB:10/03/2547.

I currently live at Address: 99/12 Sukhumvit Road, Khlong Toei, Bangkok 10110.
My old address was Address: 45/7 Ratchadaphisek Road, Din Daeng, Bangkok 10400.

For emergencies, please call 062-987-6543.
My mother's DOB:05/08/2525 and her address is Address: 123/45 Rama 9 Road, Huai Khwang, Bangkok 10310.

Another contact is 090-111-2222. His DOB:01/01/2540.
His address is Address: 78/9 Phahonyothin Road, Chatuchak, Bangkok 10900."""

if __name__ == "__main__":
    print(censor(test))
