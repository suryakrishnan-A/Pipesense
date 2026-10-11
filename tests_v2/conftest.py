import os
import pytest

# Point to an isolated test database file for all tests in tests_v2
TEST_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_topology.db"))
os.environ["PIPESENSE_DB_PATH"] = TEST_DB_PATH

from backend_v2.repository.topology_db import configure_db, init_db, reset_db_to_seed
from backend_v2.repository.db import db as in_memory_db
from backend_v2.services.pipesense_service_sql import PipeSenseServiceSQL

service = PipeSenseServiceSQL()

@pytest.fixture(scope="session", autouse=True)
def setup_test_db_session():
    """Configures isolated test SQLite database for test session."""
    configure_db(TEST_DB_PATH)
    init_db()
    reset_db_to_seed()
    in_memory_db.reset_demo_state()
    yield
    # Cleanup test database file after all tests finish
    try:
        from backend_v2.repository.topology_db import engine
        engine.dispose()
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)
    except Exception:
        pass

@pytest.fixture(autouse=True)
def clean_isolated_test_state():
    """Ensures each test starts and finishes with isolated, known database state."""
    service.reset_demo()
    yield
    service.reset_demo()
