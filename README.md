# Extra Forever

Gmail-style message classification system with CLI, API, and Web UI interfaces.

## Quick Start with Tilt (Recommended)

The easiest way to run everything:

```bash
# Install Tilt (one-time setup)
brew install tilt-dev/tap/tilt  # macOS
# See TILT.md for other platforms

# Start all services
tilt up
```

Press **space** to open the Tilt UI, then visit:
- **Web UI**: http://localhost:5173
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

See [TILT.md](TILT.md) for detailed Tilt documentation.

## Manual Setup

If you prefer to run services individually:

```bash
# Install Python dependencies
uv sync

# Install UI dependencies
cd ui && pnpm install

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

## Web UI

A modern Preact-based web interface for managing messages and categories.

### Quick Start
```bash
# With Tilt (recommended)
tilt up

# Manual
cd ui
pnpm install
pnpm dev
```

Visit http://localhost:5173 to:
- View and classify messages
- Create and manage categories
- See classifications in real-time

See [ui/README.md](ui/README.md) for UI documentation.

## Development

### With Tilt (Recommended)
```bash
# Start everything
tilt up

# Bootstrap sample data (click in Tilt UI or run manually)
uv run python cli.py bootstrap sample-messages.jsonl sample-categories.jsonl --drop-existing

# Run tests (click in Tilt UI or run manually)
uv run pytest -v

# Format and lint (click in Tilt UI or run manually)
ruff format .
ruff check . && mypy .
```

### Manual (Traditional)
```bash
# Terminal 1 - API
uv run uvicorn api:app --reload

# Terminal 2 - UI
cd ui && pnpm dev

# Terminal 3 - CLI commands
uv run extra --help

# View API docs
open http://localhost:8000/docs

# View UI
open http://localhost:5173
```

## Features

### 📧 Message Management
- Import messages from JSONL files
- View message details (subject, sender, body, etc.)
- Classify messages into custom categories
- Web UI, API, and CLI interfaces

### 🏷️ Category Management
- Define categories with natural language descriptions
- AI-powered classification using embeddings
- Support for multiple classification strategies:
  - Cosine similarity (default)
  - LLM-based classification
  - Hybrid approaches

### 🔍 Classification
- Embedding-based similarity matching
- Configurable threshold and top-N results
- Explanations for each classification
- Batch processing support

## Testing

```bash
# With Tilt
tilt up
# Click "tests" in Tilt UI

# Manual
uv run pytest -v

# With coverage
uv run pytest --cov=app --cov=models --cov-report=html

# View coverage report
open htmlcov/index.html
```
