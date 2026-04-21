import redis.asyncio as redis
import json
from datetime import datetime, timedelta
from typing import Optional, List
from uuid import uuid4
from app.config import settings
from app.models.message import SessionData, Message

class SessionManager:
    """Redis-based session management"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
    
    async def init(self):
        """Initialize Redis connection"""
        self.redis_client = await redis.from_url(settings.REDIS_URL)
    
    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
    
    async def create_session(self, employee_id: str, employee_role: str) -> str:
        """Create new session and return session ID"""
        session_id = str(uuid4())
        session_data = SessionData(
            session_id=session_id,
            employee_id=employee_id,
            employee_role=employee_role,
            created_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            messages=[],
            context={}
        )
        
        await self.redis_client.setex(
            f"session:{session_id}",
            settings.SESSION_TTL,
            session_data.model_dump_json()
        )
        
        return session_id
    
    async def get_session(self, session_id: str) -> Optional[SessionData]:
        """Retrieve session data from Redis"""
        data = await self.redis_client.get(f"session:{session_id}")
        if not data:
            return None
        
        return SessionData.model_validate_json(data)
    
    async def update_session(self, session_data: SessionData):
        """Update session in Redis"""
        await self.redis_client.setex(
            f"session:{session_data.session_id}",
            settings.SESSION_TTL,
            session_data.model_dump_json()
        )
    
    async def add_message(self, session_id: str, message: Message):
        """Add message to session history"""
        session = await self.get_session(session_id)
        if not session:
            return
        
        # Keep only last 8 turns (16 messages)
        session.messages.append(message)
        if len(session.messages) > 16:
            session.messages = session.messages[-16:]
        
        session.last_activity = datetime.utcnow()
        await self.update_session(session)
    
    async def get_conversation_history(self, session_id: str) -> List[Message]:
        """Get conversation history for context injection"""
        session = await self.get_session(session_id)
        return session.messages if session else []
    
    async def end_session(self, session_id: str):
        """End session and remove from Redis"""
        await self.redis_client.delete(f"session:{session_id}")

# Global session manager instance
session_manager = SessionManager()
