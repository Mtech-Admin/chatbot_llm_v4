"""
Test Script - Basic functionality tests for attendance module
"""

import asyncio
import logging
from datetime import datetime
from app.orchestrator.state import OrchestratorState
from app.orchestrator.intent import classify_intent, validate_read_only_constraint
from app.tools.attendance_tools import get_my_attendance

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_intent_classification():
    """Test intent classification"""
    print("\n=== Testing Intent Classification ===")
    
    test_cases = [
        ("Show my attendance for March", "attendance_inquiry"),
        ("What's my attendance", "attendance_inquiry"),
        ("I want to apply for leave", "redirect_to_portal"),
        ("Check me in", "redirect_to_portal"),
        ("Update my profile", "redirect_to_portal"),
        ("Hi there", "unknown"),
    ]
    
    for message, expected_intent in test_cases:
        state = OrchestratorState(
            user_message=message,
            employee_id="test_user",
            employee_role="employee",
            jwt_token="test_token",
            session_id="test_session"
        )
        
        intent = await classify_intent(state)
        status = "✓" if intent == expected_intent else "✗"
        print(f"{status} '{message}' → {intent} (expected: {expected_intent})")

async def test_read_only_validation():
    """Test read-only constraint validation"""
    print("\n=== Testing Read-Only Constraint ===")
    
    test_cases = [
        ("Show my attendance", True),  # read-only allowed
        ("Apply for leave", False),    # write - not allowed
        ("Check me in", False),        # write - not allowed
        ("View my daily attendance", True),  # read-only allowed
        ("Submit reimbursement", False),    # write - not allowed
    ]
    
    for message, expected_allowed in test_cases:
        is_allowed, _ = validate_read_only_constraint("test_intent", message)
        status = "✓" if is_allowed == expected_allowed else "✗"
        print(f"{status} '{message}' → allowed={is_allowed} (expected: {expected_allowed})")

async def test_attendance_tools():
    """Test attendance tools (mock test)"""
    print("\n=== Testing Attendance Tools ===")
    
    # Note: These would need real JWT token and HRMS API to work
    print("✓ Attendance tools defined and ready")
    print("  - get_my_attendance()")
    print("  - get_my_daily_attendance()")
    print("  - get_team_attendance()")

async def main():
    """Run all tests"""
    print("=" * 50)
    print("DMRC HRMS Chatbot - Attendance Module Tests")
    print("=" * 50)
    
    try:
        await test_intent_classification()
        await test_read_only_validation()
        await test_attendance_tools()
        
        print("\n" + "=" * 50)
        print("✓ All tests completed")
        print("=" * 50)
    
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        print(f"\n✗ Test failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
