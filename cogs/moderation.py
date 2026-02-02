import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
import json
import datetime
import os

VANTAX_COLOR = discord.Color.blurple()
VANTAX_FOOTER = "VANTAX Discord Bot by Maurice"
LOG_FILE = "moderation_logs.json"

class ModerationLogger:
    def __init__(self):
        self.logs = self.load_logs()
    
    def load_logs(self):
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def save_logs(self):
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.logs, f, indent=4, ensure_ascii=False)
    
    def log_action(self, guild_id, action, moderator_id, target_id, reason, additional_data=None):
        guild_id = str(guild_id)
        if guild_id not in self.logs:
            self.logs[guild_id] = []
        
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "action": action,
            "moderator_id": moderator_id,
            "target_id": target_id,
            "reason": reason,
            "additional_data": additional_data or {}
        }
        
        self.logs[guild_id].append(log_entry)
        self.save_logs()
        return log_entry
    
    def get_logs(self, guild_id, limit=50):
        guild_id = str(guild_id)
        logs = self.logs.get(guild_id, [])
        return logs[-limit:]  # Return last N logs
    
    def get_user_logs(self, guild_id, user_id, limit=20):
        guild_id = str(guild_id)
        user_id = str(user_id)
        logs = self.logs.get(guild_id, [])
        user_logs = [log for log in logs if log.get("target_id") == user_id or log.get("moderator_id") == user_id]
        return user_logs[-limit:]

class ConfirmView(View):
    def __init__(self, action, interaction, member, reason, logger):
        super().__init__(timeout=30)
        self.action = action
        self.interaction = interaction
        self.member = member
        self.reason = reason
        self.logger = logger
        self.value = None

    @discord.ui.button(label="Bestätigen", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.interaction.user:
            await interaction.response.send_message("Du kannst das nicht bestätigen!", ephemeral=True)
            return
            
        try:
            if self.action == "kick":
                await self.member.kick(reason=self.reason)
                await interaction.response.send_message(f"✅ {self.member.mention} wurde gekickt.")
                
                # Log the action
                self.logger.log_action(
                    guild_id=self.interaction.guild.id,
                    action="kick",
                    moderator_id=self.interaction.user.id,
                    target_id=self.member.id,
                    reason=self.reason,
                    additional_data={"target_name": str(self.member), "moderator_name": str(self.interaction.user)}
                )
                
            elif self.action == "ban":
                await self.member.ban(reason=self.reason, delete_message_days=7)
                await interaction.response.send_message(f"✅ {self.member.mention} wurde gebannt.")
                
                # Log the action
                self.logger.log_action(
                    guild_id=self.interaction.guild.id,
                    action="ban",
                    moderator_id=self.interaction.user.id,
                    target_id=self.member.id,
                    reason=self.reason,
                    additional_data={"target_name": str(self.member), "moderator_name": str(self.interaction.user), "delete_days": 7}
                )
                
            self.value = True
            self.stop()
            
        except discord.Forbidden:
            await interaction.response.send_message("❌ Ich habe keine Berechtigung für diese Aktion.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.response.send_message(f"❌ Fehler bei der Ausführung: {e}", ephemeral=True)
        except Exception as e:
            print(f"Unexpected error in moderation action: {e}")
            await interaction.response.send_message("❌ Ein unerwarteter Fehler ist aufgetreten.", ephemeral=True)

    @discord.ui.button(label="Abbrechen", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.interaction.user:
            await interaction.response.send_message("Du kannst das nicht abbrechen!", ephemeral=True)
            return
        await interaction.response.send_message("❌ Aktion abgebrochen.")
        self.value = False
        self.stop()

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = ModerationLogger()

    async def cog_app_command_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.errors.MissingPermissions):
            embed = discord.Embed(
                title="Keine Berechtigung!",
                description="Du hast nicht die nötigen Rechte, um diesen Befehl zu benutzen.",
                color=discord.Color.red()
            )
            embed.set_footer(text=VANTAX_FOOTER)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            raise error

    @app_commands.command(name="kick", description="Kicke ein Mitglied vom Server.")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick_slash(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Kein Grund angegeben"):
        # Check hierarchy
        if member.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            await interaction.response.send_message("❌ Du kannst keine Mitglieder mit höherer oder gleicher Rolle kicken.", ephemeral=True)
            return
            
        if member.top_role >= interaction.guild.me.top_role:
            await interaction.response.send_message("❌ Ich kann keine Mitglieder mit höherer oder gleicher Rolle kicken.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🔨 Kick bestätigen", 
            description=f"Soll {member.mention} wirklich gekickt werden?",
            color=discord.Color.orange()
        )
        embed.add_field(name="👤 Ziel", value=f"{member} ({member.id})", inline=True)
        embed.add_field(name="📝 Grund", value=reason, inline=True)
        embed.add_field(name="⚠️ Aktion", value="Diese Aktion wird geloggt!", inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=VANTAX_FOOTER)
        
        view = ConfirmView("kick", interaction, member, reason, self.logger)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="ban", description="Bannt ein Mitglied vom Server.")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban_slash(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Kein Grund angegeben"):
        # Check hierarchy
        if member.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            await interaction.response.send_message("❌ Du kannst keine Mitglieder mit höherer oder gleicher Rolle bannen.", ephemeral=True)
            return
            
        if member.top_role >= interaction.guild.me.top_role:
            await interaction.response.send_message("❌ Ich kann keine Mitglieder mit höherer oder gleicher Rolle bannen.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🔨 Ban bestätigen", 
            description=f"Soll {member.mention} wirklich gebannt werden?",
            color=discord.Color.red()
        )
        embed.add_field(name="👤 Ziel", value=f"{member} ({member.id})", inline=True)
        embed.add_field(name="📝 Grund", value=reason, inline=True)
        embed.add_field(name="⚠️ Aktion", value="Nachrichten der letzten 7 Tage werden gelöscht! Diese Aktion wird geloggt!", inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=VANTAX_FOOTER)
        
        view = ConfirmView("ban", interaction, member, reason, self.logger)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="clear", description="Löscht Nachrichten im Channel.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clear_slash(self, interaction: discord.Interaction, amount: int = 5):
        if amount < 1 or amount > 100:
            await interaction.response.send_message("❌ Anzahl muss zwischen 1 und 100 liegen.", ephemeral=True)
            return
            
        try:
            deleted_messages = await interaction.channel.purge(limit=amount)
            
            # Log the action
            self.logger.log_action(
                guild_id=interaction.guild.id,
                action="clear",
                moderator_id=interaction.user.id,
                target_id=interaction.channel.id,
                reason=f"Deleted {len(deleted_messages)} messages",
                additional_data={
                    "channel_name": interaction.channel.name,
                    "moderator_name": str(interaction.user),
                    "message_count": len(deleted_messages)
                }
            )
            
            embed = discord.Embed(
                title="🧹 Nachrichten gelöscht", 
                description=f"**{len(deleted_messages)}** Nachrichten wurden in {interaction.channel.mention} gelöscht.",
                color=discord.Color.green()
            )
            embed.set_footer(text=VANTAX_FOOTER)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except discord.Forbidden:
            await interaction.response.send_message("❌ Ich habe keine Berechtigung, Nachrichten zu löschen.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.response.send_message(f"❌ Fehler beim Löschen: {e}", ephemeral=True)
        except Exception as e:
            print(f"Unexpected error in clear command: {e}")
            await interaction.response.send_message("❌ Ein unerwarteter Fehler ist aufgetreten.", ephemeral=True)
    
    @app_commands.command(name="modlogs", description="Zeigt Moderations-Logs an.")
    @app_commands.checks.has_permissions(view_audit_log=True)
    async def mod_logs_slash(self, interaction: discord.Interaction, limit: int = 20):
        if limit < 1 or limit > 100:
            await interaction.response.send_message("❌ Limit muss zwischen 1 und 100 liegen.", ephemeral=True)
            return
            
        logs = self.logger.get_logs(interaction.guild.id, limit)
        
        if not logs:
            embed = discord.Embed(
                title="📋 Moderations-Logs",
                description="Noch keine Moderations-Aktionen protokolliert.",
                color=VANTAX_COLOR
            )
        else:
            embed = discord.Embed(
                title="📋 Moderations-Logs",
                description=f"Die letzten {len(logs)} Aktionen:",
                color=VANTAX_COLOR
            )
            
            for log in reversed(logs):  # Show newest first
                timestamp = datetime.datetime.fromisoformat(log["timestamp"])
                moderator = self.bot.get_user(int(log["moderator_id"]))
                target = self.bot.get_user(int(log["target_id"]))
                
                moderator_name = moderator.name if moderator else f"ID: {log['moderator_id']}"
                target_name = target.name if target else f"ID: {log['target_id']}"
                
                action_emoji = {
                    "kick": "👢",
                    "ban": "🔨", 
                    "clear": "🧹"
                }.get(log["action"], "⚙️")
                
                embed.add_field(
                    name=f"{action_emoji} {log['action'].title()} - {timestamp.strftime('%d.%m.%Y %H:%M')}",
                    value=f"**Moderator:** {moderator_name}\n**Ziel:** {target_name}\n**Grund:** {log['reason']}",
                    inline=False
                )
        
        embed.set_footer(text=VANTAX_FOOTER)
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Moderation(bot))
