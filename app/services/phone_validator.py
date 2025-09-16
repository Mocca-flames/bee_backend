import re
from typing import Optional

class PhoneValidatorService:
    @staticmethod
    def _clean_and_validate_phone(phone: str) -> str:
        """
        Cleans and validates a South African phone number according to specified rules.
        Ensures it's in 27XXXXXXXXX format (11 characters).
        Raises ValueError for invalid formats.
        """
        original_phone = phone
        digits_only = re.sub(r'\D', '', phone)

        if not digits_only:
            raise ValueError("Phone number cannot be empty.")

        formatted_phone = None

        if original_phone.startswith('0'):
            if len(digits_only) == 10 and digits_only.startswith('0'):
                # Remove leading '0' and prepend '27'
                formatted_phone = '27' + digits_only[1:]
            else:
                raise ValueError(f"Invalid South African phone number format: '{original_phone}'. Numbers starting with '0' must be 10 digits long.")
        elif original_phone.startswith('27'):
            if len(digits_only) == 11 and digits_only.startswith('27'):
                # No change needed, already in '27' format
                formatted_phone = digits_only
            else:
                raise ValueError(f"Invalid South African phone number format: '{original_phone}'. Numbers starting with '27' must be 11 digits long.")
        elif original_phone.startswith('+27'):
            if len(digits_only) == 11 and digits_only.startswith('27'):
                formatted_phone = digits_only
            else:
                raise ValueError(f"Invalid South African phone number format: '{original_phone}'. Numbers starting with '+27' must have 11 digits after the prefix (e.g., '+27721234567').")
        else:
            raise ValueError(f"Invalid South African phone number format: '{original_phone}'. Must start with '0', '27', or '+27'.")

        # Final check for the expected 11-character format (27XXXXXXXXX)
        if len(formatted_phone) != 11:
            raise ValueError(f"Internal error: Formatted phone number '{formatted_phone}' has incorrect length. Expected 11 characters (27XXXXXXXXX).")

        return formatted_phone