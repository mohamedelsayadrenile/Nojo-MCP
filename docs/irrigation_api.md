Returns today's irrigation for every crop on all the user's farms: whether to
irrigate, how much water, and for how long.

## `GET /api/irrigation/overview`

```json
[
  {
    "farmId": "a3f1c2d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
    "farmName": "North Farm",
    "farmType": "Open Field",
    "crops": [
      {
        "cropId": "b7e2d1c0-1a2b-3c4d-5e6f-7a8b9c0d1e2f",
        "cropName": "Avocado",
        "cropNameAr": "أفوكادو",
        "aliasCropName": "Avocado 1",
        "growthStage": "development",
        "irrigationSystem": "Drip",
        "status": "optimal",
        "waterMm": 5.8,
        "waterM3": 60.9,
        "runtimeHours": 2.5
      }
    ]
  }
]
```

| Field | Unit | Description |
|---|---|---|
| `growthStage` | — | `initial`, `development`, `mid`, `late`, or `post-harvest` |
| `status` | — | `optimal`: irrigate the normal amount today. `increase`: soil is dry, irrigate more. `reduce`: soil is wet enough, irrigate less. `skip`: soil is very wet, no irrigation today. `rest`: the tree is dormant, no irrigation. `not_active`: the crop is not planted yet or its season ended |
| `waterMm` | mm | Water to give today, as depth over the crop's land |
| `waterM3` | m³ | The same water as volume, for the crop's whole land area |
| `runtimeHours` | hours | How long to run the irrigation system. Can be `null` (for example in a greenhouse) |

A value is `null` when it cannot be calculated right now. `crops` is `[]`
when the farm has no crops, or its irrigation cannot be calculated right now.
Tell the user there is no data. Do not guess.

**One farm only:** add `?farmId=` (the `farmId` from `GET /api/farms/overview`):
`GET /api/irrigation/overview?farmId=a3f1c2d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d`.
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

Returns the irrigation for the next 7 days (today first) for every crop on all
the user's farms. The numbers are the same as the 7-day chart on the Nojo
irrigation page.

## `GET /api/irrigation/overview/forecast`

```json
[
  {
    "farmId": "a3f1c2d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
    "farmName": "North Farm",
    "farmType": "Open Field",
    "crops": [
      {
        "cropId": "b7e2d1c0-1a2b-3c4d-5e6f-7a8b9c0d1e2f",
        "cropName": "Avocado",
        "cropNameAr": "أفوكادو",
        "aliasCropName": "Avocado 1",
        "days": [
          { "date": "2026-09-28", "status": "optimal", "waterMm": 5.8, "waterM3": 60.9 },
          { "date": "2026-09-29", "status": "optimal", "waterMm": 6.1, "waterM3": 64.1 }
        ]
      }
    ]
  }
]
```

(Shortened — each crop has 7 days.)

| Field | Unit | Description |
|---|---|---|
| `date` | — | `YYYY-MM-DD` |
| `status` | — | Same values as in `GET /api/irrigation/overview` |
| `waterMm` | mm | Water to give that day, as depth over the crop's land |
| `waterM3` | m³ | The same water as volume, for the crop's whole land area |

A value is `null` when it cannot be calculated for that day. `crops` is `[]`
when the farm has no crops, or its forecast cannot be calculated right now.
Tell the user there is no data. Do not guess.

**One farm only:** add `?farmId=` (the `farmId` from `GET /api/farms/overview`):
`GET /api/irrigation/overview/forecast?farmId=a3f1c2d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d`.
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

Returns the irrigation of the past days (yesterday and before) for every crop
on all the user's farms: how much water each crop needed each day.

## `GET /api/irrigation/overview/history?days=7`

`days` is how many days back: `1` = yesterday only, up to `7`. Default `7`.
Days are oldest first; the last one is yesterday. Today is not included.

```json
[
  {
    "farmId": "a3f1c2d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
    "farmName": "North Farm",
    "farmType": "Open Field",
    "crops": [
      {
        "cropId": "b7e2d1c0-1a2b-3c4d-5e6f-7a8b9c0d1e2f",
        "cropName": "Avocado",
        "cropNameAr": "أفوكادو",
        "aliasCropName": "Avocado 1",
        "days": [
          { "date": "2026-09-26", "waterMm": 5.6, "waterM3": 58.8 },
          { "date": "2026-09-27", "waterMm": 5.9, "waterM3": 62.0 }
        ]
      }
    ]
  }
]
```

(Shortened — each crop has one entry per day asked for.)

| Field | Unit | Description |
|---|---|---|
| `date` | — | `YYYY-MM-DD` |
| `waterMm` | mm | Water the crop needed that day, as depth over the crop's land |
| `waterM3` | m³ | The same water as volume, for the crop's whole land area |

There is no `status` for past days: Nojo only knows today's soil moisture,
so it cannot say whether a past day was a skip or an increase day.

A value is `null` when it cannot be calculated for that day (for example the
farm's device did not report that day). `crops` is `[]` when the farm has no
crops, or its history cannot be calculated right now. Tell the user there is no
data. Do not guess.

**One farm only:** add `farmId` (the `farmId` from `GET /api/farms/overview`):
`GET /api/irrigation/overview/history?days=1&farmId=a3f1c2d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d`.
It returns that farm's one row (an object, not a list).

### Responses

| Status | Description |
|---|---|
| `200` | Success — returns the list above (`[]` if the user has no farms), or one farm's row with `farmId` |
| `400` | `days` is not a whole number from 1 to 7, or `farmId` is not a valid UUID |
| `401` | Missing, expired, or invalid Nojo JWT — exchange the OAuth token again |
| `403` | The account is not a farmer account |
| `404` | Farm not found, or it belongs to another user |
| `429` | Too many requests — wait and retry |
| `500` | Unexpected backend error |
