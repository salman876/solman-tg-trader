"""
Main bot class for Solana Telegram Bot
"""
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from config.settings import settings
from .handlers import MessageHandlers, CommandHandlers, CallbackHandlers
from .auth import AuthManager
from .api_client import APIClient


logger = logging.getLogger(__name__)


class SolanaTelegramBot:
    """Main bot class that orchestrates all components."""
    
    def __init__(self):
        """Initialize bot components."""
        self.auth_manager = AuthManager()
        self.api_client = APIClient()
        self.message_handlers = MessageHandlers(self.auth_manager, self.api_client)
        self.command_handlers = CommandHandlers(self.auth_manager, self.api_client)
        self.callback_handlers = CallbackHandlers(self.auth_manager, self.api_client)
        
        # Create application
        self.app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
        
        # Setup handlers
        self._setup_handlers()
        
        # Setup lifecycle hooks
        self.app.post_init = self._post_init
        self.app.post_shutdown = self._post_shutdown
    
    def _setup_handlers(self):
        """Register all handlers with the application."""
        # Command handlers
        self.app.add_handler(CommandHandler("start", self.command_handlers.handle_start))
        self.app.add_handler(CommandHandler("help", self.command_handlers.handle_help))
        self.app.add_handler(CommandHandler("status", self.command_handlers.handle_status))
        self.app.add_handler(CommandHandler("positions", self.command_handlers.handle_positions))
        self.app.add_handler(CommandHandler("sell", self.command_handlers.handle_sell_position))
        self.app.add_handler(CommandHandler("admin", self.command_handlers.handle_admin))
        self.app.add_handler(CommandHandler("wallet", self.command_handlers.handle_wallet))
        
        # Message handler for token detection
        self.app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self.message_handlers.handle_message
        ))
        
        # Callback query handlers
        self.app.add_handler(CallbackQueryHandler(
            self.callback_handlers.handle_access_request,
            pattern="^request_access_"
        ))
        self.app.add_handler(CallbackQueryHandler(
            self.callback_handlers.handle_approval,
            pattern="^(approve|deny)_"
        ))
        self.app.add_handler(CallbackQueryHandler(
            self.callback_handlers.handle_admin_callback,
            pattern="^admin_"
        ))
        
        # Positions pagination handler
        self.app.add_handler(CallbackQueryHandler(
            self.command_handlers.handle_positions,
            pattern="^positions_"
        ))
        
        # Sell position handler
        self.app.add_handler(CallbackQueryHandler(
            self.callback_handlers.handle_sell_callback,
            pattern="^sell_"
        ))
        
        logger.info("All handlers registered successfully")
    
    async def _post_init(self, application: Application) -> None:
        """Initialize resources after application starts."""
        await self.api_client.initialize()
        
        # Set bot commands for autocomplete
        await self._set_bot_commands()
        
        logger.info("Bot initialized successfully")
    
    async def _set_bot_commands(self):
        """Set bot commands for Telegram's autocomplete menu."""
        from telegram import BotCommand
        
        commands = [
            BotCommand("start", "Welcome message and instructions"),
            BotCommand("help", "Usage guide"),
            BotCommand("status", "Check bot and API status"),
            BotCommand("positions", "View all current positions with PnL"),
            BotCommand("sell", "Sell a position"),
            BotCommand("wallet", "View wallet balance"),
            BotCommand("admin", "Admin panel (owner only)")
        ]
        
        try:
            await self.app.bot.set_my_commands(commands)
            logger.info("Bot commands set successfully")
        except Exception as e:
            logger.error(f"Failed to set bot commands: {e}")
    
    async def _post_shutdown(self, application: Application) -> None:
        """Cleanup resources when application stops."""
        await self.api_client.close()
        logger.info("Bot shutdown complete")
    
    def run(self):
        """Start the bot."""
        logger.info("Starting bot polling...")
        self.app.run_polling(allowed_updates=["message", "callback_query"])