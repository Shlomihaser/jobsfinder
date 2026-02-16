from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str
    DB_USER: str
    DB_PASS: str
    DB_NAME: str
    DATABASE_URL: str
    
    RABBITMQ_USER: str
    RABBITMQ_PASS: str
    RABBITMQ_URL: str
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
