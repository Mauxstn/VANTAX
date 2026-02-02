import discord
from discord.ext import commands
from discord import app_commands

TICKET_CATEGORY_NAME = "Tickets"
TICKET_ROLE_NAME = "Support"  # Passe ggf. an

class TicketCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ticket", description="Erstellt ein privates Ticket für dich.")
    async def ticket(self, interaction: discord.Interaction):
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("Nur auf Servern verfügbar.", ephemeral=True)
            return
        category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
        if not category:
            category = await guild.create_category(TICKET_CATEGORY_NAME)
        # Prüfe, ob User schon ein Ticket hat
        existing = discord.utils.get(category.channels, name=f"ticket-{interaction.user.name.lower()}")
        if existing:
            await interaction.response.send_message(f"Du hast bereits ein Ticket: {existing.mention}", ephemeral=True)
            return
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True),
        }
        support_role = discord.utils.get(guild.roles, name=TICKET_ROLE_NAME)
        if support_role:
            overwrites[support_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
        channel = await guild.create_text_channel(f"ticket-{interaction.user.name}", category=category, overwrites=overwrites)
        await channel.send(f"Willkommen {interaction.user.mention}! Das Support-Team wird sich um dich kümmern.")
        await interaction.response.send_message(f"Ticket erstellt: {channel.mention}", ephemeral=True)

    @app_commands.command(name="close_ticket", description="Schließt das aktuelle Ticket.")
    async def close_ticket(self, interaction: discord.Interaction):
        channel = interaction.channel
        if channel.category and channel.category.name == TICKET_CATEGORY_NAME:
            await interaction.response.send_message("Ticket wird geschlossen...", ephemeral=True)
            await channel.delete()
        else:
            await interaction.response.send_message("Dies ist kein Ticket-Channel!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(TicketCog(bot))
