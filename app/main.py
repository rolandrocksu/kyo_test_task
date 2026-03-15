from fastapi import FastAPI

from alembic.config import Config
from alembic import command
from app.core.config import APP_NAME
from app.db import init_db
from app.routers import dashboard as dashboard_router


app = FastAPI(title=APP_NAME)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    # Run migrations programmatically
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    


app.include_router(dashboard_router.router)

