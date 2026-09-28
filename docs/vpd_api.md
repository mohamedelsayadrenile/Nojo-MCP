Returns the VPD (vapour pressure deficit) now for all the user's farms — how
dry the air is for the plants — with its status, trend and what to do. The
same reading as the Nojo VPD page.

## `GET /api/agronomy/vpd/overview`

```json
[
  {
    "farmId": "a3f1c2d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
    "farmName": "North Farm",
    "farmType": "Open Field",
    "source": "model",
    "time": "2026-09-28T10:00",
    "vpd": 1.35,
    "status": "High Stress",
    "trend": "Rising",
    "recommendation": "VPD is high and rising. Plants are starting to lose water faster. Consider early irrigation to maintain turgor.",
    "temperature": 29.4,
    "humidity": 48
  }
]
```

| Field | Unit | Description |
|---|---|---|
| `vpd` | kPa | VPD now |
| `status` | — | `Danger (Too Low - Disease Risk)` (below 0.4), `Low Stress` (0.4–0.8), `Optimal` (0.8–1.2), `High Stress` (1.2–1.6), `Danger (Too High - Wilting Risk)` (above 1.6) |
| `trend` | — | Where VPD is going: `Rising Fast`, `Rising`, `Stable`, `Falling`, `Falling Fast` |
| `recommendation` | — | What the farmer should do, in English |
| `temperature` | °C | The temperature VPD was calculated from |
| `humidity` | % | The humidity VPD was calculated from |
| `time` | — | When the reading was taken |
| `source` | — | `device`: from the farm's own device (a greenhouse reads the air inside it). `model`: from the weather forecast |

A value is `null` when it cannot be read right now (for example the farm's
device is offline). Tell the user there is no data. Do not guess.

**One farm only:** add `?farmId=` (the `farmId` from `GET /api/farms/overview`):
`GET /api/agronomy/vpd/overview?farmId=a3f1c2d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d`.
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

Returns the average VPD of past days (yesterday and before) for all the
user's farms, with its status — to answer "was yesterday a stressful day?".

## `GET /api/agronomy/vpd/overview/history?days=1`

`days` is how many days back: `1` = yesterday only (the default), up to `7`.
Days are oldest first; the last one is yesterday. Today is not included.

```json
[
  {
    "farmId": "a3f1c2d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
    "farmName": "North Farm",
    "farmType": "Open Field",
    "source": "model",
    "days": [
      { "date": "2026-09-27", "vpd": 1.42, "status": "High Stress" }
    ]
  },
  {
    "farmId": "b8c9d0e1-2f3a-4b5c-6d7e-8f9a0b1c2d3e",
    "farmName": "Greenhouse 1",
    "farmType": "Greenhouse",
    "source": "device",
    "days": [
      { "date": "2026-09-27", "vpd": 0.95, "status": "Optimal" }
    ]
  }
]
```

| Field | Unit | Description |
|---|---|---|
| `date` | — | `YYYY-MM-DD` |
| `vpd` | kPa | The day's average VPD |
| `status` | — | Same values as in `GET /api/agronomy/vpd/overview`, for the day's average |
| `source` | — | `device`: from the farm's own device (a greenhouse: the average of its hourly readings inside). `model`: calculated from that day's weather |

A value is `null` when it is not known for that day (for example the farm's
device did not report that day). `days` is `[]` when the history cannot be read
right now. Tell the user there is no data. Do not guess.

**One farm only:** add `farmId` (the `farmId` from `GET /api/farms/overview`):
`GET /api/agronomy/vpd/overview/history?days=1&farmId=a3f1c2d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d`.
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
