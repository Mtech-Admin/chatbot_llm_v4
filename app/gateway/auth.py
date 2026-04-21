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
