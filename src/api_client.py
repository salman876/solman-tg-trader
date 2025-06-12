"""
API client for interacting with the Solana purchase server
"""
import logging
import asyncio
from datetime import datetime
from typing import Dict, Optional
import aiohttp

from config.settings import settings


logger = logging.getLogger(__name__)


class APIClient:
    """Handles all API interactions with the purchase server."""
    
    def __init__(self):
        """Initialize API client."""
        self.session: Optional[aiohttp.ClientSession] = None
        self.base_url = settings.API_BASE_URL
        self.api_key = settings.API_KEY
        self.timeout = aiohttp.ClientTimeout(total=settings.API_TIMEOUT)
    
    async def initialize(self):
        """Initialize aiohttp session."""
        headers = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
            
        self.session = aiohttp.ClientSession(
            timeout=self.timeout,
            connector=aiohttp.TCPConnector(limit=100),
            headers=headers
        )
        logger.info(f"API client initialized for {self.base_url}")
    
    async def close(self):
        """Close aiohttp session."""
        if self.session:
            await self.session.close()
            logger.info("API client session closed")
    
    async def health_check(self) -> Dict[str, any]:
        """
        Check API server health status.
        
        Returns:
            Dict with status and response time
        """
        if not self.session:
            return {"status": "error", "message": "Client not initialized"}
        
        try:
            start_time = datetime.now()
            
            async with self.session.get(
                f"{self.base_url}/api/v1/health",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                elapsed = (datetime.now() - start_time).total_seconds()
                
                if response.status == 200:
                    data = await response.json()
                    # Check if the server status is "ok"
                    if data.get("status") == "ok":
                        return {
                            "status": "healthy",
                            "response_time": elapsed,
                            "timestamp": data.get("timestamp"),
                            "tracker_running": data.get("tracker_running"),
                            "tracked_positions": data.get("tracked_positions")
                        }
                    else:
                        return {
                            "status": "unhealthy",
                            "response_time": elapsed,
                            "server_status": data.get("status"),
                            "timestamp": data.get("timestamp")
                        }
                else:
                    return {
                        "status": "unhealthy",
                        "http_status": response.status,
                        "response_time": elapsed
                    }
                    
        except asyncio.TimeoutError:
            return {"status": "error", "message": "Request timeout"}
        except aiohttp.ClientError as e:
            return {"status": "error", "message": f"Network error: {str(e)}"}
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "error", "message": str(e)}
    
    async def buy_token(
        self,
        token_address: str,
        user_id: int,
        username: str
    ) -> Dict[str, any]:
        """
        Make a token purchase request.
        
        Args:
            token_address: Solana token address (mint)
            user_id: Telegram user ID
            username: Telegram username
            
        Returns:
            Dict with success status and data/error
        """
        if not self.session:
            return {"success": False, "error": "Client not initialized"}
        
        if not self.api_key:
            return {"success": False, "error": "API key not configured"}
        
        payload = {
            "token_mint": token_address
        }
        
        try:
            logger.info(f"Making buy request for token {token_address} by user {username} ({user_id})")
            
            async with self.session.post(
                f"{self.base_url}/api/v1/buy",
                json=payload
            ) as response:
                if response.status == 200:
                    response_text = await response.text()
                    logger.info(f"Purchase request successful for token {token_address}: {response_text}")
                    return {
                        "success": True,
                        "message": response_text
                    }
                else:
                    try:
                        data = await response.json()
                        error_message = data.get("message", f"HTTP {response.status}")
                        error_type = data.get("error", "unknown_error")
                        logger.error(f"Purchase failed for token {token_address}: {error_type} - {error_message}")
                        return {
                            "success": False,
                            "error": error_message,
                            "error_type": error_type,
                            "http_status": response.status
                        }
                    except Exception:
                        # Fallback if response is not JSON
                        logger.error(f"Purchase failed with status {response.status} for token {token_address}")
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}",
                            "http_status": response.status
                        }
                    
        except asyncio.TimeoutError:
            logger.error(f"Purchase request timed out for token {token_address}")
            return {
                "success": False,
                "error": "Request timeout - server took too long to respond"
            }
        except aiohttp.ClientError as e:
            logger.error(f"Network error during purchase: {e}")
            return {
                "success": False,
                "error": f"Network error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Unexpected error during purchase: {e}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }
    
    async def get_positions(self) -> Dict[str, any]:
        """
        Get current positions from the API.
        
        Returns:
            Dict with positions data or error
        """
        if not self.session:
            return {"success": False, "error": "Client not initialized"}
        
        if not self.api_key:
            return {"success": False, "error": "API key not configured"}
        
        try:
            logger.info("Fetching current positions")
            
            async with self.session.get(
                f"{self.base_url}/api/v1/positions"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    positions = data.get("positions", [])
                    count = data.get("count", len(positions))
                    logger.info(f"Retrieved {count} positions")
                    return {
                        "success": True,
                        "positions": positions,
                        "count": count
                    }
                else:
                    error_msg = f"HTTP {response.status}"
                    logger.error(f"Failed to fetch positions: {error_msg}")
                    return {
                        "success": False,
                        "error": error_msg,
                        "http_status": response.status
                    }
                    
        except asyncio.TimeoutError:
            logger.error("Positions request timed out")
            return {
                "success": False,
                "error": "Request timeout"
            }
        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching positions: {e}")
            return {
                "success": False,
                "error": f"Network error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Unexpected error fetching positions: {e}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }

    async def get_wallet_balance(self) -> Dict[str, any]:
        """
        Get wallet balance information from the API.
        
        Returns:
            Dict with wallet balance data or error
        """
        if not self.session:
            return {"success": False, "error": "Client not initialized"}
        
        if not self.api_key:
            return {"success": False, "error": "API key not configured"}
        
        try:
            logger.info("Fetching wallet balance")
            
            async with self.session.get(
                f"{self.base_url}/api/v1/wallet/balance"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Retrieved wallet balance: {data.get('uiAmount')} {data.get('symbol')}")
                    return {
                        "success": True,
                        "data": data
                    }
                else:
                    error_msg = f"HTTP {response.status}"
                    logger.error(f"Failed to fetch wallet balance: {error_msg}")
                    return {
                        "success": False,
                        "error": error_msg,
                        "http_status": response.status
                    }
                    
        except asyncio.TimeoutError:
            logger.error("Wallet balance request timed out")
            return {
                "success": False,
                "error": "Request timeout"
            }
        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching wallet balance: {e}")
            return {
                "success": False,
                "error": f"Network error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Unexpected error fetching wallet balance: {e}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }

    async def sell_position(self, token_mint: str) -> Dict[str, any]:
        """
        Sell a position.
        
        Args:
            token_mint: Token mint address to sell
            
        Returns:
            Dict with success status and transaction details
        """
        if not self.session:
            return {"success": False, "error": "Client not initialized"}
        
        if not self.api_key:
            return {"success": False, "error": "API key not configured"}
        
        payload = {
            "token_mint": token_mint
        }
        
        try:
            logger.info(f"Making sell request for token {token_mint}")
            
            async with self.session.post(
                f"{self.base_url}/api/v1/sell",
                json=payload
            ) as response:
                if response.status == 200:
                    response_text = await response.text()
                    logger.info(f"Sell request successful for token {token_mint}: {response_text}")
                    return {
                        "success": True,
                        "message": response_text
                    }
                else:
                    logger.error(f"Sell failed with status {response.status} for token {token_mint}")
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}",
                        "http_status": response.status
                    }
                    
        except asyncio.TimeoutError:
            logger.error(f"Sell request timed out for token {token_mint}")
            return {
                "success": False,
                "error": "Request timeout - server took too long to respond"
            }
        except aiohttp.ClientError as e:
            logger.error(f"Network error during sell: {e}")
            return {
                "success": False,
                "error": f"Network error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Unexpected error during sell: {e}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }