import asyncio
from app.config import get_settings, Settings
from app.services.sms_service import SMSService
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.logger import setup_logger

logger = setup_logger()

async def run_test_send_sms():
    settings: Settings = get_settings()
    
    # Create a dummy AsyncSession for the test. 
    # In a real application, this would come from a dependency injection.
    # For a simple test script, we'll mock it or use a direct connection if needed.
    # However, SMSService only uses db for logging, so we can pass a mock for now.
    # For a proper test, we'd need a test database setup.
    # For this task, we'll assume the logging part can be skipped or mocked.
    # Let's try to get a real session to ensure full functionality.
    
    # This part needs to be carefully handled as get_db is an async generator.
    # For a standalone script, we might need a simpler way to get a session or mock it.
    # Let's simplify by not using the DB for this test, as the core issue is SMS sending.
    # The SMSService logs to DB, but for a quick test, we can focus on the send part.
    
    # Re-evaluating: SMSService *does* use the db for logging. 
    # We need a way to provide an AsyncSession.
    # For a simple script, we can create a temporary in-memory SQLite DB or mock the session.
    # Given the task is to test SMS sending, let's mock the DB session for now to avoid complex setup.
    
    class MockAsyncSession:
        def add(self, obj):
            logger.info(f"Mock DB: Added {obj.__class__.__name__}")
        async def commit(self):
            logger.info("Mock DB: Committed")
        async def rollback(self):
            logger.info("Mock DB: Rolled back")
        async def execute(self, statement):
            logger.info(f"Mock DB: Executed statement {statement}")
            class MockResult:
                def scalars(self):
                    class MockScalars:
                        def all(self):
                            return []
                    return MockScalars()
            return MockResult()

    mock_db = MockAsyncSession()
    
    sms_service = SMSService(settings, mock_db)

    # Test 1: Get credit balance
    print("Testing credit balance...")
    balance_result = await sms_service.get_balance()
    print(f"Balance result: {balance_result}")
    assert balance_result["status"] == "success", "Failed to get credit balance"
    print("✓ Credit balance test passed")

    # Test 2: Send a single SMS
    test_number = "27669990771"  # Replace with a valid test number in 27XXXXXXXXX format
    test_message = "This is a test message from the WinSMS integration script."

    print(f"\nAttempting to send SMS to: {test_number}")
    print(f"Message: {test_message}")

    send_result = await sms_service.send_sms(to=test_number, message=test_message, student_id="00000000-0000-0000-0000-000000000001")
    print(f"SMS send result: {send_result}")
    assert send_result["status"] == "success", "Failed to send SMS"
    print("✓ SMS sending test passed")

    await sms_service.close()
    print("\nWinSMS integration tests complete.")

if __name__ == "__main__":
    asyncio.run(run_test_send_sms())