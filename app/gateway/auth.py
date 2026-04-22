import jwt
from typing import Optional
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from app.config import settings

def verify_jwt_token(token: str) -> dict:
    """
    Verify JWT token and extract employee information.
    Only validates signature and basic claims.
    Does NOT decode for business logic - trusts API for authorization.
    """
    try:
        # Remove 'Bearer ' prefix if present
        if token.startswith("Bearer "):
            token = token[7:]
        
        # Verify signature using SSO public key
        payload = jwt.decode(
            token,
            settings.SSO_PUBLIC_KEY,
            algorithms=["HS256", "RS256"],
            options={"verify_signature": bool(settings.SSO_PUBLIC_KEY)}
        )
        
        # Extract minimal claims needed for logging and session scoping
        employee_id = payload.get("employee_id") or payload.get("empId") or payload.get("sub")
        role = payload.get("role") or payload.get("user_type", "employee")
        
        if not employee_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing employee_id"
            )
        
        return {
            "employee_id": employee_id,
            "role": role,
            "token": token,  # Pass through to HRMS API
        }
    
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )

def get_token_from_header(auth_header: Optional[str]) -> str:
    """Extract JWT token from Authorization header"""
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header"
        )
    
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format"
        )
    
    return auth_header[7:]  # Remove 'Bearer ' prefix


def verify_jwt_token_history_h256(token: str) -> dict:
    """
    Verify HS256 JWT for /v1/chat/history. Claims must include empId or emp_id.
    Uses settings.JWT_SECRET, or SECRET_KEY if JWT_SECRET is empty.
    """
    if token.startswith("Bearer "):
        token = token[7:].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing token",
        )

    secret = (settings.JWT_SECRET or settings.SECRET_KEY or "").strip()
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server JWT secret is not configured",
        )

    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"verify_signature": True},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
        )

    employee_id = payload.get("emp_id") or payload.get("empId")
    if not employee_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing emp_id or empId claim",
        )

    return {
        "employee_id": str(employee_id).strip(),
        "role": (payload.get("role") or payload.get("user_type") or "employee"),
    }
