from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings): 
    model_config = SettingsConfigDict(env_file=".env", extra="ignore") 
    database_url: str = "postgresql://sentinel:sentinel@localhost:5432/sentinel" 
    groq_api_key: str = "" 
    gemini_api_key: str = "" 
    environment: str = "development" 

settings = Settings()