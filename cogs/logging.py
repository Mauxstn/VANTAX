import discord
from discord.ext import commands
from discord.utils import get

LOG_CHANNEL_NAMES = ["log", "logs", "modlog"]
VANTAX_COLOR = discord.Color.blurple()
VANTAX_FOOTER = "VANTAX Discord Bot by Maurice"

class Logging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_log_channel(self, guild):
        for name in LOG_CHANNEL_NAMES:
            channel = get(guild.text_channels, name=name)
            if channel:
                return channel
        return None

    @commands.Cog.listener()
    async def on_member_join(self, member):
        channel = self.get_log_channel(member.guild)
        if channel:
            embed = discord.Embed(title="Beitritt", description=f"{member} ist beigetreten.", color=VANTAX_COLOR)
            embed.set_footer(text=VANTAX_FOOTER)
            await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        channel = self.get_log_channel(member.guild)
        if channel:
            embed = discord.Embed(title="Verlassen", description=f"{member} hat den Server verlassen.", color=discord.Color.orange())
            embed.set_footer(text=VANTAX_FOOTER)
            await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        channel = self.get_log_channel(guild)
        if channel:
            embed = discord.Embed(title="Ban", description=f"{user} wurde gebannt.", color=discord.Color.red())
            embed.set_footer(text=VANTAX_FOOTER)
            await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        channel = self.get_log_channel(guild)
        if channel:
            embed = discord.Embed(title="Unban", description=f"{user} wurde entbannt.", color=discord.Color.green())
            embed.set_footer(text=VANTAX_FOOTER)
            await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot or not message.guild:
            return
        channel = self.get_log_channel(message.guild)
        if channel:
            embed = discord.Embed(title="Nachricht gelöscht", description=f"Von: {message.author}\nIn: {message.channel.mention}", color=discord.Color.red())
            embed.add_field(name="Inhalt", value=message.content or "[Embed/Datei]", inline=False)
            embed.set_footer(text=VANTAX_FOOTER)
            await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot or not before.guild:
            return
        if before.content == after.content:
            return
        channel = self.get_log_channel(before.guild)
        if channel:
            embed = discord.Embed(title="Nachricht bearbeitet", description=f"Von: {before.author}\nIn: {before.channel.mention}", color=VANTAX_COLOR)
            embed.add_field(name="Vorher", value=before.content or "[Embed/Datei]", inline=False)
            embed.add_field(name="Nachher", value=after.content or "[Embed/Datei]", inline=False)
            embed.set_footer(text=VANTAX_FOOTER)
            await channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Logging(bot))
