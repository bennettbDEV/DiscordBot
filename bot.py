import os
import discord
from discord.ext import tasks, commands
from dotenv import load_dotenv
from datetime import datetime, timedelta
import asyncio

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Set up the bot
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Variable to store the channel name
channel_name = None

def load_channel_name():
    global channel_name
    try:
        with open('channel.txt', 'r') as file:
            channel_name = file.read().strip()
            print(f"Loaded channel name: {channel_name}")
    except FileNotFoundError:
        print("No channel file found. Please set the channel using !setchannel.")

def save_channel_name(name):
    with open('channel.txt', 'w') as file:
        file.write(name)
        print(f"Saved channel name: {name}")

def time_until_2pm():
    now = datetime.now()
    target_time = now.replace(hour=14, minute=0, second=0, microsecond=0)
    if now > target_time:
        target_time += timedelta(days=1)
    return (target_time - now).total_seconds()

@tasks.loop(seconds=86400)
async def send_daily_message():
    await bot.wait_until_ready()

    if channel_name is None:
        print("Error: Channel not set.")
        return

    # Search for the channel by name
    for guild in bot.guilds:
        channel = discord.utils.get(guild.text_channels, name=channel_name)
        if channel:
            message = await channel.send("Hello! Here is your daily update.")
            await message.create_thread(name="Daily Update Discussion", auto_archive_duration=60)
            break
    else:
        print(f"Error: No channel named '{channel_name}' found.")

@bot.command(name='setchannel')
async def set_channel(ctx, *, name: str):
    global channel_name
    channel_name = name
    save_channel_name(channel_name)  # Save the channel name to the file
    await ctx.send(f"Channel set to: {channel_name}")

# add set_time command

@bot.event
async def on_ready():
    print(f'Bot connected as {bot.user}')
    load_channel_name()  # Load the channel name on startup
    await asyncio.sleep(time_until_2pm())
    send_daily_message.start()

if __name__ == "__main__":
    bot.run(TOKEN)
