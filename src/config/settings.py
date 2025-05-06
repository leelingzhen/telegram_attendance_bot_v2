from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # Bot tokens
    training_bot_token: str = Field(default=os.getenv("TRAINING_BOT_TOKEN", ""))
    admin_bot_token: str = Field(default=os.getenv("ADMIN_BOT_TOKEN", ""))
    
    # Backend service URL
    backend_url: str = Field(default=os.getenv("BACKEND_URL", "http://localhost:8000"))
    
    # Team configuration
    team_name: str = Field(default=os.getenv("TEAM_NAME", "My Team"))
    
    # Environment
    environment: str = Field(default=os.getenv("ENVIRONMENT", "development"))
    
    class Config:
        env_file = ".env"

settings = Settings() 