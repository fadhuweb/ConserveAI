import re

import bcrypt


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# Password policy — keep these labels in sync with the frontend checklist.
PASSWORD_RULES = [
    ("at least 8 characters", lambda p: len(p) >= 8),
    ("an uppercase letter",   lambda p: bool(re.search(r"[A-Z]", p))),
    ("a lowercase letter",    lambda p: bool(re.search(r"[a-z]", p))),
    ("a number",              lambda p: bool(re.search(r"\d", p))),
    ("a special character",   lambda p: bool(re.search(r"[^A-Za-z0-9]", p))),
]


def password_problems(plain: str) -> list[str]:
    """Return the list of unmet password requirements (empty = valid)."""
    return [label for label, ok in PASSWORD_RULES if not ok(plain or "")]