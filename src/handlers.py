"""
Message and command handlers for the bot
"""
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config.settings import settings
from .auth import AuthManager
from .api_client import APIClient
from .utils import SolanaAddressValidator, truncate_address, format_tx_link, format_photon_link, format_duration, format_price


logger = logging.getLogger(__name__)


class BaseHandler:
    """Base class for handlers."""
    
    def __init__(self, auth_manager: AuthManager, api_client: APIClient = None):
        self.auth = auth_manager
        self.api = api_client


class MessageHandlers(BaseHandler):
    """Handles regular messages."""
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process messages for Solana addresses."""
        message = update.message
        if not message or not message.text:
            return
        
        user_id = message.from_user.id
        username = message.from_user.username or f"user_{user_id}"
        
        # Check authorization
        if not self.auth.is_authorized(user_id):
            await self._send_unauthorized_message(update)
            return
        
        # Extract Solana addresses
        addresses = SolanaAddressValidator.extract_addresses(message.text)
        
        if not addresses:
            return
        
        # Log the action
        logger.info(f"User {username} ({user_id}) triggered purchase for {len(addresses)} token(s)")
        
        # Process each address
        for address in addresses:
            await self._process_token_purchase(message, address, user_id, username)
    
    async def _process_token_purchase(self, message, address: str, user_id: int, username: str):
        """Process a single token purchase."""
        # Send initial notification
        status_msg = await message.reply_text(
            f"🔍 *Token Detected!*\n"
            f"*Address:* `{address}`\n"
            f"🚀 Initiating purchase...",
            parse_mode="Markdown",
            reply_to_message_id=message.message_id
        )
        
        # Make the purchase
        result = await self.api.buy_token(
            token_address=address,
            user_id=user_id,
            username=username
        )
        
        # Update with result
        if result["success"]:
            tx_hash = result.get('signature', 'N/A')
            token_amount = result.get('token_amount', 0)
            token_price = result.get('token_price', 0)
            token_mint = result.get('token_mint', address)
            slippage = result.get('slippage')
            
            # Create explorer link if we have tx hash
            tx_display = tx_hash
            if tx_hash != 'N/A':
                explorer_link = format_tx_link(tx_hash)
                tx_display = f"[{truncate_address(tx_hash)}]({explorer_link})"
            
            success_msg = (
                f"✅ *Purchase Successful!*\n"
                f"*Token:* `{token_mint}`\n"
                f"*Transaction:* {tx_display}\n"
                f"*Amount:* {token_amount:,.6f} tokens\n"
                f"*Price:* {format_price(token_price)}"
            )
            
            if slippage:
                success_msg += f"\n*Slippage:* {slippage}%"
            
            await status_msg.edit_text(
                success_msg,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
        else:
            await status_msg.edit_text(
                f"❌ *Purchase Failed!*\n"
                f"*Token:* `{address}`\n"
                f"*Error:* {result['error']}",
                parse_mode="Markdown"
            )
    
    async def _send_unauthorized_message(self, update: Update):
        """Send unauthorized access message."""
        user_id = update.effective_user.id
        
        if self.auth.is_request_pending(user_id):
            await update.message.reply_text(
                "⏳ Your access request is pending approval. Please wait for the owner to approve."
            )
        else:
            keyboard = [[
                InlineKeyboardButton("Request Access", callback_data=f"request_access_{user_id}")
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "🔒 *Access Denied*\n\n"
                "This bot is private. You can request access from the owner.",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )


class CommandHandlers(BaseHandler):
    """Handles bot commands."""
    
    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        user_id = update.effective_user.id
        
        if not self.auth.is_authorized(user_id):
            await MessageHandlers(self.auth)._send_unauthorized_message(update)
            return
        
        welcome_message = (
            "👋 *Welcome to Solana Token Auto-Buy Bot!*\n\n"
            "Simply paste any Solana token address and I'll automatically "
            "initiate a purchase for you.\n\n"
            "*Features:*\n"
            "• *Automatic token detection*\n"
            "• *Instant purchase execution*\n"
            "• *Whitelist-based security*\n\n"
            "*Commands:*\n"
            "/start - Show this message\n"
            "/help - Get help\n"
            "/status - Check bot status\n"
            "/positions - View current positions\n"
            "/sell - Sell a position\n"
        )
        
        if self.auth.is_owner(user_id):
            welcome_message += "/admin - Admin panel\n"
        
        welcome_message += "\nJust paste a token address to get started! 🚀"
        
        await update.message.reply_text(welcome_message, parse_mode="Markdown")
    
    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        if not self.auth.is_authorized(update.effective_user.id):
            await MessageHandlers(self.auth)._send_unauthorized_message(update)
            return
        
        help_message = (
            "ℹ️ *How to use this bot:*\n\n"
            "1. Copy any Solana token address\n"
            "2. Paste it in this chat\n"
            "3. The bot will automatically detect and purchase it\n\n"
            "*Valid Address Format:*\n"
            f"• {settings.MIN_TOKEN_LENGTH}-{settings.MAX_TOKEN_LENGTH} characters long\n"
            "• Base58 encoded (no 0, O, I, or l)\n"
            "• Example: `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`\n\n"
            "*Commands:*\n"
            "• `/positions` - View your current positions\n"
            "• `/sell TOKEN` - Sell a specific position\n\n"
            "*Need help?* Contact the bot owner."
        )
        
        await update.message.reply_text(help_message, parse_mode="Markdown")
    
    async def handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        if not self.auth.is_authorized(update.effective_user.id):
            await MessageHandlers(self.auth)._send_unauthorized_message(update)
            return
        
        # Check API health
        api_health = await self.api.health_check()
        
        if api_health["status"] == "healthy":
            api_status = f"🟢 Online ({api_health['response_time']:.2f}s)"
        elif api_health["status"] == "error":
            api_status = f"🔴 {api_health['message']}"
        else:
            api_status = f"🟡 {api_health['status']}"
        
        status_message = (
            "📊 *Bot Status*\n\n"
            f"Bot: 🟢 Online\n"
            f"API Server: {api_status}\n"
            f"Endpoint: `{settings.API_BASE_URL}`\n"
            f"Authorized Users: {len(self.auth.authenticated_users)}"
        )
        
        await update.message.reply_text(status_message, parse_mode="Markdown")
    
    async def handle_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /admin command - owner only."""
        user_id = update.effective_user.id
        
        if not self.auth.is_owner(user_id):
            await update.message.reply_text("This command is only available to the bot owner.")
            return
        
        keyboard = [
            [InlineKeyboardButton("👥 List Users", callback_data="admin_list_users")],
            [InlineKeyboardButton("📊 Statistics", callback_data="admin_stats")],
            [InlineKeyboardButton("🔄 Refresh", callback_data="admin_refresh")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        stats = self.auth.get_stats()
        
        await update.message.reply_text(
            f"🔧 *Admin Panel*\n\n"
            f"Authorized Users: {stats['authorized_users']}\n"
            f"Pending Requests: {stats['pending_requests']}\n\n"
            f"Select an option:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    async def handle_positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /positions command."""
        if not self.auth.is_authorized(update.effective_user.id):
            await MessageHandlers(self.auth)._send_unauthorized_message(update)
            return
        
        # Send loading message
        loading_msg = await update.message.reply_text("📊 Fetching positions...")
        
        # Get positions from API
        result = await self.api.get_positions()
        
        if not result["success"]:
            await loading_msg.edit_text(
                f"❌ Failed to fetch positions: {result.get('error', 'Unknown error')}",
                parse_mode="Markdown"
            )
            return
        
        positions = result.get("positions", [])
        
        if not positions:
            await loading_msg.edit_text(
                "📭 No active positions found.",
                parse_mode="Markdown"
            )
            return
        
        # Format positions message
        message = "📊 *Current Positions*\n\n"
        
        for i, pos in enumerate(positions, 1):
            token_mint = pos.get("token_mint", "Unknown")
            current_pnl = pos.get("current_pnl", 0)
            current_pnl_percent = pos.get("current_pnl_percent", 0)
            highest_pnl_percent = pos.get("highest_pnl_percent", 0)
            hold_duration = pos.get("hold_duration", "Unknown")
            signature = pos.get("signature", "")
            
            # Format PnL with color indicator
            if current_pnl_percent > 0:
                pnl_emoji = "🟢"
                pnl_sign = "+"
            elif current_pnl_percent < 0:
                pnl_emoji = "🔴"
                pnl_sign = ""
            else:
                pnl_emoji = "⚪"
                pnl_sign = ""
            
            # Create explorer link for buy transaction
            tx_display = ""
            if signature:
                explorer_link = format_tx_link(signature)
                tx_display = f"├ Buy TX: [{truncate_address(signature)}]({explorer_link})\n"
            
            message += (
                f"*{i}. {truncate_address(token_mint)}*\n"
                f"├ Token: `{token_mint}`\n"
                f"{tx_display}"
                f"├ PnL: {pnl_emoji} {pnl_sign}{current_pnl_percent:.2f}% ({pnl_sign}{format_price(current_pnl)} SOL)\n"
                f"├ Peak PnL: {highest_pnl_percent:.2f}%\n"
                f"├ Duration: {format_duration(hold_duration)}\n"
                f"└ [photon]({format_photon_link(token_mint)})\n\n"
            )
        
        # Add summary
        total_pnl = sum(pos.get("current_pnl", 0) for pos in positions)
        total_pnl_sign = "+" if total_pnl > 0 else ""
        
        message += (
            f"*Summary:*\n"
            f"Total Positions: {len(positions)}\n"
            f"Total PnL: {total_pnl_sign}{format_price(total_pnl)} SOL"
        )
        
        await loading_msg.edit_text(message, parse_mode="Markdown", disable_web_page_preview=True)
    
    async def handle_sell_position(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /sell_position command."""
        if not self.auth.is_authorized(update.effective_user.id):
            await MessageHandlers(self.auth)._send_unauthorized_message(update)
            return
        
        # Check if token address was provided
        if not context.args:  
            message = (
                "*To sell a position, use:*\n"
                "`/sell TOKEN_MINT`\n\n"
                "Example:\n"
                f"`/sell 35cNWuWpRkTNAG2KiZDjhpi6QJr92Y3U8Ac6vShZpump`"
            )
            
            await update.message.reply_text(message, parse_mode="Markdown")
            return
        
        # Get token address from command
        token_mint = context.args[0]
        
        # Validate it's a valid Solana address
        if not SolanaAddressValidator.is_valid_address(token_mint):
            await update.message.reply_text(
                "❌ Invalid token address format.\n\n"
                "Please provide a valid Solana token mint address.",
                parse_mode="Markdown"
            )
            return
        
        # Send confirmation message
        status_msg = await update.message.reply_text(
            f"🔄 *Selling Position*\n"
            f"Token: `{token_mint}`\n"
            f"Processing...",
            parse_mode="Markdown"
        )
        
        # Execute sell
        result = await self.api.sell_position(token_mint)
        
        if result["success"]:
            tx_hash = result.get('signature', 'N/A')
            
            # Create explorer link
            tx_display = tx_hash
            if tx_hash != 'N/A':
                explorer_link = format_tx_link(tx_hash)
                tx_display = f"[{truncate_address(tx_hash)}]({explorer_link})"
            
            await status_msg.edit_text(
                f"✅ *Position sold successfully*\n\n"
                f"*Token:* `{token_mint}`\n"
                f"*Transaction:* {tx_display}",
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
        else:
            await status_msg.edit_text(
                f"❌ *Sell Failed!*\n\n"
                f"*Token:* `{token_mint}`\n"
                f"*Error:* {result['error']}",
                parse_mode="Markdown"
            )


class CallbackHandlers(BaseHandler):
    """Handles callback queries from inline keyboards."""
    
    async def handle_access_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle access request callback."""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        username = query.from_user.username or f"User {user_id}"
        
        # Add to pending requests
        self.auth.add_pending_request(user_id)
        
        # Notify user
        await query.edit_message_text(
            "✅ Access request sent to the owner. You'll be notified once approved."
        )
        
        # Notify owner
        if settings.OWNER_USER_ID:
            keyboard = [
                [
                    InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user_id}"),
                    InlineKeyboardButton("❌ Deny", callback_data=f"deny_{user_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                chat_id=settings.OWNER_USER_ID,
                text=f"🔔 *Access Request*\n\n"
                     f"*User:* @{username}\n"
                     f"*ID:* `{user_id}`\n"
                     f"*Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
    
    async def handle_approval(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle approval/denial of access requests."""
        query = update.callback_query
        await query.answer()
        
        # Only owner can approve
        if not self.auth.is_owner(query.from_user.id):
            await query.answer("Only the owner can approve requests!", show_alert=True)
            return
        
        data = query.data.split("_")
        action = data[0]
        user_id = int(data[1])
        
        # Remove from pending
        self.auth.remove_pending_request(user_id)
        
        if action == "approve":
            self.auth.add_user(user_id)
            
            await query.edit_message_text(
                f"✅ Access approved for user {user_id}"
            )
            
            # Notify the user
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="✅ *Access Granted!*\n\n"
                         "The owner has approved your request. You can now use the bot.",
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.error(f"Failed to notify user {user_id}: {e}")
        else:
            await query.edit_message_text(
                f"❌ Access denied for user {user_id}"
            )
            
            # Notify the user
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❌ Your access request was denied.",
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.error(f"Failed to notify user {user_id}: {e}")
    
    async def handle_admin_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle admin panel callbacks."""
        query = update.callback_query
        await query.answer()
        
        if not self.auth.is_owner(query.from_user.id):
            return
        
        if query.data == "admin_list_users":
            users_list = "\n".join([f"• `{user_id}`" for user_id in self.auth.authenticated_users])
            await query.edit_message_text(
                f"👥 *Authorized Users:*\n\n{users_list or 'No users authorized'}",
                parse_mode="Markdown"
            )
        
        elif query.data == "admin_stats":
            stats = self.auth.get_stats()
            
            await query.edit_message_text(
                f"📊 *Bot Statistics*\n\n"
                f"Authorized Users: {stats['authorized_users']}\n"
                f"Pending Requests: {stats['pending_requests']}\n"
                f"Owner ID: `{stats['owner_id']}`\n"
                f"API Endpoint: `{settings.API_BASE_URL}`",
                parse_mode="Markdown"
            )
        
        elif query.data == "admin_refresh":
            # Refresh the admin panel
            keyboard = [
                [InlineKeyboardButton("👥 List Users", callback_data="admin_list_users")],
                [InlineKeyboardButton("📊 Statistics", callback_data="admin_stats")],
                [InlineKeyboardButton("🔄 Refresh", callback_data="admin_refresh")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            stats = self.auth.get_stats()
            
            await query.edit_message_text(
                f"🔧 *Admin Panel* *(Updated)*\n\n"
                f"Authorized Users: {stats['authorized_users']}\n"
                f"Pending Requests: {stats['pending_requests']}\n\n"
                f"Select an option:",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )