import discord
from discord.ext import commands
from discord import app_commands

class ServerStatsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="serverstats", description="Zeigt Serverstatistiken als Embed an.")
    async def serverstats(self, interaction: discord.Interaction):
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("Nur auf Servern verfügbar.", ephemeral=True)
            return
        total_members = guild.member_count
        online_members = sum(1 for m in guild.members if m.status != discord.Status.offline)
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        embed = discord.Embed(title=f"📊 Serverstatistiken für {guild.name}", color=discord.Color.blurple())
        embed.add_field(name="Mitglieder", value=str(total_members))
        embed.add_field(name="Online", value=str(online_members))
        embed.add_field(name="Textkanäle", value=str(text_channels))
        embed.add_field(name="Sprachkanäle", value=str(voice_channels))
        embed.set_thumbnail(url=guild.icon.url if guild.icon else discord.Embed.Empty)
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(ServerStatsCog(bot))
