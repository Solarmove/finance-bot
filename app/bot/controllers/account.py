from aiogram.types import Message

from app.application.services import FinanceService
from app.bot.chat import is_private_chat
from app.bot.controllers.base import BotController
from app.bot.views import api_key_created, api_key_private_only, welcome


class AccountController(BotController):
    def __init__(self, finance_service: FinanceService) -> None:
        self._finance_service = finance_service

    async def start(self, message: Message) -> None:
        if message.from_user is None:
            return
        registration = await self._finance_service.ensure_user(
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name,
        )
        await self.answer(
            message,
            welcome(registration.api_key, is_private_chat(message.chat.type)),
        )

    async def rotate_api_key(self, message: Message) -> None:
        if message.from_user is None:
            return
        if not is_private_chat(message.chat.type):
            await self.answer(message, api_key_private_only())
            return

        registration = await self._finance_service.ensure_user(
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name,
        )
        is_rotation = registration.api_key is None
        api_key = (
            registration.api_key
            if registration.api_key
            else await self._finance_service.rotate_api_key(message.from_user.id)
        )
        await self.answer(message, api_key_created(api_key, is_rotation))
