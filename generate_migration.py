"""Generate Alembic migration with proper PYTHONPATH"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from alembic.config import Config
from alembic import command

# Create Alembic config
alembic_cfg = Config("alembic.ini")

# Generate migration
command.revision(
    alembic_cfg,
    message="Add platform-agnostic agent models and adapters",
    autogenerate=True
)

print("Migration generated successfully!")
