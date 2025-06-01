"""
Configuration management for Solana Telegram Bot
"""
import os
import logging
from typing import Set, Optional
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv


# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


@dataclass
class Settings:
    """Application settings."""
    
    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", ""))
    
    # API Configuration
    API_BASE_URL: str = field(default_factory=lambda: os.getenv("API_BASE_URL", "https://solman-trader.fly.dev"))
    API_KEY: str = field(default_factory=lambda: os.getenv("API_KEY", ""))
    API_TIMEOUT: int = field(default_factory=lambda: int(os.getenv("API_TIMEOUT", "30")))
    
    # Authentication
    OWNER_USER_ID: int = field(default_factory=lambda: int(os.getenv("OWNER_USER_ID", "0").split("#")[0].strip()))
    AUTHORIZED_USERS: Set[int] = field(default_factory=set)
    

    
    # Logging
    LOG_LEVEL: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    
    # Solana Settings
    MIN_TOKEN_LENGTH: int = 32
    MAX_TOKEN_LENGTH: int = 44
    
    def __post_init__(self):
        """Initialize authorized users from environment."""
        # Add owner to authorized users
        if self.OWNER_USER_ID:
            self.AUTHORIZED_USERS.add(self.OWNER_USER_ID)
        
        # Parse additional authorized users
        auth_users_str = os.getenv("AUTHORIZED_USERS", "")
        if auth_users_str:
            for user_id in auth_users_str.split(","):
                try:
                    self.AUTHORIZED_USERS.add(int(user_id.strip()))
                except ValueError:
                    logging.warning(f"Invalid user ID in AUTHORIZED_USERS: {user_id}")
    
    def validate(self) -> bool:
        """Validate settings."""
        errors = []
        
        if not self.TELEGRAM_BOT_TOKEN:
            errors.append("TELEGRAM_BOT_TOKEN is required")
        
        if self.TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
            errors.append("Please set a valid TELEGRAM_BOT_TOKEN")
        
        if not self.API_BASE_URL:
            errors.append("API_BASE_URL is required")
        
        if not self.API_KEY:
            errors.append("API_KEY is required for authentication")
        
        if not self.OWNER_USER_ID:
            logging.warning("⚠️  No OWNER_USER_ID set - bot will be open to everyone!")
            logging.warning("⚠️  Set OWNER_USER_ID to your Telegram user ID for security!")
        
        if errors:
            for error in errors:
                logging.error(f"Configuration error: {error}")
            return False
        
        return True


# Create global settings instance
settings = Settings()