import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import re
import asyncio
from datetime import datetime, timedelta

# Constants
VANTAX_COLOR = discord.Color.blurple()
VANTAX_FOOTER = "VANTAX Discord Bot by Maurice"

class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.automod_file = "automod_config.json"
        self.automod_config = self.load_automod_config()
        self.violations_file = "automod_violations.json"
        self.violations = self.load_violations()
        
        # Start monitoring task
        self.bot.loop.create_task(self.monitor_messages())
    
    def load_automod_config(self):
        try:
            if os.path.exists(self.automod_file):
                with open(self.automod_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"Error loading automod config: {e}")
            return {}
    
    def save_automod_config(self):
        try:
            with open(self.automod_file, 'w', encoding='utf-8') as f:
                json.dump(self.automod_config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving automod config: {e}")
    
    def load_violations(self):
        try:
            if os.path.exists(self.violations_file):
                with open(self.violations_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"Error loading violations: {e}")
            return {}
    
    def save_violations(self):
        try:
            with open(self.violations_file, 'w', encoding='utf-8') as f:
                json.dump(self.violations, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving violations: {e}")
    
    def get_guild_config(self, guild_id):
        guild_id_str = str(guild_id)
        if guild_id_str not in self.automod_config:
            self.automod_config[guild_id_str] = {
                "enabled": False,
                "banned_words": [],
                "spam_protection": {
                    "enabled": False,
                    "max_messages": 5,
                    "time_window": 10,
                    "punishment": "warn"
                },
                "invite_protection": {
                    "enabled": False,
                    "punishment": "delete"
                },
                "mention_protection": {
                    "enabled": False,
                    "max_mentions": 5,
                    "punishment": "warn"
                },
                "caps_protection": {
                    "enabled": False,
                    "max_caps": 70,
                    "min_length": 10,
                    "punishment": "warn"
                },
                "link_protection": {
                    "enabled": False,
                    "allowed_domains": [],
                    "punishment": "delete"
                }
            }
        return self.automod_config[guild_id_str]
    
    def add_violation(self, user_id, guild_id, violation_type):
        user_id_str = str(user_id)
        guild_id_str = str(guild_id)
        
        if user_id_str not in self.violations:
            self.violations[user_id_str] = {}
        
        if guild_id_str not in self.violations[user_id_str]:
            self.violations[user_id_str][guild_id_str] = []
        
        self.violations[user_id_str][guild_id_str].append({
            "type": violation_type,
            "timestamp": datetime.now().isoformat()
        })
        
        self.save_violations()
        return len(self.violations[user_id_str][guild_id_str])
    
    async def monitor_messages(self):
        """Monitor messages for automod violations"""
        await self.bot.wait_until_ready()
        
        while not self.bot.is_closed():
            try:
                # This will be handled in on_message event
                await asyncio.sleep(1)
            except Exception as e:
                print(f"Error in monitor_messages: {e}")
                await asyncio.sleep(5)
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle message monitoring"""
        if message.author.bot:
            return
        
        if not message.guild:
            return
        
        guild_id = str(message.guild.id)
        config = self.get_guild_config(message.guild.id)
        
        if not config.get("enabled", False):
            return
        
        # Check for violations
        await self.check_banned_words(message, config)
        await self.check_spam(message, config)
        await self.check_invites(message, config)
        await self.check_mentions(message, config)
        await self.check_caps(message, config)
        await self.check_links(message, config)
    
    async def check_banned_words(self, message, config):
        """Check for banned words"""
        banned_words = config.get("banned_words", [])
        if not banned_words:
            return
        
        content_lower = message.content.lower()
        for word in banned_words:
            if word.lower() in content_lower:
                await self.handle_violation(message, "banned_word", "Banned word detected")
                break
    
    async def check_spam(self, message, config):
        """Check for spam"""
        spam_config = config.get("spam_protection", {})
        if not spam_config.get("enabled", False):
            return
        
        user_id = str(message.author.id)
        guild_id = str(message.guild.id)
        max_messages = spam_config.get("max_messages", 5)
        time_window = spam_config.get("time_window", 10)
        
        # Count recent messages
        recent_count = 0
        now = datetime.now()
        
        if user_id in self.violations and guild_id in self.violations[user_id]:
            for violation in self.violations[user_id][guild_id]:
                if violation["type"] == "spam":
                    violation_time = datetime.fromisoformat(violation["timestamp"])
                    if (now - violation_time).total_seconds() < time_window:
                        recent_count += 1
        
        if recent_count >= max_messages:
            await self.handle_violation(message, "spam", "Spam detected")
    
    async def check_invites(self, message, config):
        """Check for Discord invites"""
        invite_config = config.get("invite_protection", {})
        if not invite_config.get("enabled", False):
            return
        
        # Pattern for Discord invites
        invite_pattern = r'(discord\.gg/|discord\.com/invite/|discordapp\.com/invite/)[\w-]+'
        if re.search(invite_pattern, message.content, re.IGNORECASE):
            await self.handle_violation(message, "invite", "Discord invite detected")
    
    async def check_mentions(self, message, config):
        """Check for excessive mentions"""
        mention_config = config.get("mention_protection", {})
        if not mention_config.get("enabled", False):
            return
        
        max_mentions = mention_config.get("max_mentions", 5)
        mention_count = len(message.mentions)
        
        if mention_count > max_mentions:
            await self.handle_violation(message, "mentions", f"Too many mentions ({mention_count}/{max_mentions})")
    
    async def check_caps(self, message, config):
        """Check for excessive caps"""
        caps_config = config.get("caps_protection", {})
        if not caps_config.get("enabled", False):
            return
        
        max_caps = caps_config.get("max_caps", 70)
        min_length = caps_config.get("min_length", 10)
        
        if len(message.content) < min_length:
            return
        
        caps_count = sum(1 for c in message.content if c.isupper())
        caps_percentage = (caps_count / len(message.content)) * 100
        
        if caps_percentage > max_caps:
            await self.handle_violation(message, "caps", f"Too many caps ({caps_percentage:.1f}%/{max_caps}%)")
    
    async def check_links(self, message, config):
        """Check for unwanted links"""
        link_config = config.get("link_protection", {})
        if not link_config.get("enabled", False):
            return
        
        # Pattern for URLs
        url_pattern = r'https?://[^\s]+'
        urls = re.findall(url_pattern, message.content)
        
        if not urls:
            return
        
        allowed_domains = link_config.get("allowed_domains", [])
        
        for url in urls:
            domain = url.split('/')[2].lower()
            if not any(allowed in domain for allowed in allowed_domains):
                await self.handle_violation(message, "link", f"Unwanted link detected: {domain}")
                break
    
    async def handle_violation(self, message, violation_type, reason):
        """Handle automod violations"""
        guild_id = str(message.guild.id)
        config = self.get_guild_config(message.guild.id)
        
        # Get punishment for this violation type
        punishment = "warn"
        if violation_type == "banned_word":
            punishment = "delete"
        elif violation_type == "spam":
            punishment = config.get("spam_protection", {}).get("punishment", "warn")
        elif violation_type == "invite":
            punishment = config.get("invite_protection", {}).get("punishment", "delete")
        elif violation_type == "mentions":
            punishment = config.get("mention_protection", {}).get("punishment", "warn")
        elif violation_type == "caps":
            punishment = config.get("caps_protection", {}).get("punishment", "warn")
        elif violation_type == "link":
            punishment = config.get("link_protection", {}).get("punishment", "delete")
        
        # Add violation
        violation_count = self.add_violation(message.author.id, message.guild.id, violation_type)
        
        # Apply punishment
        if punishment == "delete":
            try:
                await message.delete()
                await message.author.send(f"⚠️ Deine Nachricht wurde gelöscht: {reason}")
            except:
                pass
        
        elif punishment == "warn":
            try:
                await message.author.send(f"⚠️ Warnung: {reason}")
            except:
                pass
        
        elif punishment == "kick":
            try:
                await message.guild.kick(message.author, reason=f"AutoMod: {reason}")
            except:
                pass
        
        elif punishment == "ban":
            try:
                await message.guild.ban(message.author, reason=f"AutoMod: {reason}")
            except:
                pass
        
        # Log to channel if configured
        await self.log_violation(message, violation_type, reason, punishment, violation_count)
    
    async def log_violation(self, message, violation_type, reason, punishment, count):
        """Log violations to a channel"""
        try:
            guild_id = str(message.guild.id)
            config = self.get_guild_config(message.guild.id)
            log_channel_id = config.get("log_channel")
            
            if not log_channel_id:
                return
            
            log_channel = message.guild.get_channel(log_channel_id)
            if not log_channel:
                return
            
            embed = discord.Embed(
                title="🛡️ AutoMod Violation",
                description=f"**User:** {message.author.mention}\n**Violation:** {violation_type}\n**Reason:** {reason}\n**Punishment:** {punishment}\n**Count:** {count}",
                color=discord.Color.red()
            )
            
            embed.add_field(
                name="Message Content",
                value=message.content[:500] + "..." if len(message.content) > 500 else message.content,
                inline=False
            )
            
            embed.add_field(
                name="Channel",
                value=message.channel.mention,
                inline=True
            )
            
            embed.add_field(
                name="Time",
                value=message.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                inline=True
            )
            
            embed.set_thumbnail(url=message.author.display_avatar.url)
            embed.set_footer(text=VANTAX_FOOTER)
            
            await log_channel.send(embed=embed)
            
        except Exception as e:
            print(f"Error logging violation: {e}")
    
    @app_commands.command(name="automod", description="AutoMod Konfiguration")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def automod_command(self, interaction: discord.Interaction):
        """Show automod configuration"""
        try:
            guild_id = str(interaction.guild.id)
            config = self.get_guild_config(interaction.guild.id)
            
            embed = discord.Embed(
                title="🛡️ AutoMod Konfiguration",
                description=f"Status: {'✅ Aktiviert' if config.get('enabled', False) else '❌ Deaktiviert'}",
                color=VANTAX_COLOR
            )
            
            # Banned words
            banned_words = config.get("banned_words", [])
            embed.add_field(
                name="🚫 Banned Words",
                value=f"{len(banned_words)} Wörter" if banned_words else "Keine",
                inline=True
            )
            
            # Spam protection
            spam_config = config.get("spam_protection", {})
            embed.add_field(
                name="📧 Spam Protection",
                value=f"{'✅' if spam_config.get('enabled', False) else '❌'} {spam_config.get('max_messages', 5)}/{spam_config.get('time_window', 10)}s",
                inline=True
            )
            
            # Invite protection
            invite_config = config.get("invite_protection", {})
            embed.add_field(
                name="📨 Invite Protection",
                value=f"{'✅' if invite_config.get('enabled', False) else '❌'}",
                inline=True
            )
            
            # Mention protection
            mention_config = config.get("mention_protection", {})
            embed.add_field(
                name="📢 Mention Protection",
                value=f"{'✅' if mention_config.get('enabled', False) else '❌'} Max: {mention_config.get('max_mentions', 5)}",
                inline=True
            )
            
            # Caps protection
            caps_config = config.get("caps_protection", {})
            embed.add_field(
                name="🔤 Caps Protection",
                value=f"{'✅' if caps_config.get('enabled', False) else '❌'} Max: {caps_config.get('max_caps', 70)}%",
                inline=True
            )
            
            # Link protection
            link_config = config.get("link_protection", {})
            embed.add_field(
                name="🔗 Link Protection",
                value=f"{'✅' if link_config.get('enabled', False) else '❌'}",
                inline=True
            )
            
            embed.set_footer(text=VANTAX_FOOTER)
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            print(f"Error showing automod config: {e}")
            await interaction.response.send_message("❌ Ein Fehler ist aufgetreten.", ephemeral=True)
    
    @app_commands.command(name="toggleautomod", description="AutoMod aktivieren/deaktivieren")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def toggle_automod(self, interaction: discord.Interaction):
        """Toggle automod on/off"""
        try:
            guild_id = str(interaction.guild.id)
            config = self.get_guild_config(interaction.guild.id)
            
            config["enabled"] = not config.get("enabled", False)
            self.save_automod_config()
            
            status = "✅ Aktiviert" if config["enabled"] else "❌ Deaktiviert"
            
            embed = discord.Embed(
                title="🛡️ AutoMod Status",
                description=f"AutoMod wurde {status}!",
                color=VANTAX_COLOR
            )
            
            embed.set_footer(text=VANTAX_FOOTER)
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            print(f"Error toggling automod: {e}")
            await interaction.response.send_message("❌ Ein Fehler ist aufgetreten.", ephemeral=True)
    
    @app_commands.command(name="addbannedword", description="Füge ein verbotenes Wort hinzu")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def add_banned_word(self, interaction: discord.Interaction, word: str):
        """Add a banned word"""
        try:
            guild_id = str(interaction.guild.id)
            config = self.get_guild_config(interaction.guild.id)
            
            if word.lower() not in config["banned_words"]:
                config["banned_words"].append(word.lower())
                self.save_automod_config()
                
                embed = discord.Embed(
                    title="🚫 Banned Word Added",
                    description=f"Wort '{word}' wurde zur Blacklist hinzugefügt!",
                    color=VANTAX_COLOR
                )
            else:
                embed = discord.Embed(
                    title="⚠️ Word Already Exists",
                    description=f"Wort '{word}' ist bereits auf der Blacklist!",
                    color=discord.Color.orange()
                )
            
            embed.set_footer(text=VANTAX_FOOTER)
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            print(f"Error adding banned word: {e}")
            await interaction.response.send_message("❌ Ein Fehler ist aufgetreten.", ephemeral=True)
    
    @app_commands.command(name="removebannedword", description="Entferne ein verbotenes Wort")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def remove_banned_word(self, interaction: discord.Interaction, word: str):
        """Remove a banned word"""
        try:
            guild_id = str(interaction.guild.id)
            config = self.get_guild_config(interaction.guild.id)
            
            if word.lower() in config["banned_words"]:
                config["banned_words"].remove(word.lower())
                self.save_automod_config()
                
                embed = discord.Embed(
                    title="✅ Banned Word Removed",
                    description=f"Wort '{word}' wurde von der Blacklist entfernt!",
                    color=VANTAX_COLOR
                )
            else:
                embed = discord.Embed(
                    title="⚠️ Word Not Found",
                    description=f"Wort '{word}' wurde nicht auf der Blacklist gefunden!",
                    color=discord.Color.orange()
                )
            
            embed.set_footer(text=VANTAX_FOOTER)
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            print(f"Error removing banned word: {e}")
            await interaction.response.send_message("❌ Ein Fehler ist aufgetreten.", ephemeral=True)

async def setup(bot):
    try:
        await bot.add_cog(AutoMod(bot))
        print("AutoMod cog loaded successfully!")
        return True
    except Exception as e:
        print(f"Error loading AutoMod cog: {e}")
        raise
