# T-RexX API Reference (v1)

PII / PDPA data-masking API. เอกสารนี้อธิบาย endpoint ทั้งหมดตามที่ backend ทำงานจริง สำหรับฝั่ง frontend ใช้อ้างอิง

- **Stack:** Python + FastAPI
- **Base URL:** `<domain>/api/v1` (prefix จาก `API_V1_PREFIX`)
- **Content-Type:** `application/json; charset=utf-8`
- **Field naming:** `snake_case` ทุก field
- **Stateless:** ไม่มี DB / ไม่มี auth / ไม่เก็บข้อความต้นฉบับ
- **Interactive docs (Swagger):** `<domain>/docs` · **OpenAPI JSON:** `<domain>/openapi.json`
- **CORS:** ตั้งค่าจาก env `CORS_ORIGINS` (default `*`)

---

## Rule IDs

ใช้ค่า `id` เหล่านี้ในทุก request/response (`enabled_rules`, `by_type`, `matches[].rule_id`)

| id | label (th) | ตัวอย่าง input | ตัวอย่าง output | เก็บอะไรไว้ |
|---|---|---|---|---|
| `email` | อีเมล | `somchai.d@company.com` | `s*******d@company.com` | ตัวแรก + ตัวสุดท้ายของ local part |
| `credit_card` | เลขบัตรเครดิต | `1234-5678-9012-3456` | `XXXX-XXXX-XXXX-3456` | 4 ตัวท้าย |
| `phone` | เบอร์โทรศัพท์ | `093-245-7894` | `XXX-XXX-7894` | 4 ตัวท้าย |
| `dob` | วันเดือนปีเกิด | `DOB:25/12/2549` | `DOB:XX/XX/25XX` | 2 ตัวแรกของปี |
| `address` | ที่อยู่ | `Address: 689/12 Sukhumvit Road` | `Address: XXX/XX Sukhumvit Road` | เซ็นเซอร์เฉพาะเลขที่บ้านหลัง `Address:` |

> รายละเอียด regex / ตัวอย่างเต็มดึงได้จาก `GET /rules` (ดูด้านล่าง)

---

## Endpoints

| Method | Path | หน้าที่ |
|---|---|---|
| `GET` | `/health` | เช็คว่า service ทำงานอยู่ |
| `GET` | `/rules` | metadata ของกฎทั้ง 5 (label, regex, ตัวอย่าง) |
| `POST` | `/detect` | หา PII โดย **ไม่** เซ็นเซอร์ (ใช้ไฮไลต์) |
| `POST` | `/mask` | เซ็นเซอร์ข้อความ + คืน `masked_text` |

*(path จริงมี prefix `/api/v1` เช่น `POST /api/v1/mask`)*

---

## `POST /mask`

เซ็นเซอร์ข้อความและคืนผลลัพธ์ที่เซ็นเซอร์แล้ว

### Request

```json
{
  "text": "user=somchai.d@company.com card=1234-5678-9012-3456 tel=093-245-7894",
  "enabled_rules": ["email", "credit_card", "phone", "dob", "address"],
  "include_matches": true
}
```

| field | type | required | default | หมายเหตุ |
|---|---|---|---|---|
| `text` | string | required | — | ข้อความที่ผู้ใช้พิมพ์ (สูงสุด 50,000 ตัวอักษร) |
| `enabled_rules` | string[] \| null | not required | `null` → รันทั้ง 5 กฎ | ผูกกับ checkbox บนหน้าเว็บ · id ที่ไม่รู้จักจะถูก **ข้ามเงียบ ๆ** (ไม่ error) |
| `include_matches` | boolean | not required | `true` | `false` → field `matches` คืนเป็น `null` |

### Response `200`

```json
{
  "masked_text": "user=s*******d@company.com card=XXXX-XXXX-XXXX-3456 tel=XXX-XXX-7894",
  "summary": {
    "total": 3,
    "by_type": { "email": 1, "credit_card": 1, "phone": 1 }
  },
  "matches": [
    { "rule_id": "email",       "label": "อีเมล",         "start": 5,  "end": 26, "masked_value": null },
    { "rule_id": "credit_card", "label": "เลขบัตรเครดิต", "start": 32, "end": 51, "masked_value": null },
    { "rule_id": "phone",       "label": "เบอร์โทรศัพท์", "start": 56, "end": 68, "masked_value": null }
  ],
  "processing_time_ms": 0.9
}
```

| field | type | หมายเหตุ |
|---|---|---|
| `masked_text` | string | ข้อความหลังเซ็นเซอร์ |
| `summary.total` | int | จำนวน match ทั้งหมด |
| `summary.by_type` | object | นับตาม rule_id — **มีเฉพาะกฎที่เจออย่างน้อย 1 ครั้ง** |
| `matches` | array \| null | `null` เมื่อ `include_matches=false` |
| `processing_time_ms` | float | เวลาประมวลผล (ms) |

---

## `POST /detect`

Request เหมือน `/mask` ทุกอย่าง — Response **ตัด `masked_text` ออก** เหลือแค่ `summary` + `matches` + `processing_time_ms`
ใช้ตอนอยากไฮไลต์ PII ระหว่างผู้ใช้พิมพ์ (แนะนำ debounce ~300ms)

### Response `200`

```json
{
  "summary": {
    "total": 3,
    "by_type": { "email": 1, "credit_card": 1, "phone": 1 }
  },
  "matches": [
    { "rule_id": "email", "label": "อีเมล", "start": 5, "end": 26, "masked_value": null }
  ],
  "processing_time_ms": 0.7
}
```

---

## Match object (ใช้ร่วมกันทั้ง `/mask` และ `/detect`)

| field | type | หมายเหตุ |
|---|---|---|
| `rule_id` | string | หนึ่งใน Rule IDs |
| `label` | string | label ภาษาไทยของกฎ |
| `start` | int | ตำแหน่งเริ่ม (character offset ของข้อความต้นฉบับ) |
| `end` | int | ตำแหน่งจบ (exclusive) |
| `masked_value` | string \| null | **ปัจจุบันเป็น `null` เสมอ** (ยังไม่ถูก implement) |

### สิ่งที่ backend การันตี

- `matches` เรียงตาม `start` จากน้อยไปมากเสมอ (ไม่จัดกลุ่มตาม rule)
- `start` / `end` เป็น character offset ของ **ข้อความต้นฉบับ** — Python `len()` และ JS `.length` ให้ค่าตรงกัน
- ไม่มีค่าต้นฉบับ (raw PII) ส่งกลับไป — มีแค่ประเภทและตำแหน่ง
- ค่าเดียวกันโผล่หลายที่ = หลาย match (ไม่ dedupe)
- `by_type` ไม่มี key ของกฎที่ไม่เจออะไรเลย → frontend ใช้ `by_type[rule] ?? 0`

---

## `GET /rules`

ใช้ render panel แสดงกฎ / regex / ตัวอย่างบนหน้าเว็บ

### Response `200`

```json
{
  "rules": [
    {
      "id": "credit_card",
      "label_th": "เลขบัตรเครดิต",
      "label_en": "Credit Card",
      "pattern": "(?<![0-9-])[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{4}(?![0-9-])",
      "example_before": "1234-5678-9012-3456",
      "example_after": "XXXX-XXXX-XXXX-3456",
      "description": "เก็บเฉพาะ 4 ตัวท้าย"
    }
  ]
}
```

| field | type | หมายเหตุ |
|---|---|---|
| `rules` | array | รายการกฎทั้งหมด |
| `rules[].id` | string | ตรงกับ Rule IDs |
| `rules[].label_th` | string | label ภาษาไทย |
| `rules[].label_en` | string | label ภาษาอังกฤษ |
| `rules[].pattern` | string | regex ที่ใช้ตรวจจับ |
| `rules[].example_before` | string | ตัวอย่างก่อนเซ็นเซอร์ |
| `rules[].example_after` | string | ตัวอย่างหลังเซ็นเซอร์ |
| `rules[].description` | string | คำอธิบายสั้น ๆ |

---

## `GET /health`

```json
{
  "status": "ok",
  "app": "T-RexX API",
  "version": "0.1.0"
}
```

---

## Errors

ใช้ envelope มาตรฐานของ FastAPI

```json
{ "detail": "..." }
```

| code | เมื่อไหร่ |
|---|---|
| `422` | validation ไม่ผ่าน — ไม่มี field `text`, ผิด type, หรือ `text` ยาวเกิน 50,000 ตัวอักษร |
| `500` | error ที่ไม่คาดคิดฝั่ง server |

> หมายเหตุ: `enabled_rules` ที่มี id แปลก ๆ **ไม่** ทำให้ error — จะถูกข้ามไปเฉย ๆ

---

## Flow แนะนำสำหรับ frontend

1. โหลดหน้าเว็บ → `GET /rules` เพื่อ render checkbox + panel แสดง regex
2. ผู้ใช้พิมพ์ข้อความ → (optional) `POST /detect` แบบ debounce เพื่อไฮไลต์ PII สด ๆ
3. ผู้ใช้กดปุ่ม → `POST /mask` เพื่อรับ `masked_text`
4. ผู้ใช้ติ๊ก/เอาติ๊ก rule ออก → ยิง `POST /mask` ใหม่ด้วย `enabled_rules` ชุดใหม่
   (ไม่มี endpoint filter แยก เพราะ server ไม่เก็บข้อความต้นฉบับ)
