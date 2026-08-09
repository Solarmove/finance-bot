import re
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

IDEMPOTENCY_KEY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{8,120}$")


def get_idempotency_key(
    value: Annotated[str, Header(alias="Idempotency-Key")],
) -> str:
    if not IDEMPOTENCY_KEY_PATTERN.fullmatch(value):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "Idempotency-Key must contain 8-120 characters: letters, digits, '.', '_', ':', '-'"
            ),
        )
    return value


IdempotencyKey = Annotated[str, Depends(get_idempotency_key)]
