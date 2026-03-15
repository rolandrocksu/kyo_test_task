import os


# Basic FastAPI/app configuration and shared settings.

APP_NAME = os.getenv("APP_NAME", "Leave Request Demo Dashboard")

# Database
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://leave_demo:leave_demo@postgres:5432/leave_demo",
)

# Email archive directory (where outbound emails are stored as .txt/.html)
EMAIL_ARCHIVE_DIR = os.getenv("EMAIL_ARCHIVE_DIR", "mail")

