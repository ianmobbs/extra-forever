# Test Suite

Comprehensive pytest test suite with 100% code coverage.

## Running Tests

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/controllers/test_messages_controller.py

# Run specific test class
uv run pytest tests/controllers/test_messages_controller.py::TestMessagesController

# Run specific test
uv run pytest tests/controllers/test_messages_controller.py::TestMessagesController::test_import_messages

# Run tests matching pattern
uv run pytest -k "import"
```

## Coverage

```bash
# Run tests with coverage report
uv run pytest --cov

# Generate HTML coverage report
uv run pytest --cov --cov-report=html
open htmlcov/index.html
```

## Test Structure

```
tests/
├── conftest.py                          # Shared fixtures
├── test_models.py                       # ORM model tests
├── controllers/
│   └── test_messages_controller.py      # Controller + integration tests
├── services/
│   └── test_messages_service.py         # Service layer tests
├── managers/
│   └── test_message_manager.py          # Manager tests
└── stores/
    └── test_sqlite_store.py             # Store tests
```

## Test Types

### Unit Tests
Test individual components in isolation:
- `test_models.py` - ORM models
- `test_sqlite_store.py` - Database store
- `test_message_manager.py` - CRUD operations
- `test_messages_service.py` - Business logic

### Integration Tests
Test full workflows across components:
- `TestMessagesControllerIntegration` - Complete import workflows
- End-to-end scenarios testing CLI and API together
- Database persistence verification

### API Tests
Test FastAPI endpoints:
- `TestMessagesControllerAPI` - HTTP endpoint tests
- File upload handling
- Request/response validation

## Fixtures

Key fixtures defined in `conftest.py`:

- `temp_db` - Temporary SQLite database
- `sqlite_store` - Configured SQLiteStore instance  
- `db_session` - Database session for tests
- `sample_message_data` - Single message test data
- `sample_messages_data` - Multiple messages test data
- `sample_jsonl_file` - Temporary JSONL file
- `sample_message` - ORM Message instance

## Coverage Report

Current coverage: **100%**

All code paths in:
- `app/controllers/`
- `app/services/`
- `app/managers/`
- `app/stores/`
- `models.py`

## Writing New Tests

When adding new features:

1. **Add unit tests** in the appropriate `test_*.py` file
2. **Add integration tests** in the controller test file
3. **Use existing fixtures** from `conftest.py`
4. **Follow naming conventions**: `test_<what_it_tests>`
5. **Add docstrings** explaining what the test verifies

Example:

```python
def test_new_feature(self, temp_db, sample_data):
    """Test that new feature works correctly."""
    controller = MessagesController(db_path=temp_db)
    result = controller.new_feature(sample_data)
    assert result.success is True
```

## Continuous Integration

Tests are configured to run with:
- pytest-asyncio for async tests
- pytest-cov for coverage reporting
- httpx TestClient for API tests

