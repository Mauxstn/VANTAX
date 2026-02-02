import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import asyncio
from datetime import datetime, timedelta

# Constants
VANTAX_COLOR = discord.Color.blurple()
VANTAX_FOOTER = "VANTAX Discord Bot by Maurice"

class AntiRaid(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.antiraid_file = "antiraid_config.json"
        self.antiraid_config = self.load_antiraid_config()
        self.raid_data_file = "raid_data.json"
        self.raid_data = self.load_raid_data()
        
        # Start monitoring task
        self.bot.loop.create_task(self.monitor_raid())
    
    def load_antiraid_config(self):
        try:
            if os.path.exists(self.antiraid_file):
                with open(self.antiraid_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"Error loading antiraid config: {e}")
            return {}
    
    def save_antiraid_config(self):
        try:
            with open(self.antiraid_file, 'w', encoding='utf-8') as f:
                json.dump(self.antiraid_config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving antiraid config: {e}")
    
    def load_raid_data(self):
        try:
            if os.path.exists(self.raid_data_file):
                with open(self.raid_data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"Error loading raid data: {e}")
            return {}
    
    def save_raid_data(self):
        try:
            with open(self.raid_data_file, 'w', encoding='utf-8') as f:
                json.dump(self.raid_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving raid data: {e}")
    
    def get_guild_config(self, guild_id):
        guild_id_str = str(guild_id)
        if guild_id_str not in self.antiraid_config:
            self.antiraid_config[guild_id_str] = {
                "enabled": False,
                "join_threshold": 5,
                "time_window": 30,
                "punishment": "kick",
                "alert_channel": None,
                "auto_lockdown": False,
                "lockdown_duration": 300,
                "verification_required": False,
                "min_account_age": 86400,  # 24 hours in seconds
                "new_member_role": None
            }
        return self.antiraid_config[guild_id_str]
    
    def get_guild_raid_data(self, guild_id):
        guild_id_str = str(guild_id)
        if guild_id_str not in self.raid_data:
            self.raid_data[guild_id_str] = {
                "recent_joins": [],
                "raid_detected": False,
                "lockdown_active": False,
                "lockdown_start": None,
                "alerts_sent": []
            }
        return self.raid_data[guild_id_str]
    
    async def monitor_raid(self):
        """Monitor for raid activity"""
        await self.bot.wait_until_ready()
        
        while not self.bot.is_closed():
            try:
                # Clean old join data
                await self.clean_old_join_data()
                await asyncio.sleep(10)
            except Exception as e:
                print(f"Error in monitor_raid: {e}")
                await asyncio.sleep(10)
    
    async def clean_old_join_data(self):
        """Clean old join data"""
        try:
            current_time = datetime.now()
            
            for guild_id_str, guild_config in self.antiraid_config.items():
                time_window = guild_config.get("time_window", 30)
                cutoff_time = current_time - timedelta(seconds=time_window)
                
                if guild_id_str in self.raid_data:
                    raid_data = self.raid_data[guild_id_str]
                    
                    # Clean old joins
                    raid_data["recent_joins"] = [
                        join for join in raid_data["recent_joins"]
                        if datetime.fromisoformat(join["timestamp"]) > cutoff_time
                    ]
                    
                    # Check if lockdown should be lifted
                    if raid_data.get("lockdown_active", False):
                        lockdown_duration = guild_config.get("lockdown_duration", 300)
                        lockdown_start = datetime.fromisoformat(raid_data["lockdown_start"])
                        
                        if (current_time - lockdown_start).total_seconds() > lockdown_duration:
                            await self.lift_lockdown(int(guild_id_str))
            
            self.save_raid_data()
            
        except Exception as e:
            print(f"Error cleaning old join data: {e}")
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Handle member join events"""
        if member.bot:
            return
        
        guild_id = str(member.guild.id)
        config = self.get_guild_config(member.guild.id)
        raid_data = self.get_guild_raid_data(member.guild.id)
        
        if not config.get("enabled", False):
            return
        
        # Check account age
        min_account_age = config.get("min_account_age", 86400)
        account_age = (datetime.now() - member.created_at).total_seconds()
        
        if account_age < min_account_age:
            await self.handle_suspicious_join(member, config, "new_account")
            return
        
        # Add to recent joins
        raid_data["recent_joins"].append({
            "user_id": str(member.id),
            "username": member.name,
            "timestamp": datetime.now().isoformat()
        })
        
        # Check for raid
        join_threshold = config.get("join_threshold", 5)
        time_window = config.get("time_window", 30)
        
        recent_count = len(raid_data["recent_joins"])
        
        if recent_count >= join_threshold and not raid_data.get("raid_detected", False):
            await self.detect_raid(member.guild, config, raid_data, recent_count)
        
        # Apply verification if required
        if config.get("verification_required", False):
            await self.apply_verification(member, config)
    
    async def handle_suspicious_join(self, member, config, reason):
        """Handle suspicious joins"""
        guild_id = str(member.guild.id)
        raid_data = self.get_guild_raid_data(member.guild.id)
        
        # Add to suspicious joins
        if "suspicious_joins" not in raid_data:
            raid_data["suspicious_joins"] = []
        
        raid_data["suspicious_joins"].append({
            "user_id": str(member.id),
            "username": member.name,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        })
        
        # Apply punishment
        punishment = config.get("punishment", "kick")
        
        if punishment == "kick":
            try:
                await member.guild.kick(member, reason=f"AntiRaid: Suspicious account ({reason})")
                await self.log_action(member.guild, f"🛡️ Suspicious user kicked: {member.mention} ({reason})")
            except:
                pass
        
        elif punishment == "ban":
            try:
                await member.guild.ban(member, reason=f"AntiRaid: Suspicious account ({reason})")
                await self.log_action(member.guild, f"🛡️ Suspicious user banned: {member.mention} ({reason})")
            except:
                pass
        
        self.save_raid_data()
    
    async def detect_raid(self, guild, config, raid_data, join_count):
        """Handle raid detection"""
        raid_data["raid_detected"] = True
        
        # Send alert
        await self.send_raid_alert(guild, config, raid_data, join_count)
        
        # Apply auto-lockdown if enabled
        if config.get("auto_lockdown", False):
            await self.initiate_lockdown(guild, config)
        
        # Apply punishment to recent joins
        punishment = config.get("punishment", "kick")
        
        for join in raid_data["recent_joins"]:
            try:
                member = guild.get_member(int(join["user_id"]))
                if member:
                    if punishment == "kick":
                        await guild.kick(member, reason="AntiRaid: Raid detected")
                    elif punishment == "ban":
                        await guild.ban(member, reason="AntiRaid: Raid detected")
            except:
                pass
        
        self.save_raid_data()
    
    async def send_raid_alert(self, guild, config, raid_data, join_count):
        """Send raid alert"""
        try:
            alert_channel_id = config.get("alert_channel")
            if not alert_channel_id:
                return
            
            alert_channel = guild.get_channel(alert_channel_id)
            if not alert_channel:
                return
            
            embed = discord.Embed(
                title="🚨 RAID DETECTED! 🚨",
                description=f"**{join_count}** neue Mitglieder in den letzten {config.get('time_window', 30)} Sekunden!",
                color=discord.Color.red()
            )
            
            embed.add_field(
                name="⚡ Maßnahmen",
                value=f"Punishment: {config.get('punishment', 'kick').title()}\nAuto-Lockdown: {'✅' if config.get('auto_lockdown', False) else '❌'}",
                inline=False
            )
            
            embed.add_field(
                name="📊 Statistik",
                value=f"Schwellenwert: {config.get('join_threshold', 5)}\nZeitfenster: {config.get('time_window', 30)}s",
                inline=False
            )
            
            embed.set_footer(text=VANTAX_FOOTER)
            
            await alert_channel.send(f"@everyone 🚨 RAID ALARM! 🚨")
            await alert_channel.send(embed=embed)
            
        except Exception as e:
            print(f"Error sending raid alert: {e}")
    
    async def initiate_lockdown(self, guild, config):
        """Initiate server lockdown"""
        try:
            guild_id = str(guild.id)
            raid_data = self.get_guild_raid_data(guild.id)
            
            raid_data["lockdown_active"] = True
            raid_data["lockdown_start"] = datetime.now().isoformat()
            
            # Lock all text channels
            for channel in guild.text_channels:
                try:
                    await channel.set_permissions(guild.default_role, send_messages=False)
                except:
                    pass
            
            await self.log_action(guild, f"🔒 Server lockdown initiated")
            self.save_raid_data()
            
        except Exception as e:
            print(f"Error initiating lockdown: {e}")
    
    async def lift_lockdown(self, guild_id):
        """Lift server lockdown"""
        try:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return
            
            guild_id_str = str(guild_id)
            raid_data = self.get_guild_raid_data(guild_id)
            
            raid_data["lockdown_active"] = False
            raid_data["lockdown_start"] = None
            
            # Unlock all text channels
            for channel in guild.text_channels:
                try:
                    await channel.set_permissions(guild.default_role, send_messages=True)
                except:
                    pass
            
            await self.log_action(guild, f"🔓 Server lockdown lifted")
            self.save_raid_data()
            
        except Exception as e:
            print(f"Error lifting lockdown: {e}")
    
    async def apply_verification(self, member, config):
        """Apply verification to new members"""
        try:
            new_member_role_id = config.get("new_member_role")
            if new_member_role_id:
                role = member.guild.get_role(new_member_role_id)
                if role:
                    await member.add_roles(role)
        except Exception as e:
            print(f"Error applying verification: {e}")
    
    async def log_action(self, guild, message):
        """Log anti-raid actions"""
        try:
            guild_id = str(guild.id)
            config = self.get_guild_config(guild.id)
            alert_channel_id = config.get("alert_channel")
            
            if not alert_channel_id:
                return
            
            alert_channel = guild.get_channel(alert_channel_id)
            if not alert_channel:
                return
            
            embed = discord.Embed(
                title="🛡️ AntiRaid Action",
                description=message,
                color=discord.Color.orange()
            )
            
            embed.set_footer(text=VANTAX_FOOTER)
            await alert_channel.send(embed=embed)
            
        except Exception as e:
            print(f"Error logging action: {e}")
    
    @app_commands.command(name="antiraid", description="AntiRaid Konfiguration")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def antiraid_command(self, interaction: discord.Interaction):
        """Show anti-raid configuration"""
        try:
            guild_id = str(interaction.guild.id)
            config = self.get_guild_config(interaction.guild.id)
            raid_data = self.get_guild_raid_data(interaction.guild.id)
            
            embed = discord.Embed(
                title="🛡️ AntiRaid Konfiguration",
                description=f"Status: {'✅ Aktiviert' if config.get('enabled', False) else '❌ Deaktiviert'}",
                color=VANTAX_COLOR
            )
            
            # Current stats
            embed.add_field(
                name="📊 Aktuelle Statistik",
                value=f"Recent Joins: {len(raid_data.get('recent_joins', 0))}\nRaid Detected: {'✅' if raid_data.get('raid_detected', False) else '❌'}\nLockdown: {'✅' if raid_data.get('lockdown_active', False) else '❌'}",
                inline=True
            )
            
            # Threshold settings
            embed.add_field(
                name="⚡ Schwellenwerte",
                value=f"Join Threshold: {config.get('join_threshold', 5)}\nTime Window: {config.get('time_window', 30)}s\nMin Account Age: {config.get('min_account_age', 86400)//3600}h",
                inline=True
            )
            
            # Protection settings
            embed.add_field(
                name="🛡️ Schutz",
                value=f"Punishment: {config.get('punishment', 'kick').title()}\nAuto-Lockdown: {'✅' if config.get('auto_lockdown', False) else '❌'}\nVerification: {'✅' if config.get('verification_required', False) else '❌'}",
                inline=True
            )
            
            embed.set_footer(text=VANTAX_FOOTER)
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            print(f"Error showing antiraid config: {e}")
            await interaction.response.send_message("❌ Ein Fehler ist aufgetreten.", ephemeral=True)
    
    @app_commands.command(name="toggleantiraid", description="AntiRaid aktivieren/deaktivieren")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def toggle_antiraid(self, interaction: discord.Interaction):
        """Toggle anti-raid on/off"""
        try:
            guild_id = str(interaction.guild.id)
            config = self.get_guild_config(interaction.guild.id)
            
            config["enabled"] = not config.get("enabled", False)
            self.save_antiraid_config()
            
            status = "✅ Aktiviert" if config["enabled"] else "❌ Deaktiviert"
            
            embed = discord.Embed(
                title="🛡️ AntiRaid Status",
                description=f"AntiRaid wurde {status}!",
                color=VANTAX_COLOR
            )
            
            embed.set_footer(text=VANTAX_FOOTER)
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            print(f"Error toggling antiraid: {e}")
            await interaction.response.send_message("❌ Ein Fehler ist aufgetreten.", ephemeral=True)
    
    @app_commands.command(name="setantiraidalert", description="Setze den AntiRaid Alert-Kanal")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_antiraid_alert(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Set anti-raid alert channel"""
        try:
            guild_id = str(interaction.guild.id)
            config = self.get_guild_config(interaction.guild.id)
            
            config["alert_channel"] = channel.id
            self.save_antiraid_config()
            
            embed = discord.Embed(
                title="🚨 AntiRaid Alert-Kanal gesetzt",
                description=f"AntiRaid-Alarme werden jetzt in {channel.mention} gesendet!",
                color=VANTAX_COLOR
            )
            
            embed.set_footer(text=VANTAX_FOOTER)
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            print(f"Error setting antiraid alert channel: {e}")
            await interaction.response.send_message("❌ Ein Fehler ist aufgetreten.", ephemeral=True)
    
    @app_commands.command(name="lockdown", description="Manuelles Server-Lockdown")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def manual_lockdown(self, interaction: discord.Interaction):
        """Manual server lockdown"""
        try:
            guild_id = str(interaction.guild.id)
            config = self.get_guild_config(interaction.guild.id)
            raid_data = self.get_guild_raid_data(interaction.guild.id)
            
            if raid_data.get("lockdown_active", False):
                await interaction.response.send_message("❌ Lockdown ist bereits aktiv!", ephemeral=True)
                return
            
            await self.initiate_lockdown(interaction.guild, config)
            
            embed = discord.Embed(
                title="🔒 Manuelles Lockdown",
                description="Server-Lockdown wurde manuell aktiviert!",
                color=discord.Color.red()
            )
            
            embed.set_footer(text=VANTAX_FOOTER)
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            print(f"Error in manual lockdown: {e}")
            await interaction.response.send_message("❌ Ein Fehler ist aufgetreten.", ephemeral=True)
    
    @app_commands.command(name="unlockdown", description="Hebe Server-Lockdown auf")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def manual_unlockdown(self, interaction: discord.Interaction):
        """Manual server unlock"""
        try:
            guild_id = str(interaction.guild.id)
            raid_data = self.get_guild_raid_data(interaction.guild.id)
            
            if not raid_data.get("lockdown_active", False):
                await interaction.response.send_message("❌ Kein aktives Lockdown!", ephemeral=True)
                return
            
            await self.lift_lockdown(interaction.guild.id)
            
            embed = discord.Embed(
                title="🔓 Lockdown aufgehoben",
                description="Server-Lockdown wurde manuell aufgehoben!",
                color=discord.Color.green()
            )
            
            embed.set_footer(text=VANTAX_FOOTER)
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            print(f"Error in manual unlockdown: {e}")
            await interaction.response.send_message("❌ Ein Fehler ist aufgetreten.", ephemeral=True)

async def setup(bot):
    try:
        await bot.add_cog(AntiRaid(bot))
        print("AntiRaid cog loaded successfully!")
        return True
    except Exception as e:
        print(f"Error loading AntiRaid cog: {e}")
        raise
