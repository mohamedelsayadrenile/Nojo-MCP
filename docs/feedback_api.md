Sends the user's feedback to the Nojo team: a problem they found, a
suggestion, or anything else they want to tell Nojo. The Nojo team gets it
by email. Confirm the text with the user before sending it.

## `POST /api/feedback`

Body:

```json
{
  "message": "The irrigation page does not show my second farm."
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `message` | string | Yes | The feedback text, 2–1200 characters (spaces at the start and end are not counted) |

Unknown fields are rejected with `400`.

Response — the saved feedback:

```json
{
  "id": "e1f2a3b4-c5d6-7e8f-9a0b-1c2d3e4f5a6b",
  "userId": "81b49124-d509-4607-af93-fae0df6cb0c8",
  "message": "The irrigation page does not show my second farm.",
  "createdAt": "2026-09-28T10:15:00.000Z"
}
```

### Responses

| Status | Description |
|---|---|
| `201` | Success — returns the saved feedback |
| `400` | `message` is missing, shorter than 2 or longer than 1200 characters, or an unknown field was sent. `message` says which |
| `401` | Missing, expired, or invalid Nojo JWT — exchange the OAuth token again |
| `403` | The account is not a farmer account |
| `429` | Too many requests — wait and retry |
| `500` | Unexpected backend error |
