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
import socket # Import socket for DNS lookup

logger = setup_logger()

class SMSService:
    def __init__(self, settings: Settings, db: AsyncSession):
        self.settings = settings
        self.db = db
        self.phone_validator = PhoneValidatorService()
        self.client = httpx.AsyncClient(base_url=settings.winsms_api_url)
        self.api_key = settings.winsms_api_key.strip()
        
        self.headers = {
            "AUTHORIZATION": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        logger.info(f"SMSService initialized with Base URL: {settings.winsms_api_url} and API Key (first 5 chars): {self.api_key[:5]}*****")
        
        try:
            # Perform a DNS lookup to check connectivity
            hostname = self.client.base_url.host
            ip_address = socket.gethostbyname(hostname)
            logger.info(f"Successfully resolved {hostname} to {ip_address}")
        except socket.gaierror as e:
            logger.error(f"DNS resolution failed for {hostname}: {e}")
            # Depending on desired behavior, you might want to raise an exception or set a flag here
        
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
                             message: str, status: str, error_detail: Optional[str] = None,
                             api_message_id: Optional[str] = None):
        """
        Helper method to log SMS results to database asynchronously.
        """
        try:
            sms_log = SMSLogCreate(
                student_id=student_id,
                recipient_phone=recipient_phone,
                message_content=message,
                status=status,
                error_detail=error_detail,
                api_message_id=api_message_id
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
            "message": message,
            "recipients": [
                {
                    "mobileNumber": validated_to
                }
            ]
        }

        try:
            response = await self.client.post(
                "/sms/outgoing/send",
                json=payload,
                headers=self.headers,
                timeout=30
            )
            
            response.raise_for_status()
            response_data = response.json()
            
            if response_data.get("statusCode") == 200 and response_data.get("recipients"):
                api_message_id = str(response_data["recipients"][0]["apiMessageId"])
                logger.info(f"SMS sent successfully to {validated_to} for student {student_id}. WinSMS API Message ID: {api_message_id}")
                await self._log_sms_result(student_id, validated_to, message, "success", api_message_id=api_message_id)
                return {"status": "success", "detail": response_data, "message_id": api_message_id}
            else:
                error_msg = response_data.get("errorMessage", "Unknown error from WinSMS API")
                logger.error(f"SMS send failed to {validated_to} for student {student_id}. Error: {error_msg}")
                await self._log_sms_result(student_id, validated_to, message, "failed", error_msg)
                return {"status": "failed", "detail": error_msg}

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

    async def send_bulk_sms(self, recipients: List[str], message: str) -> List[Dict[str, Any]]:
        """
        Sends bulk SMS messages using the WinSMS API.
        """
        messages_payload = []
        processed_results = []

        for recipient in recipients:
            try:
                validated_to = self.phone_validator._clean_and_validate_phone(recipient)
                messages_payload.append({
                    "mobileNumber": validated_to
                })
            except ValueError as e:
                logger.error(f"Bulk SMS failed for recipient {recipient}: Invalid phone number - {e}")
                await self._log_sms_result(None, recipient, message, "failed", f"Invalid phone number: {e}")
                processed_results.append({"to": recipient, "status": "failed", "detail": f"Invalid phone number: {e}"})
        
        if not messages_payload:
            return processed_results # No valid recipients to send to

        payload = {
            "message": message,
            "recipients": messages_payload
        }

        try:
            response = await self.client.post(
                "/sms/outgoing/send",
                json=payload,
                headers=self.headers,
                timeout=30
            )

            response.raise_for_status()
            response_data = response.json()

            if response_data.get("statusCode") == 200 and response_data.get("recipients"):
                for msg_result in response_data["recipients"]:
                    recipient_phone = msg_result.get("mobileNumber")
                    api_message_id = str(msg_result.get("apiMessageId")) if msg_result.get("apiMessageId") else None
                    logger.info(f"Bulk SMS sent successfully to {recipient_phone}. WinSMS API Message ID: {api_message_id}")
                    await self._log_sms_result(None, recipient_phone, message, "success", api_message_id=api_message_id)
                    processed_results.append({
                        "to": recipient_phone,
                        "status": "success",
                        "detail": msg_result,
                        "message_id": api_message_id
                    })
            else:
                error_msg = response_data.get("errorMessage", "Unknown error from WinSMS API")
                logger.error(f"Bulk SMS send failed. Error: {error_msg}")
                # Log failures for all recipients in the payload if the entire request failed
                for msg_data in messages_payload:
                    recipient_phone = msg_data.get("mobileNumber")
                    if recipient_phone not in [res.get("to") for res in processed_results]: # Avoid double logging if already failed due to validation
                        await self._log_sms_result(None, recipient_phone, message, "failed", error_msg)
                        processed_results.append({"to": recipient_phone, "status": "failed", "detail": error_msg})

        except httpx.RequestError as e:
            error_msg = f"Network error: {e}"
            logger.error(f"Bulk SMS send failed: {error_msg}")
            for msg_data in messages_payload:
                recipient_phone = msg_data.get("mobileNumber")
                if recipient_phone not in [res.get("to") for res in processed_results]:
                    await self._log_sms_result(None, recipient_phone, message, "failed", error_msg)
                    processed_results.append({"to": recipient_phone, "status": "failed", "detail": error_msg})
        
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            logger.error(f"Bulk SMS send failed: {error_msg}")
            for msg_data in messages_payload:
                recipient_phone = msg_data.get("mobileNumber")
                if recipient_phone not in [res.get("to") for res in processed_results]:
                    await self._log_sms_result(None, recipient_phone, message, "failed", error_msg)
                    processed_results.append({"to": recipient_phone, "status": "failed", "detail": error_msg})
        
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            logger.error(f"Unexpected error while sending bulk SMS: {e}")
            for msg_data in messages_payload:
                recipient_phone = msg_data.get("mobileNumber")
                if recipient_phone not in [res.get("to") for res in processed_results]:
                    await self._log_sms_result(None, recipient_phone, message, "failed", error_msg)
                    processed_results.append({"to": recipient_phone, "status": "failed", "detail": error_msg})

        return processed_results

    async def get_credit_balance(self) -> Dict[str, Any]:
        """
        Checks the credit balance using the WinSMS API.
        """
        try:
            response = await self.client.get(
                "/credits/balance",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            response_data = response.json()

            if response_data.get("statusCode") == 200:
                credit_balance = response_data.get("creditBalance")
                logger.info(f"WinSMS credit balance: {credit_balance}")
                return {"status": "success", "credit_balance": credit_balance, "detail": response_data}
            else:
                error_msg = response_data.get("errorMessage", "Unknown error getting credit balance from WinSMS API")
                logger.error(f"Failed to get credit balance. Error: {error_msg}")
                return {"status": "failed", "detail": error_msg}

        except httpx.RequestError as e:
            logger.error(f"Failed to get credit balance: Network error - {e}")
            return {"status": "failed", "detail": f"Network error: {e}"}
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            logger.error(f"Failed to get credit balance: {error_msg}")
            return {"status": "failed", "detail": error_msg}
        except Exception as e:
            logger.error(f"Unexpected error while getting credit balance: {e}")
            return {"status": "failed", "detail": f"Unexpected error: {e}"}

    async def get_message_status(self, api_message_id: int) -> Dict[str, Any]:
        """
        Retrieves the status of a single SMS message using the WinSMS API.
        Refactored to use the multiple status endpoint with a single ID.
        """
        return await self.get_multiple_message_statuses(api_message_ids=[api_message_id])

    async def get_multiple_message_statuses(self, api_message_ids: List[int]) -> Dict[str, Any]:
        """
        Retrieves the status of multiple SMS messages using the WinSMS API.
        """
        payload = {"apiMessageIds": api_message_ids}
        try:
            response = await self.client.post(
                "/sms/outgoing/status",
                json=payload,
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            response_data = response.json()

            if response_data.get("statusCode") == 200 and response_data.get("messages"):
                logger.info(f"WinSMS multiple message statuses retrieved for IDs: {api_message_ids}")
                return {"status": "success", "detail": response_data}
            else:
                error_msg = response_data.get("errorMessage", "Unknown error getting multiple message statuses from WinSMS API")
                logger.error(f"Failed to get multiple message statuses for IDs {api_message_ids}. Error: {error_msg}")
                return {"status": "failed", "detail": error_msg}

        except httpx.RequestError as e:
            logger.error(f"Failed to get multiple message statuses for IDs {api_message_ids}: Network error - {e}")
            return {"status": "failed", "detail": f"Network error: {e}"}
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            logger.error(f"Failed to get multiple message statuses for IDs {api_message_ids}: {error_msg}")
            return {"status": "failed", "detail": error_msg}
        except Exception as e:
            logger.error(f"Unexpected error while getting multiple message statuses for IDs {api_message_ids}: {e}")
            return {"status": "failed", "detail": f"Unexpected error: {e}"}

    async def get_incoming_sms_messages(self) -> Dict[str, Any]:
        """
        Retrieves incoming SMS messages using the WinSMS API.
        """
        try:
            response = await self.client.get(
                "/sms/incoming",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            response_data = response.json()

            if response_data.get("statusCode") == 200 and response_data.get("incomingMessages"):
                logger.info(f"WinSMS incoming messages retrieved.")
                return {"status": "success", "detail": response_data}
            else:
                error_msg = response_data.get("errorMessage", "Unknown error getting incoming messages from WinSMS API")
                logger.error(f"Failed to get incoming messages. Error: {error_msg}")
                return {"status": "failed", "detail": error_msg}

        except httpx.RequestError as e:
            logger.error(f"Failed to get incoming messages: Network error - {e}")
            return {"status": "failed", "detail": f"Network error: {e}"}
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            logger.error(f"Failed to get incoming messages: {error_msg}")
            return {"status": "failed", "detail": error_msg}
        except Exception as e:
            logger.error(f"Unexpected error while getting incoming messages: {e}")
            return {"status": "failed", "detail": f"Unexpected error: {e}"}

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
