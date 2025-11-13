# Extra Forever

Gmail-style custom category builder with a CLI, HTTP API, and lightweight web UI.

---

## 1. What this system actually does

From the spec, there are three core requirements:

1. **Ingest messages** from a JSONL file.
2. **Let a user define categories** with natural language descriptions.
3. **Decide, for each message, whether it belongs in each category**, and explain why.

This repo implements that end to end:
- Messages and categories are stored in a SQLite database.
- Both are turned into embeddings, so they can be compared in vector space.
- A pluggable **classification strategy** decides category membership. The default is an LLM-based strategy that evaluates all categories for a message in a single call and returns:
  - which categories match,
  - a confidence score for each match,
  - and an explanation.

There are three ways to interact:
- **CLI** (`uv run extra <args>`) for local workflows and demos
- **HTTP API** (FastAPI) for programmatic access
- **Web UI** (Preact + Vite) for browsing messages and categories

---

## 2. First-principles design

### 2.1 Data model

At the core there are three tables (see `models.py`):

- `Message`
  - `id`, `subject`, `sender`, `to[]`, `snippet`, `body`, `date`
  - `embedding: list[float]` (JSON) for semantic representation
- `Category`
  - `id`, `name`, `description`
  - `embedding: list[float]` (JSON)
- `MessageCategory`
  - Association table (`message_id`, `category_id`)
  - Also stores:
    - `score` (0–1 confidence or similarity)
    - `explanation` (plain English)
    - `classified_at` (timestamp)

### 2.2 How category descriptions become decisions

There are two classification strategies implemented behind a common interface:

#### A) LLM classification (default, spec “Option B”)

Classes: `LLMClassificationStrategy`, `ClassificationService`

1. **Input representation**

   - The message is formatted as text:

     ```text
     Subject: …
     From: …
     To: …
     Date: …
     Preview: …
     Body: …
     ```

   - All categories are represented as:

     ```text
     [0] Work Travel
         Description: Work-related travel receipts from airlines, hotels, etc.
     [1] AI Research Newsletters
         Description: …
     …
     ```

2. **Single LLM call per message**

   - The strategy uses [pydantic-ai](https://ai.pydantic.dev/agents/) for our agent loop with a typed output schema:

     ```python
     class CategoryMatchOutput(BaseModel):
         category_index: int
         is_in_category: bool
         explanation: str
         confidence: float
     ```

   - The agent is instructed to, for each individual message:
     - Evaluate **every** category simultaneously.
     - Return `is_in_category`, `confidence`, and an explanation for each.

#### B) Embedding similarity classification (spec “Option A”)

Classes: `EmbeddingSimilarityStrategy`, `EmbeddingService`

This is a pure cosine-similarity strategy that uses the stored embeddings:

1. `EmbeddingService` builds embeddings using the OpenAI embeddings API:

   * Messages: `"Subject + From + Snippet + Body"` combined to a single text span.
   * Categories: `"Category name + description"` combined similarly.
2. At classification time:

   * Compute cosine similarity between `message.embedding` and each `category.embedding`.
   * Filter to similarities ≥ `threshold`.
   * Sort by similarity and take `top_n`.
3. The resulting scores and explanations are persisted the same way as with the LLM strategy.

---

## 3. Surfaces: CLI, API, UI

### 3.1 CLI (Typer)

Entry point: `cli.py` exposed as the `extra` command via `pyproject.toml`.

Key commands:

```bash
# One-shot end-to-end demo: bootstrap messages + categories & classify with LLM
uv run extra bootstrap \
  --messages sample-messages.jsonl \
  --categories sample-categories.jsonl \
  --drop \
  --classify \
  --top-n 3 \
  --threshold 0.5
```

Other useful commands:

```bash
# Import messages only (embedding + optional auto-classification)
uv run extra messages import sample-messages.jsonl --drop --classify

# List messages with their assigned categories
uv run extra messages list

# Inspect a single message in detail
uv run extra messages get a3a67dc0

# Classify a specific message on demand
uv run extra messages classify a3a67dc0 --top-n 3 --threshold 0.5

# Manage categories
uv run extra category create "Work Travel" \
  "Work-related travel receipts from airlines, hotels, and travel agencies"

uv run extra category list
```

The CLI is tuned for the interview: you can show ingestion, category creation, and classification in a few self-contained commands, with nicely formatted table output and explanations.

### 3.2 HTTP API (FastAPI)

Entry point: `api.py` → `app: FastAPI`.

Start the server:

```bash
uv run uvicorn api:app --host 0.0.0.0 --port 8000
# or
uv run python api.py
```

Core endpoints:

* `GET /health` – health check
* `POST /bootstrap/` – upload messages and categories and optionally auto-classify
* `GET /categories/` – list categories
* `POST /categories/` – create a category
* `GET /messages/` – list messages with their categories
* `POST /messages/import` – upload messages JSONL
* `POST /messages/{message_id}/classify` – classify a message

#### Classification endpoint shape

`POST /messages/{message_id}/classify` returns:

```json
{
  "message_id": "a3a67dc0",
  "classifications": [
    {
      "category_id": 1,
      "category_name": "Work Travel",
      "score": 0.93,
      "is_in_category": true,
      "explanation": "This email is a flight receipt for a work trip."
    }
  ]
}
```

This is a small extension of the spec’s suggested shape:

* For each **(message, category)** pair that passes the decision rule, you get:

  * `message_id`
  * `is_in_category` (always `true` in this list)
  * `explanation`
  * plus `category_id`, `category_name`, and `score` for debugging and UI.

If you want an array exactly of the spec’s form, you can flatten this response to something like:

```json
[
  {
    "message_id": "a3a67dc0",
    "is_in_category": true,
    "explanation": "This email is a flight receipt for a work trip."
  }
]
```

### 3.3 Web UI (Preact + Vite)

The UI in `ui/` is intentionally minimal but demonstrates the full loop:
* Shows all categories and their descriptions.
* Click a category to see messages currently assigned to it (using the persisted `MessageCategory` rows).
* Shows sender, subject, snippet, date, and assigned categories.
* Expand a row to see full body, category explanations, and scores.

The UI talks to the backend via the same API (proxied to `/api` in dev).

---

## 4. How ingestion works

### 4.1 Message ingestion

Input format: `messages.jsonl` where each line is:

```json
{
  "id": "174a9",
  "subject": "Your Delta eTicket Receipt",
  "from": "Delta <no-reply@delta.com>",
  "to": ["sam@example.com"],
  "snippet": "Thanks for flying with us",
  "body": "PGh0bWw+CiAgPGhlYWQ+Li4uPC9oZWFkPgogIDxib2R5Pi4uLjwvYm9keT4KPC9odG1sPg==",
  "date": "2025-08-12T14:33:22Z"
}
```

The ingestion pipeline in `MessagesService` does:

1. **Base64 decode** of `body`.
2. **HTML to text** if the body looks like HTML (via BeautifulSoup).
3. **Embedding generation** using `EmbeddingService.embed_message`.
4. **Persist** the `Message` with its embedding in SQLite.

All plain-text normalization lives in `MessagesService.parse_message_content`, so the same logic is reused for both CLI and API ingestion.

### 4.2 Category ingestion

Input format: `sample-categories.jsonl` where each line is:

```json
{"name": "Work Travel", "description": "Work-related travel receipts, bookings, and itineraries from airlines, hotels, and travel agencies"}
```

The category pipeline in `CategoriesService`:

1. Creates a `Category` with the given `name` and `description`.
2. Calls `EmbeddingService.embed_category` on `"Category: {name}\nDescription: {description}"`.
3. Stores the embedding alongside the category.

Names are unique; attempts to create duplicates raise a 400 error in the API or a `ValueError` in the service layer.

---

## 5. Example run on the sample dataset

This is the “show me it all works” path for reviewers.

### 5.1 CLI demo

```bash
# Install deps
uv sync

# Bootstrap sample data and classify with LLM
uv run extra bootstrap \
  --messages sample-messages.jsonl \
  --categories sample-categories.jsonl \
  --drop \
  --classify \
  --top-n 3 \
  --threshold 0.5
```

The CLI prints:

* A summary of how many categories, messages, and classifications were created.
* A table of sample categories.
* A table of sample messages, including assigned categories.
* For the first few messages, the matched categories with scores and explanations.

### 5.2 API demo

1. Start the API:

   ```bash
   uv run uvicorn api:app --reload --port 8000
   ```

2. Bootstrap via HTTP:

   ```bash
   curl -X POST http://localhost:8000/bootstrap/ \
     -F "messages_file=@sample-messages.jsonl" \
     -F "categories_file=@sample-categories.jsonl" \
     -F "drop_existing=true" \
     -F "auto_classify=true" \
     -F "classification_top_n=3" \
     -F "classification_threshold=0.5"
   ```

3. Inspect classifications for a single message:

   ```bash
   curl -X POST "http://localhost:8000/messages/a3a67dc0/classify?top_n=3&threshold=0.5"
   ```

   Example response shape:

   ```json
   {
     "message_id": "a3a67dc0",
     "classifications": [
       {
         "category_id": 1,
         "category_name": "Work Travel",
         "score": 0.94,
         "is_in_category": true,
         "explanation": "This email is a flight receipt from an airline for a work trip."
       }
     ]
   }
   ```

4. Browse messages and categories in the built-in docs:

   * Open `http://localhost:8000/docs` in a browser.

### 5.3 UI demo

With the backend running:

```bash
cd ui
pnpm install
pnpm dev
```

Then open `http://localhost:5173`:

* You should see the categories from `sample-categories.jsonl`.
* The messages from `sample-messages.jsonl` appear with their assigned categories.
* Expanding a message shows the same explanation text persisted from the classification step.

---

## 6. Setup, tooling, and project layout

### 6.1 Requirements

* Python 3.12 (see `.python-version`)
* [`uv`](https://github.com/astral-sh/uv) for Python env and packaging
* Node.js 20+ and `pnpm` for the UI (only if you want to run the UI)
* SQLite (embedded, no separate service)

### 6.2 Quickstart with Tilt (runs API + UI + helpers)

If you have [Tilt](https://tilt.dev/) installed:

```bash
brew install tilt-dev/tap/tilt  # on macOS

tilt up
```

Tilt will:

* start the FastAPI backend on port 8000,
* start the Preact UI on port 5173,
* give you clickable buttons to:

  * bootstrap sample data,
  * run tests,
  * lint and format,
  * build the UI.

See `Tiltfile` for details.

### 6.3 Manual setup

```bash
# Install Python deps
uv sync

# Start API
uv run uvicorn api:app --reload --port 8000

# (Optional) install CLI globally in your environment
uv pip install -e .
```

UI (optional):

```bash
cd ui
pnpm install
pnpm dev
```

### 6.4 Project structure

```text
.
├── api.py                 # FastAPI app entry point
├── cli.py                 # Typer CLI ("extra")
├── models.py              # SQLAlchemy ORM models (Message, Category, MessageCategory)
├── app/
│   ├── config.py          # Config (DB URL, thresholds, model names)
│   ├── deps.py            # FastAPI dependency wiring
│   ├── controllers/       # FastAPI routers (bootstrap, messages, categories)
│   ├── services/          # Orchestration: embedding, classification, messages, categories, bootstrap
│   ├── managers/          # Thin CRUD wrappers over SQLAlchemy sessions
│   ├── stores/            # SQLiteStore: engine and session management
│   └── utils/             # JSONL parsing, HTML handling
├── ui/                    # Preact + Vite front-end
├── tests/                 # Unit and integration tests
└── sample-*.jsonl         # Sample messages and categories for the demo
```

The layering is:

* **Controllers**: HTTP request / response translation, validation.
* **Services**: business logic and orchestration (classification, ingestion).
* **Managers**: direct DB operations for a single entity.
* **Store**: DB engine and session lifetime management.

---

## 7. Testing

Tests are structured to avoid hitting real OpenAI APIs:

* Embeddings are replaced with deterministic random vectors via `MockEmbeddingService`.
* LLM calls are replaced with `FunctionModel` instances that return structured JSON.

To run tests:

```bash
uv run pytest -v
```
