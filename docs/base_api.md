Returns all the user's farms, each with its crops, as ids and names only. Call
it once to find the farm and crop ids the other APIs need.

## `GET /api/farms/overview`

```json
[
  {
    "farmId": "a3f1c2d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
    "farmName": "North Field",
    "crops": [
      {
        "cropId": "b7e2d1c0-1a2b-3c4d-5e6f-7a8b9c0d1e2f",
        "cropName": "Avocado",
        "cropNameAr": "أفوكادو"
      }
    ]
  }
]
```
### Error Responses

| Status | Description |
|---|---|
| `200` | Success — returns the farms list above |
| `401` | Missing, expired, or invalid Nojo JWT — exchange the OAuth token again |
| `403` | The account is not a farmer account |
| `429` | Too many requests — wait and retry |
| `500` | Unexpected backend error |

---

Returns the three lists needed to add a crop — crop types, soil types, and
irrigation systems — as ids and names only. When adding a crop, send `cropId`
as `cropTypeId`, `soilId` as `soilTypeId`, and `irrigationId` as
`irrigationSystemId`.

## `GET /api/crops/options`

```json
{
  "cropTypes": [
    {
      "cropId": "e5f6a7b8-9c0d-1e2f-3a4b-5c6d7e8f9a0b",
      "cropName": "Wheat",
      "cropNameAr": "قمح"
    }
  ],
  "soilTypes": [
    {
      "soilId": "c1d2e3f4-a5b6-7c8d-9e0f-1a2b3c4d5e6f",
      "soilName": "Clay"
    }
  ],
  "irrigationSystems": [
    {
      "irrigationId": "d4e5f6a7-b8c9-0d1e-2f3a-4b5c6d7e8f9a",
      "irrigationName": "Drip"
    }
  ]
}
```
### Error Responses

| Status | Description |
|---|---|
| `200` | Success — returns the lists above |
| `401` | Missing, expired, or invalid Nojo JWT — exchange the OAuth token again |
| `403` | The account is not a farmer account |
| `429` | Too many requests — wait and retry |
| `500` | Unexpected backend error |

---

Returns the two lists needed to add a ledger entry — actions and categories —
as ids and names only, the same choices as the website's add-entry form. When
adding an entry, send `actionId` as `actionId` and `categoryId` as
`actionTypeId`. If the chosen one is named `Other`, put the user's own name
for it in `description` (action) or `descriptionAr` (category).

## `GET /api/farmer-ledger/options`

```json
{
  "actions": [
    {
      "actionId": "7e3f4a5b-6c7d-8e9f-0a1b-2c3d4e5f6a7b",
      "name": "Purchase",
      "nameAr": "شراء"
    }
  ],
  "categories": [
    {
      "categoryId": "8f4a5b6c-7d8e-9f0a-1b2c-3d4e5f6a7b8c",
      "name": "Fertilizer",
      "nameAr": "أسمدة"
    }
  ]
}
```
### Error Responses

| Status | Description |
|---|---|
| `200` | Success — returns the lists above |
| `401` | Missing, expired, or invalid Nojo JWT — exchange the OAuth token again |
| `403` | The account is not a farmer account |
| `429` | Too many requests — wait and retry |
| `500` | Unexpected backend error |
