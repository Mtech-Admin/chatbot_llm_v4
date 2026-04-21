"""
FastAPI Router - HTTP endpoints for chatbot
"""

import logging
from pathlib import Path
import tempfile

from fastapi import APIRouter, Header, HTTPException, UploadFile, File, status
from typing import Optional
from datetime import datetime

from app.models.message import ChatRequest, ChatResponse, MessageRole, Message
from app.gateway.auth import verify_jwt_token, get_token_from_header
from app.gateway.session import session_manager
from app.orchestrator.state import OrchestratorState
from app.orchestrator.graph import process_message
from app.agents.response_agent import review_user_response
from app.knowledge.ingest import read_policy_rows
from app.knowledge.store import policy_store
from app.storage.chatbot_conversations import save_conversation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["chat"])

@router.post("/chat", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    authorization: Optional[str] = Header(None)
) -> ChatResponse:
    """
    Send chat message and get response from chatbot
    
    Args:
        request: ChatRequest with message and optional session_id
        authorization: Bearer token from header
    
    Returns:
        ChatResponse with assistant response
    """
    
    try:
        # Step 1: Extract and verify JWT token
        jwt_token = get_token_from_header(authorization)
        auth_info = verify_jwt_token(jwt_token)
        
        employee_id = auth_info["employee_id"]
        employee_role = auth_info["role"]
        
        logger.info(f"Message received from employee {employee_id}")
        
        # Step 2: Get or create session
        session_id = request.session_id
        if not session_id:
            session_id = await session_manager.create_session(employee_id, employee_role)
            logger.info(f"Created new session {session_id}")
        else:
            # Validate session belongs to this employee
            session_data = await session_manager.get_session(session_id)
            if not session_data or session_data.employee_id != employee_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Session does not belong to this employee"
                )
        
        # Step 3: Retrieve conversation history
        conversation_history = await session_manager.get_conversation_history(session_id)
        
        # Step 4: Build orchestrator state
        state = OrchestratorState(
            user_message=request.message,
            employee_id=employee_id,
            employee_role=employee_role,
            jwt_token=jwt_token,
            session_id=session_id,
            language=request.language,
            conversation_history=conversation_history
        )
        
        # Step 5: Process message through orchestrator
        state = await process_message(state)

        # Step 5.5: Final user-facing response review (skip for deterministic outputs)
        if not getattr(state, "skip_response_review", False):
            state.response_message = await review_user_response(
                user_message=request.message,
                draft_response=state.response_message,
                language=request.language,
            )
        
        # Step 6: Build response
        response = ChatResponse(
            session_id=session_id,
            answer=state.response_message,
            timestamp=datetime.utcnow(),
            sources=state.sources if state.sources else None,
            requires_action=state.requires_action,
            action_url=state.action_url
        )

        try:
            save_conversation(
                str(employee_id),
                request.message,
                response.answer,
            )
        except Exception as persist_exc:
            logger.error(
                "Could not save conversation to chatbot_conversations: %s",
                persist_exc,
                exc_info=True,
            )

        logger.info(f"Response sent to employee {employee_id}")
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your message"
        )

@router.post("/session/end")
async def end_session(
    session_id: str,
    authorization: Optional[str] = Header(None)
) -> dict:
    """
    End a chat session
    """
    
    try:
        # Verify JWT
        jwt_token = get_token_from_header(authorization)
        auth_info = verify_jwt_token(jwt_token)
        
        # Validate session
        session_data = await session_manager.get_session(session_id)
        if not session_data or session_data.employee_id != auth_info["employee_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Session does not belong to this employee"
            )
        
        # End session
        await session_manager.end_session(session_id)
        logger.info(f"Session {session_id} ended")
        
        return {"status": "success", "message": "Session ended"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ending session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to end session"
        )

@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint"""
    return {"status": "ok", "service": "dmrc-hrms-chatbot"}


@router.post("/knowledge/upload")
async def upload_policy_knowledge(
    file: UploadFile = File(...),
    replace: bool = True,
    authorization: Optional[str] = Header(None),
) -> dict:
    """
    Upload policy Q&A Excel/CSV and ingest into knowledge store.
    Required file columns: question, answer
    """
    try:
        jwt_token = get_token_from_header(authorization)
        auth_info = verify_jwt_token(jwt_token)
        employee_id = auth_info["employee_id"]

        file_name = file.filename or "uploaded_policy_file"
        suffix = Path(file_name).suffix.lower()
        if suffix not in {".csv", ".xlsx", ".xlsm"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported file type. Upload .csv, .xlsx, or .xlsm",
            )

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp_path = Path(tmp.name)
            content = await file.read()
            tmp.write(content)

        try:
            rows = read_policy_rows(tmp_path)
            valid_rows = [r for r in rows if str(r.get("question", "")).strip() and str(r.get("answer", "")).strip()]
            if replace:
                policy_store.clear()
            total_rows = policy_store.upsert_entries(valid_rows, source_file=file_name)
        finally:
            tmp_path.unlink(missing_ok=True)

        logger.info(
            "Policy knowledge uploaded by employee %s, file=%s, rows_read=%s, valid_rows=%s, rows_in_store=%s",
            employee_id,
            file_name,
            len(rows),
            len(valid_rows),
            total_rows,
        )
        return {
            "status": "success",
            "file": file_name,
            "rows_read": len(rows),
            "valid_rows": len(valid_rows),
            "rows_in_store": total_rows,
            "replace": replace,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Policy upload failed: %s", str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Policy upload failed: {str(exc)}",
        )


@router.get("/knowledge/stats")
async def policy_knowledge_stats(authorization: Optional[str] = Header(None)) -> dict:
    """Return policy knowledge base row counts and embedding diagnostics."""
    try:
        jwt_token = get_token_from_header(authorization)
        verify_jwt_token(jwt_token)
        return {"status": "ok", **policy_store.stats()}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Policy stats failed: %s", str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Policy stats failed: {str(exc)}",
        )
