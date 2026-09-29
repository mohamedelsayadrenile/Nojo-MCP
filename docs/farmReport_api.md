Returns the report of one farm for a date range — the same data as the PDF
the farmer downloads on the Nojo reports page: the farm's crops, and for each
day the weather, the VPD and each crop's water need, plus the alerts of those
days. Show it to the user as text, then give them `reportsPageUrl` and tell
them: to download the report as a PDF file, open this link.

## `GET /api/reports/farm/:farmId/summary?from=2026-09-26&to=2026-09-28`

`:farmId` is the `farmId` from `GET /api/farms/overview`.

| Query | Required | Description |
|---|---|---|
| `from` | Yes | First day, `YYYY-MM-DD` |
| `to` | Yes | Last day, `YYYY-MM-DD` (included) |

**Date limit — at most one week, until today.** The report only covers the
last 7 days including today, the same as on the website:

- `from` can be as early as 6 days ago, never earlier
- `to` can be today at the latest, never a future day
- `from` must not be after `to`

For example, if today is `2026-09-28`, the widest report is
`from=2026-09-22&to=2026-09-28` (7 days). If the user asks for older days (for
example "last month"), do not call the API — tell them Nojo reports cover
only the last week, and offer the last 7 days (today included) instead.

```json
{
  "farmId": "a3f1c2d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
  "farmName": "North Farm",
  "farmType": "Open Field",
  "source": "model",
  "from": "2026-09-26",
  "to": "2026-09-28",
  "reportsPageUrl": "https://nojo.ai/reports",
  "crops": [
    {
      "cropId": "b7e2d1c0-1a2b-3c4d-5e6f-7a8b9c0d1e2f",
      "cropName": "Avocado",
      "cropNameAr": "أفوكادو",
      "aliasCropName": "Avocado 1",
      "plantingDate": "2026-03-15",
      "landArea": 2.5,
      "landAreaUnit": "feddan",
      "irrigationSystem": "Drip"
    }
  ],
  "days": [
    {
      "date": "2026-09-26",
      "weather": {
        "maxTemp": 30.0,
        "minTemp": 19.0,
        "humidity": 54,
        "solarRadiation": 21.55,
        "windSpeed": 2.91,
        "rain": 0
      },
      "vpd": 1.42,
      "vpdStatus": "High Stress",
      "irrigation": [
        { "cropId": "b7e2d1c0-1a2b-3c4d-5e6f-7a8b9c0d1e2f", "waterMm": 5.6, "waterM3": 58.8 }
      ],
      "totalWaterM3": 58.8
    }
  ],
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
      "actionAr": "اروِ في الصباح الباكر."
    }
  ]
}
```

(Shortened — `days` has one entry per day from `from` to `to`.)

| Field | Unit | Description |
|---|---|---|
| `source` | — | `device`: the days come from the farm's own device. `model`: from the weather service (past days as recorded, today as forecast) |
| `reportsPageUrl` | — | The Nojo reports page, where the user downloads this report as a PDF (they pick the farm and the dates there) |
| `weather.maxTemp` / `minTemp` | °C | Highest and lowest temperature of the day |
| `weather.humidity` | % | Average humidity of the day |
| `weather.solarRadiation` | MJ/m² | Total solar radiation of the day |
| `weather.windSpeed` | m/s | Highest wind speed of the day. Open field only |
| `weather.rain` | mm | Total rain of the day. Open field only |
| `vpd` | kPa | The day's VPD |
| `vpdStatus` | — | Same values as in `GET /api/agronomy/vpd/overview` |
| `irrigation` | — | One entry per crop: the water it needed that day, `waterMm` (mm over its land) and `waterM3` (m³) |
| `totalWaterM3` | m³ | All crops together that day |
| `alerts` | — | The alerts of the range, same fields as in `GET /api/alerts/overview` |

A value is `null` when it is not known for that day (for example the farm's
device did not report that day). Tell the user there is no data. Do not guess.

### Responses

| Status | Description |
|---|---|
| `200` | Success — returns the report above |
| `400` | `from` or `to` is missing or not `YYYY-MM-DD`, `from` is after `to`, `to` is after today, or `from` is more than 6 days ago. `message` says which |
| `401` | Missing, expired, or invalid Nojo JWT — exchange the OAuth token again |
| `403` | The account is not a farmer account, or the farm belongs to another user |
| `404` | Farm not found, or `:farmId` is not a valid UUID |
| `429` | Too many requests — wait and retry |
| `500` | Unexpected backend error |
