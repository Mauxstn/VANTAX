import discord
from discord.ext import commands
from discord import app_commands
import time
import platform
import psutil
import datetime

VANTAX_OWNER_ID = 536529309133701121  # Deine Discord-ID
VANTAX_COLOR = discord.Color.blurple()
VANTAX_FOOTER = "VANTAX Discord Bot by Maurice"

BOT_START_TIME = time.time()

class Owner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="vantaxinfo", description="Geheime Infos und Features für Maurice!")
    async def vantaxinfo(self, interaction: discord.Interaction):
        if interaction.user.id != VANTAX_OWNER_ID:
            await interaction.response.send_message("Nur der Bot-Owner kann diesen Befehl nutzen!", ephemeral=True)
            return
        embed = discord.Embed(title="VANTAX Owner Info", color=VANTAX_COLOR)
        embed.add_field(name="Entwickler", value="Maurice", inline=False)
        embed.add_field(name="Features", value="Levelsystem, Logging, Moderation, Musik, Fun, uvm.")
        embed.add_field(name="Spezial", value="Du bist der Boss! 🦾", inline=False)
        embed.set_footer(text=VANTAX_FOOTER)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="vantaxsay", description="Lasse den Bot als dich sprechen (Owner Only)")
    async def vantaxsay(self, interaction: discord.Interaction, text: str):
        if interaction.user.id != VANTAX_OWNER_ID:
            await interaction.response.send_message("Nur der Bot-Owner kann diesen Befehl nutzen!", ephemeral=True)
            return
        await interaction.response.send_message(text)

    @app_commands.command(name="status", description="Zeigt den aktuellen Bot-Status (Owner Only)")
    async def status(self, interaction: discord.Interaction):
        if interaction.user.id != VANTAX_OWNER_ID:
            await interaction.response.send_message("Nur der Bot-Owner kann diesen Befehl nutzen!", ephemeral=True)
            return
        uptime_sec = int(time.time() - BOT_START_TIME)
        uptime_str = str(datetime.timedelta(seconds=uptime_sec))
        process = psutil.Process()
        mem = process.memory_info().rss / 1024 / 1024
        bot = self.bot
        # Discord-spezifische Werte
        guilds = len(bot.guilds)
        users = len(set(bot.get_all_members()))
        ping = round(bot.latency * 1000)
        embed = discord.Embed(title="VANTAX Bot Status", color=VANTAX_COLOR)
        embed.add_field(name="Uptime", value=uptime_str)
        embed.add_field(name="Server", value=str(guilds))
        embed.add_field(name="User", value=str(users))
        embed.add_field(name="RAM", value=f"{mem:.2f} MB")
        embed.add_field(name="Ping", value=f"{ping} ms")
        embed.add_field(name="Python", value=platform.python_version())
        embed.add_field(name="discord.py", value=discord.__version__)
        embed.set_footer(text=VANTAX_FOOTER)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        # Terminal-Ausgabe
        print("\n===== VANTAX STATUS =====")
        print(f"Uptime:   {uptime_str}")
        print(f"Server:   {guilds}")
        print(f"User:     {users}")
        print(f"RAM:      {mem:.2f} MB")
        print(f"Ping:     {ping} ms")
        print(f"Python:   {platform.python_version()}")
        print(f"discord.py: {discord.__version__}")
        print("========================\n")

async def setup(bot):
    await bot.add_cog(Owner(bot))
