import json
import os
import discord
from discord.ext import tasks, commands
from dotenv import load_dotenv
from datetime import datetime, timedelta
import asyncio


class ReminderBot(commands.Bot):
    SETTINGS_FILE = "settings.json"

    def __init__(self, command_prefix, intents):
        super().__init__(command_prefix=command_prefix, intents=intents)
        self.c_prefix = command_prefix
        self.military_time = False
        self.load_settings()

    def load_settings(self):
        try:
            with open(self.SETTINGS_FILE, "r") as file:
                self.settings = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            self.settings = {
                "channel_name": None,
                "hour": 14,
                "minute": 0,
            }  # Default to 2:00 PM

    def save_settings(self, channel_name=None, hour=None, minute=None):
        if channel_name is not None:
            self.settings["channel_name"] = channel_name
        if hour is not None and minute is not None:
            self.settings["hour"] = hour
            self.settings["minute"] = minute
        with open(self.SETTINGS_FILE, "w") as file:
            json.dump(self.settings, file)

    def enable_24H(self):
        self.military_time = True

    def disable_24H(self):
        self.military_time = False

    async def get_time_until_reminder(self):
        current_time = datetime.now()
        target_time = current_time.replace(
            hour=self.settings["hour"],
            minute=self.settings["minute"],
            second=0,
            microsecond=0,
        )
        if current_time > target_time:
            target_time += timedelta(days=1)
        return (target_time - current_time).total_seconds()

    @tasks.loop(hours=24)
    async def send_daily_message(self):
        await self.wait_until_ready()
        await asyncio.sleep(await self.get_time_until_reminder())

        cur_time = datetime.now()
        date = cur_time.strftime("%m/%d")

        # Skip weekends
        if cur_time.weekday() >= 5:
            return

        channel_name = self.settings.get("channel_name")
        if channel_name is None:
            print(
                f"Error: No channel has been set. Use the `{self.c_prefix}setchannel` command to set one."
            )
            return

        # Search for the channel
        for guild in self.guilds:
            channel = discord.utils.get(guild.text_channels, name=channel_name)
            if channel:
                h, m = self.settings.get("hour"), self.settings.get("minute")
                if self.military_time:
                    time_msg = f"{h}:{m}"
                else:
                    if h > 12:
                        time_msg = f"{int(h)-12}:{m}pm"
                    else:
                        time_msg = f"{h}:{m}am"
                message = await channel.send(
                    f"@everyone remember to post your standup at {time_msg}!"
                )
                await message.create_thread(
                    name=f"{date} Standup", auto_archive_duration=60
                )
                return
        print(f"Error: No channel named '{channel_name}' found.")

    async def on_ready(self):
        print(f"Bot connected as {self.user}")
        if not self.send_daily_message.is_running():
            self.send_daily_message.start()

    async def is_moderator_check(self, ctx):
        return (
            ctx.author.guild_permissions.manage_messages
            or ctx.author.guild_permissions.ban_members
        )


def main():
    # Load environment variables
    load_dotenv()
    TOKEN = os.getenv("DISCORD_TOKEN")

    # Commands
    @commands.command(name="setchannel")
    async def set_channel(ctx, *, channel_name: str):
        ctx.bot.save_settings(channel_name=channel_name)
        await ctx.send(f"Reminder channel set to #{channel_name}")

    @commands.command(name="settime")
    async def set_time(ctx, time_str: str):
        try:
            hour, minute = map(int, time_str.split(":"))
            if not (0 <= hour < 24 and 0 <= minute < 60):
                raise ValueError
            ctx.bot.save_settings(hour=hour, minute=minute)
            await ctx.send(f"Reminder time set to {hour:02}:{minute:02}.")
        except ValueError:
            await ctx.send("Please provide a valid time in HH:MM format (24-hour).")

    @commands.command(name="enable24H")
    async def enable_24H_format(ctx):
        ctx.bot.enable_24H()
        await ctx.send("24H time format enabled")

    @commands.command(name="disable24H")
    async def disable_24H_format(ctx):
        ctx.bot.disable_24H()
        await ctx.send("12H time format enabled")

    # Setting up the bot and adding commands
    intents = discord.Intents.default()
    intents.messages = True
    intents.message_content = True
    intents.guilds = True
    bot = ReminderBot(command_prefix="$", intents=intents)

    # Ensure all commands are run by moderator
    bot.check(bot.is_moderator_check)

    bot.add_command(set_channel)
    bot.add_command(set_time)
    bot.add_command(enable_24H_format)
    bot.add_command(disable_24H_format)

    # Start bot
    bot.run(TOKEN)


if __name__ == "__main__":
    main()
