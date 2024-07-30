import asyncio
import configparser
import hashlib
import json
import os

import requests
from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.filters.command import Command
from aiogram.types import Message
from config import user_config
from dotenv import load_dotenv
from loguru import logger

lg = logger.info

load_dotenv("../.env")

if os.environ["RUN_ENV"] == "LOCAL":
    url = "http://127.0.0.1:5000"
    lg(f"Local server. Connecting to {url}")
else:
    url = "http://rag_service:5000"
    lg(f"Remote server. Connecting to {url}")

# token – Telegram Bot token Obtained from telegram @BotFather
token = os.environ["TELEGRAM_BOT_TOKEN"]

bot = Bot(token)
dp = Dispatcher()


# handling command /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):

    credentials = get_creds(message)
    response = f""""Hello, I'm a bot that can save and retrieve your notes with semantic search.
    To authenticate, add your details to the config.py file:
    username: {credentials.get("username")}
    chat_id_hash: {credentials.get("chat_id_hash")}
    
    Once configured, you should be able to run /healthcheck as an authenticated user.
    """
    await message.answer(response)


# All commands below require authentication.
def get_creds(message):
    credentials = {}
    credentials["username"] = message.chat.username
    credentials["chat_id_hash"] = hash_string(str(message.chat.id))
    return credentials


def hash_string(input_string: str) -> str:

    sha256_hash = hashlib.sha256()
    sha256_hash.update(input_string.encode("utf-8"))
    hashed_string = sha256_hash.hexdigest()

    return hashed_string


def auth(credentials):
    if credentials.get("username") == user_config.username:
        if credentials.get("chat_id_hash") in user_config.allowed_chat_id_hash:
            return True
    return False


@dp.message(Command("healthcheck"))
async def cmd_start(message: types.Message):

    if not auth(get_creds(message)):
        response = f"Denied. Unauthenticated user."

    else:
        healthcheck = requests.get(url + "/healthcheck").json().get("message")
        response = f"""User and chat authenticated. 
        Server status: {healthcheck}
        """
    await message.answer(response)


@dp.message(Command("save"))
async def save_doc(message: types.Message):

    if not auth(get_creds(message)):
        response = f"Denied. Unauthenticated user."
        await message.answer(response)
        return

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

    if not auth(get_creds(message)):
        response = f"Denied. Unauthenticated user."
        await message.answer(response)
        return

    lg(message)
    payload = {}
    payload["message_id"] = message.message_id
    payload["text"] = message.text
    lg(payload)
    get_message = requests.post(url + "/get_message", json=payload)
    lg(get_message)

    if get_message.status_code == 200:
        response = get_message.json()

        lg(response)

        escape_response = response

        await message.answer(text=escape_response)
    else:
        await message.answer(text="Server error, please retry")


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
    lg("Started Telegram polling, waiting for messages ...")

    asyncio.run(main())
