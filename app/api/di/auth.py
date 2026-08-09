from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.api.di.container import FinanceServiceDep
from app.application.dto import UserDTO

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def authenticated_user(
    service: FinanceServiceDep,
    x_api_key: Annotated[str | None, Security(api_key_header)],
) -> UserDTO:
    user = await service.authenticate_api_key(x_api_key or "")
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return user


CurrentUser = Annotated[UserDTO, Depends(authenticated_user)]
