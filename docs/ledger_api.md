Returns the farmer's ledger for all their farms: every money entry they
recorded in Nojo (what they spent or earned, on what, for which crop, and
when), newest first, with each farm's total.

## `GET /api/farmer-ledger/overview`

```json
[
  {
    "farmId": "a3f1c2d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
    "farmName": "North Farm",
    "farmType": "Open Field",
    "currency": "EGP",
    "totalAmount": 1850.5,
    "entries": [
      {
        "entryId": "f1e2d3c4-b5a6-9788-6950-4a3b2c1d0e9f",
        "date": "2026-09-22T12:10:00.000Z",
        "action": "Purchase",
        "actionAr": "شراء",
        "category": "Fertilizer",
        "categoryAr": "أسمدة",
        "amount": 1250.5,
        "cropId": "b7e2d1c0-1a2b-3c4d-5e6f-7a8b9c0d1e2f",
        "cropName": "Avocado",
        "cropNameAr": "أفوكادو",
        "aliasCropName": "Avocado 1",
        "description": "NPK 20-20-20, 5 bags",
        "descriptionAr": null,
        "notes": null
      },
      {
        "entryId": "0a9b8c7d-6e5f-4a3b-2c1d-0e9f8a7b6c5d",
        "date": "2026-09-15T08:00:00.000Z",
        "action": "Expense",
        "actionAr": "مصروف",
        "category": "Labor",
        "categoryAr": "عمالة",
        "amount": 600,
        "cropId": null,
        "cropName": null,
        "cropNameAr": null,
        "aliasCropName": null,
        "description": "Weeding, 3 workers",
        "descriptionAr": null,
        "notes": null
      }
    ]
  }
]
```

| Field | Unit | Description |
|---|---|---|
| `currency` | — | The currency of this farm's amounts, from where the farm is (for example `EGP` in Egypt, `SAR` in Saudi Arabia). `null` if Nojo cannot tell |
| `totalAmount` | `currency` | All the farm's entries added together |
| `date` | — | When the entry happened (ISO date and time) |
| `action` / `actionAr` | — | What kind of entry, for example `Expense`, `Payment`, `Purchase`, `Harvest` |
| `category` / `categoryAr` | — | What it was for, for example `Fertilizer`, `Seeds`, `Labor`, `Water`, `Fuel`, `Electricity`, `Pesticides`, `Harvest` |
| `amount` | `currency` | The money of this entry |
| `cropId` | — | The crop the entry is for. `null` = for the whole farm, not one crop (then the crop names are `null` too) |
| `description` / `descriptionAr` | — | What the farmer wrote about it |
| `notes` | — | Extra notes the farmer wrote |

Amounts are in the farm's `currency`, the same one the website shows for that
farm. Any text field can be `null`
when the farmer left it empty. `entries` is `[]`
when the farm has no ledger entries yet.

**One farm only:** add `?farmId=` (the `farmId` from `GET /api/farms/overview`):
`GET /api/farmer-ledger/overview?farmId=a3f1c2d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d`.
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

Adds a new entry to a farm's ledger. Confirm the details with the user before
sending it.

## `POST /api/farmer-ledger`

Body:

```json
{
  "farmId": "a3f1c2d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
  "cropId": "b7e2d1c0-1a2b-3c4d-5e6f-7a8b9c0d1e2f",
  "actionId": "7e3f4a5b-6c7d-8e9f-0a1b-2c3d4e5f6a7b",
  "actionTypeId": "8f4a5b6c-7d8e-9f0a-1b2c-3d4e5f6a7b8c",
  "amount": 1250.5,
  "entryDate": "2026-09-22T12:10:00.000Z"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `farmId` | string (uuid) | Yes | `farmId` from `GET /api/farms/overview` |
| `cropId` | string (uuid) | Yes | `cropId` from `GET /api/farms/overview`, a crop on that same farm whose cycle has not ended |
| `actionId` | string (uuid) | Yes | `actionId` from `GET /api/farmer-ledger/options` (in base.md) |
| `actionTypeId` | string (uuid) | Yes | `categoryId` from `GET /api/farmer-ledger/options` (in base.md) |
| `amount` | number | Yes | The money, in the farm's `currency` (see `GET /api/farmer-ledger/overview`). More than 0, at most 9,999,999,999. A number, not a string |
| `entryDate` | string | No | When it happened, ISO date and time. Not in the future. Now when left out |
| `description` | string | Only for `Other` | When the action is `Other`: what the action was, in the user's words (for example `"Hand weeding"`), at most 100 characters |
| `descriptionAr` | string | Only for `Other` | When the category is `Other`: what it was for, in the user's words, at most 100 characters |

Unknown fields are rejected with `400`.

Same rules as the website: the farm needs at least one crop, and entries can
only be added to a crop still in its cycle. Once a crop's cycle has ended
(harvested), or the whole farm's cycle has ended (or every crop on the farm is harvested), no new entries can be added
to it — tell the user, do not retry.

A harvest cannot be added as an entry: on the website a harvest is recorded by
ending the crop's cycle. If the user wants to record a harvest, send them to
the ledger page on the website.

Response — the saved entry:

```json
{
  "id": "f1e2d3c4-b5a6-9788-6950-4a3b2c1d0e9f",
  "farmId": "a3f1c2d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
  "cropId": "b7e2d1c0-1a2b-3c4d-5e6f-7a8b9c0d1e2f",
  "actionId": "7e3f4a5b-6c7d-8e9f-0a1b-2c3d4e5f6a7b",
  "actionTypeId": "8f4a5b6c-7d8e-9f0a-1b2c-3d4e5f6a7b8c",
  "amount": "1250.5",
  "entryDate": "2026-09-22T12:10:00.000Z",
  "description": null,
  "descriptionAr": null,
  "notes": null,
  "createdAt": "2026-09-28T10:15:00.000Z"
}
```

(Shortened. `amount` comes back as text here — read it as a number.)

### Responses

| Status | Description |
|---|---|
| `201` | Success — returns the saved entry |
| `400` | A required field is missing or has the wrong type, `amount` is negative, `entryDate` is in the future, the crop is not on that farm, the crop's or the farm's cycle has ended, `Other` was chosen without its name or with a name over 100 characters, `amount` is over 9,999,999,999, a harvest was sent, or an unknown field was sent. `message` says which |
| `401` | Missing, expired, or invalid Nojo JWT — exchange the OAuth token again |
| `403` | The account is not a farmer account, or the farm belongs to another user |
| `404` | Farm (or a farm the user removed), crop, action or category not found |
| `429` | Too many requests — wait and retry |
| `500` | Unexpected backend error |

---

Edits one of the farm's ledger entries. Send only the fields to change — the
rest stay as they are. Confirm the change with the user before sending it.

## `PUT /api/farmer-ledger/:id`

`:id` is the `entryId` from `GET /api/farmer-ledger/overview`.

Body (any one or more of):

```json
{
  "cropId": "b7e2d1c0-1a2b-3c4d-5e6f-7a8b9c0d1e2f",
  "actionId": "7e3f4a5b-6c7d-8e9f-0a1b-2c3d4e5f6a7b",
  "actionTypeId": "8f4a5b6c-7d8e-9f0a-1b2c-3d4e5f6a7b8c",
  "amount": 1500,
  "entryDate": "2026-09-21T09:00:00.000Z"
}
```

| Field | Type | Description |
|---|---|---|
| `cropId` | string (uuid) or `null` | Move the entry to another crop on the same farm whose cycle has not ended, or `null` for the whole farm |
| `actionId` | string (uuid) | `actionId` from `GET /api/farmer-ledger/options` (in base.md) |
| `actionTypeId` | string (uuid) | `categoryId` from `GET /api/farmer-ledger/options` (in base.md) |
| `amount` | number | The money, in the farm's `currency`. More than 0, at most 9,999,999,999. A number, not a string |
| `entryDate` | string | When it happened, ISO date and time. Not in the future |
| `description` | string | When the action is `Other`: what the action was, in the user's words, at most 100 characters |
| `descriptionAr` | string | When the category is `Other`: what it was for, in the user's words, at most 100 characters |

An empty body `{}` is rejected with `400 Invalid body`. Unknown fields are
rejected with `400`.

Same rules as the website: an entry cannot be edited once its crop's cycle has
ended (harvested) or the whole farm's cycle has ended (or every crop on the farm is harvested) — tell the user, do not
retry.

Response — the updated entry, same fields as when adding one:

```json
{
  "id": "f1e2d3c4-b5a6-9788-6950-4a3b2c1d0e9f",
  "farmId": "a3f1c2d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
  "cropId": "b7e2d1c0-1a2b-3c4d-5e6f-7a8b9c0d1e2f",
  "actionId": "7e3f4a5b-6c7d-8e9f-0a1b-2c3d4e5f6a7b",
  "actionTypeId": "8f4a5b6c-7d8e-9f0a-1b2c-3d4e5f6a7b8c",
  "amount": "1500",
  "entryDate": "2026-09-21T09:00:00.000Z"
}
```

(Shortened. `amount` comes back as text here — read it as a number.)

### Responses

| Status | Description |
|---|---|
| `200` | Success — returns the updated entry |
| `400` | Empty body, wrong field type, unknown field, `amount` negative, `entryDate` in the future, the entry's crop or the farm's cycle has ended, the new crop's cycle has ended or it is on another farm, `Other` chosen without its name or with a name over 100 characters, `amount` over 9,999,999,999, a switch to a harvest action or category, or `:id` not a valid UUID. `message` says which |
| `401` | Missing, expired, or invalid Nojo JWT — exchange the OAuth token again |
| `403` | The account is not a farmer account, or the entry belongs to another user |
| `404` | Entry, crop, action or category not found |
| `429` | Too many requests — wait and retry |
| `500` | Unexpected backend error |

---

Deletes one of the farm's ledger entries. Ask the user to confirm before
calling it.

## `DELETE /api/farmer-ledger/:id`

`:id` is the `entryId` from `GET /api/farmer-ledger/overview`.

```json
{
  "message": "Ledger entry deleted successfully"
}
```

Same rules as the website: an entry cannot be deleted once its crop's cycle
has ended (harvested) or the whole farm's cycle has ended (or every crop on the farm is harvested) — tell the user, do
not retry.

### Responses

| Status | Description |
|---|---|
| `200` | Success — returns the message above |
| `400` | The entry's crop or the farm's cycle has ended, or `:id` is not a valid UUID. `message` says which |
| `401` | Missing, expired, or invalid Nojo JWT — exchange the OAuth token again |
| `403` | The account is not a farmer account, or the entry belongs to another user |
| `404` | Entry not found, or already deleted |
| `429` | Too many requests — wait and retry |
| `500` | Unexpected backend error |
