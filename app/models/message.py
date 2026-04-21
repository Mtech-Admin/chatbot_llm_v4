from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class Message(BaseModel):
    """Chat message model"""
    role: MessageRole
    content: str
    timestamp: Optional[datetime] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None

class ChatRequest(BaseModel):
    """User chat message request"""
    message: str
    session_id: Optional[str] = None
    employee_id: Optional[str] = None
    language: str = Field(default="en", description="Language: 'en' or 'hi'")

class ChatResponse(BaseModel):
    """Chat response from assistant"""
    session_id: str
    answer: str
    timestamp: datetime
    sources: Optional[List[Dict[str, Any]]] = None
    requires_action: bool = False
    action_url: Optional[str] = None

class SessionData(BaseModel):
    """Session data stored in Redis"""
    session_id: str
    employee_id: str
    employee_role: str
    created_at: datetime
    last_activity: datetime
    messages: List[Message]
    context: Optional[Dict[str, Any]] = None

class EmployeeProfile(BaseModel):
    """Employee profile for context"""
    employee_id: str
    name: str
    department: str
    designation: str
    email: str
    phone: Optional[str] = None
    manager_id: Optional[str] = None
    role: str
    language_preference: str = "en"

class AttendanceRecord(BaseModel):
    """Attendance record from HRMS API"""
    id: int
    employee_id: str
    check_in_time: Optional[datetime] = None
    check_out_time: Optional[datetime] = None
    date: str
    attendance_status: str  # P, A, L, WFH, etc.
    is_verified: str  # PENDING, APPROVED, REJECTED
    remarks: Optional[str] = None

class AttendanceResponse(BaseModel):
    """Response containing attendance information"""
    attendance_records: List[AttendanceRecord]
    summary: Optional[Dict[str, Any]] = None
    total_records: int
