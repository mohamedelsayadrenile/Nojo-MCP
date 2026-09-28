Returns all the user's farms with their full details: name, location, farm
type, linked devices, and alert settings.

## `GET /api/farms`

```json
[
  {
    "id": "a3f1c2d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
    "farmerId": "81b49124-d509-4607-af93-fae0df6cb0c8",
    "name": "North Field",
    "latitude": "30.0444000",
    "longitude": "31.2357000",
    "address": "Giza, Egypt",
    "elevation": "23.00",
    "soilTypeId": null,
    "cropTypeId": null,
    "farmType": "open field",
    "weatherStationDeviceId": "67bf20c6cb3bc86f9cae9044",
    "climateDeviceId": null,
    "receiveWhatsAppAlerts": true,
    "receiveTelegramAlerts": true,
    "isActiveToUser": true,
    "locationEditsCount": 1,
    "lastLocationEditDate": "2026-09-10T08:12:00.000Z",
    "locationEditsLimit": 5,
    "locationEditsRemaining": 4,
    "createdBy": "81b49124-d509-4607-af93-fae0df6cb0c8",
    "createdAt": "2026-06-01T10:00:00.000Z",
    "updatedAt": "2026-09-10T08:12:00.000Z",
    "deletedAt": null
  }
]
```

### Responses

| Status | Description |
|---|---|
| `200` | Success — returns the farms list above |
| `401` | Missing, expired, or invalid Nojo JWT — exchange the OAuth token again |
| `403` | The account is not a farmer account |
| `429` | Too many requests — wait and retry |
| `500` | Unexpected backend error |

---

Deletes one of the user's farms. All crops on it are removed too, and its
linked devices are freed so another farm can use them. Ask the user to confirm
before calling it.

## `DELETE /api/farms/:id`

`:id` is the `farmId` from `GET /api/farms/overview`.

```json
{
  "message": "Farm deleted successfully"
}
```

### Responses

| Status | Description |
|---|---|
| `200` | Success — returns the message above |
| `400` | `:id` is not a valid UUID |
| `401` | Missing, expired, or invalid Nojo JWT — exchange the OAuth token again |
| `403` | The account is not a farmer account |
| `404` | Farm not found, or it belongs to another user |
| `429` | Too many requests — wait and retry |
| `500` | Unexpected backend error |

---

Adds a new farm for the user.

## `POST /api/farms`

Body:

```json
{
  "name": "North Field",
  "farmType": "Open Field",
  "latitude": 30.0444,
  "longitude": 31.2357
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Farm name, 2–50 characters |
| `farmType` | string | No | `Open Field` or `Greenhouse` (not case-sensitive). Defaults to `Open Field` |
| `latitude` | number | No | Decimal degrees. Must be a number, not a string |
| `longitude` | number | No | Decimal degrees. Must be a number, not a string |

Send only these fields — any other field is rejected with `400`.

Response — the new farm, same shape as one item of `GET /api/farms`:

```json
{
  "id": "a3f1c2d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
  "name": "North Field",
  "farmType": "Open Field",
  "latitude": 30.0444,
  "longitude": 31.2357,
  "locationEditsLimit": 5,
  "locationEditsRemaining": 5,
  "createdAt": "2026-09-28T10:00:00.000Z"
}
```

### Responses

| Status | Description |
|---|---|
| `201` | Success — returns the new farm |
| `400` | Invalid body: name too short/long, unknown farm type, latitude/longitude not numbers, or an extra field |
| `401` | Missing, expired, or invalid Nojo JWT — exchange the OAuth token again |
| `403` | The account is not a farmer account |
| `429` | Too many requests — wait and retry |
| `500` | Unexpected backend error |

---

Edits one of the user's farms. Send at least one field, at most all four —
only the fields sent are changed.

## `PATCH /api/farms/:id`

`:id` is the `farmId` from `GET /api/farms/overview`.

Body (any one or more of):

```json
{
  "name": "North Field",
  "farmType": "Open Field",
  "latitude": 30.0444,
  "longitude": 31.2357
}
```

| Field | Type | Description |
|---|---|---|
| `name` | string | Farm name, 2–50 characters |
| `farmType` | string | `Open Field` or `Greenhouse` (not case-sensitive) |
| `latitude` | number | Decimal degrees. Must be a number, not a string |
| `longitude` | number | Decimal degrees. Must be a number, not a string |

Send only these fields — any other field is rejected with `400`.

An empty body `{}` is rejected with `400 Invalid body`.

Location changes made through the AI chat have no limit — they do not count
against the farmer's monthly map-edit allowance (`locationEditsRemaining`).

Response — the updated farm, same shape as one item of `GET /api/farms`:

```json
{
  "id": "a3f1c2d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
  "name": "North Field",
  "farmType": "Open Field",
  "latitude": 30.0444,
  "longitude": 31.2357,
  "locationEditsLimit": 5,
  "locationEditsRemaining": 5,
  "updatedAt": "2026-09-28T10:00:00.000Z"
}
```

### Responses

| Status | Description |
|---|---|
| `200` | Success — returns the updated farm |
| `400` | Invalid body (empty `{}`, name too short/long, unknown farm type, latitude/longitude not numbers, extra field), or `:id` not a valid UUID |
| `401` | Missing, expired, or invalid Nojo JWT — exchange the OAuth token again |
| `403` | The account is not a farmer account |
| `404` | Farm not found, or it belongs to another user |
| `429` | Too many requests — wait and retry |
| `500` | Unexpected backend error |
