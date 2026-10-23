from alembic import context
from sqlalchemy import create_engine
from services.api.config import Settings
from services.api.models import Base

config = Settings()
if context.is_offline_mode():
    context.configure(url=config.database_url, target_metadata=Base.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    with create_engine(config.database_url).connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()
