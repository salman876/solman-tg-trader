"""
Utility functions for Solana Telegram Bot
"""
import re
import base58
import logging
from typing import List, Optional

from config.settings import settings


logger = logging.getLogger(__name__)


class SolanaAddressValidator:
    """Validates and extracts Solana addresses."""
    
    # Base58 alphabet used by Solana
    BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    
    @classmethod
    def is_valid_address(cls, address: str) -> bool:
        """
        Validate Solana address format.
        
        Args:
            address: Potential Solana address string
            
        Returns:
            bool: True if valid Solana address
        """
        try:
            # Check length
            if not (settings.MIN_TOKEN_LENGTH <= len(address) <= settings.MAX_TOKEN_LENGTH):
                return False
            
            # Check if it only contains base58 characters
            if not all(c in cls.BASE58_ALPHABET for c in address):
                return False
            
            # Try to decode
            decoded = base58.b58decode(address)
            
            # Should decode to 32 bytes
            return len(decoded) == 32
            
        except Exception as e:
            logger.debug(f"Address validation failed for {address}: {e}")
            return False
    
    @classmethod
    def extract_addresses(cls, text: str) -> List[str]:
        """
        Extract valid Solana addresses from text.
        
        Args:
            text: Input text containing potential addresses
            
        Returns:
            List of valid unique Solana addresses
        """
        # Pattern for potential Solana addresses
        pattern = rf'\b[{cls.BASE58_ALPHABET}]{{{settings.MIN_TOKEN_LENGTH},{settings.MAX_TOKEN_LENGTH}}}\b'
        potential_addresses = re.findall(pattern, text)
        
        # Validate and deduplicate
        valid_addresses = []
        seen = set()
        
        for addr in potential_addresses:
            if addr not in seen and cls.is_valid_address(addr):
                valid_addresses.append(addr)
                seen.add(addr)
                logger.debug(f"Found valid Solana address: {addr}")
        
        return valid_addresses


def format_tx_link(tx_hash: str, network: str = "mainnet") -> str:
    """
    Format a transaction hash into a Solana explorer link.
    
    Args:
        tx_hash: Transaction hash
        network: Network name (mainnet, devnet, testnet)
        
    Returns:
        Formatted explorer URL
    """
    base_urls = {
        "mainnet": "https://solscan.io/tx",
        "devnet": "https://solscan.io/tx",
        "testnet": "https://solscan.io/tx"
    }
    
    base_url = base_urls.get(network, base_urls["mainnet"])
    return f"{base_url}/{tx_hash}"


def truncate_address(address: str, length: int = 6) -> str:
    """
    Truncate a long address for display.
    
    Args:
        address: Full address
        length: Number of characters to show at start and end
        
    Returns:
        Truncated address like "EPjFWd...wNYB"
    """
    if len(address) <= length * 2:
        return address
    
    return f"{address[:length]}...{address[-length:]}"

def format_photon_link(address: str) -> str:
    """
    Format a photon address into a Solana explorer link.
    
    Args:
        address: Photon address
        
    Returns:
        Formatted photon URL
    """
    return f"https://photon-sol.tinyastro.io/en/lp/{address}"

def format_duration(duration_str: str) -> str:
    """
    Format a duration string into a more readable format.
    
    Args:
        duration_str: Duration string like "20m57.369032128s" or "1h30m45.123s"
        
    Returns:
        Formatted duration like "20m 57s" or "1h 30m 45s"
    """
    if not duration_str or duration_str == "Unknown":
        return "Unknown"
    
    try:
        import re
        
        # Extract hours, minutes, and seconds using regex
        pattern = r'(?:(\d+)h)?(?:(\d+)m)?(?:(\d+(?:\.\d+)?)s)?'
        match = re.match(pattern, duration_str)
        
        if not match:
            return duration_str  # Return original if can't parse
        
        hours, minutes, seconds = match.groups()
        
        parts = []
        
        if hours:
            parts.append(f"{hours}h")
        
        if minutes:
            parts.append(f"{minutes}m")
        
        if seconds:
            # Convert to integer seconds (remove decimal part)
            seconds_int = int(float(seconds))
            if seconds_int > 0 or not parts:  # Show seconds if it's the only unit or > 0
                parts.append(f"{seconds_int}s")
        
        return " ".join(parts) if parts else "0s"
        
    except Exception:
        return duration_str  # Return original if any error occurs

def format_price(price) -> str:
    """
    Format a price value to avoid scientific notation and show up to 10 decimal places.
    
    Args:
        price: Price value (float, int, or string)
        
    Returns:
        Formatted price string like "0.0000001707"
    """
    try:
        # Convert to float if it's not already
        if isinstance(price, str):
            price_float = float(price)
        else:
            price_float = float(price)
        
        # Format with up to 10 decimal places, removing trailing zeros
        formatted = f"{price_float:.10f}".rstrip('0').rstrip('.')
        
        # If the result is empty (was 0.0000000000), return "0"
        if not formatted:
            return "0"
            
        return formatted
        
    except (ValueError, TypeError):
        # If conversion fails, return the original value as string
        return str(price)

def escape_markdown(text: str) -> str:
    """
    Escape special characters for Telegram Markdown.
    
    Args:
        text: Text to escape
        
    Returns:
        Escaped text safe for Markdown
    """
    # Characters that need escaping in Markdown
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    
    return text