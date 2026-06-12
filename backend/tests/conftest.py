import os
from pathlib import Path

os.environ["FORGE_ENV"] = "test"
os.environ["FORGE_DATABASE_URL"] = "sqlite:///./forge_test.db"
os.environ["FORGE_MOCK_LLM"] = "true"
os.environ["FORGE_SECRET_KEY"] = "test-secret-key"

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import Base, engine
from app.main import app


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    get_settings.cache_clear()
    with TestClient(app) as test_client:
        yield test_client
