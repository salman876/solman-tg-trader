"""
Authentication and authorization management
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Set, Optional

from config.settings import settings


logger = logging.getLogger(__name__)


class AuthManager:
    """Manages user authentication and authorization."""
    
    def __init__(self):
        """Initialize auth manager."""
        self.authenticated_users: Set[int] = settings.AUTHORIZED_USERS.copy()
        self.pending_requests: Dict[int, datetime] = {}
    
    def is_authorized(self, user_id: int) -> bool:
        """Check if user is authorized to use the bot."""
        # If no owner is set, allow all (for testing)
        if not settings.OWNER_USER_ID:
            logger.warning("No OWNER_USER_ID set - allowing all users!")
            return True
        
        return user_id in self.authenticated_users
    
    def is_owner(self, user_id: int) -> bool:
        """Check if user is the bot owner."""
        return user_id == settings.OWNER_USER_ID
    
    def add_user(self, user_id: int) -> bool:
        """Add a user to the authorized list."""
        if user_id not in self.authenticated_users:
            self.authenticated_users.add(user_id)
            logger.info(f"User {user_id} added to authorized users")
            return True
        return False
    
    def remove_user(self, user_id: int) -> bool:
        """Remove a user from the authorized list."""
        if user_id in self.authenticated_users and user_id != settings.OWNER_USER_ID:
            self.authenticated_users.remove(user_id)
            logger.info(f"User {user_id} removed from authorized users")
            return True
        return False
    
    def add_pending_request(self, user_id: int) -> None:
        """Add a pending access request."""
        self.pending_requests[user_id] = datetime.now()
        logger.info(f"Access request from user {user_id} added to pending")
    
    def remove_pending_request(self, user_id: int) -> None:
        """Remove a pending access request."""
        if user_id in self.pending_requests:
            del self.pending_requests[user_id]
    
    def is_request_pending(self, user_id: int) -> bool:
        """Check if user has a pending request."""
        if user_id not in self.pending_requests:
            return False
        
        # Check if request is still valid (within 5 minutes)
        request_time = self.pending_requests[user_id]
        if datetime.now() - request_time > timedelta(minutes=5):
            del self.pending_requests[user_id]
            return False
        
        return True
    
    def get_stats(self) -> Dict[str, int]:
        """Get authentication statistics."""
        return {
            "authorized_users": len(self.authenticated_users),
            "pending_requests": len(self.pending_requests),
            "owner_id": settings.OWNER_USER_ID
        }