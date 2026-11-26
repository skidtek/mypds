# Contributing

Thank you for taking the time! Bug reports, connector ideas, translations, documentation fixes and code are all welcome.

## Before you start

- **Found a bug?** Open an issue with what you expected, what happened, your MyPDS version and, if relevant, the device and its firmware version. Logs from `journalctl -u mypds` help a lot. Please remove any addresses or names you'd rather keep private.
- **Security issue?** Don't open an issue. See [SECURITY.md](SECURITY.md).
- **Bigger change or new connector?** Open an issue first, so we can agree on the approach before you spend an evening on it.
- **Own a Synology NAS or a remote Docker host?** Simply trying those experimental connectors and reporting back is one of the most useful things you can do right now.

## Running it locally

You'll need Python 3.13, Node.js 22 and PostgreSQL 17. On macOS:

```bash
brew install python@3.13 node postgresql@17
```

Install the dependencies:

```bash
python3.13 -m venv backend/.venv && backend/.venv/bin/pip install -e "backend[dev]"
```

```bash
npm --prefix frontend ci
```

Start a throwaway PostgreSQL inside the project (in `.dev/`, ignored by git):

```bash
scripts/dev-db.sh start
```

Create `.dev/dev.env` based on `deploy/mypds.env.example`, with:

```
MYPDS_DATABASE_URL="postgresql+asyncpg://mypds@/mypds?host=<repo>/.dev/run&port=5433"
MYPDS_SECRET_KEY_FILE=<repo>/.dev/secret.key
MYPDS_COOKIE_SECURE=false
MYPDS_DEV_MODE=true
PYTHONPATH=<repo>/backend/src
```

Then create the key, the schema and an account:

```bash
backend/.venv/bin/mypds gen-key .dev/secret.key
```

```bash
set -a; . .dev/dev.env; set +a; backend/.venv/bin/mypds migrate && backend/.venv/bin/mypds create-user admin --role admin
```

Optionally, add demo connectors so the cockpit has something to show:

```bash
set -a; . .dev/dev.env; set +a; backend/.venv/bin/mypds demo
```

Run the back end (port 8080, API docs at `/api/docs` in dev mode) and the interface (port 5173, which proxies `/api` to 8080):

```bash
scripts/dev-backend.sh
```

```bash
npm --prefix frontend run dev
```

## Tests and checks

These are the same checks CI runs on every pull request:

```bash
backend/.venv/bin/ruff check backend && backend/.venv/bin/ruff format --check backend
```

```bash
backend/.venv/bin/python -m pytest -q --rootdir backend backend/tests
```

```bash
npm --prefix frontend run typecheck && npm --prefix frontend test
```

```bash
shellcheck -S warning deploy/*.sh deploy/proxmox/*.sh scripts/*.sh
```

Back-end tests use a `mypds_test` database on the dev PostgreSQL, created automatically.

## House rules

- **Read-only toward devices.** A connector never changes anything on a device. Controlling devices will need its own design: confirmation, a separate credential, an audit trail, two-factor authentication.
- **Never present fake data as real.** Demo data is always labeled.
- **No secrets in the repo, in logs or in exports.**
- **Every outbound request goes through `mypds.core.net`.**
- **The start page and the cockpit don't share layout code** ([ADR 0008](docs/adr/0008-two-layout-engines.md)).
- **Interface text goes through `$t()`**, with the French text as the key. Add the English translation to `frontend/src/i18n/en.ts`, and a test will tell you if you forget.
- **A structural decision gets a short record** in `docs/adr/`.
- **One idea per commit.** Write the message in the imperative ("Add Synology fan speed"), in English or French.

The code comments are mostly in French, the original author's language. New code may use English.

## Adding a connector

Look at `backend/src/mypds/connectors/unifi/`. It is the smallest complete example. A connector needs:

1. a configuration model and a secrets model;
2. `test()` and `collect()`;
3. demo data with the same shape as real data;
4. alert rules in `alerts/rules.py`, if it makes sense;
5. tiles in `frontend/src/spaces/cockpit/tiles/`;
6. its setup steps in the connection form and in [docs/connectors.md](docs/connectors.md);
7. tests against recorded responses, with every address and name anonymized.

By contributing, you agree that your contribution is licensed under the [AGPL-3.0-or-later](LICENSE), like the rest of the project.
