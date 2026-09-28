Returns all the user's crops, across all farms, with their full details:
crop type, farm, planting date, stage, soil, land area, and irrigation state.

## `GET /api/crops`

```json
[
  {
    "id": "b7e2d1c0-1a2b-3c4d-5e6f-7a8b9c0d1e2f",
    "farmId": "a3f1c2d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
    "cropTypeId": "e5f6a7b8-9c0d-1e2f-3a4b-5c6d7e8f9a0b",
    "cropType": {
      "id": "e5f6a7b8-9c0d-1e2f-3a4b-5c6d7e8f9a0b",
      "name": "avocado",
      "display_name": "Avocado",
      "display_name_ar": "أفوكادو",
      "icon": "🥑"
    },
    "cropTypeName": "Avocado",
    "cropTypeAr": "أفوكادو",
    "aliasCropName": "Avocado 1",
    "status": "growing",
    "plantingDate": "2026-03-15",
    "currentStage": "development",
    "gddCumulative": "845.20",
    "soilTypeId": "c1d2e3f4-a5b6-7c8d-9e0f-1a2b3c4d5e6f",
    "soilType": "clay loam",
    "soilTypeName": "Clay Loam",
    "rootDepthZ": "0.6000",
    "fieldCapacity": 0.32,
    "wiltingPoint": 0.15,
    "landArea": 2.5,
    "landAreaUnit": "feddan",
    "irrigationSystem": "Drip",
    "irrigationAmount": 1.43,
    "irrigateNow": true,
    "irrigateNowTriggerPct": "50.00",
    "irrigateNowCheckedAt": "2026-09-28T07:27:00.000Z",
    "lastSoilMoisturePct": "38.50",
    "lastSoilMoistureAt": "2026-09-28T07:25:00.000Z",
    "drDepletion": "12.4000",
    "soilDeviceId": null,
    "endCycle": false,
    "dormancyBroken": false,
    "breakDate": null,
    "translations": {},
    "isActiveToUser": true,
    "createdBy": "81b49124-d509-4607-af93-fae0df6cb0c8",
    "createdAt": "2026-03-15T09:00:00.000Z",
    "updatedAt": "2026-09-28T07:27:00.000Z",
    "deletedAt": null
  }
]
```

### Responses

| Status | Description |
|---|---|
| `200` | Success — returns the crops list above |
| `401` | Missing, expired, or invalid Nojo JWT — exchange the OAuth token again |
| `403` | The account is not a farmer account |
| `429` | Too many requests — wait and retry |
| `500` | Unexpected backend error |

---

Returns all the data of one crop — the same fields as one item of
`GET /api/crops`.

## `GET /api/crops/:id`

`:id` is the `cropId` from `GET /api/farms/overview`.

```json
{
  "id": "b7e2d1c0-1a2b-3c4d-5e6f-7a8b9c0d1e2f",
  "farmId": "a3f1c2d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
  "cropTypeName": "Avocado",
  "cropTypeAr": "أفوكادو",
  "status": "growing",
  "plantingDate": "2026-03-15",
  "currentStage": "development",
  "soilTypeName": "Clay Loam",
  "landArea": 2.5,
  "landAreaUnit": "feddan",
  "irrigationSystem": "Drip",
  "irrigationAmount": 1.43,
  "irrigateNow": true,
  "lastSoilMoisturePct": "38.50"
}
```

(Shortened — the real response has every field shown in `GET /api/crops`.)

### Responses

| Status | Description |
|---|---|
| `200` | Success — returns the crop |
| `400` | `:id` is not a valid UUID |
| `401` | Missing, expired, or invalid Nojo JWT — exchange the OAuth token again |
| `403` | The account is not a farmer account |
| `404` | Crop not found, or it belongs to another user |
| `429` | Too many requests — wait and retry |
| `500` | Unexpected backend error |

---

Deletes one of the user's crops. Its alerts are removed too. Ask the user to
confirm before calling it.

## `DELETE /api/crops/:id`

`:id` is the `cropId` from `GET /api/farms/overview`.

```json
{
  "message": "Crop deleted successfully"
}
```

### Responses

| Status | Description |
|---|---|
| `200` | Success — returns the message above |
| `400` | `:id` is not a valid UUID |
| `401` | Missing, expired, or invalid Nojo JWT — exchange the OAuth token again |
| `403` | The account is not a farmer account |
| `404` | Crop not found, or it belongs to another user |
| `429` | Too many requests — wait and retry |
| `500` | Unexpected backend error |

---

Adds a new crop to one of the user's farms.

## `POST /api/crops`

Body:

```json
{
  "farmId": "a3f1c2d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
  "cropTypeId": "e5f6a7b8-9c0d-1e2f-3a4b-5c6d7e8f9a0b",
  "aliasCropName": "Avocado 1",
  "plantingDate": "2026-03-15",
  "soilTypeId": "c1d2e3f4-a5b6-7c8d-9e0f-1a2b3c4d5e6f",
  "irrigationSystemId": "d4e5f6a7-b8c9-0d1e-2f3a-4b5c6d7e8f9a",
  "landArea": 2.5,
  "landAreaUnit": "feddan"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `farmId` | string (uuid) | Yes | `farmId` from `GET /api/farms/overview` |
| `cropTypeId` | string (uuid) | Yes | `cropId` from `GET /api/crops/options` |
| `aliasCropName` | string | Yes | The farmer's own name for this crop. 2–50 characters: letters, numbers, spaces, `_` and `-` only, with at least one letter. Must not already be used on the same farm (not case-sensitive) |
| `plantingDate` | string | Yes | `YYYY-MM-DD`. Not in the future |
| `soilTypeId` | string (uuid) | Yes | `soilId` from `GET /api/crops/options` |
| `irrigationSystemId` | string (uuid) | Yes | `irrigationId` from `GET /api/crops/options` |
| `landArea` | number | Yes | More than 0. Must be a number, not a string. Between 1 m² and 100,000,000 m² once converted (1 feddan = 4,200 m², 1 ha = 10,000 m²) |
| `landAreaUnit` | string | Yes | `m²`, `feddan`, or `ha` |

Unknown fields are rejected with `400`.

Response — the new crop, same shape as one item of `GET /api/crops`:

```json
{
  "id": "b7e2d1c0-1a2b-3c4d-5e6f-7a8b9c0d1e2f",
  "farmId": "a3f1c2d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
  "cropTypeName": "Avocado",
  "cropTypeAr": "أفوكادو",
  "status": "growing",
  "plantingDate": "2026-03-15",
  "currentStage": "initial"
}
```

(Shortened — the real response has every field shown in `GET /api/crops`.)

### Responses

| Status | Description |
|---|---|
| `201` | Success — returns the new crop |
| `400` | A required field is missing, the name is invalid or already used on the farm, the land area or unit is out of range, the planting date is in the future, the crop type / soil type / irrigation system is unknown, or the farm is not the user's. `message` says which |
| `401` | Missing, expired, or invalid Nojo JWT — exchange the OAuth token again |
| `403` | The account is not a farmer account |
| `429` | Too many requests — wait and retry |
| `500` | Unexpected backend error |

---

Edits one of the user's crops. Send only the fields to change — the rest stay
as they are.

## `PATCH /api/crops/:id`

`:id` is the `cropId` from `GET /api/farms/overview` (the crop's own id). The crop type itself cannot be changed.

Body (any one or more of):

```json
{
  "aliasCropName": "Avocado 1",
  "plantingDate": "2026-03-15",
  "soilTypeId": "c1d2e3f4-a5b6-7c8d-9e0f-1a2b3c4d5e6f",
  "irrigationSystemId": "d4e5f6a7-b8c9-0d1e-2f3a-4b5c6d7e8f9a",
  "landArea": 2.5,
  "landAreaUnit": "feddan"
}
```

| Field | Type | Description |
|---|---|---|
| `aliasCropName` | string | The farmer's own name for this crop. Same rules as when adding: 2–50 characters, letters/numbers/spaces/`_`/`-`, not already used on the farm |
| `plantingDate` | string | `YYYY-MM-DD`. Not in the future |
| `soilTypeId` | string (uuid) | `soilId` from `GET /api/crops/options` |
| `irrigationSystemId` | string (uuid) | `irrigationId` from `GET /api/crops/options` |
| `landArea` | number | More than 0, between 1 m² and 100,000,000 m² once converted. Must be a number, not a string |
| `landAreaUnit` | string | `m²`, `feddan`, or `ha` |

An empty body `{}` is rejected with `400 Invalid body`. Unknown fields are rejected with `400`.

Response — the updated crop, same shape as one item of `GET /api/crops`:

```json
{
  "id": "b7e2d1c0-1a2b-3c4d-5e6f-7a8b9c0d1e2f",
  "farmId": "a3f1c2d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
  "cropTypeName": "Avocado",
  "cropTypeAr": "أفوكادو",
  "aliasCropName": "Avocado 1",
  "plantingDate": "2026-03-15",
  "irrigationSystem": "Drip",
  "landArea": 2.5,
  "landAreaUnit": "feddan"
}
```

(Shortened — the real response has every field shown in `GET /api/crops`.)

### Responses

| Status | Description |
|---|---|
| `200` | Success — returns the updated crop |
| `400` | Invalid body (empty `{}`, unknown field, wrong type), invalid or duplicate name, land area or unit out of range, planting date in the future, a different crop type sent, unknown soil type or irrigation system, or `:id` not a valid UUID. `message` says which |
| `401` | Missing, expired, or invalid Nojo JWT — exchange the OAuth token again |
| `403` | The account is not a farmer account |
| `404` | Crop not found, or it belongs to another user |
| `429` | Too many requests — wait and retry |
| `500` | Unexpected backend error |
