from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    db_user: str
    db_password: str
    db_name: str
    database_url: str
    debug: bool = False
    log_level: str = "INFO"

    # BulkSMS Configuration
    bulksms_username: str
    bulksms_password: str
    bulksms_api_url: str = "https://api.bulksms.com/v1/messages"

    # Docker Development
    compose_project_name: str

    class Config:
        env_file = ".env"

def get_settings():
    return Settings()
