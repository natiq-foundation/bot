import os
from balethon import Client
from balethon.conditions import private, equals
from balethon.objects import ReplyKeyboard
import requests
import asyncio

BOT_TOKEN = "BOT_TOKEN" #Your BOT token
API_URL = "API_URL" #Request URL

CHANEL_CHAT_ID = 000000000 #Chanel ID

bot = Client(BOT_TOKEN)

@bot.on_message(private & equals("Button 1", "Button 2"))
async def answer_buttons(message):
    print(f"Received message from chat ID: {message.chat.id}")
    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.get(API_URL, timeout=10)
        )

        response.raise_for_status()
        data = response.json()
        verse_text = data.get("text", "Ayah text not Found.")

        await bot.send_message(
            chat_id=CHANEL_CHAT_ID,
            text=f"Recived Ayah:\n{verse_text}"
        )

    except requests.exceptions.ConnectionError:
        await message.reply(f"Error: Cannot connect to API at {API_URL}.")
        print(f"Connection Error: Could not connect to {API_URL}")
    except requests.exceptions.Timeout:
        await message.reply("Error: Request to API timed out.")
        print(f"Timeout Error: Request to {API_URL} timed out.")
    except requests.exceptions.HTTPError as http_err:
        await message.reply(f"HTTP Error from API: {http_err} - Status Code: {response.status_code}")
        print(f"HTTP Error: {http_err} - Status Code: {response.status_code}")
    except Exception as e:
        error_message = str(e)
        print(f"An unexpected error occurred: {error_message}")
        if "no such group or user" in error_message or "chat not found" in error_message or "peer id invalid" in error_message:
             await message.reply(f"Error: Group with ID '{CHANEL_CHAT_ID}' not found or the bot lacks necessary permissions. Please ensure the numerical ID is correct and the bot is a member of the group.")
        else:
            await message.reply(f"Error processing request: {error_message}")

@bot.on_message(private)
async def answer_message(message):
    print(f"Received private message from chat ID: {message.chat.id}")
    await message.reply(
        "Hello! Please select one of the buttons below:",
        ReplyKeyboard(
            ["Button 1"],
            ["Button 2"],
            resize_keyboard=True
        )
    )

if __name__ == "__main__":
    print("Bot is running...")
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        print("Bot stopped.")
    except Exception as e:
        print(f"Critical error in running the bot: {e}")
