# Ensure models are registered in SQLModel metadata when this package is imported.
# This is required so that session_fixture in tests can call create_all()
# after only importing backend.database (which triggers this __init__.py).
from backend import models as _models  # noqa: F401
