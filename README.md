# Extra Forever

Gmail-style message classification system with CLI and API interfaces.

## Setup

```bash
# Install dependencies
uv sync

# Install CLI globally (optional)
uv pip install -e .
```

## CLI Usage

```bash
# Import messages from JSONL file
uv run extra import sample-messages.jsonl --drop

# Import without dropping existing tables
uv run extra import sample-messages.jsonl --no-drop
```

## API Usage

### Start the API server

```bash
# Start with uvicorn
uv run uvicorn api:app --host 0.0.0.0 --port 8000

# Or use the script directly
uv run python api.py
```

### API Endpoints

- `GET /` - Health check
- `GET /health` - Health check
- `GET /docs` - Swagger UI documentation
- `POST /messages/import` - Import messages from uploaded JSONL file

### Example API Request

```bash
# Import messages via API
curl -X POST http://localhost:8000/messages/import \
  -F "file=@sample-messages.jsonl" \
  -F "drop_existing=true"
```

## Architecture

```
extra-forever/
├── api.py              # FastAPI application
├── cli.py              # Typer CLI application
├── models.py           # SQLAlchemy ORM models
└── app/
    ├── controllers/    # Handle requests (CLI & API)
    ├── services/       # Business logic orchestration
    ├── managers/       # Entity CRUD operations
    └── stores/         # Database persistence
```

### Separation of Concerns

- **Controllers** - Handle incoming requests from CLI or API, use FastAPI router annotations
- **Services** - Orchestrate business logic and coordinate operations
- **Managers** - Perform CRUD operations on entities
- **Stores** - Abstract database connections and sessions

Both CLI and API use the same controllers, ensuring consistent behavior across interfaces.

## Development

```bash
# Run CLI
uv run extra --help

# Run API server
uv run uvicorn api:app --reload

# View API docs
open http://localhost:8000/docs
```
