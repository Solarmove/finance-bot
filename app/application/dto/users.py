from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class UserDTO:
    id: UUID
    telegram_user_id: int
    username: str | None
    first_name: str | None
    timezone: str


@dataclass(frozen=True, slots=True)
class EnsureUserResult:
    user: UserDTO
    api_key: str | None
