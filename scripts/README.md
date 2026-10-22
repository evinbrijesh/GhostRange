# Scripts

Developer workflow scripts.

| Script | Purpose |
|---|---|
| `dev.sh` | Start backend + frontend for local development |
| `seed.sh` | Create or refresh the fixed demo run (`run_demo_seed_0001`) — idempotent |
| `reset.sh` | Clear all demo state — idempotent |

Storage location is controlled by `DATABASE_URL` in `.env`
(default `sqlite:///./ghostrange.db`, resolved against the repository root).
