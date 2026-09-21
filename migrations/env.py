"""Flask-Migrate-Anbindung; Schemaänderungen laufen nur als expliziter CLI-Schritt.

Aus dem Flask-Migrate-Template abgeleitet:
https://github.com/miguelgrinberg/Flask-Migrate/tree/main/src/flask_migrate/templates/flask
"""

from logging.config import fileConfig

from alembic import context
from flask import current_app

config = context.config
fileConfig(config.config_file_name, disable_existing_loggers=False)
database = current_app.extensions["migrate"].db

if context.is_offline_mode():
    context.configure(
        url=database.engine.url,
        target_metadata=database.metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    with database.engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=database.metadata,
            **current_app.extensions["migrate"].configure_args,
        )
        with context.begin_transaction():
            context.run_migrations()
