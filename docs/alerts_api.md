Returns the alerts of all the user's farms for today and the next 3 days — the
same alerts the farmer sees on the Nojo alerts page. Alerts come from the
weather, the crops and the farm's devices: heat, frost, disease risk,
irrigation, spraying, and so on.

## `GET /api/alerts/overview`

```json
[
  {
    "farmId": "a3f1c2d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
    "farmName": "North Farm",
    "farmType": "Open Field",
    "alerts": [
      {
        "alertId": "c9d8e7f6-5a4b-3c2d-1e0f-9a8b7c6d5e4f",
        "cropId": "b7e2d1c0-1a2b-3c4d-5e6f-7a8b9c0d1e2f",
        "cropName": "Avocado",
        "cropNameAr": "أفوكادو",
        "aliasCropName": "Avocado 1",
        "date": "2026-10-01",
        "severity": "Warning",
        "category": "Irrigation",
        "title": "Water / Drought Stress",
        "titleAr": "الإجهاد المائي (نقص ري)",
        "description": "Conditions favour Water / Drought Stress.",
        "descriptionAr": "الظروف مواتية للإجهاد المائي.",
        "action": "Irrigate now and check the drip lines.",
        "actionAr": "ابدأ رية فوراً وتحقق من انسداد الخطوط.",
        "isRead": false
      }
    ]
  }
]
```

| Field | Description |
|---|---|
| `cropId` | The crop the alert is about. `null` = about the whole farm, not one crop (then the crop names are `null` too) |
| `date` | `YYYY-MM-DD`, the day the alert is about. `null` = today |
| `severity` | `Info`, `Warning`, `High`, or `Critical` (from lowest to highest) |
| `category` | What the alert is about, for example `Heat Stress`, `Disease Risk`, `Irrigation`, `Wind`, `Spraying` |
| `title` / `titleAr` | The alert in short, English / Arabic |
| `description` / `descriptionAr` | Why the alert was raised, English / Arabic |
| `action` / `actionAr` | What the farmer should do, English / Arabic |
| `isRead` | Whether the farmer already opened it in Nojo |

Any text field can be `null` when Nojo has no text for it. `alerts` is `[]`
when the farm has no alerts, or no active crops.

**One farm only:** add `?farmId=` (the `farmId` from `GET /api/farms/overview`):
`GET /api/alerts/overview?farmId=a3f1c2d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d`.
It returns that farm's one row (an object, not a list).

### Responses

| Status | Description |
|---|---|
| `200` | Success — returns the list above (`[]` if the user has no farms), or one farm's row with `?farmId=` |
| `400` | `farmId` is not a valid UUID |
| `401` | Missing, expired, or invalid Nojo JWT — exchange the OAuth token again |
| `403` | The account is not a farmer account |
| `404` | Farm not found, or it belongs to another user |
| `429` | Too many requests — wait and retry |
| `500` | Unexpected backend error |

---

Returns the past alerts of all the user's farms: yesterday, the day before
yesterday, or both. Same fields as `GET /api/alerts/overview`. Includes alerts
that have already ended.

## `GET /api/alerts/overview/history`

| Query | Returns |
|---|---|
| (none) | Yesterday and the day before yesterday together |
| `?day=yesterday` | Yesterday only |
| `?day=before-yesterday` | The day before yesterday only |

```json
[
  {
    "farmId": "a3f1c2d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
    "farmName": "North Farm",
    "farmType": "Open Field",
    "alerts": [
      {
        "alertId": "c9d8e7f6-5a4b-3c2d-1e0f-9a8b7c6d5e4f",
        "cropId": "b7e2d1c0-1a2b-3c4d-5e6f-7a8b9c0d1e2f",
        "cropName": "Avocado",
        "cropNameAr": "أفوكادو",
        "aliasCropName": "Avocado 1",
        "date": "2026-09-27",
        "severity": "High",
        "category": "Heat Stress",
        "title": "Heat stress",
        "titleAr": "إجهاد حراري",
        "description": "Temperature above the crop's limit.",
        "descriptionAr": "درجة الحرارة أعلى من حد المحصول.",
        "action": "Irrigate early in the morning.",
        "actionAr": "اروِ في الصباح الباكر.",
        "isRead": true
      }
    ]
  }
]
```

`date` is always set here (never `null`), so use it to tell the two days apart.
`alerts` is `[]` when the farm had no alerts on those days.

**One farm only:** add `farmId` (the `farmId` from `GET /api/farms/overview`):
`GET /api/alerts/overview/history?day=yesterday&farmId=a3f1c2d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d`.
It returns that farm's one row (an object, not a list).

### Responses

| Status | Description |
|---|---|
| `200` | Success — returns the list above (`[]` if the user has no farms), or one farm's row with `farmId` |
| `400` | `day` is not `yesterday` or `before-yesterday`, or `farmId` is not a valid UUID |
| `401` | Missing, expired, or invalid Nojo JWT — exchange the OAuth token again |
| `403` | The account is not a farmer account |
| `404` | Farm not found, or it belongs to another user |
| `429` | Too many requests — wait and retry |
| `500` | Unexpected backend error |
