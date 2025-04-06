from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Super awesome API"
    admin_email: str | None = None
    items_per_user: int = 50