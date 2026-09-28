Returns the weather now for all the user's farms, one row per farm:
temperature, humidity, and solar radiation. Open-field farms also get wind
speed and today's rain. Greenhouse farms do not.

## `GET /api/weather/overview`

```json
[
  {
    "farmId": "a3f1c2d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
    "farmName": "North Farm",
    "farmType": "Open Field",
    "source": "model",
    "temperature": 29.4,
    "humidity": 48,
    "solarRadiation": 610,
    "windSpeed": 3.2,
    "rain": 0
  },
  {
    "farmId": "b8c9d0e1-2f3a-4b5c-6d7e-8f9a0b1c2d3e",
    "farmName": "Greenhouse 1",
    "farmType": "Greenhouse",
    "source": "device",
    "temperature": 24.1,
    "humidity": 70,
    "solarRadiation": 300
  }
]
```

| Field | Unit | Description |
|---|---|---|
| `temperature` | °C | Air temperature now |
| `humidity` | % | Air humidity now |
| `solarRadiation` | W/m² | Solar radiation now |
| `windSpeed` | m/s | Wind speed now. Open field only |
| `rain` | mm | Today's rain. Open field only |
| `source` | — | `device`: from the farm's own device. `model`: from the weather forecast |

A value is `null` when it cannot be read right now (for example the farm's
device is offline). Tell the user there is no data. Do not guess.

**One farm only:** add `?farmId=` (the `farmId` from `GET /api/farms/overview`):
`GET /api/weather/overview?farmId=a3f1c2d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d`.
It returns that farm's one row (an object, not a list):

```json
{
  "farmId": "a3f1c2d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
  "farmName": "North Farm",
  "farmType": "Open Field",
  "source": "model",
  "temperature": 29.4,
  "humidity": 48,
  "solarRadiation": 610,
  "windSpeed": 3.2,
  "rain": 0
}
```

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

Returns the weather for the next 7 days (today first) for all the user's
farms. Same data as above, per day. Open-field farms also get wind and rain.
Greenhouse farms do not.

## `GET /api/weather/overview/forecast`

```json
[
  {
    "farmId": "a3f1c2d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
    "farmName": "North Farm",
    "farmType": "Open Field",
    "source": "model",
    "days": [
      {
        "date": "2026-09-28",
        "maxTemp": 33.1,
        "minTemp": 21.7,
        "humidity": 50,
        "solarRadiation": 22.5,
        "windSpeed": 6.4,
        "rain": 0
      }
    ]
  },
  {
    "farmId": "b8c9d0e1-2f3a-4b5c-6d7e-8f9a0b1c2d3e",
    "farmName": "Greenhouse 1",
    "farmType": "Greenhouse",
    "source": "device",
    "days": [
      {
        "date": "2026-09-28",
        "maxTemp": 27.0,
        "minTemp": 19.5,
        "humidity": 68,
        "solarRadiation": 14.2
      }
    ]
  }
]
```

(Shortened — each farm has up to 7 days.)

| Field | Unit | Description |
|---|---|---|
| `date` | — | `YYYY-MM-DD` |
| `maxTemp` / `minTemp` | °C | Highest and lowest temperature of the day |
| `humidity` | % | Average humidity of the day |
| `solarRadiation` | MJ/m² | Total solar radiation of the day |
| `windSpeed` | m/s | Highest wind speed of the day. Open field only |
| `rain` | mm | Total rain of the day. Open field only |
| `source` | — | `device`: from the farm's own device. `model`: from the weather forecast |

A value is `null` when it is not known for that day. `days` is `[]` when the
farm has no forecast right now (for example its device is offline). Tell the
user there is no data. Do not guess.

**One farm only:** add `?farmId=` (the `farmId` from `GET /api/farms/overview`):
`GET /api/weather/overview/forecast?farmId=a3f1c2d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d`.
It returns that farm's one row (an object, not a list):

```json
{
  "farmId": "a3f1c2d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
  "farmName": "North Farm",
  "farmType": "Open Field",
  "source": "model",
  "days": [
    {
      "date": "2026-09-28",
      "maxTemp": 33.1,
      "minTemp": 21.7,
      "humidity": 50,
      "solarRadiation": 22.5,
      "windSpeed": 6.4,
      "rain": 0
    }
  ]
}
```

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

Returns the weather of the past days (yesterday and before) for all the
user's farms. Same fields per day as the 7-day forecast. Open-field farms also
get wind and rain. Greenhouse farms do not.

## `GET /api/weather/overview/history?days=7`

`days` is how many days back: `1` = yesterday only, up to `7`. Default `7`.
Days are oldest first; the last one is yesterday. Today is not included.

```json
[
  {
    "farmId": "a3f1c2d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
    "farmName": "North Farm",
    "farmType": "Open Field",
    "source": "model",
    "days": [
      {
        "date": "2026-09-26",
        "maxTemp": 30.0,
        "minTemp": 19.0,
        "humidity": 54,
        "solarRadiation": 21.55,
        "windSpeed": 2.91,
        "rain": 0
      },
      {
        "date": "2026-09-27",
        "maxTemp": 33.8,
        "minTemp": 20.7,
        "humidity": 50,
        "solarRadiation": 19.96,
        "windSpeed": 2.42,
        "rain": 0
      }
    ]
  }
]
```

(Shortened — the fields and units are the same as in `GET /api/weather/overview/forecast`.)

A value is `null` when it is not known for that day (for example the farm's
device did not report that day). `days` is `[]` when the history cannot be read
right now. Tell the user there is no data. Do not guess.

**One farm only:** add `farmId` (the `farmId` from `GET /api/farms/overview`):
`GET /api/weather/overview/history?days=1&farmId=a3f1c2d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d`.
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
