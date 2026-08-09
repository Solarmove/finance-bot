from aiogram.types import Message

from app.bot.controllers.base import BotController
from app.bot.views import help_message, unknown_message


class StaticController(BotController):
    async def help(self, message: Message) -> None:
        await self.answer(message, help_message())

    async def unknown(self, message: Message) -> None:
        await self.answer(message, unknown_message())
