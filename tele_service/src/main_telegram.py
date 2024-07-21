import asyncio
import configparser
import json
import os

import requests
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters.command import Command
from aiogram.types import Message
from dotenv import load_dotenv
from loguru import logger

lg = logger.info

load_dotenv("../.env")

url = "http://127.0.0.1:5000"
# token – Telegram Bot token Obtained from telegram @BotFather
token = os.environ["TELEGRAM_BOT_TOKEN"]

bot = Bot(token)
dp = Dispatcher()


# handling command /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):

    healthcheck = requests.get(url + "/healthcheck").json().get("message")
    response = f""""Hello, I'm a bot that can save and retrieve your notes with semantic search.
    
    Server status: {healthcheck}
    """
    await message.answer(response)


@dp.message(Command("save"))
async def save_doc(message: types.Message):

    payload = {}
    payload["message_id"] = message.message_id
    payload["text"] = message.text.replace("/save ", "")

    lg(payload)

    send_message = requests.post(url + "/send_message", json=payload)
    if send_message.status_code == 200:
        response = send_message.json()
        lg(response)
        await message.answer("Message saved")
    else:
        await message.answer("Server error, please retry")
    # Save


@dp.message(F.text)
async def retrieve_doc(message: types.Message):

    payload = {}
    payload["message_id"] = message.message_id
    payload["text"] = message.text
    lg(payload)
    get_message = requests.post(url + "/get_message", json=payload)
    lg(get_message)

    if get_message.status_code == 200:
        response = get_message.json()

        lg(response)
        await message.answer(response)
    else:
        await message.answer("Server error, please retry")


# @dp.message(F.text)
# async def receive_prompt(message: Message):
#     print(message)
#     jsonData = {"message": prompt}
#     jsonResponse = requests.post(url + "/send_message", json=json.dumps(jsonData))
#     response = jsonResponse.json()
#     await message.answer(response["message"])


# initialize polling to wait for incoming messages
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
