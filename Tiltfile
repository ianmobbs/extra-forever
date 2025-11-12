# Tiltfile for Extra Forever - Gmail Category Builder
# Run everything with: tilt up

# Configuration
config.define_string("api-port", args=False, usage="Port for the API server")
config.define_string("ui-port", args=False, usage="Port for the UI dev server")
cfg = config.parse()

API_PORT = cfg.get("api-port", "8000")
UI_PORT = cfg.get("ui-port", "5173")

# Set up project-wide settings
update_settings(max_parallel_updates=2)

# ============================================================================
# Backend API (FastAPI + Python)
# ============================================================================

# Run the FastAPI backend using uv
local_resource(
    'api',
    serve_cmd='uv run uvicorn api:app --host 0.0.0.0 --port ' + API_PORT + ' --reload',
    serve_dir='.',
    deps=[
        'api.py',
        'models.py',
        'app/',
        'pyproject.toml',
        'uv.lock',
    ],
    labels=['backend'],
    links=[
        link('http://localhost:' + API_PORT, 'API'),
        link('http://localhost:' + API_PORT + '/docs', 'API Docs'),
    ],
    readiness_probe=probe(
        period_secs=5,
        http_get=http_get_action(port=int(API_PORT), path='/health')
    ),
)

# ============================================================================
# Frontend UI (Preact + Vite)
# ============================================================================

# Install UI dependencies if needed
local_resource(
    'ui-install',
    cmd='cd ui && pnpm install',
    deps=['ui/package.json', 'ui/pnpm-lock.yaml'],
    labels=['frontend'],
)

# Run the Vite dev server
local_resource(
    'ui',
    serve_cmd='cd ui && pnpm dev --host 0.0.0.0 --port ' + UI_PORT,
    serve_dir='.',
    deps=[
        'ui/src/',
        'ui/index.html',
        'ui/vite.config.ts',
        'ui/tsconfig.json',
        'ui/postcss.config.js',
    ],
    resource_deps=['ui-install', 'api'],  # Wait for install and API to be ready
    labels=['frontend'],
    links=[
        link('http://localhost:' + UI_PORT, 'UI'),
    ],
    readiness_probe=probe(
        period_secs=5,
        http_get=http_get_action(port=int(UI_PORT), path='/')
    ),
)

# ============================================================================
# Database (SQLite) - No separate service needed, just show location
# ============================================================================

local_resource(
    'database-info',
    cmd='echo "SQLite database: $(pwd)/messages.db"',
    labels=['database'],
    auto_init=True,
    trigger_mode=TRIGGER_MODE_MANUAL,
)

# ============================================================================
# Utilities
# ============================================================================

# Bootstrap with sample data
local_resource(
    'bootstrap',
    cmd='uv run python cli.py bootstrap sample-messages.jsonl sample-categories.jsonl --drop-existing',
    auto_init=False,
    trigger_mode=TRIGGER_MODE_MANUAL,
    resource_deps=['api'],
    labels=['utilities'],
)

# Run tests
local_resource(
    'tests',
    cmd='uv run pytest -v',
    auto_init=False,
    trigger_mode=TRIGGER_MODE_MANUAL,
    deps=[
        'tests/',
        'app/',
        'models.py',
    ],
    labels=['utilities'],
)

# Format code
local_resource(
    'format',
    cmd='ruff format .',
    auto_init=False,
    trigger_mode=TRIGGER_MODE_MANUAL,
    labels=['utilities'],
)

# Lint code
local_resource(
    'lint',
    cmd='ruff check . && mypy .',
    auto_init=False,
    trigger_mode=TRIGGER_MODE_MANUAL,
    labels=['utilities'],
)

# ============================================================================
# UI Build (for testing production build)
# ============================================================================

local_resource(
    'ui-build',
    cmd='cd ui && pnpm run build',
    auto_init=False,
    trigger_mode=TRIGGER_MODE_MANUAL,
    deps=['ui/src/', 'ui/index.html'],
    labels=['utilities'],
)

# ============================================================================
# Status and Help
# ============================================================================

print("""
╔═══════════════════════════════════════════════════════════════════════╗
║                                                                       ║
║  📧 Extra Forever - Gmail Category Builder                            ║
║                                                                       ║
║  Services will start automatically:                                  ║
║  • API:  http://localhost:""" + API_PORT + """                                          ║
║  • UI:   http://localhost:""" + UI_PORT + """                                          ║
║                                                                       ║
║  Manual triggers (click in Tilt UI):                                 ║
║  • bootstrap - Load sample data                                      ║
║  • tests     - Run test suite                                        ║
║  • format    - Format code with ruff                                 ║
║  • lint      - Check code with ruff & mypy                           ║
║  • ui-build  - Build UI for production                               ║
║                                                                       ║
║  Press 'space' in terminal to open Tilt UI in browser               ║
║                                                                       ║
╚═══════════════════════════════════════════════════════════════════════╝
""")
