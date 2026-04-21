"""
Legacy script: creates optional chat_logs / employee_memory tables only.

Chatbot tables `policy_qa` and `chatbot_conversations` are created by
DMRC_HRMS_API TypeORM migrations — use the same DATABASE_URL as HRMS.
"""

import asyncio
import logging
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from app.config import settings
from app.knowledge.store import policy_store

logger = logging.getLogger(__name__)
Base = declarative_base()

class ChatLog(Base):
    """Chat log entries for audit trail"""
    __tablename__ = "chat_logs"
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String(36), index=True)
    employee_id = Column(String(50), index=True)
    message_type = Column(String(10))  # user, assistant
    content = Column(Text)
    intent = Column(String(50), nullable=True)
    routing_agent = Column(String(50), nullable=True)
    tool_calls = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    metadata_json = Column("metadata", JSON, nullable=True)

class EmployeeMemory(Base):
    """Long-term employee memory for personalization"""
    __tablename__ = "employee_memory"
    
    id = Column(Integer, primary_key=True)
    employee_id = Column(String(50), unique=True, index=True)
    language_preference = Column(String(5), default="en")
    personality_traits = Column(JSON, nullable=True)  # e.g., prefers concise answers
    common_queries = Column(JSON, nullable=True)  # e.g., frequently asked topics
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

def init_database():
    """Initialize database schema"""
    try:
        engine = create_engine(settings.DATABASE_URL)
        
        logger.info("Creating legacy schema (chat_logs / employee_memory only)...")
        Base.metadata.create_all(engine)
        logger.info("Schema step complete (run HRMS migrations for policy_qa / chatbot_conversations)")
        
        # Log sample data for chat table
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Check if tables were created
        inspector = None
        try:
            from sqlalchemy import inspect
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            logger.info(f"Tables created: {tables}")
        except Exception as e:
            logger.warning(f"Could not verify tables: {e}")
        
        session.close()
        return True
    
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        return False

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    success = init_database()
    if success:
        print("✓ Database initialized successfully")
    else:
        print("✗ Failed to initialize database")
