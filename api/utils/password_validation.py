import re
from typing import Optional


def validate_password(password: str, account: str = "") -> Optional[str]:
    """
    Validate password strength per security requirements.
    Returns None if valid, error message string if invalid.

    Rules:
    1. At least 8 characters
    2. Must contain at least 3 of: uppercase, lowercase, digits, special characters
    3. No 4+ consecutive ascending/descending characters (e.g., 1234, abcd, DCBA)
    4. Must not contain the account name (case-insensitive, only checked if account >= 3 chars)
    """
    if len(password) < 8:
        return "Password must be at least 8 characters long"

    type_count = 0
    if re.search(r'[A-Z]', password):
        type_count += 1
    if re.search(r'[a-z]', password):
        type_count += 1
    if re.search(r'[0-9]', password):
        type_count += 1
    if re.search(r'[^A-Za-z0-9]', password):
        type_count += 1
    if type_count < 3:
        return "Password must contain at least 3 of: uppercase, lowercase, digits, special characters"

    if _has_consecutive_sequence(password, 4):
        return "Password must not contain 4 or more consecutive characters (e.g., 1234, abcd, DCBA)"

    if account and len(account) >= 3 and account.lower() in password.lower():
        return "Password must not contain the account name"

    return None


def _has_consecutive_sequence(s: str, min_len: int) -> bool:
    """Check if string contains min_len or more consecutive ascending/descending characters."""
    if len(s) < min_len:
        return False
    lower = s.lower()
    for i in range(len(lower) - min_len + 1):
        is_ascending = True
        is_descending = True
        for j in range(1, min_len):
            if ord(lower[i + j]) != ord(lower[i + j - 1]) + 1:
                is_ascending = False
            if ord(lower[i + j]) != ord(lower[i + j - 1]) - 1:
                is_descending = False
            if not is_ascending and not is_descending:
                break
        if is_ascending or is_descending:
            return True
    return False
