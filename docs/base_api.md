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
