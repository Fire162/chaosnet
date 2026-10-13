# ChaosNet

An interactive laboratory for building, running, observing and deliberately
breaking real distributed systems and networks.

> **Status:** early development (Sprint 1). Nothing here is usable yet. See the
> [project board](https://github.com/users/kesamot11/projects/2) and
> [milestones](https://github.com/kesamot11/chaosnet/milestones).

ChaosNet measures real system behaviour. It never fabricates results.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Architecture decisions](docs/DECISIONS.md)
- [Learning log](docs/LEARNING.md)

## Development setup

Requirements:

- [uv](https://docs.astral.sh/uv/) (it installs the right Python, 3.14, for you)
- Docker with Compose v2+ (developed on Docker Desktop for Mac, Apple Silicon)
- `make`

```bash
git clone https://github.com/kesamot11/chaosnet.git
cd chaosnet/backend
uv sync          # creates .venv with Python 3.14 and dev tools from uv.lock
cd ..
make check       # lint, format check, type check, tests
```

`make fmt` applies formatting and safe lint fixes.
