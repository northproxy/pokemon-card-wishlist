# Local PostgreSQL Development Setup on Windows

## Document status

- Project: `Pokemon Card Wishlist`
- Area: Local development environment
- Milestones supported: `M2 — Infrastructure`, `M3 — Data model`
- Status: `Implemented and validated locally`
- Validation date: `2026-07-28`
- Target environment: Windows with WSL 2 and Docker Desktop
- Production relevance: This setup supports local development only. It does not validate the future Raspberry Pi deployment, backup strategy, restore procedure, or production security controls.

## Purpose

This document records the local Windows setup used to develop and validate the PostgreSQL schema and database migrations for `Pokemon Card Wishlist`.

The setup intentionally avoids installing PostgreSQL Server or `dbmate` directly as project dependencies in Windows. PostgreSQL runs in Docker, and `dbmate` runs as an ephemeral Docker Compose service.

This approach provides:

- a reproducible local database environment;
- isolation from the host operating system;
- versioned database migrations;
- a clean path toward later Docker-based deployment;
- portfolio evidence that the environment was not only configured, but also tested.

## Validated components

The following components were installed and validated:

- WSL 2;
- Ubuntu 24.04 LTS under WSL 2;
- Docker Desktop with the WSL 2 backend;
- Docker CLI access from Windows PowerShell;
- Docker CLI access from Ubuntu under WSL;
- DBeaver Community;
- PostgreSQL 17 in a Docker container;
- DBeaver connection to the containerized PostgreSQL database;
- `dbmate` 2.34.1 through Docker;
- migration creation, apply, status, and rollback workflows.

Observed versions during validation:

- Docker Desktop: `4.84.0`;
- Docker Engine: `29.6.2`;
- PostgreSQL: `17.10`;
- `dbmate`: `2.34.1`;
- Ubuntu: `24.04 LTS`.

## Architecture

```text
Windows
├── Docker Desktop
│   └── WSL 2 backend
├── Ubuntu 24.04 LTS under WSL 2
├── DBeaver Community
└── Project repository
    ├── compose.yaml
    ├── .env                  # local secret values, ignored by Git
    ├── .env.example          # safe template, tracked by Git
    └── db/
        ├── migrations/
        └── schema.sql
```

Runtime database path:

```text
DBeaver or local tools
        │
        ▼
127.0.0.1:5432
        │
        ▼
PostgreSQL 17 Docker container
        │
        ▼
Docker named volume: postgres_data
```

`dbmate` does not connect through `localhost`. Inside the Docker Compose network it connects to the PostgreSQL service by the service name `postgres`.

## WSL 2 setup

WSL 2 was installed with:

```powershell
wsl --install
```

After restarting Windows, the default WSL version was verified:

```powershell
wsl --status
```

Ubuntu 24.04 LTS was installed explicitly:

```powershell
wsl --install -d Ubuntu-24.04
```

The installed distribution was verified:

```powershell
wsl --list --verbose
```

Validated result:

```text
NAME            STATE     VERSION
Ubuntu-24.04    Running   2
```

## Docker Desktop setup

Docker Desktop was installed with the WSL 2 backend enabled.

WSL integration was enabled for `Ubuntu-24.04` in:

```text
Docker Desktop → Settings → Resources → WSL Integration
```

Docker was validated from Windows PowerShell:

```powershell
docker version
```

Docker was also validated from Ubuntu under WSL:

```bash
docker version
```

A test container confirmed that image pulling and container execution worked:

```powershell
docker run --rm hello-world
```

Validated result:

```text
Hello from Docker!
```

## DBeaver Community setup

DBeaver Community was installed as the local database client.

It is used only as a client and does not run PostgreSQL itself.

The validated connection settings are:

```text
Host: localhost
Port: 5432
Database: pokemon_wishlist
Username: pokemon_app
Password: value from the local .env file
```

The PostgreSQL JDBC driver was downloaded through DBeaver when prompted.

The connection test succeeded against PostgreSQL `17.10`.

## Local environment variables

The local `.env` file contains the real development credentials:

```dotenv
POSTGRES_DB=pokemon_wishlist
POSTGRES_USER=pokemon_app
POSTGRES_PASSWORD=<local-random-password>
```

The real `.env` file must never be committed.

The repository `.gitignore` contains:

```gitignore
.env
.env.*
!.env.example
```

Git ignore behavior was validated with:

```powershell
git check-ignore -v .env
```

The safe tracked template is `.env.example`:

```dotenv
POSTGRES_DB=pokemon_wishlist
POSTGRES_USER=pokemon_app
POSTGRES_PASSWORD=replace_with_local_password
```

### Encoding requirement

The `.env` file must be saved as UTF-8 without BOM.

An earlier PowerShell-generated file included a UTF-8 BOM. `dbmate` reported:

```text
unexpected character in variable name
```

The issue was fixed by saving the file without BOM. VS Code can be used to create and save the file directly as UTF-8.

## Docker Compose configuration

The local `compose.yaml` contains two services:

- `postgres` — the persistent local database;
- `dbmate` — an on-demand migration tool enabled through the `tools` profile.

```yaml
services:
  postgres:
    image: postgres:17
    container_name: pokemon-wishlist-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports:
      - "127.0.0.1:5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test:
        - CMD-SHELL
        - pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}
      interval: 5s
      timeout: 5s
      retries: 10

  dbmate:
    image: ghcr.io/amacneil/dbmate:2
    profiles:
      - tools
    environment:
      DATABASE_URL: postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}?sslmode=disable
    volumes:
      - .:/workspace
    working_dir: /workspace
    depends_on:
      postgres:
        condition: service_healthy

volumes:
  postgres_data:
```

### Security boundary

The host port is bound to:

```text
127.0.0.1:5432
```

It is not bound to all network interfaces. This keeps the local development database inaccessible from other devices on the network unless the configuration is deliberately changed.

## PostgreSQL lifecycle commands

Run all commands from the repository root.

Start PostgreSQL:

```powershell
docker compose up -d postgres
```

Check status:

```powershell
docker compose ps
```

Validated state:

```text
pokemon-wishlist-postgres   postgres:17   Up (...) (healthy)   127.0.0.1:5432->5432/tcp
```

View logs:

```powershell
docker compose logs postgres
```

Stop the project containers without deleting data:

```powershell
docker compose stop
```

Start stopped containers:

```powershell
docker compose start
```

Stop and remove containers and the network while preserving the named volume:

```powershell
docker compose down
```

### Destructive command

The following command also deletes the PostgreSQL named volume and all local database data:

```powershell
docker compose down -v
```

Do not run it unless a complete local database reset is intentional.

## PostgreSQL validation

The database was validated from inside the container:

```powershell
docker compose exec postgres psql `
  -U pokemon_app `
  -d pokemon_wishlist `
  -c "SELECT current_database(), current_user, version();"
```

Validated result:

```text
current_database: pokemon_wishlist
current_user: pokemon_app
version: PostgreSQL 17.10
```

## Migration directory

The migration directory is:

```text
db/migrations/
```

`dbmate` also writes the current schema snapshot to:

```text
db/schema.sql
```

## dbmate workflow through Docker Compose

`dbmate` is not installed directly in Windows.

The Docker Compose service is activated only when the `tools` profile is used.

Verify services:

```powershell
docker compose --profile tools config --services
```

Expected result:

```text
postgres
dbmate
```

### Check migration status

```powershell
docker compose --profile tools run --rm dbmate `
  --migrations-dir db/migrations `
  status
```

### Create a migration

```powershell
docker compose --profile tools run --rm dbmate `
  --migrations-dir db/migrations `
  new descriptive_migration_name
```

Example generated file:

```text
db/migrations/20260728202935_create_migration_command_check.sql
```

### Apply pending migrations

```powershell
docker compose --profile tools run --rm dbmate `
  --migrations-dir db/migrations `
  up
```

### Roll back the latest migration

```powershell
docker compose --profile tools run --rm dbmate `
  --migrations-dir db/migrations `
  down
```

## Migration validation performed

A temporary smoke-test migration was created:

```sql
-- migrate:up

CREATE TABLE dbmate_smoke_test (
    id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- migrate:down

DROP TABLE dbmate_smoke_test;
```

The following lifecycle was validated:

1. `dbmate new` created a migration file.
2. `dbmate up` created the test table.
3. `dbmate status` reported `Applied: 1` and `Pending: 0`.
4. `dbmate down` removed the test table.
5. The temporary migration file was deleted.
6. Final status reported `Applied: 0` and `Pending: 0`.

This confirms that migration creation, database connectivity, migration tracking, schema dumping, and rollback all work through Docker.

## Port conflict discovered and resolved

The first PostgreSQL container start failed because host port `5432` was already occupied.

The listening process was identified with:

```powershell
Get-NetTCPConnection -LocalPort 5432 -ErrorAction SilentlyContinue |
    Select-Object LocalAddress, LocalPort, State, OwningProcess
```

The process was identified as a separately installed Windows PostgreSQL 18 instance:

```text
C:\Program Files\PostgreSQL\18\bin\postgres.exe
```

Its Windows service name was:

```text
postgresql-x64-18
```

The service was stopped:

```powershell
Stop-Service -Name postgresql-x64-18
```

Its automatic startup was disabled to prevent the port conflict from returning after a Windows restart:

```powershell
Set-Service -Name postgresql-x64-18 -StartupType Disabled
```

Validated state:

```text
Name: postgresql-x64-18
State: Stopped
StartMode: Disabled
```

The existing Windows PostgreSQL installation was not deleted. It can be re-enabled later if another project requires it.

Re-enable it with administrator privileges:

```powershell
Set-Service -Name postgresql-x64-18 -StartupType Manual
Start-Service -Name postgresql-x64-18
```

Before doing that, stop the Docker PostgreSQL container or assign one of the PostgreSQL instances a different host port.

## Problems encountered and lessons learned

### Existing terminals may not receive a new PATH

Immediately after Docker Desktop installation, an already-open PowerShell window could not find the `docker` command.

Opening a new PowerShell window resolved the problem because it loaded the updated environment variables.

### YAML indentation is structural

The first edited `compose.yaml` contained an incorrectly indented port entry:

```yaml
ports:
- "127.0.0.1:5432:5432"
```

The correct nested structure is:

```yaml
ports:
  - "127.0.0.1:5432:5432"
```

Docker Compose rejected the invalid YAML before starting any service.

### Expanded Compose configuration can expose secrets

Running this command expands environment variables:

```powershell
docker compose config
```

The expanded output included the PostgreSQL password. The password was rotated immediately.

For routine structural checks, prefer commands that do not print expanded environment values, such as:

```powershell
docker compose config --services
```

Do not paste expanded Compose configuration into issues, pull requests, documentation, or chat logs without reviewing it for secrets.

### Containers use service names, not host localhost

From Windows, DBeaver connects to:

```text
localhost:5432
```

From the `dbmate` container, `localhost` would refer to the `dbmate` container itself. The correct database host inside the Compose network is:

```text
postgres:5432
```

### Healthchecks make tool startup safer

The `dbmate` service depends on the PostgreSQL healthcheck:

```yaml
depends_on:
  postgres:
    condition: service_healthy
```

This prevents migrations from being attempted before PostgreSQL is ready to accept connections.

## Learning outcomes demonstrated

This setup demonstrates practical understanding of:

- the difference between a database server and a database client;
- Windows host processes versus Linux containers;
- WSL 2 integration with Docker Desktop;
- host ports versus container ports;
- Docker networks and service-name DNS;
- persistent Docker volumes;
- healthchecks and startup dependencies;
- local secret management with `.env`;
- safe repository templates with `.env.example`;
- UTF-8 BOM compatibility issues;
- declarative database migrations;
- forward migration and rollback validation;
- identifying and resolving port conflicts;
- distinguishing implementation from validation evidence.

## Validation checklist

- [x] WSL 2 installed.
- [x] Ubuntu 24.04 installed under WSL 2.
- [x] Docker Desktop installed with WSL 2 backend.
- [x] Docker CLI works from Windows.
- [x] Docker CLI works from Ubuntu under WSL.
- [x] Test container executed successfully.
- [x] DBeaver Community installed.
- [x] PostgreSQL 17 container starts successfully.
- [x] PostgreSQL healthcheck reports `healthy`.
- [x] PostgreSQL is bound only to `127.0.0.1`.
- [x] DBeaver test connection succeeds.
- [x] `.env` is ignored by Git.
- [x] `.env.example` contains no real secret.
- [x] `dbmate` runs through Docker.
- [x] `dbmate` connects through the Compose network.
- [x] Migration creation works.
- [x] Migration apply works.
- [x] Migration status works.
- [x] Migration rollback works.
- [x] Temporary smoke-test objects were removed.
- [x] Conflicting Windows PostgreSQL service was disabled.

## Current boundary

The local database toolchain is ready for physical schema implementation.

The next database work should use real project migrations for the accepted data model. This setup alone does not complete `M2 — Infrastructure` or `M3 — Data model`, because the following remain separate work:

- Raspberry Pi deployment;
- SSD-backed persistent storage;
- NocoDB deployment;
- Tailscale private access;
- backup scheduling;
- restore validation;
- restart recovery validation;
- production secret handling;
- executable project schema migrations;
- database validation queries.

## Recommended evidence for GitHub

For a portfolio-quality pull request or issue, include:

- this setup document;
- `compose.yaml`;
- `.env.example`;
- the empty `db/migrations/` directory or its first real migration;
- `db/schema.sql` once real migrations exist;
- sanitized output showing PostgreSQL as `healthy`;
- sanitized `psql` version and database validation output;
- sanitized `dbmate status` output;
- a note that real credentials and expanded Compose configuration were intentionally excluded.

Do not include:

- `.env`;
- real database passwords;
- output from `docker compose config` containing expanded secrets;
- database dumps containing personal or imported data unless they are explicitly approved fixtures.
