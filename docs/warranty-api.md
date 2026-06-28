# Warranty API Documentation

เอกสาร API สำหรับระบบลงทะเบียนรับประกันสินค้า (`partner.warranty`)

## Overview

ระบบประกอบด้วย models หลัก:

| Model | คำอธิบาย |
|-------|----------|
| `partner.warranty` | รายการลงทะเบียนรับประกันที่ member ส่งเข้ามา |
| `partner.warranty.product` | สินค้าที่ portal config สำหรับ dropdown |
| `partner.warranty.contributor` | ช่องทางการซื้อสินค้า (dropdown) |
| `partner.warranty.status` | สถานะ custom ที่ portal กำหนด label ได้ |
| `partner.warranty.comment` | ความคิดเห็นจาก portal staff |

## การเปิดใช้งาน

Admin ต้องเปิด **Enable Warranty Registration** (`ui_warranty_enabled`) ที่หน้า Partner ใน Odoo backend ก่อน

- LIFF/Member app จะเห็น `warranty` ใน partner config เมื่อเปิดใช้งาน
- Portal จะเห็น `warranty_enabled: true` ใน `/api/portal/login` และ `/api/portal/me`

---

## Authentication

### Member API (LIFF)

```
Authorization: Bearer <LINE_ACCESS_TOKEN>
```

### Portal API

```
Authorization: Bearer <PORTAL_TOKEN>
```

หรือ

```
X-api-key: <API_KEY>
```

---

## Member API (LIFF)

Base path: `/api/partner/<slug>`

### GET `/warranty/options`

ดึง dropdown options สำหรับฟอร์มลงทะเบียน

**Response 200**

```json
{
  "enabled": true,
  "products": [
    {
      "id": 1,
      "name": "Product A",
      "description": "รายละเอียด",
      "sku": "SKU-001",
      "cost_price": 1000,
      "sell_price": 1500
    }
  ],
  "contributors": [
    { "id": 1, "name": "ออนไลน์" }
  ],
  "statuses": [
    {
      "id": 1,
      "code": "pending",
      "label": "รอตรวจสอบ",
      "color": "#FFC107",
      "is_default": true
    }
  ]
}
```

**Response 403** — ระบบยังไม่เปิดใช้งาน (`warranty_not_enabled`)

---

### POST `/user/<line_user_id>/warranty`

ส่งฟอร์มลงทะเบียนรับประกัน (รองรับทั้งรายการเดียวและหลายรายการ)

**JSON Body — รายการเดียว**

```json
{
  "product_id": 1,
  "serial_number": "1U-2509K-0001",
  "receipt_number": "INV-12345",
  "contributor_id": 1,
  "purchase_date": "2026-06-15",
  "receipt_image": "<base64>"
}
```

**JSON Body — หลายรายการ**

```json
{
  "warranties": [
    {
      "product_id": 1,
      "serial_number": "1U-2509K-0001",
      "receipt_number": "INV-12345",
      "contributor_id": 1,
      "purchase_date": "2026-06-15",
      "receipt_image": "<base64>"
    },
    {
      "product_id": 2,
      "serial_number": "1U-2509K-0002",
      "receipt_number": "INV-12345",
      "contributor_id": 2,
      "purchase_date": "2026-06-15",
      "receipt_image": "<base64>"
    }
  ]
}
```

**Multipart Form**

- `items` — JSON string ของ array รายการ
- `receiptImage_0`, `receiptImage_1`, ... — ไฟล์รูปใบเสร็จตาม index

หรือส่งฟิลด์เดี่ยว: `productId`, `serialNumber`, `receiptNumber`, `contributorId`, `purchaseDate`, `receiptImage`

**Response 201 — รายการเดียว**

```json
{
  "warranty": {
    "id": 10,
    "serial_number": "1U-2509K-0001",
    "receipt_number": "INV-12345",
    "purchase_date": "2026-06-15",
    "receipt_image_url": "https://...",
    "submitted_date": "2026-06-28 10:00:00",
    "product": { "id": 1, "name": "Product A", ... },
    "contributor": { "id": 1, "name": "ออนไลน์" },
    "status": { "id": 1, "code": "pending", "label": "รอตรวจสอบ", ... }
  }
}
```

**Response 201 — หลายรายการ**

```json
{
  "warranties": [ ... ]
}
```

---

### GET `/user/<line_user_id>/warranty`

ดึงประวัติการลงทะเบียนของ member (หน้า "ประวัติ")

**Response 200**

```json
{
  "warranties": [ ... ]
}
```

---

### GET `/user/<line_user_id>/warranty/<warranty_id>`

ดึงรายละเอียดรายการเดียว

---

## Partner Config

### GET `/api/partner/<slug>`

เมื่อเปิดใช้งาน warranty จะมี field เพิ่ม:

```json
{
  "warranty": {
    "enabled": true,
    "products": [ { "id": 1, "name": "Product A", "description": false, "sku": "SKU-001" } ],
    "contributors": [ { "id": 1, "name": "ออนไลน์" } ]
  }
}
```

---

## Portal API

Base path: `/api/portal`

### GET `/warranty/config`

ดึง config ทั้งหมด (products, contributors, statuses)

**Response 200**

```json
{
  "enabled": true,
  "products": [ ... ],
  "contributors": [ ... ],
  "statuses": [ ... ]
}
```

---

## Warranty Registrations

### GET `/warranties`

รายการลงทะเบียนทั้งหมด

**Query params**

| Param | คำอธิบาย |
|-------|----------|
| `status_id` | กรองตาม status |
| `user_id` | กรองตาม member |
| `search` | ค้นหา serial, receipt, ชื่อ member, ชื่อสินค้า |
| `limit`, `offset` | pagination |

**Response 200**

```json
{
  "warranties": [ ... ],
  "total": 42
}
```

---

### GET `/warranties/<id>`

รายละเอียดพร้อม comments

---

### PUT `/warranties/<id>`

อัปเดตสถานะ

**Body**

```json
{
  "status_id": 2
}
```

---

### POST `/warranties/<id>/comments`

เพิ่ม comment

**Body**

```json
{
  "body": "ตรวจสอบใบเสร็จแล้ว รออนุมัติ"
}
```

**Response 201**

```json
{
  "comment": {
    "id": 1,
    "body": "...",
    "author_name": "Admin User",
    "author_id": 5,
    "created_at": "2026-06-28 11:00:00"
  }
}
```

---

## Product Config

### GET `/warranty-products`

**Query:** `include_inactive=true` — รวมรายการที่ปิดใช้งาน

### POST `/warranty-products`

```json
{
  "name": "Product A",
  "description": "รายละเอียด",
  "sku": "SKU-001",
  "cost_price": 1000,
  "sell_price": 1500,
  "image_base64": "<base64>",
  "active": true
}
```

`image_base64` — optional, อัปโหลดรูปสินค้าไป S3

Response รวม `image_url`:

```json
{
  "id": 1,
  "name": "Product A",
  "image_url": "https://..."
}
```

`name` — required

### PUT `/warranty-products/<id>`

แก้ไข field ใดก็ได้จาก POST body

### DELETE `/warranty-products/<id>`

Soft delete (`active = false`)

---

## Purchase Channel Config

### GET `/warranty-contributors`

### POST `/warranty-contributors`

```json
{
  "name": "ออนไลน์",
  "sequence": 10,
  "active": true
}
```

`name` — required

### PUT `/warranty-contributors/<id>`

### DELETE `/warranty-contributors/<id>`

Soft delete

---

## Status Config

Default statuses จะถูกสร้างอัตโนมัติเมื่อเรียก config ครั้งแรก:

| code | label (default) |
|------|-----------------|
| `pending` | รอตรวจสอบ |
| `approved` | อนุมัติ |
| `rejected` | ปฏิเสธ |

### GET `/warranty-statuses`

### POST `/warranty-statuses`

```json
{
  "code": "processing",
  "label": "กำลังดำเนินการ",
  "sequence": 15,
  "color": "#17A2B8",
  "is_default": false,
  "active": true
}
```

`code`, `label` — required

### PUT `/warranty-statuses/<id>`

แก้ไข label หรือ field อื่นได้จาก portal

### DELETE `/warranty-statuses/<id>`

Soft delete

---

## Portal Login / Me

Response `partner` object เพิ่ม:

```json
{
  "warranty_enabled": true
}
```

---

## Error Codes

| Code | HTTP | คำอธิบาย |
|------|------|----------|
| `warranty_not_enabled` | 403 | ระบบยังไม่เปิดใช้งาน |
| `warranty_not_allowed` | 400 | validation error |
| `warranty_not_found` | 404 | ไม่พบรายการ |
| `product_not_found` | 404 | ไม่พบสินค้า |
| `contributor_not_found` | 404 | ไม่พบช่องทาง |
| `status_not_found` | 404 | ไม่พบสถานะ |
| `comment_not_allowed` | 400 | comment validation error |
| `invalid_json` | 400 | JSON ไม่ถูกต้อง |
| `unauthorized` | 401 | token ไม่ถูกต้อง |

---

## Odoo Backend

Admin สามารถจัดการได้ที่ Partner form:

1. เปิด **Enable Warranty Registration**
2. Tab **Warranty** — จัดการ products, channels, statuses, ดู registrations

Default status จะถูก seed เมื่อมีการเรียก API config หรือ options ครั้งแรก
