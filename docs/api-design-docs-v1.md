# API Contract — Data Masking for PDPA

This is the original design proposal. See `api-reference.md` for the implemented
contract, including original-text masking, overlap handling, and rule selection.

**Stack:** Python + FastAPI 

**Base URL:** `https://<domain>/api/v1` 

**Content-Type:** `application/json; charset=utf-8` 

**Naming:** `snake_case` ทุก field

**Stateless:** ไม่เก็บข้อมูลดิบของผู้ใช้ ไม่มี DB ไม่มี auth

**Interactive docs:** `<base>/docs` 

---

## Rule IDs

ใช้ค่าเหล่านี้ทุกที่ในระบบ

| id | ความหมาย | ตัวอย่าง input | ตัวอย่าง output |
|---|---|---|---|
| `credit_card` | เลขบัตรเครดิต | `1234-5678-9012-3456` | `XXXX-XXXX-XXXX-3456` |
| `email` | อีเมล | `somchai.d@company.com` | `s*******d@company.com` |
| `phone` | เบอร์โทรศัพท์ | `093-245-7894` | `XXX-XXX-7894` |
| `dob` | วันเดือนปีเกิด | `DOB:25/12/2549` | `DOB:XX/XX/25XX` |
| `address` | ที่อยู่ (เฉพาะเลขที่บ้าน) | `Address: 689 ซอย...` | `Address: XXX ซอย...` |

---

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | ตรวจสอบว่า service ทำงานอยู่ |
| `GET` | `/rules` | metadata ของกฎทั้ง 5 (label, regex, ตัวอย่าง) |
| `POST` | `/mask` | **หลัก** — เซ็นเซอร์ข้อความ |
| `POST` | `/detect` | หา PII โดยไม่เซ็นเซอร์ (optional) |
| `GET` | `/samples` | ตัวอย่าง log สำเร็จรูป (optional) |

---

## `POST /mask`

### Request

```json
{
  "text": "user=somchai.d@company.com card=1234-5678-9012-3456 tel=093-245-7894",
  "enabled_rules": ["credit_card", "email", "phone", "dob", "address"],
  "include_matches": true
}
```

| field | type | required | default | หมายเหตุ |
|---|---|---|---|---|
| `text` | string | required | — | ข้อความที่ผู้ใช้พิมพ์ (จำกัด 50,000 ตัวอักษร) |
| `enabled_rules` | string[] | not required | ทั้ง 5 กฎ | ผูกกับ checkbox บนหน้าเว็บ |
| `include_matches` | boolean | not required | `true` | `false` = ไม่ส่ง `matches` กลับ |

### Response `200`

```json
{
  "masked_text": "user=s*******d@company.com card=XXXX-XXXX-XXXX-3456 tel=XXX-XXX-7894",
  "summary": {
    "total": 3,
    "by_type": { "email": 1, "credit_card": 1, "phone": 1 }
  },
  "matches": [
    { "rule_id": "email",       "label": "อีเมล",        "start": 5,  "end": 26, "masked_value": "s*******d@company.com" },
    { "rule_id": "credit_card", "label": "เลขบัตรเครดิต", "start": 32, "end": 51, "masked_value": "XXXX-XXXX-XXXX-3456" },
    { "rule_id": "phone",       "label": "เบอร์โทรศัพท์",  "start": 56, "end": 68, "masked_value": "XXX-XXX-7894" }
  ],
  "processing_time_ms": 0.9
}
```

### กฎของ `matches` ที่ backend การันตี

- เรียงตาม `start` จากน้อยไปมากเสมอ (ไม่ได้จัดกลุ่มตาม rule)
- Match ranges may overlap when multiple rules detect the same source characters; all required masking is combined.
- `start` / `end` are Unicode code-point offsets into the original text. JavaScript UTF-16 offsets can differ after emoji.
- **ไม่มีค่าต้นฉบับส่งกลับไปเด็ดขาด** มีแค่ประเภท ตำแหน่ง และค่าที่เซ็นเซอร์แล้ว
- ค่าเดียวกันที่โผล่หลายที่ = หลาย match (ไม่ dedupe ให้)
- `by_type` ไม่มี key ของกฎที่ไม่เจออะไรเลย → ฝั่ง frontend ใช้ `by_type[rule] ?? 0`

---

## `GET /rules`

ใช้ render panel แสดง regex บนหน้าเว็บ (ตรงกับเกณฑ์ให้คะแนนข้อ 1)

### Response `200`

```json
{
  "rules": [
    {
      "id": "credit_card",
      "label_th": "เลขบัตรเครดิต",
      "label_en": "Credit Card",
      "pattern": "\\b(\\d{4})-(\\d{4})-(\\d{4})-(\\d{4})\\b",
      "example_before": "1234-5678-9012-3456",
      "example_after": "XXXX-XXXX-XXXX-3456",
      "description": "เก็บเฉพาะ 4 ตัวท้าย"
    }
  ]
}
```

---

## `POST /detect` (optional)

Request เหมือน `/mask` ทุกอย่าง — Response ตัด `masked_text` ออก เหลือแค่ `summary` + `matches`
ใช้กรณีอยากไฮไลต์ PII ระหว่างผู้ใช้พิมพ์ (ต้อง debounce ~300ms)

---

## `GET /health`

```json
{ "status": "ok", "version": "1.0.0" }
```

---

## Errors

ใช้ envelope มาตรฐานของ FastAPI

```json
{ "detail": "text must not be empty" }
```

| code | เมื่อไหร่ |
|---|---|
| `422` | validation ไม่ผ่าน — ไม่มี `text`, หรือ `enabled_rules` มี id ที่ไม่รู้จัก |
| `413` | `text` ยาวเกิน 50,000 ตัวอักษร |
| `500` | error ที่ไม่คาดคิด |

---

## Flow คร่าว ๆ ไม่ชัวร์

1. หน้าเว็บโหลด → `GET /rules` เพื่อ render checkbox + panel แสดง regex
2. ผู้ใช้พิมพ์ข้อความ → กดปุ่ม → `POST /mask`
3. ผู้ใช้ติ๊ก/เอาติ๊กออก → **ยิง `POST /mask` ใหม่** ด้วย `enabled_rules` ชุดใหม่
   (ไม่มี endpoint filter แยก — เพราะ server ไม่เก็บข้อความต้นฉบับไว้)

---

## ค้างไว้ — ตัดสินใจกันทีหลัง

1. **CORS origin** — frontend รันที่ origin ไหนบ้าง (dev + production)
2. **span ของ `address`** ตอนนี้ครอบคำว่า `Address: ` เข้าไปด้วย ทำให้ `masked_value` เป็น `"Address: XXX"`
   ถ้าจะไฮไลต์เฉพาะเลขที่บ้าน ต้องขยับ span → **แก้ทีหลังกระทบทั้งสองฝั่ง**
3. **รูปแบบที่อยู่แปลก ๆ** เช่น `689/12`, `98/1 หมู่ 4` จะแทนด้วย `X` กี่ตัว
4. **ติ๊กออกหมด (`enabled_rules: []`)** คืนข้อความเดิม ไม่ใช้กฎใดเลย
5. **ใครทำ highlight rendering** — backend ส่ง offset ให้แล้ว ฝั่ง frontend จัดการ DOM เองมั้ย
