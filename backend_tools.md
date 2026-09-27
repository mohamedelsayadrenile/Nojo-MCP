# Nojo MCP Test APIs (Test Server)

**Base URL:** `https://41.38.196.107.nip.io/api`  
**Authorization Header:** `Authorization: Bearer $NOJO`

## APIs

### 1. Get Current User

`GET /auth/me`

Returns the profile of the token owner:

- `id`
- `name`
- `phone`
- `role`

Use this to prove that the exchanged JWT works.

> **Validation:** `id` must equal the `sub` claim from API 5.

---

### 2. List Farms

`GET /farms`

Lists all farms owned by the farmer.

- **Parameters:** None
- **Response:** Array of farms
- **Array length:** Number of farms owned by the farmer

---

### 3. List Crops

`GET /crops`

Lists all crops across all of the farmer's farms.

- **Parameters:** None

---

### 4. List Alerts

`GET /alerts`

Lists active alerts across all of the farmer's farms.

- **Parameters:** None
- **Default range:** Today + 3 days ahead

---

### 5. List IoT Stations

`GET /stations`

Lists the farmer's IoT station devices.

- **Parameters:** None