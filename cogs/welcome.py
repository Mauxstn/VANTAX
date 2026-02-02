import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Modal, TextInput
from discord.utils import get
import json
import os
import traceback

VANTAX_COLOR = discord.Color.blurple()
VANTAX_FOOTER = "VANTAX Discord Bot by Maurice"
WELCOME_CONFIG_FILE = "welcome_config.json"

class WelcomeConfigModal(Modal, title="Willkommens-Nachricht anpassen"):
    def __init__(self, cog, guild_id):
        super().__init__()
        self.cog = cog
        self.guild_id = guild_id
        
        # Load current config
        config = self.cog.load_config()
        guild_config = config.get(str(guild_id), {})
        
        self.title_input = TextInput(
            label="Titel",
            placeholder="Willkommen auf unserem Server!",
            default=guild_config.get("title", "Willkommen!"),
            required=True,
            max_length=100
        )
        
        self.description_input = TextInput(
            label="Beschreibung",
            placeholder="Hey {user}! Wir freuen uns, dich hier zu haben!",
            default=guild_config.get("description", "Wir freuen uns, dich hier zu haben!"),
            required=True,
            max_length=500,
            style=discord.TextStyle.paragraph
        )
        
        self.footer_input = TextInput(
            label="Footer",
            placeholder="Viel Spaß auf dem Server!",
            default=guild_config.get("footer", "Viel Spaß auf dem Server!"),
            required=True,
            max_length=100
        )
        
        self.color_input = TextInput(
            label="Farbe (Hex)",
            placeholder="#00ff00 oder grün/blau/rot",
            default=guild_config.get("color", "#00ff00"),
            required=True,
            max_length=20
        )
        
        self.add_item(self.title_input)
        self.add_item(self.description_input)
        self.add_item(self.footer_input)
        self.add_item(self.color_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Parse color
            color = self.parse_color(self.color_input.value)
            
            # Save config
            config = self.cog.load_config()
            guild_id = str(self.guild_id)
            
            if guild_id not in config:
                config[guild_id] = {}
            
            config[guild_id].update({
                "title": self.title_input.value,
                "description": self.description_input.value,
                "footer": self.footer_input.value,
                "color": self.color_input.value,
                "custom_color": color,
                "thumbnail": True,  # Default settings
                "member_count": True,
                "join_date": True,
                "auto_role": True
            })
            
            self.cog.save_config(config)
            
            # Show preview
            embed = self.cog.create_welcome_embed(
                interaction.user,
                interaction.guild,
                config[guild_id]
            )
            
            await interaction.response.send_message(
                "✅ Willkommens-Konfiguration gespeichert! Hier ist eine Vorschau:",
                embed=embed,
                ephemeral=True
            )
            
        except Exception as e:
            print(f"Error saving welcome config: {e}")
            await interaction.response.send_message(
                "❌ Fehler beim Speichern der Konfiguration!",
                ephemeral=True
            )
    
    def parse_color(self, color_str):
        """Parse color string to discord.Color"""
        color_str = color_str.strip().lower()
        
        # Try hex color
        if color_str.startswith('#'):
            try:
                return discord.Color(int(color_str[1:], 16))
            except ValueError:
                pass
        
        # Try named colors
        color_map = {
            'rot': discord.Color.red(),
            'grün': discord.Color.green(),
            'blau': discord.Color.blue(),
            'gelb': discord.Color.yellow(),
            'orange': discord.Color.orange(),
            'lila': discord.Color.purple(),
            'schwarz': discord.Color.dark_grey(),
            'weiß': discord.Color.white(),
            'red': discord.Color.red(),
            'green': discord.Color.green(),
            'blue': discord.Color.blue(),
            'yellow': discord.Color.yellow(),
            'orange': discord.Color.orange(),
            'purple': discord.Color.purple(),
            'black': discord.Color.dark_grey(),
            'white': discord.Color.white()
        }
        
        return color_map.get(color_str, discord.Color.green())

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = self.load_config()
    
    def load_config(self):
        if os.path.exists(WELCOME_CONFIG_FILE):
            with open(WELCOME_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def save_config(self, config):
        # Convert discord.Color objects to hex for JSON serialization
        serializable_config = {}
        for guild_id, guild_config in config.items():
            serializable_config[guild_id] = guild_config.copy()
            if 'color' in serializable_config[guild_id] and hasattr(serializable_config[guild_id]['color'], 'value'):
                serializable_config[guild_id]['color'] = serializable_config[guild_id]['color'].value
        
        with open(WELCOME_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(serializable_config, f, indent=4, ensure_ascii=False)
        self.config = config
    
    def create_welcome_embed(self, member, guild, config):
        """Create welcome embed based on configuration"""
        # Use custom color if available, otherwise default
        color = config.get("custom_color", discord.Color.green())
        
        embed = discord.Embed(
            title=config.get("title", "Willkommen!"),
            description=config.get("description", "Wir freuen uns, dich hier zu haben!").replace(
                "{user}", member.mention
            ).replace(
                "{username}", member.name
            ).replace(
                "{server}", guild.name
            ),
            color=color
        )
        
        # Add thumbnail if enabled
        if config.get("thumbnail", True):
            embed.set_thumbnail(url=member.display_avatar.url)
        
        # Add member count if enabled
        if config.get("member_count", True):
            embed.add_field(
                name="👥 Mitglieder",
                value=f"Du bist das **{guild.member_count}te** Mitglied!",
                inline=True
            )
        
        # Add join date if enabled
        if config.get("join_date", True):
            embed.add_field(
                name="📅 Beigetreten",
                value=member.joined_at.strftime("%d.%m.%Y %H:%M"),
                inline=True
            )
        
        # Add account creation date
        embed.add_field(
            name="🎂 Account erstellt",
            value=member.created_at.strftime("%d.%m.%Y"),
            inline=True
        )
        
        # Set footer
        embed.set_footer(text=config.get("footer", "Viel Spaß auf dem Server!"))
        
        return embed
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        guild = member.guild
        guild_id = str(guild.id)
        
        # Get configuration for this guild
        guild_config = self.config.get(guild_id, {})
        
        # Find welcome channel - prioritize the specific channel ID 1466118269663580396
        channel = None
        target_channel_id = 1466118269663580396
        
        # First try the specific channel ID
        channel = guild.get_channel(target_channel_id)
        
        # If not found, try configured welcome channel
        if not channel:
            welcome_channel = guild_config.get("welcome_channel")
            if welcome_channel:
                try:
                    channel = guild.get_channel(int(welcome_channel))
                except (ValueError, TypeError):
                    pass
        
        # Fallback to default channel names
        if not channel:
            welcome_channel_names = ["willkommen", "welcome", "allgemein"]
            for name in welcome_channel_names:
                channel = get(guild.text_channels, name=name)
                if channel:
                    break
        
        # Create and send welcome embed
        try:
            if channel:
                embed = self.create_welcome_embed(member, guild, guild_config)
                await channel.send(embed=embed)
                print(f"Welcome message sent to channel {channel.id} for member {member.name}")
            else:
                print(f"No welcome channel found for guild {guild.name}")
        except Exception as e:
            print(f"Fehler beim Senden der Willkommensnachricht: {e}")
            print(traceback.format_exc())
        
        # Auto role if enabled
        if guild_config.get("auto_role", True):
            role_names = guild_config.get("auto_roles", ["Mitglied", "Member", "Willkommen"])
            
            for role_name in role_names:
                role = get(guild.roles, name=role_name)
                if role:
                    try:
                        await member.add_roles(role, reason="Willkommensrolle")
                        break
                    except Exception as e:
                        print(f"Fehler beim Rollen vergeben: {e}")
                        print(traceback.format_exc())
        
        # Logging in log channel
        log_channel = None
        log_channel_id = guild_config.get("log_channel")
        
        if log_channel_id:
            try:
                log_channel = guild.get_channel(int(log_channel_id))
            except (ValueError, TypeError):
                pass
        
        # Fallback to default log channel names
        if not log_channel:
            log_channel_names = ["log", "logs", "join-log"]
            for name in log_channel_names:
                log_channel = get(guild.text_channels, name=name)
                if log_channel:
                    break
        
        if log_channel:
            try:
                log_embed = discord.Embed(
                    title="👋 Mitglied beigetreten",
                    color=discord.Color.green()
                )
                log_embed.add_field(name="Mitglied", value=member.mention, inline=True)
                log_embed.add_field(name="ID", value=member.id, inline=True)
                log_embed.add_field(name="Account erstellt", value=member.created_at.strftime("%d.%m.%Y"), inline=True)
                log_embed.set_thumbnail(url=member.display_avatar.url)
                log_embed.set_footer(text=VANTAX_FOOTER)
                
                await log_channel.send(embed=log_embed)
            except Exception as e:
                print(f"Fehler beim Logging: {e}")
                print(traceback.format_exc())
    
    @app_commands.command(name="welcome", description="Konfiguriere die Willkommens-Nachricht für den Server.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def welcome_config(self, interaction: discord.Interaction):
        """Open welcome configuration modal"""
        modal = WelcomeConfigModal(self, interaction.guild.id)
        await interaction.response.send_modal(modal)
    
    @app_commands.command(name="setwelcomechannel", description="Setze den Willkommens-Channel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_welcome_channel(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        """Set the welcome channel"""
        if not channel:
            channel = interaction.channel
        
        config = self.load_config()
        guild_id = str(interaction.guild.id)
        
        if guild_id not in config:
            config[guild_id] = {}
        
        config[guild_id]["welcome_channel"] = str(channel.id)
        self.save_config(config)
        
        await interaction.response.send_message(
            f"✅ Willkommens-Channel wurde auf {channel.mention} gesetzt!",
            ephemeral=True
        )
    
    @app_commands.command(name="setlogchannel", description="Setze den Log-Channel für Member-Joins.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_log_channel(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        """Set the log channel"""
        if not channel:
            channel = interaction.channel
        
        config = self.load_config()
        guild_id = str(interaction.guild.id)
        
        if guild_id not in config:
            config[guild_id] = {}
        
        config[guild_id]["log_channel"] = str(channel.id)
        self.save_config(config)
        
        await interaction.response.send_message(
            f"✅ Log-Channel wurde auf {channel.mention} gesetzt!",
            ephemeral=True
        )
    
    @app_commands.command(name="previewwelcome", description="Zeigt eine Vorschau der Willkommens-Nachricht.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def preview_welcome(self, interaction: discord.Interaction):
        """Show preview of welcome message"""
        config = self.load_config()
        guild_config = config.get(str(interaction.guild.id), {})
        
        embed = self.create_welcome_embed(interaction.user, interaction.guild, guild_config)
        
        await interaction.response.send_message(
            "📋 Vorschau der Willkommens-Nachricht:",
            embed=embed,
            ephemeral=True
        )
    
    @app_commands.command(name="testwelcome", description="Sendet eine Test-Willkommens-Nachricht.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def test_welcome(self, interaction: discord.Interaction):
        """Send a test welcome message to the configured channel"""
        guild = interaction.guild
        guild_id = str(guild.id)
        
        # Get configuration for this guild
        guild_config = self.config.get(guild_id, {})
        
        # Find welcome channel - prioritize the specific channel ID 1466118269663580396
        channel = None
        target_channel_id = 1466118269663580396
        
        # First try the specific channel ID
        channel = guild.get_channel(target_channel_id)
        
        # If not found, try configured welcome channel
        if not channel:
            welcome_channel = guild_config.get("welcome_channel")
            if welcome_channel:
                try:
                    channel = guild.get_channel(int(welcome_channel))
                except (ValueError, TypeError):
                    pass
        
        # Fallback to default channel names
        if not channel:
            welcome_channel_names = ["willkommen", "welcome", "allgemein"]
            for name in welcome_channel_names:
                channel = get(guild.text_channels, name=name)
                if channel:
                    break
        
        # Create and send test welcome embed
        try:
            if channel:
                embed = self.create_welcome_embed(interaction.user, guild, guild_config)
                await channel.send(embed=embed)
                print(f"Test welcome message sent to channel {channel.id} by {interaction.user.name}")
                
                await interaction.response.send_message(
                    f"✅ Test-Willkommens-Nachricht wurde in {channel.mention} gesendet!",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "❌ Kein Willkommens-Channel gefunden!",
                    ephemeral=True
                )
        except Exception as e:
            print(f"Fehler beim Senden der Test-Willkommensnachricht: {e}")
            print(traceback.format_exc())
            await interaction.response.send_message(
                "❌ Fehler beim Senden der Test-Nachricht!",
                ephemeral=True
            )
    
    @app_commands.command(name="setwelcomeroles", description="Setze die automatischen Willkommens-Rollen.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_welcome_roles(self, interaction: discord.Interaction, roles: str):
        """Set auto-assign roles (comma separated)"""
        role_names = [name.strip() for name in roles.split(",")]
        
        config = self.load_config()
        guild_id = str(interaction.guild.id)
        
        if guild_id not in config:
            config[guild_id] = {}
        
        config[guild_id]["auto_roles"] = role_names
        self.save_config(config)
        
        await interaction.response.send_message(
            f"✅ Willkommens-Rollen wurden auf: {', '.join(role_names)} gesetzt!",
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(Welcome(bot))
