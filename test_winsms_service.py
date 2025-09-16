import pytest
from unittest.mock import AsyncMock, patch
from app.config import Settings
from app.services.sms_service import SMSService
from app.schemas.sms_log import SMSLogCreate
from httpx import Response, Request, HTTPStatusError, RequestError

# Fixture for settings
@pytest.fixture
def settings():
    return Settings(
        winsms_api_key="TEST_API_KEY",
        winsms_api_url="https://api.winsms.co.za/api/rest/v1",
        db_user="test",
        db_password="test",
        db_name="test",
        database_url="sqlite+aiosqlite:///./test.db",
        compose_project_name="test"
    )

# Fixture for SMSService with mocked dependencies
@pytest.fixture
def sms_service(settings):
    mock_db_session = AsyncMock()
    service = SMSService(settings=settings, db=mock_db_session)
    service.client = AsyncMock() # Mock the httpx.AsyncClient
    return service

@pytest.mark.asyncio
async def test_send_sms_success(sms_service):
    # Mock successful API response
    sms_service.client.post.return_value = Response(
        status_code=200,
        request=Request("POST", "http://test.com"),
        json={
            "timeStamp": "20240101120000000",
            "version": "1.0",
            "statusCode": 200,
            "messages": [
                {
                    "apiMessageId": 12345678,
                    "acceptedTime": "2024-01-01 12:00:00",
                    "creditCost": 1.0,
                    "newCreditBalance": 99.0,
                    "mobileNumber": "27821234567",
                    "clientMessageId": "your-unique-id-123"
                }
            ]
        }
    )

    to = "27821234567"
    message = "Test message"
    student_id = "test-student-123"
    result = await sms_service.send_sms(to=to, message=message, student_id=student_id)

    assert result["status"] == "success"
    assert result["message_id"] == "12345678"
    sms_service.client.post.assert_called_once()
    sms_service.db.add.assert_called_once()
    logged_sms = sms_service.db.add.call_args[0][0]
    assert logged_sms.recipient_phone == to
    assert logged_sms.message_content == message
    assert logged_sms.status == "success"
    assert logged_sms.api_message_id == "12345678"

@pytest.mark.asyncio
async def test_send_sms_invalid_phone(sms_service):
    to = "invalid-phone"
    message = "Test message"
    student_id = "test-student-123"
    result = await sms_service.send_sms(to=to, message=message, student_id=student_id)

    assert result["status"] == "failed"
    assert "Invalid phone number" in result["detail"]
    sms_service.client.post.assert_not_called()
    sms_service.db.add.assert_called_once()
    logged_sms = sms_service.db.add.call_args[0][0]
    assert logged_sms.status == "failed"
    assert "Invalid phone number" in logged_sms.error_detail

@pytest.mark.asyncio
async def test_send_sms_api_error(sms_service):
    # Mock API error response
    sms_service.client.post.return_value = Response(
        status_code=401,
        request=Request("POST", "http://test.com"),
        json={"errorMessage": "Unauthorized"}
    )

    to = "27821234567"
    message = "Test message"
    student_id = "test-student-123"
    result = await sms_service.send_sms(to=to, message=message, student_id=student_id)

    assert result["status"] == "failed"
    assert "Unauthorized" in result["detail"]
    sms_service.client.post.assert_called_once()
    sms_service.db.add.assert_called_once()
    logged_sms = sms_service.db.add.call_args[0][0]
    assert logged_sms.status == "failed"
    assert "Unauthorized" in logged_sms.error_detail

@pytest.mark.asyncio
async def test_send_sms_network_error(sms_service):
    sms_service.client.post.side_effect = RequestError("Network issue", request=Request("POST", "http://test.com"))

    to = "27821234567"
    message = "Test message"
    student_id = "test-student-123"
    result = await sms_service.send_sms(to=to, message=message, student_id=student_id)

    assert result["status"] == "failed"
    assert "Network error" in result["detail"]
    sms_service.client.post.assert_called_once()
    sms_service.db.add.assert_called_once()
    logged_sms = sms_service.db.add.call_args[0][0]
    assert logged_sms.status == "failed"
    assert "Network error" in logged_sms.error_detail

@pytest.mark.asyncio
async def test_get_credit_balance_success(sms_service):
    sms_service.client.get.return_value = Response(
        status_code=200,
        request=Request("GET", "http://test.com"),
        json={
            "timeStamp": "20240101120000000",
            "version": "1.0",
            "statusCode": 200,
            "creditBalance": 150.5
        }
    )

    result = await sms_service.get_credit_balance()

    assert result["status"] == "success"
    assert result["credit_balance"] == 150.5
    sms_service.client.get.assert_called_once()

@pytest.mark.asyncio
async def test_get_credit_balance_failure(sms_service):
    sms_service.client.get.return_value = Response(
        status_code=500,
        request=Request("GET", "http://test.com"),
        json={"errorMessage": "Internal Server Error"}
    )

    result = await sms_service.get_credit_balance()

    assert result["status"] == "failed"
    assert "Internal Server Error" in result["detail"]
    sms_service.client.get.assert_called_once()

@pytest.mark.asyncio
async def test_send_bulk_sms_success(sms_service):
    sms_service.client.post.return_value = Response(
        status_code=200,
        request=Request("POST", "http://test.com"),
        json={
            "timeStamp": "20240101120000000",
            "version": "1.0",
            "statusCode": 200,
            "messages": [
                {"apiMessageId": 1, "mobileNumber": "27821234567"},
                {"apiMessageId": 2, "mobileNumber": "27827654321"}
            ]
        }
    )

    recipients = ["27821234567", "27827654321"]
    message = "Bulk test message"
    results = await sms_service.send_bulk_sms(recipients=recipients, message=message)

    assert len(results) == 2
    assert all(r["status"] == "success" for r in results)
    assert results[0]["message_id"] == "1"
    assert results[1]["message_id"] == "2"
    sms_service.client.post.assert_called_once()
    assert sms_service.db.add.call_count == 2
    
    logged_sms_1 = sms_service.db.add.call_args_list[0][0][0]
    assert logged_sms_1.recipient_phone == "27821234567"
    assert logged_sms_1.api_message_id == "1"

    logged_sms_2 = sms_service.db.add.call_args_list[1][0][0]
    assert logged_sms_2.recipient_phone == "27827654321"
    assert logged_sms_2.api_message_id == "2"

@pytest.mark.asyncio
async def test_send_bulk_sms_partial_failure_invalid_phone(sms_service):
    sms_service.client.post.return_value = Response(
        status_code=200,
        request=Request("POST", "http://test.com"),
        json={
            "timeStamp": "20240101120000000",
            "version": "1.0",
            "statusCode": 200,
            "messages": [
                {"apiMessageId": 1, "mobileNumber": "27821234567"}
            ]
        }
    )

    recipients = ["27821234567", "invalid-phone"]
    message = "Bulk test message"
    results = await sms_service.send_bulk_sms(recipients=recipients, message=message)

    assert len(results) == 2
    assert results[0]["status"] == "success"
    assert results[0]["message_id"] == "1"
    assert results[1]["status"] == "failed"
    assert "Invalid phone number" in results[1]["detail"]
    
    sms_service.client.post.assert_called_once() # Only called for the valid number
    assert sms_service.db.add.call_count == 2

    logged_sms_1 = sms_service.db.add.call_args_list[0][0][0]
    assert logged_sms_1.recipient_phone == "27821234567"
    assert logged_sms_1.status == "success"
    assert logged_sms_1.api_message_id == "1"

    logged_sms_2 = sms_service.db.add.call_args_list[1][0][0]
    assert logged_sms_2.recipient_phone == "invalid-phone"
    assert logged_sms_2.status == "failed"
    assert "Invalid phone number" in logged_sms_2.error_detail

@pytest.mark.asyncio
async def test_get_message_status_success(sms_service):
    sms_service.client.get.return_value = Response(
        status_code=200,
        request=Request("GET", "http://test.com"),
        json={
            "timeStamp": "20240101120000000",
            "version": "1.0",
            "statusCode": 200,
            "apiMessageId": 12345678,
            "mobileNumber": "27821234567",
            "statusCode": 10,
            "statusDescription": "Delivered",
            "creditCost": 1.0
        }
    )

    api_message_id = 12345678
    result = await sms_service.get_message_status(api_message_id=api_message_id)

    assert result["status"] == "success"
    assert result["detail"]["statusDescription"] == "Delivered"
    sms_service.client.get.assert_called_once_with(
        f"{sms_service.base_url}/sms/outbound/status/{api_message_id}",
        headers=sms_service.headers,
        timeout=30
    )

@pytest.mark.asyncio
async def test_get_message_status_failure(sms_service):
    sms_service.client.get.return_value = Response(
        status_code=404,
        request=Request("GET", "http://test.com"),
        json={"errorMessage": "Message not found"}
    )

    api_message_id = 99999999
    result = await sms_service.get_message_status(api_message_id=api_message_id)

    assert result["status"] == "failed"
    assert "Message not found" in result["detail"]
    sms_service.client.get.assert_called_once()

@pytest.mark.asyncio
async def test_get_multiple_message_statuses_success(sms_service):
    sms_service.client.post.return_value = Response(
        status_code=200,
        request=Request("POST", "http://test.com"),
        json={
            "timeStamp": "20240101120000000",
            "version": "1.0",
            "statusCode": 200,
            "messages": [
                {"apiMessageId": 1, "statusDescription": "Delivered"},
                {"apiMessageId": 2, "statusDescription": "Sent"}
            ]
        }
    )

    api_message_ids = [1, 2]
    result = await sms_service.get_multiple_message_statuses(api_message_ids=api_message_ids)

    assert result["status"] == "success"
    assert len(result["detail"]["messages"]) == 2
    sms_service.client.post.assert_called_once_with(
        f"{sms_service.base_url}/sms/outbound/status",
        json={"apiMessageIds": api_message_ids},
        headers=sms_service.headers,
        timeout=30
    )

@pytest.mark.asyncio
async def test_get_multiple_message_statuses_failure(sms_service):
    sms_service.client.post.return_value = Response(
        status_code=500,
        request=Request("POST", "http://test.com"),
        json={"errorMessage": "Internal Server Error"}
    )

    api_message_ids = [1, 2]
    result = await sms_service.get_multiple_message_statuses(api_message_ids=api_message_ids)

    assert result["status"] == "failed"
    assert "Internal Server Error" in result["detail"]
    sms_service.client.post.assert_called_once()

@pytest.mark.asyncio
async def test_get_incoming_sms_messages_success(sms_service):
    sms_service.client.get.return_value = Response(
        status_code=200,
        request=Request("GET", "http://test.com"),
        json={
            "timeStamp": "20240101120000000",
            "version": "1.0",
            "statusCode": 200,
            "incomingMessages": [
                {"mobileNumber": "27821234567", "message": "Hi", "apiMessageId": 1}
            ]
        }
    )

    result = await sms_service.get_incoming_sms_messages()

    assert result["status"] == "success"
    assert len(result["detail"]["incomingMessages"]) == 1
    sms_service.client.get.assert_called_once_with(
        f"{sms_service.base_url}/sms/inbound",
        headers=sms_service.headers,
        timeout=30
    )

@pytest.mark.asyncio
async def test_get_incoming_sms_messages_failure(sms_service):
    sms_service.client.get.return_value = Response(
        status_code=401,
        request=Request("GET", "http://test.com"),
        json={"errorMessage": "Unauthorized"}
    )

    result = await sms_service.get_incoming_sms_messages()

    assert result["status"] == "failed"
    assert "Unauthorized" in result["detail"]
    sms_service.client.get.assert_called_once()
