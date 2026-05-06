import httpx
import logging
from typing import Dict, Any, Optional
import jwt
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from app.config import settings

logger = logging.getLogger(__name__)


class HRMSClient:
    """HTTP client for HRMS API with JWT passthrough"""
    
    def __init__(self):
        self.base_url = settings.HRMS_BASE_URL
        self.timeout = settings.HRMS_TIMEOUT
        self.engine = create_engine(settings.DATABASE_URL)
        self.http_client = httpx.AsyncClient(
            timeout=self.timeout,
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        )

    def _masked_token(self, jwt_token: str) -> str:
        token = (jwt_token or "").strip()
        if token.startswith("Bearer "):
            token = token[7:].strip()
        if len(token) <= 12:
            return "***"
        return f"{token[:6]}...{token[-6:]}"

    async def aclose(self) -> None:
        await self.http_client.aclose()

    def _extract_emp_id_from_token(self, jwt_token: str) -> Optional[str]:
        """Read empId claim from JWT without verifying signature."""
        token = (jwt_token or "").strip()
        if token.startswith("Bearer "):
            token = token[7:].strip()
        if not token:
            return None
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            emp_id = payload.get("empId") or payload.get("emp_id")
            if emp_id is None:
                return None
            return str(emp_id).strip()
        except Exception:
            return None

    def _latest_device_header_for_emp(self, emp_id: Optional[str]) -> Dict[str, str]:
        """Fetch latest otp_logs device details for the employee."""
        fallback = {"device_type": "WEB"}
        if not emp_id:
            return fallback
        query = text(
            """
            SELECT device_id, device_type
            FROM public.otp_logs
            WHERE "empId" = :emp_id
              AND deleted_at IS NULL
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """
        )
        try:
            with Session(self.engine) as session:
                row = session.execute(query, {"emp_id": emp_id}).mappings().first()
            if not row:
                return fallback
            device_id = (row.get("device_id") or "").strip()
            device_type = (row.get("device_type") or "").strip() or "WEB"
            header: Dict[str, str] = {"device_type": device_type}
            if device_id:
                header["device_id"] = device_id
            return header
        except Exception as e:
            logger.warning("Failed to read otp_logs for empId %s: %s", emp_id, str(e))
            return fallback

    def _build_hrms_wrapped_body(
        self,
        jwt_token: str,
        body: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Convert payload to RequestInterceptor-friendly shape:
        { Header: {device_id, device_type}, Request: { data: <original body> } }.
        """
        emp_id = self._extract_emp_id_from_token(jwt_token)
        header = self._latest_device_header_for_emp(emp_id)
        return {
            "Header": header,
            "Request": {"data": body or {}},
        }
    
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
        wrapped_body = self._build_hrms_wrapped_body(jwt_token, body)
        
        url = f"{self.base_url}{endpoint}"
        logger.info("HRMS API request: %s %s", method, endpoint)
        if settings.DEBUG:
            logger.debug(
                "HRMS request details endpoint=%s params=%s body_keys=%s token=%s",
                endpoint,
                params,
                list((body or {}).keys()),
                self._masked_token(jwt_token),
            )

        try:
            if method == "POST":
                response = await self.http_client.post(url, json=wrapped_body, headers=headers)
            elif method == "GET":
                response = await self.http_client.get(url, params=params, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            logger.info(
                "HRMS API response: %s %s status=%s",
                method,
                endpoint,
                response.status_code,
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
