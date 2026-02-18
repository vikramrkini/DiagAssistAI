import re
from typing import Annotated

from pydantic import AfterValidator

# Keep validation strict enough for obvious bad inputs while allowing demo domains
# such as *.local used by seed data.
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_email(value: str) -> str:
    email = value.strip().lower()
    if not EMAIL_REGEX.fullmatch(email):
        raise ValueError("value is not a valid email address")
    return email


AppEmail = Annotated[str, AfterValidator(validate_email)]
