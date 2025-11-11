"""
Tests for app/services/messages_service.py
"""
import json
import pytest
from pathlib import Path
from app.services.messages_service import (
    MessagesService, 
    ImportOptions, 
    ImportResult
)
from models import Message


class TestImportOptions:
    """Test ImportOptions dataclass."""
    
    def test_default_options(self):
        """Test default ImportOptions values."""
        options = ImportOptions()
        assert options.drop_existing is True
    
    def test_custom_options(self):
        """Test custom ImportOptions values."""
        options = ImportOptions(drop_existing=False)
        assert options.drop_existing is False


class TestImportResult:
    """Test ImportResult dataclass."""
    
    def test_import_result_creation(self, sample_message):
        """Test creating ImportResult."""
        result = ImportResult(
            total_imported=5,
            preview_messages=[sample_message]
        )
        assert result.total_imported == 5
        assert len(result.preview_messages) == 1


class TestMessagesService:
    """Test MessagesService class."""
    
    def test_service_initialization(self, sqlite_store, mock_embedding_service):
        """Test service can be initialized."""
        service = MessagesService(sqlite_store, mock_embedding_service)
        assert service.store == sqlite_store
    
    def test_import_from_jsonl(self, sqlite_store, sample_jsonl_file, mock_embedding_service):
        """Test importing messages from JSONL file."""
        service = MessagesService(sqlite_store, mock_embedding_service)
        options = ImportOptions(drop_existing=True)
        
        result = service.import_from_jsonl(sample_jsonl_file, options)
        
        assert isinstance(result, ImportResult)
        assert result.total_imported == 3
        assert len(result.preview_messages) == 3
        # Verify embeddings were added
        assert result.preview_messages[0].embedding is not None
        assert len(result.preview_messages[0].embedding) == 1536
    
    def test_import_decodes_body(self, sqlite_store, sample_jsonl_file, mock_embedding_service):
        """Test that body is decoded from base64."""
        service = MessagesService(sqlite_store, mock_embedding_service)
        options = ImportOptions(drop_existing=True)
        
        result = service.import_from_jsonl(sample_jsonl_file, options)
        
        msg = result.preview_messages[0]
        assert msg.body == "First email body"
    
    def test_import_with_drop_existing(self, sqlite_store, sample_jsonl_file, mock_embedding_service):
        """Test import with drop_existing=True."""
        service = MessagesService(sqlite_store, mock_embedding_service)
        
        # First import
        options = ImportOptions(drop_existing=True)
        result1 = service.import_from_jsonl(sample_jsonl_file, options)
        assert result1.total_imported == 3
        
        # Second import with drop
        result2 = service.import_from_jsonl(sample_jsonl_file, options)
        assert result2.total_imported == 3
        
        # Should still only have 3 messages
        session = sqlite_store.create_session()
        count = session.query(Message).count()
        assert count == 3
        session.close()
    
    def test_import_without_drop_existing(self, sqlite_store, tmp_path, mock_embedding_service):
        """Test import with drop_existing=False."""
        # Create two different JSONL files
        file1 = tmp_path / "messages1.jsonl"
        file2 = tmp_path / "messages2.jsonl"
        
        import base64
        msg1 = {
            "id": "msg1",
            "subject": "First",
            "from": "test@example.com",
            "to": ["recipient@example.com"],
            "snippet": "snippet",
            "body": base64.b64encode(b"body").decode('utf-8'),
            "date": "2025-01-01T12:00:00Z"
        }
        msg2 = {
            "id": "msg2",
            "subject": "Second",
            "from": "test@example.com",
            "to": ["recipient@example.com"],
            "snippet": "snippet",
            "body": base64.b64encode(b"body").decode('utf-8'),
            "date": "2025-01-02T12:00:00Z"
        }
        
        with open(file1, 'w') as f:
            f.write(json.dumps(msg1) + '\n')
        
        with open(file2, 'w') as f:
            f.write(json.dumps(msg2) + '\n')
        
        service = MessagesService(sqlite_store, mock_embedding_service)
        
        # First import with drop
        options_drop = ImportOptions(drop_existing=True)
        service.import_from_jsonl(file1, options_drop)
        
        # Second import without drop
        options_no_drop = ImportOptions(drop_existing=False)
        service.import_from_jsonl(file2, options_no_drop)
        
        # Should have both messages
        session = sqlite_store.create_session()
        count = session.query(Message).count()
        assert count == 2
        session.close()

