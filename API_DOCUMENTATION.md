
Below is **Postman-style API documentation** (exactly how Postman presents it: endpoint-wise, concise, request/response focused).
You can **copy-paste this directly into Postman Documentation** or share it as a public API doc.

---

# Smart Free Time Utilizer – semi Documentation (Postman Style)


### ✅ Why You Do NOT Need Postman Tests

You already have two stronger test layers:

1️⃣ Frontend Integration Tests (Vitest + RTL(React Testing Library))
*  Tests real user flows
*  Tests routing & auth logic
*  Tests UI behavior
2️⃣ Backend API Tests (unittest + Flask test client)
*  Tests every REST endpoint
*  Tests success + failure cases
*  Mocks DB and AI services
Fully automated
👉 Postman tests would only duplicate this.

### RTL:
You are using RTL.
You are doing frontend integration testing.
You are testing real user flows.


## UNIT TESTS:
units are all that done for backend for this project
### Backend Unit Tests

These test one API endpoint in isolation, with everything mocked.
```
| Test                         | Type | Why             |
| ---------------------------- | ---- | --------------- |
| `test_health_check`          | Unit | No dependencies |
| `test_home`                  | Unit | Static response |
| `test_signup_success`        | Unit | DB mocked       |
| `test_signup_user_exists`    | Unit | DB mocked       |
| `test_signup_missing_fields` | Unit | Validation only |
| `test_signin_success`        | Unit | DB mocked       |
| `test_signin_failure`        | Unit | DB mocked       |
| `test_get_history`           | Unit | DB mocked       |
| `test_delete_history`        | Unit | DB mocked       |
```
## INTEGRATION TESTS:
Most of these are in frontend and excatly oe in backend
### Frontend Tests (Vitest + RTL)
❌ NOT Unit Tests
Even though components are mocked, these are NOT pure unit tests.
Why?
You are testing routing
You are testing multiple components together
You are testing navigation side-effects
```
| Test                       | Type        | Why                 |
| -------------------------- | ----------- | ------------------- |
| Redirect to `/signin`      | Integration | Router + App state  |
| Signin → Signup navigation | Integration | Multiple components |
| Login → TimeUtilizer       | Integration | State + Router      |
| LocalStorage persistence   | Integration | Browser API + App   |
```
### Backend Integration Test (Borderline)
```
| Test                        | Type        | Why                                        |
| --------------------------- | ----------- | ------------------------------------------ |
| `test_process_data_success` | Integration | Combines validation + AI logic + DB writes |
```
