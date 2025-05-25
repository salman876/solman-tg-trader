#!/usr/bin/env python3
"""
Solana Telegram Bot - Main Entry Point
"""
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.bot import SolanaTelegramBot
from config.settings import settings


def setup_logging():
    """Configure logging for the application."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure logging format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(settings.LOG_LEVEL)
    
    # File handler
    file_handler = logging.FileHandler(
        log_dir / "bot.log",
        encoding="utf-8"
    )
    file_handler.setLevel(logging.INFO)
    
    # Configure root logger
    logging.basicConfig(
        level=settings.LOG_LEVEL,
        format=log_format,
        handlers=[console_handler, file_handler]
    )
    
    # Set third-party loggers to WARNING
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def main():
    """Main function to start the bot."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Validate configuration
    if not settings.validate():
        logger.error("Invalid configuration. Please check your settings.")
        sys.exit(1)
    
    # Log configuration (without sensitive data)
    logger.info("Starting Solana Telegram Bot")
    logger.info(f"Owner ID: {settings.OWNER_USER_ID}")
    logger.info(f"Authorized users: {len(settings.AUTHORIZED_USERS)}")
    logger.info(f"API endpoint: {settings.API_BASE_URL}")
    
    try:
        # Create and run bot
        bot = SolanaTelegramBot()
        bot.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()