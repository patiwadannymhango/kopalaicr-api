# Kopala ICR 2026 — Backend API

A Django REST API for the KCM Kopala Inter Company Relay 2026 registration
site ([kopalaicr](../kopalaicr)). Built from the same pattern as the
sibling Independence Run APIs, extended with a team/relay side those don't
have: companies register a team with a captain login, and the captain later
signs in to a dashboard to manage their roster.

```
kopalaicr-api/
├── backend/                   Django REST API
├── docker-compose.yml         local development
├── docker-compose.prod.yml    production (backend + Postgres + Caddy)
├── Caddyfile                  reverse proxy in front of the backend
└── .github/workflows/deploy.yml
```

## What's here

- **Categories** — 10KM Individual Race, 5KM Fun Race & Walk, and the
  10KM Corporate Relay's per-team entry fee, seeded automatically
  (**placeholder prices** — see "Prices" below). Managed in Django admin
  (`/django-admin/`) or via `python manage.py seed_categories`.
- **Individual registration** — a runner submits their details once (race,
  division for the 10KM race, t-shirt size, emergency contact, etc.); a
  `Participant` + `IndividualRegistration` pair is created
  `PENDING_PAYMENT`.
- **Team (relay) registration** — a company registers a team (name,
  category, captain, an optional starting roster) and gets a login for the
  captain in the same request — no separate sign-up step. The first 8
  runners on the roster are covered by the team's one entry fee; anyone
  added beyond that from the team dashboard owes their own small
  extra-runner fee.
- **Team dashboard login** — the captain signs in with their email +
  password (set at registration) to check the team's payment status and
  add more runners. Authenticated with a simple opaque bearer token (not
  JWT) — see `apps/registrations/auth.py`.
- **Payments** — mobile money (MTN/Airtel/Zamtel), card, or bank transfer,
  via a pluggable gateway, shared by individual registrations, a team's
  base entry fee, and extra-runner fees alike:
  - **`console`** (default) — no credentials needed. Simulates a payment
    settling ~5 seconds after being initiated, so the full
    register → pay → poll → confirmed flow works locally out of the box.
  - **`lipila`** — the real Zambian payment gateway. Switch by setting
    `PAYMENT_GATEWAY=lipila` and filling in the `LIPILA_*` keys in
    `backend/.env` once you have sandbox/production credentials.
- **Notifications** — SMS on registration received / payment confirmed /
  payment failed, one email on confirmation (to the runner, or to the
  captain for a team). SMS defaults to a `console` backend (logs instead
  of sending — see `apps/notifications/sms.py` to wire up Africa's Talking
  later). Email defaults to Django's console backend in dev, real SMTP in
  production.
- **Admin** — Django's built-in admin site at `/django-admin/`: full CRUD
  over categories, registrations, team rosters, payments and the
  notification log. Manually flipping a registration's status to
  `CONFIRMED` there (e.g. reconciling a bank transfer) sends the same
  confirmation email/SMS a real payment would.

  There's deliberately no separate JWT-protected admin REST API here (the
  Kabwe reference this was built from has one, for a future admin
  dashboard SPA) — nothing in the `kopalaicr` frontend needs it yet.
  Django admin covers day-to-day admin work for now; that surface can be
  added later, largely copy-paste from the Kabwe reference, once an admin
  dashboard actually exists to consume it.

## API surface

Public (no auth), consumed directly by the registration site:

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/registrations/individual/categories/` | Individual race categories + prices |
| POST | `/api/v1/registrations/individual/` | Create an individual registration |
| GET | `/api/v1/registrations/team/categories/` | The relay team entry fee |
| POST | `/api/v1/registrations/team/` | Create a team registration + captain login |
| GET | `/api/v1/registrations/team/extra-runner-fee/` | Per-runner fee beyond the free 8 |
| GET | `/api/v1/registrations/lookup/?q=` | "Track your registration" by reference or email (individual or team) |
| POST | `/api/v1/auth/team/login/` | Captain login (email + password → bearer token) |
| POST | `/api/v1/payments/initiate/` | Start mobile money / card / bank transfer payment |
| GET | `/api/v1/payments/<id>/status/` | Poll payment status |
| POST | `/api/v1/payments/webhooks/lipila/` | Lipila's server-to-server callback |
| GET | `/api/v1/payments/bank-details/` | Bank account details for bank transfer |

Captain-authenticated (`Authorization: Bearer <token>` from the login
response above):

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/team/me/` | The logged-in captain's team account + roster |
| POST | `/api/v1/team/me/roster/` | Add one runner to the roster |

## Running locally

Requires Docker Desktop.

```bash
cp backend/.env.example backend/.env   # defaults work as-is for local dev
docker compose up -d --build
```

This starts Postgres and the Django dev server (hot-reload) on
`http://localhost:8004` (port 8004, not 8000 — matches `VITE_API_BASE_URL`
already set in `kopalaicr/.env.example`, and avoids clashing with the
sibling Independence Run APIs on this machine, which use 8001/8002/8003;
change it in `docker-compose.yml` if that's not a concern for you). On
first boot the entrypoint runs migrations and seeds the categories
automatically.

Create an admin login (for `/django-admin/`):

```bash
docker compose exec backend python manage.py createsuperuser
```

Confirm it's up:

```bash
curl http://localhost:8004/api/v1/registrations/individual/categories/
```

Point the frontend at it — in `kopalaicr/.env`:

```
VITE_API_BASE_URL=http://localhost:8004
```

(This is already the default in `kopalaicr/.env.example`, so no frontend
change is actually needed for local dev.)

### Running without Docker

```bash
cd backend
python -m venv .venv && .venv\Scripts\activate   # or source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # set DB_HOST=localhost and point at a local Postgres
python manage.py migrate
python manage.py seed_categories
python manage.py createsuperuser
python manage.py runserver
```

## Prices

Nothing in the `kopalaicr` frontend or design documents the real entry
fees yet, so `seed_categories` seeds clearly-marked **placeholder** prices
(ZMW 150 for the 10KM individual race, ZMW 100 for the 5KM fun run, ZMW
800 for the relay team entry, ZMW 100 for the extra-runner fee). Edit
these in `/django-admin/` → **Categories** before this goes live — the
seed command is create-only, so it will never overwrite a price you've
already changed there.

## Testing payments locally

With the default `PAYMENT_GATEWAY=console`, no real money or credentials
are involved: initiate a payment, then poll `/api/v1/payments/<id>/status/`
— it flips from `PROCESSING` to `SUCCESS` on its own about 5 seconds after
creation (see `apps/payments/gateways/console.py`), which also confirms
the registration/team/roster-runner and sends the confirmation email/SMS
(except for an extra-runner fee, which confirms silently — see
`RosterRunner.confirm_payment` in `apps/registrations/models.py`).

Bank transfer skips the gateway entirely — the frontend doesn't even call
`/payments/initiate/` for it, the registration just stays
`PENDING_PAYMENT` (or the roster runner `paid=False`) until an admin
manually confirms it once the transfer is reconciled against the bank
statement (via `/django-admin/`).

## Switching on real Lipila payments

1. Get sandbox (then production) API keys and a webhook secret from
   Lipila.
2. In `backend/.env`: `PAYMENT_GATEWAY=lipila`, `LIPILA_ENVIRONMENT=sandbox`,
   `LIPILA_SANDBOX_API_KEY=...`, `LIPILA_WEBHOOK_SECRET=...`.
3. Point Lipila's webhook URL at
   `http://<your-address>/api/v1/payments/webhooks/lipila/`. Lipila calls
   this from the internet, so it only works once the backend is reachable
   from outside — a laptop on `localhost` never receives webhooks.
   Registration, the payment status poll, and payment *initiation* all
   still work locally either way; only the webhook *confirmation* needs a
   public address. For local webhook testing, put a tunnel (ngrok,
   cloudflared) in front of the backend and use the tunnel's URL here.
4. Restart the backend so the new env vars take effect.

Note: Lipila's docs describe two API generations (a legacy `x-api-key` /
`/api/v1/collections/...` surface and a newer Bearer-token surface). The
client in `apps/payments/gateways/lipila/client.py` is built against the
older style — confirm against your Lipila merchant dashboard which one you
were issued, and adjust if needed.

## Deploying

This repo deploys the same way regardless of address — a laptop, a LAN IP,
or a cloud server's public IP, all work identically since nothing here
depends on a domain existing yet.

**1. Push to GitHub, then on the server:**

```bash
git clone <this-repo-url>
cd kopalaicr-api
cp .env.prod.example .env.prod          # set DB password; leave HTTP_PORT=80
cp backend/.env.example backend/.env    # set DEBUG=False, a real SECRET_KEY,
                                          # DJANGO_SETTINGS_MODULE=config.settings.production,
                                          # DB credentials matching .env.prod,
                                          # and ALLOWED_HOSTS listing every address
                                          # you'll reach the API by
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
```

Confirm it's up: `curl http://<server-address>/api/v1/registrations/individual/categories/`.

**2. HTTPS (needed once a real frontend deploy calls this over the
internet — browsers block an HTTPS page from calling plain `http://`).**
No domain purchase required — with a fixed IP, `<ip-with-dashes>.sslip.io`
is a real, publicly resolvable hostname Caddy can fetch a genuine Let's
Encrypt cert for automatically:

```
# in .env.prod
SITE_ADDRESS=https://15-240-170-199.sslip.io
```

(swap in a real domain later by pointing an A record at the same IP and
changing this one line). Then:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --force-recreate proxy
```

Add the hostname to `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` in
`backend/.env` too.

**3. Point the frontend at it** — set `VITE_API_BASE_URL` to the server's
address in whatever host serves the frontend, and add that frontend's real
domain to `CORS_ALLOWED_ORIGINS` in `backend/.env`, then:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --force-recreate backend
```

**4. Automatic redeploy on push** — `.github/workflows/deploy.yml` SSHes
into the server and rebuilds on every push to `main`. Add these repo
secrets (Settings → Secrets and variables → Actions):

| Secret | Value |
|---|---|
| `SERVER_HOST` | server's public IP or hostname |
| `SERVER_SSH_USER` | SSH user (e.g. `ubuntu`) |
| `SERVER_SSH_PRIVATE_KEY` | a dedicated deploy key's private key (not your personal one) |
| `SERVER_PROJECT_PATH` | absolute path to the repo on the server |

**5. Database backups** — `infra/backup-db.sh` / `infra/restore-db.sh`
handle daily dumps (local + optional offsite S3). One-time setup and cron
wiring in [`infra/README.md`](infra/README.md) — set this up before there
are real registrations to lose.

I'll help fill in the specific server/domain/Lipila details when you're
ready to deploy — just share them when you get there.
