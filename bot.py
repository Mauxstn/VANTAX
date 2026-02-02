import os
import discord
import logging
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import json
from typing import Optional, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('vantax.log')
    ]
)
logger = logging.getLogger('vantax')

# Branding
VANTAX_COLOR = discord.Color.blurple()
VANTAX_FOOTER = "VANTAX Discord Bot by Maurice"
VANTAX_OWNER_ID = 536529309133701121  # <--- DEINE DISCORD ID HIER EINGETRAGEN!

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

if not TOKEN:
    logger.error("No token found in .env file!")
    raise ValueError("Missing DISCORD_TOKEN in .env file")

# Configure intents
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True
intents.members = True

class VantaxBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned_or('!'),
            intents=intents,
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name="/help"
            ),
            status=discord.Status.online
        )
        self.initial_extensions = [
            'cogs.moderation',
            'cogs.fun',
            'cogs.info',
            'cogs.welcome',
            'cogs.level',
            'cogs.serverstats',
            'cogs.ticket',
            'cogs.utility',  # Add the new utility cog
            'cogs.poll',  # Add poll cog
            'cogs.reminder',  # Add reminder cog
            'cogs.birthday',  # Add birthday cog
            'cogs.automod',  # Add automod cog
            'cogs.antiraid',  # Add antiraid cog
            'cogs.security',  # Add security cog
            'cogs.database',  # Add database cog
        ]
        self.logger = logger

    async def setup_hook(self):
        # Load all extensions
        for ext in self.initial_extensions:
            try:
                await self.load_extension(ext)
                self.logger.info(f'Successfully loaded extension: {ext}')
            except Exception as e:
                self.logger.error(f'Failed to load extension {ext}: {e}')
                
        # Sync application commands
        try:
            synced = await self.tree.sync()
            self.logger.info(f'Synced {len(synced)} commands')
        except Exception as e:
            self.logger.error(f'Failed to sync commands: {e}')
            
        self.logger.info(f'Successfully logged in as {self.user} (ID: {self.user.id})')

bot = VantaxBot()

@bot.tree.command(name="sync", description="Synced alle Bot Commands (Nur für Owner).")
@commands.is_owner()
async def sync_commands(interaction: discord.Interaction):
    try:
        # Clear all existing commands first
        await bot.tree.sync()
        synced = await bot.tree.sync()
        await interaction.response.send_message(f"✅ Erfolgreich {len(synced)} Commands synchronisiert!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Fehler beim Synchronisieren: {e}", ephemeral=True)

@bot.tree.command(name="forcesync", description="Force-resync alle Commands (Nur für Owner).")
@commands.is_owner()
async def force_sync_commands(interaction: discord.Interaction):
    try:
        # Clear all commands and resync
        bot.tree.clear_commands()
        synced = await bot.tree.sync()
        await interaction.response.send_message(f"🔄 Force-Sync abgeschlossen! {len(synced)} Commands neu registriert.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Force-Sync fehlgeschlagen: {e}", ephemeral=True)

@bot.tree.command(name="help", description="Zeigt alle Befehle von VANTAX an.")
async def help_slash(interaction: discord.Interaction):
    embed = discord.Embed(title="VANTAX Hilfe", color=VANTAX_COLOR, description="Hier sind alle wichtigen Befehle:")
    
    # Allgemeine Befehle
    embed.add_field(name="ℹ️ Allgemein", value="""
    `/help` - Zeigt diese Übersicht
    `/funktionen` - Zeigt alle Funktionen des Bots
    `/userinfo [mitglied]` - Infos über einen User
    `/weather [stadt]` - Zeigt Wetter für eine Stadt
    `/serverinfo` - Infos über den Server
    `/botinfo` - Infos über den Bot
    `/welcome` - Konfiguriere Willkommens-Nachricht
    `/setwelcomechannel [#channel]` - Setze Willkommens-Channel
    `/testwelcome` - Sende Test-Willkommens-Nachricht
    `/previewwelcome` - Zeige Vorschau der Willkommens-Nachricht
    """, inline=False)
    
    # Spaß Befehle
    embed.add_field(name="🎉 Spaß", value="""
    `/meme` - Zeigt ein zufälliges Meme
    `/zufall [min] [max]` - Generiert eine Zufallszahl
    `/love @person` - Sende eine Liebesnachricht ❤️
    `/heart @person` - Sende ein großes Herz 💝
    `/iloveyou @person` - Sende ein riesiges Herz mit "I LOVE YOU" 💕
    `/cuddle @person` - Sende süße Kuschelnachricht 🤗
    `/hug @person` - Sende liebevolle Umarmung 🫂
    `/kiss @person` - Sende einen Kuss 💋
    `/fuck @person` - Sende explizite Nachricht 🔞
    `/poll [frage] [optionen]` - Erstelle eine Umfrage
    `/endpoll [id]` - Beendet eine Umfrage
    `/remind [zeit] [nachricht]` - Setze eine Erinnerung
    `/reminders` - Zeigt deine Erinnerungen
    `/delreminder [nachricht]` - Löscht eine Erinnerung
    `/birthday [tag] [monat] [jahr]` - Setze deinen Geburtstag 🎂
    `/birthdays` - Zeige alle Geburtstage
    `/automod` - AutoMod Konfiguration 🛡️
    `/antiraid` - AntiRaid Konfiguration 🚨
    `/security` - Security System Overview 🔐
    `/2fa` - Generate 2FA Code 🔐
    `/auditlog` - View Audit Log 📊
    `/ratelimits` - Configure Rate Limits ⚡
    `/memory` - Memory Management 💾
    `/database` - Database Management 🗄️
    """, inline=False)
    
    # Levelsystem
    embed.add_field(name="🏆 Levelsystem", value="""
    `/level [mitglied]` - Zeigt dein Level an
    `/leaderboard` - Zeigt die Top 10 Nutzer
    """, inline=False)
    
    # Moderation
    embed.add_field(name="🛡️ Moderation", value="""
    `/kick @mitglied [grund]` - Kickt ein Mitglied
    `/ban @mitglied [grund]` - Bannt ein Mitglied
    `/clear [anzahl]` - Löscht Nachrichten
    `/modlogs [limit]` - Zeigt Moderations-Logs
    """, inline=False)
    
    # Ticketsystem
    embed.add_field(name="🎫 Ticketsystem", value="""
    `/ticket` - Erstellt ein Ticket
    `/close_ticket` - Schließt das aktuelle Ticket
    """, inline=False)
    
    embed.set_footer(text=VANTAX_FOOTER)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="funktionen", description="Zeigt alle Funktionen von VANTAX als Übersicht an.")
async def funktionen_slash(interaction: discord.Interaction):
    embed = discord.Embed(title="VANTAX Funktionen", color=VANTAX_COLOR)
    embed.add_field(name="Moderation", value="/kick, /ban, /clear mit Bestätigung und Logging, /modlogs", inline=False)
    embed.add_field(name="Begrüßung & Logging", value="Customizable Willkommens-Embeds, Rollenvergabe, Log-Channel für Join/Leave/Ban usw.", inline=False)
    embed.add_field(name="Level & XP", value="Automatisches XP-System, /level, /leaderboard", inline=False)
    embed.add_field(name="Fun", value="/meme (mit Button), /zufall (mit Button), /love, /heart, /iloveyou, /cuddle, /hug, /kiss, /fuck, /poll, /endpoll, /remind, /reminders, /delreminder, /birthday, /birthdays", inline=False)
    embed.add_field(name="Sicherheit", value="/automod (Schutz vor Spam, Bad Words, etc.), /antiraid (Raid-Schutz, Lockdown), /security (2FA, Rate Limits, Audit Logging, Memory Management)", inline=False)
    embed.add_field(name="Datenbank", value="/database (SQLite/MySQL/PostgreSQL Support, Backup, Query, Management)", inline=False)
    embed.add_field(name="Info", value="/userinfo, /serverinfo, /botinfo, /status", inline=False)
    embed.add_field(name="Musik", value="/play, /queue, /skip, /pause, /resume, /stop (mit Queue, YouTube-Download und Buttons)", inline=False)
    embed.add_field(name="ServerStats", value="/serverstats zeigt Mitglieder, Kanäle, Online-User", inline=False)
    embed.add_field(name="Ticketsystem", value="/ticket (Ticket-Channel erstellen), /close_ticket (Ticket schließen)", inline=False)
    embed.add_field(name="Owner", value="/vantaxinfo, /vantaxsay (nur für Maurice)", inline=False)
    embed.set_footer(text="von mauxstn")
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Globales Error-Handling
@bot.tree.error
async def on_tree_error(interaction, error):
    embed = discord.Embed(title="Fehler", description=str(error), color=discord.Color.red())
    embed.set_footer(text=VANTAX_FOOTER)
    try:
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except:
        pass

@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user} (ID: {bot.user.id})')
    logger.info('------')

bot.run(TOKEN)
