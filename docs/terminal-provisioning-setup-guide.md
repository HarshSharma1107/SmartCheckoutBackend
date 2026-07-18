# Setup & Testing Guide — Multi-Brand + Terminal Provisioning

This is the step-by-step walkthrough for what was just built: multi-brand
store data (`docs/multi-brand-plan.md`) and device/terminal provisioning
with pairing codes (`docs/terminal-provisioning-plan.md`). No admin
dashboard UI exists yet — every admin action below is a plain HTTP call
(curl, Postman, or the interactive docs at `/docs`).

## What changed, in one paragraph

Every store now belongs to a `Brand`. Devices (phones/tablets) register
themselves, sit `UNASSIGNED` showing a 6-digit pairing code, and an admin
assigns that code + a store to give the device a `Terminal`. Once assigned,
the app never shows a store picker again — it goes straight to the scanner.
Nothing about scanning, cart, checkout, or receipts changed; only how a
device learns which store it belongs to.

## 0. Before you deploy

Set these environment variables on Render (Dashboard → your service →
Environment). None of these exist yet and the code has safe-but-insecure
defaults, so don't skip this:

| Variable | Value | Why |
|---|---|---|
| `JWT_SECRET` | a long random string (e.g. `openssl rand -hex 32`) | Signs every device/admin token. The code falls back to a published placeholder value if unset — anyone could forge tokens. |
| `DEFAULT_BRAND_CODE` | e.g. `DMART` (optional) | Name for the auto-created brand your existing stores get backfilled into. Defaults to `DEFAULT` if unset. |
| `DEFAULT_BRAND_NAME` | e.g. `D-Mart` (optional) | Display name to match. |

You don't need to run any migration command — the app patches its own
schema on startup (see `backend/main.py`'s `ensure_default_brand_and_backfill_stores`,
the same mechanism already used for enum types). Just deploy and check logs
for errors on first boot.

## 1. Deploy and sanity-check

Push this branch, let Render redeploy, then:

```bash
curl https://smartcheckoutbackend.onrender.com/health
curl https://smartcheckoutbackend.onrender.com/api/v1/brands
```

The brands call should return your one auto-created default brand — this
confirms the startup backfill ran and your existing stores didn't break.

```bash
curl https://smartcheckoutbackend.onrender.com/api/v1/stores
```

Should return the same stores as before, now with `brand_id`/`brand_name`
fields added. The existing app (if anyone has an old APK installed) keeps
working unchanged against this endpoint.

## 2. Create your first admin (one-time)

This only works while zero admins exist — it's a one-time door, not a
signup form:

```bash
curl -X POST https://smartcheckoutbackend.onrender.com/api/v1/admin/auth/bootstrap \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"a-strong-password-here","full_name":"Your Name"}'
```

Response includes an `access_token`. Save it — every admin call below needs
it as `Authorization: Bearer <token>`. It expires in 1 hour; re-login with
`POST /api/v1/admin/auth/login` (same email/password) to get a new one.

## 3. Create a brand and store (skip if using the default brand)

If you want a real brand instead of the auto-created `DEFAULT` one:

```bash
TOKEN="paste access_token here"

curl -X POST https://smartcheckoutbackend.onrender.com/api/v1/admin/brands \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"code":"DMART","name":"D-Mart"}'
# note the brand_id returned

curl -X POST https://smartcheckoutbackend.onrender.com/api/v1/admin/stores \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"brand_id":"<brand_id from above>","code":"AND01","name":"D-Mart Andheri","city":"Mumbai"}'
# note the store_id returned
```

List stores any time with:

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "https://smartcheckoutbackend.onrender.com/api/v1/admin/stores"
```

## 4. Build and install the app on a device

```bash
cd frontend
npm install         # pulls in expo-device + expo-secure-store just added
npx expo start       # quick test via Expo Go, or:
eas build -p android --profile preview   # real APK
```

Both `expo-device` and `expo-secure-store` work fine in Expo Go, so you can
iterate with `expo start` before building a real APK. Make sure
`frontend/.env`'s `EXPO_PUBLIC_API_URL` points at your deployed backend.

**The old `EXPO_PUBLIC_LOCKED_STORE_ID` env var and per-store APK builds are
no longer needed** — one APK now works for every store; the store is
resolved per-device at runtime through this provisioning flow, not baked in
at build time.

Open the app. You should land on a screen showing a large 6-digit code:
"Give this code to your admin to assign a store." That confirms
registration worked — the device just called `POST /api/v1/devices/register`
and got back `status: UNASSIGNED` with a `pairing_code`.

## 5. Assign the device to a store

Find it in the unassigned list:

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "https://smartcheckoutbackend.onrender.com/api/v1/admin/devices?status=unassigned"
```

Note its `device_id`. Read the pairing code off the phone's screen, then:

```bash
curl -X POST https://smartcheckoutbackend.onrender.com/api/v1/admin/devices/<device_id>/assign-store \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"store_id":"<store_id>","pairing_code":"<the 6 digits on screen>","notes":"Front counter"}'
```

Within ~20 seconds (the app's poll interval) the phone should flip from the
pairing screen straight to name/phone entry and then the scanner — no store
picker anywhere. If you don't want to wait, force it by killing and
reopening the app.

## 6. Confirm store isolation

Repeat steps 4-5 on a second device, assigning it to a *different* store.
Confirm:

- Each device only ever operates against the store it was assigned to
  (check the receipt after a test checkout — store should match).
- Neither device shows the other's store, or any picker at all.

## 7. Check device status / fleet view (until the dashboard exists)

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "https://smartcheckoutbackend.onrender.com/api/v1/admin/devices?status=assigned"
curl -H "Authorization: Bearer $TOKEN" \
  "https://smartcheckoutbackend.onrender.com/api/v1/admin/devices?status=offline"
```

`offline` means no heartbeat for 5+ minutes (the app heartbeats every 30s
while foregrounded and open).

## 8. Test the replacement flow (dead phone / Pi scenario)

```bash
# 1. Disable the "dead" device
curl -X POST https://smartcheckoutbackend.onrender.com/api/v1/admin/devices/<old_device_id>/deactivate \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"reason":"Device broken, replacing"}'

# 2. Install the app fresh on the replacement phone (step 4) - it registers
#    with its own new device_id and shows its own pairing code.

# 3. Assign the NEW device to the SAME store
curl -X POST https://smartcheckoutbackend.onrender.com/api/v1/admin/devices/<new_device_id>/assign-store \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"store_id":"<same store_id as before>","pairing_code":"<new device code>"}'
```

The response's `terminal_code` should be the **same terminal** the old
device held (e.g. `SC-000001`) — confirming order history for that till is
preserved, only the physical hardware changed.

## 9. Adding more admins later

Once you have your first admin, don't use `/bootstrap` again (it's now
locked - returns 409). Create additional admins as that admin:

```bash
curl -X POST https://smartcheckoutbackend.onrender.com/api/v1/admin/auth/users \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"email":"manager@dmart.example","password":"...", "brand_id":"<brand_id, omit for another SUPER_ADMIN>"}'
```

## What's intentionally not built yet

- **Admin dashboard UI** — you said you'll build this later; every action
  above is designed to be a thin wrapper the dashboard can call directly,
  no backend changes needed when it's built.
- **Raspberry Pi / mTLS certificate path** — the original enterprise
  scaffolding for cert-based Pi devices was unused/unapplied dead code; this
  pass only builds the Android JWT-based path, per your actual current
  hardware. Revisit if you add bare-metal Pi kiosks later.
- **Rate limiting, MQTT push, WhatsApp invoices** — unrelated to this
  feature, unchanged from before.

## If something looks wrong

- **`/api/v1/brands` returns empty after deploy**: check Render logs for
  errors during startup — the backfill function running against your
  existing `stores` table is the one genuinely delicate step here.
- **Device stuck showing a pairing code after you assigned it**: the app
  polls every 20s; also check the code hasn't expired (15 min TTL) — if it
  has, force-close and reopen the app to get a fresh one, then retry assign.
- **`403 Pairing code does not match`**: someone read the code while it
  was mid-refresh, or it already expired. Get a fresh one from the device.
- **A previously-working legacy APK stops scanning**: it shouldn't — legacy
  `/api/v1/products`, `/api/v1/orders`, `/api/v1/stores` are unchanged in
  shape (only additive fields). If it does break, that's a regression worth
  reporting, not expected behavior.
