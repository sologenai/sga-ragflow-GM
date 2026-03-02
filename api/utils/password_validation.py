import re
from typing import Optional


def validate_password(password: str, account: str = "") -> Optional[str]:
    """
    Validate password strength.
    Returns None when valid; otherwise returns a specific error message.
    """
    if len(password) < 8:
        return "Password must be at least 8 characters long"

    type_count = sum(
        [
            bool(re.search(r"[A-Z]", password)),
            bool(re.search(r"[a-z]", password)),
            bool(re.search(r"[0-9]", password)),
            bool(re.search(r"[^A-Za-z0-9]", password)),
        ]
    )
    if type_count < 3:
        return "Password must contain at least 3 of: uppercase, lowercase, digits, special characters"

    if _has_consecutive_sequence(password, min_len=4):
        return "Password must not contain 4 or more consecutive ascending or descending characters"

    account_tokens = _extract_account_tokens(account)
    password_lower = password.lower()
    if any(token in password_lower for token in account_tokens):
        return "Password must not contain the account name"

    return None


def _extract_account_tokens(account: str) -> set[str]:
    normalized = (account or "").strip().lower()
    if not normalized:
        return set()

    local_part = normalized.split("@", 1)[0]
    tokens: set[str] = set()

    if len(local_part) >= 3:
        tokens.add(local_part)

    # Also block meaningful fragments in email-style usernames such as john.smith.
    for token in re.split(r"[^a-z0-9]+", local_part):
        if len(token) >= 3:
            tokens.add(token)

    return tokens


def _has_consecutive_sequence(value: str, min_len: int) -> bool:
    if len(value) < min_len:
        return False

    lower = value.lower()
    for i in range(len(lower) - min_len + 1):
        window = lower[i : i + min_len]
        if not (window.isdigit() or window.isalpha()):
            continue

        steps = [ord(window[j]) - ord(window[j - 1]) for j in range(1, len(window))]
        if all(step == 1 for step in steps) or all(step == -1 for step in steps):
            return True

    return False
