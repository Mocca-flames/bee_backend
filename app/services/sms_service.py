import httpx
from app.config import Settings
from app.services.phone_validator import PhoneValidatorService
from app.utils.logger import setup_logger
from app.models.sms_log import SMSLog
from app.schemas.sms_log import SMSLogCreate
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
import asyncio
import re
import base64

logger = setup_logger()

class SMSService:
    def __init__(self, settings: Settings, db: AsyncSession):
        self.settings = settings
        self.db = db
        self.phone_validator = PhoneValidatorService()
        self.client = httpx.AsyncClient()
        self.api_url = settings.bulksms_api_url
        self.username = settings.bulksms_username.strip()
        self.password = settings.bulksms_password.strip()
        
        # Encode credentials for Basic Authentication
        auth_string = f"{self.username}:{self.password}"
        encoded_auth = base64.b64encode(auth_string.encode('utf-8')).decode('ascii')
        
        self.headers = {
            "Authorization": f"Basic {encoded_auth}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        self.message_templates = {
            "fee_notification": "Dear Parent, {student_name}'s school fees are {fee_status}.",
            "general_announcement": "Dear Parent, {message_body}",
            "custom": "{message_body}"
        }

    def render_message_template(self, template_name: str, **kwargs) -> str:
        """
        Renders a message using a predefined template and provided variables.
        """
        template = self.message_templates.get(template_name)
        if not template:
            raise ValueError(f"Message template '{template_name}' not found.")

        rendered_message = template
        for key, value in kwargs.items():
            rendered_message = rendered_message.replace(f"{{{key}}}", str(value))

        # Remove any remaining unreplaced placeholders
        rendered_message = re.sub(r"\{.*?\}", "", rendered_message)
        return rendered_message

    async def _log_sms_result(self, student_id: Optional[str], recipient_phone: str, 
                             message: str, status: str, error_detail: Optional[str] = None):
        """
        Helper method to log SMS results to database asynchronously.
        """
        try:
            sms_log = SMSLogCreate(
                student_id=student_id,
                recipient_phone=recipient_phone,
                message_content=message,
                status=status,
                error_detail=error_detail
            )
            self.db.add(SMSLog(**sms_log.dict()))
        except Exception as e:
            logger.error(f"Failed to log SMS result to database: {e}")

    async def send_sms(self, to: str, message: str, student_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Sends an SMS message using the BulkSMS API.
        """
        try:
            validated_to = self.phone_validator._clean_and_validate_phone(to)
        except ValueError as e:
            logger.error(f"SMS send failed for student {student_id} to {to}: Invalid phone number - {e}")
            await self._log_sms_result(student_id, to, message, "failed", f"Invalid phone number: {e}")
            return {"status": "failed", "detail": f"Invalid phone number: {e}"}

        payload = {
            "to": [validated_to],
            "body": message,
            "encoding": "UNICODE"
        }

        try:
            response = await self.client.post(
                self.api_url, 
                json=payload, 
                headers=self.headers, 
                timeout=30
            )
            
            # Handle 401 specifically
            if response.status_code == 401:
                error_msg = "Authentication failed - check BulkSMS credentials"
                logger.error(f"SMS send failed: {error_msg}")
                await self._log_sms_result(student_id, validated_to, message, "failed", error_msg)
                return {"status": "failed", "detail": error_msg}
            
            response.raise_for_status()
            response_data = response.json()
            
            # BulkSMS v1 API returns an array of results
            if isinstance(response_data, list) and len(response_data) > 0:
                result = response_data[0]
            elif isinstance(response_data, dict):
                result = response_data
            else:
                logger.error(f"Unexpected response format: {response_data}")
                await self._log_sms_result(student_id, validated_to, message, "failed", 
                                         "Unexpected response format")
                return {"status": "failed", "detail": "Unexpected response format"}

            # Check success status based on BulkSMS v1 API format
            status_obj = result.get("status", {})
            status_type = status_obj.get("type", "")
            result_type = result.get("type", "")
            
            # BulkSMS v1 success indicators
            is_success = (
                status_type == "ACCEPTED" or
                result_type == "SENT" or
                "ACCEPTED" in str(status_type).upper()
            )

            if is_success:
                message_id = result.get("id", "unknown")
                logger.info(f"SMS sent successfully to {validated_to} for student {student_id}. Message ID: {message_id}")
                await self._log_sms_result(student_id, validated_to, message, "success")
                return {"status": "success", "detail": response_data, "message_id": message_id}
            else:
                error_detail = f"Status type: {status_type}, Result type: {result_type}"
                logger.error(f"SMS send failed to {validated_to} for student {student_id}. {error_detail}")
                logger.error(f"Full response: {result}")
                await self._log_sms_result(student_id, validated_to, message, "failed", error_detail)
                return {"status": "failed", "detail": error_detail}

        except httpx.RequestError as e:
            logger.error(f"SMS send failed for student {student_id} to {validated_to}: Network error - {e}")
            await self._log_sms_result(student_id, validated_to, message, "failed", f"Network error: {e}")
            return {"status": "failed", "detail": f"Network error: {e}"}
        
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            logger.error(f"SMS send failed for student {student_id} to {validated_to}: {error_msg}")
            await self._log_sms_result(student_id, validated_to, message, "failed", error_msg)
            return {"status": "failed", "detail": error_msg}
        
        except Exception as e:
            logger.error(f"Unexpected error while sending SMS for student {student_id} to {validated_to}: {e}")
            await self._log_sms_result(student_id, validated_to, message, "failed", f"Unexpected error: {e}")
            return {"status": "failed", "detail": f"Unexpected error: {e}"}

    async def send_bulk_sms(self, recipients: List[str], message: str, batch_size: int = 10, delay: float = 1.0) -> List[Dict[str, Any]]:
        """
        Sends bulk SMS messages to a list of recipients in batches.
        """
        processed_results = []

        for i in range(0, len(recipients), batch_size):
            batch_recipients = recipients[i:i + batch_size]
            tasks = [self.send_sms(to=recipient, message=message) for recipient in batch_recipients]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for j, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Bulk SMS to {batch_recipients[j]} failed with exception: {result}")
                    processed_results.append({"to": batch_recipients[j], "status": "failed", "detail": str(result)})
                else:
                    processed_results.append({"to": batch_recipients[j], **result})

            if i + batch_size < len(recipients):
                await asyncio.sleep(delay)

        return processed_results

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()