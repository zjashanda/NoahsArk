# NoahsArk Control Plane (Phase 2 Vertical Slice)

Status: **SCAFFOLD / NOT FROZEN / NOT PRODUCTION**

This is the W0 scaffold for the NoahsArk control plane. It currently exposes
health endpoints only. PostgreSQL, migrations, domain models, read models and
write intents are implemented in later waves of
`.omo/plans/backend-integration-task.md`.

## Run

```bash
cd /home/bszheng/NoahsArk
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
pip install -e 'apps/control_plane[dev]'
uvicorn noahsark.main:app --host 0.0.0.0 --port 8000 --reload
```

Health:

```bash
curl -s http://127.0.0.1:8000/healthz | jq
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/readyz
```

`/readyz` returns 503 until `DATABASE_URL` is configured.

## Test

```bash
cd apps/control_plane
pytest -q
```
