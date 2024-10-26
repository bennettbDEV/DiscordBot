import json
import os
import discord
from discord.ext import tasks, commands
from dotenv import load_dotenv
from datetime import datetime, timedelta
import asyncio

# Load environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Variables
selected_channel = None
c_prefix = "$"

# Set up the bot
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix=c_prefix, intents=intents)

SETTINGS_FILE = "settings.json"

def load_settings():
    try:
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"channel_name": None, "hour": 14, "minute": 0}  # Default to 2:00 PM

def save_settings(channel_name=None, hour=None, minute=None):
    settings = load_settings()
    if channel_name is not None:
        settings["channel_name"] = channel_name
    if hour is not None and minute is not None:
        settings["hour"] = hour
        settings["minute"] = minute
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f)


def time_until_reminder(hour, minute):
    now = datetime.now()
    target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if now > target_time:
        target_time += timedelta(days=1)
    return (target_time - now).total_seconds()


@tasks.loop(hours=24)
async def send_daily_message():
    await bot.wait_until_ready()

    settings = load_settings()
    hour, minute = settings["hour"], settings["minute"]
    await asyncio.sleep(await time_until_reminder(hour, minute))

    channel_name = settings.get("channel_name")
    if channel_name is None:
        print("Error: No channel has been set. Use the `$setchannel` command to set one.")
        return

    cur_time = datetime.now()
    date = cur_time.strftime("%m/%d/%Y")

    # Skip weekends
    day_of_week = cur_time.strftime("%w")
    if day_of_week not in range(1,6):
        return
    
    # Search for the channel by name
    channel_found = False
    for guild in bot.guilds:
        channel = discord.utils.get(guild.text_channels, name=channel_name)
        if channel:
            channel_found = True
            message = await channel.send(
                "@everyone remember to post your standup at 2pm!"
            )
            await message.create_thread(
                name=f"{date} Standup", auto_archive_duration=60
            )
            break
    if not channel_found:
        print(f"Error: No channel named '{channel_name}' found.")


@bot.command(name="setchannel")
async def set_channel(ctx, *, channel_name: str):
    save_settings(channel_name=channel_name)
    await ctx.send(f"Reminder channel set to #{channel_name}")

@bot.command(name="settime")
async def set_time(ctx, time_str: str):
    try:
        hour, minute = map(int, time_str.split(":"))
        if not (0 <= hour < 24 and 0 <= minute < 60):
            raise ValueError
        save_settings(hour=hour, minute=minute)
        await ctx.send(f"Reminder time set to {hour:02}:{minute:02}.")
    except ValueError:
        await ctx.send("Please provide a valid time in HH:MM format (24-hour).")


@bot.event
async def on_ready():
    print(f"Bot connected as {bot.user}")
    if not send_daily_message.is_running():
        send_daily_message.start()


if __name__ == "__main__":
    bot.run(TOKEN)
