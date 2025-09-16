from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    db_user: str
    db_password: str
    db_name: str
    database_url: str
    debug: bool = False
    log_level: str = "INFO"

    # WinSMS Configuration
    winsms_api_key: str
    winsms_api_url: str = "https://www.winsms.co.za/api/rest/v1"  # Correct default URL

    # Docker Development
    compose_project_name: str

    class Config:
        env_file = ".env"

def get_settings():
    return Settings()