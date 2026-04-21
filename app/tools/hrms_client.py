import httpx
import logging
from typing import Dict, Any, Optional
from app.config import settings

logger = logging.getLogger(__name__)

class HRMSClient:
    """HTTP client for HRMS API with JWT passthrough"""
    
    def __init__(self):
        self.base_url = settings.HRMS_BASE_URL
        self.timeout = settings.HRMS_TIMEOUT
    
    async def call_api(
        self,
        endpoint: str,
        jwt_token: str,
        method: str = "POST",
        body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Call HRMS API with JWT passthrough.
        
        Args:
            endpoint: API endpoint (e.g., '/employee-attendance/my-attendance')
            jwt_token: Employee's JWT token
            method: HTTP method (GET, POST, etc.)
            body: Request body for POST requests
            params: Query parameters for GET requests
        
        Returns:
            API response as dictionary
        """
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Content-Type": "application/json",
        }
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if method == "POST":
                    response = await client.post(url, json=body or {}, headers=headers)
                elif method == "GET":
                    response = await client.get(url, params=params, headers=headers)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                # Log request/response for audit trail
                logger.info(
                    f"HRMS API call: {method} {endpoint} - Status: {response.status_code}"
                )
                
                # Treat any 2xx as success (HRMS returns 201 for some read endpoints)
                if 200 <= response.status_code < 300:
                    return response.json()
                elif response.status_code == 403:
                    logger.warning(f"Access denied for endpoint: {endpoint}")
                    return {"error": "access_denied"}
                elif response.status_code == 404:
                    logger.warning(f"Resource not found: {endpoint}")
                    return {"error": "not_found"}
                elif response.status_code == 401:
                    logger.warning(f"Unauthorized access to: {endpoint}")
                    return {"error": "unauthorized"}
                else:
                    logger.error(f"HRMS API error {response.status_code}: {response.text}")
                    return {"error": f"hrms_error_{response.status_code}"}
        
        except httpx.TimeoutException:
            logger.error(f"Timeout calling HRMS API: {endpoint}")
            return {"error": "timeout"}
        except Exception as e:
            logger.error(f"Exception calling HRMS API: {str(e)}")
            return {"error": f"exception: {str(e)}"}

# Global HRMS client instance
hrms_client = HRMSClient()
