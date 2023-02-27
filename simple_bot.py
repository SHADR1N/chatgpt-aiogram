import os
import logging
import openai
from aiogram import Bot, Dispatcher, executor, types


# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
openai.api_key = os.environ["GPT_TOKEN"]
bot = Bot(token=os.environ["TELEGRAM_TOKEN"], parse_mode="Html")
dp = Dispatcher(bot)

openai.api_key = "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"


@dp.message_handler(commands='start')
async def cmd_start(message: types.Message):
    await message.answer("How can i help u?")


@dp.message_handler()
async def message_openai(message: types.Message):
    response = openai.Completion.create(
      engine="text-davinci-003",
      prompt=message.text,
      max_tokens=1024,
      n=1,
      stop=None,
      temperature=0.5,
    ).choices[0].text
    await message.answer(response)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
