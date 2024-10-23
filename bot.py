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


def load_channel_name():
    global selected_channel
    try:
        with open("channel.txt", "r") as file:
            selected_channel = file.read().strip()
            print(f"Loaded channel name: {selected_channel}")
    except FileNotFoundError:
        print(
            f"No channel file found. Please set the channel using {c_prefix}setchannel."
        )


def save_channel_name(name):
    with open("channel.txt", "w") as file:
        file.write(name)
        print(f"Saved channel name: {name}")


def time_until_reminder():
    now = datetime.now()
    target_time = now.replace(hour=13, minute=50, second=0, microsecond=0)
    if now > target_time:
        target_time += timedelta(days=1)
    return (target_time - now).total_seconds()


@tasks.loop(seconds=86400)
async def send_daily_message():
    await bot.wait_until_ready()

    if selected_channel is None:
        print("Error: Channel not set.")
        return
    cur_time = datetime.now()
    date = cur_time.strftime("%m/%d/%Y")
    # Search for the channel by name
    for guild in bot.guilds:
        channel = discord.utils.get(guild.text_channels, name=selected_channel)
        if channel:
            message = await channel.send(
                "@everyone remember to post your standup at 2pm!"
            )
            await message.create_thread(
                name=f"{date} Standup", auto_archive_duration=60
            )
            break
    else:
        print(f"Error: No channel named '{selected_channel}' found.")


@bot.command(name="setchannel")
async def set_channel(ctx, *, name: str):
    global selected_channel
    selected_channel = name
    save_channel_name(selected_channel)  # Save the channel name to the file
    await ctx.send(f"Channel set to: {selected_channel}")


"""
add set_time command later
"""


@bot.event
async def on_ready():
    print(f"Bot connected as {bot.user}")
    load_channel_name()  # Load the channel name on startup
    await asyncio.sleep(time_until_reminder())
    send_daily_message.start()


if __name__ == "__main__":
    bot.run(TOKEN)
