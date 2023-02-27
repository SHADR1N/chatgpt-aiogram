import asyncio
import logging
import os
from functools import wraps

import aiogram
import openai
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import ChatActions
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from openai import APIError

openai.api_key = os.environ["GPT_TOKEN"]
bot = Bot(token=os.environ["TELEGRAM_TOKEN"], parse_mode="Html")
dp = Dispatcher(bot, storage=MemoryStorage())

# Set up logging
logging.basicConfig(level=logging.INFO)


# Define a conversation state
class ChatState(StatesGroup):
    awaiting_message = State()


AIkwargs = dict(
    engine="text-davinci-003",
    prompt="",
    max_tokens=2048,
    n=1,
    stop=None,
    temperature=0.75,
)
modelAI = openai.Completion.create


class Loading:
    def __init__(self, chat_id: int):
        self.chat_id = chat_id
        self.response = None
        self.keyboard = None

    async def __aenter__(self):
        self.keyboard = types.InlineKeyboardMarkup(row_width=1)
        self.keyboard.add(types.InlineKeyboardButton(text="Новый диалог", callback_data="new dialog"))
        self.message = await bot.send_message(self.chat_id, "Loading...", reply_markup=self.keyboard)

        await bot.send_chat_action(chat_id=self.chat_id, action=ChatActions.TYPING)
        for i in range(3):
            await asyncio.sleep(1)
            await bot.edit_message_text(f"Loading{'.' * (i + 1)}", self.chat_id, self.message.message_id,
                                        reply_markup=self.keyboard)
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        if exc_type:
            await bot.edit_message_text("Oops, something went wrong. Please try again later.", self.chat_id,
                                        self.message.message_id, reply_markup=self.keyboard)
        else:
            if self.response is None or not self.response:
                await bot.edit_message_text("Oops, something went wrong. Please try again later.",
                                            self.chat_id, self.message.message_id,
                                            reply_markup=self.keyboard)
            else:
                await bot.edit_message_text(self.response, self.chat_id, self.message.message_id,
                                            reply_markup=self.keyboard)


def send_typing_action(func):
    """Sends typing action while processing func command."""

    @wraps(func)
    def command_func(update, context, *args, **kwargs):
        context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=ChatActions.TYPING)
        return func(update, context,  *args, **kwargs)

    return command_func


# Define the start command
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.reply("Hi there! I'm a chatbot powered by OpenAI's GPT-3.")


# Define a callback query handler that handles the button clicks
@dp.callback_query_handler(lambda query: query.data == "new dialog", state="*")
async def process_callback_button(callback_query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await bot.answer_callback_query(callback_query.id)
    return await bot.send_message(callback_query.from_user.id, "Новый диалог. Чем я могу вам помочь?")


# Define a message handler that uses GPT-3 to generate a response
@dp.message_handler(state=None)
async def handle_message(message: types.Message, state: FSMContext):
    async with Loading(message.chat.id) as loading:
        async with state.proxy() as data:
            data["awaiting_message"] = "enclose the code in a <code></code> block\n" + message.text
            try:
                AIkwargs["prompt"] = data["awaiting_message"]
                response = modelAI(**AIkwargs)
                loading.response = response.choices[0].text
            except APIError as e:
                logging.error(e)
    await ChatState.awaiting_message.set()


# Define a message handler that uses GPT-3 to continue a conversation
@dp.message_handler(state=ChatState.awaiting_message)
async def handle_continuation(message: types.Message, state: FSMContext):
    async with Loading(message.chat.id) as loading:
        async with state.proxy() as data:

            if data.get("awaiting_message", None):
                data['awaiting_message'] += '\n' + message.text
            else:
                data['awaiting_message'] = message.text

            try:
                AIkwargs["prompt"] = data["awaiting_message"]
                response = modelAI(**AIkwargs)
                loading.response = response.choices[0].text
            except APIError as e:
                logging.error(e)
    await ChatState.awaiting_message.set()


if __name__ == '__main__':
    aiogram.executor.start_polling(dp, skip_updates=True)
