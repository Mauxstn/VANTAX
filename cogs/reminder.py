import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import datetime
import asyncio

VANTAX_COLOR = discord.Color.blurple()
VANTAX_FOOTER = "VANTAX Discord Bot by Maurice"
REMINDER_FILE = "reminders.json"

class Reminder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reminders = self.load_reminders()
        self.check_reminders_task = self.bot.loop.create_task(self.check_reminders())
    
    def load_reminders(self):
        if os.path.exists(REMINDER_FILE):
            with open(REMINDER_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def save_reminders(self):
        with open(REMINDER_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.reminders, f, indent=4, ensure_ascii=False)
    
    def cog_unload(self):
        """Clean up when cog is unloaded"""
        self.check_reminders_task.cancel()
    
    async def check_reminders(self):
        """Check for due reminders every minute"""
        await self.bot.wait_until_ready()
        
        while not self.bot.is_closed():
            try:
                now = datetime.datetime.now()
                current_time = now.isoformat()
                
                # Check each server's reminders
                for guild_id in list(self.reminders.keys()):
                    for reminder_id in list(self.reminders[guild_id].keys()):
                        reminder = self.reminders[guild_id][reminder_id]
                        
                        if reminder["time"] <= current_time:
                            # Send reminder
                            try:
                                guild = self.bot.get_guild(int(guild_id))
                                if guild:
                                    user = guild.get_member(int(reminder["user_id"]))
                                    if user:
                                        channel = guild.get_channel(int(reminder["channel_id"]))
                                        if channel:
                                            embed = discord.Embed(
                                                title="⏰ Erinnerung!",
                                                description=f"**{reminder['message']}**",
                                                color=discord.Color.orange()
                                            )
                                            
                                            embed.add_field(
                                                name="📅 Erstellt am",
                                                value=datetime.datetime.fromisoformat(reminder["created_at"]).strftime("%d.%m.%Y %H:%M"),
                                                inline=True
                                            )
                                            
                                            embed.set_footer(text=VANTAX_FOOTER)
                                            
                                            await channel.send(f"🔔 {user.mention}", embed=embed)
                                        
                                        # Also send DM if possible
                                        try:
                                            dm_embed = discord.Embed(
                                                title="⏰ Erinnerung!",
                                                description=f"**{reminder['message']}**",
                                                color=discord.Color.orange()
                                            )
                                            dm_embed.add_field(
                                                name="🏠 Server",
                                                value=guild.name,
                                                inline=True
                                            )
                                            dm_embed.set_footer(text=VANTAX_FOOTER)
                                            await user.send(embed=dm_embed)
                                        except discord.Forbidden:
                                            pass  # Can't send DM
                                
                                # Remove processed reminder
                                del self.reminders[guild_id][reminder_id]
                                
                                # Clean up empty guild entries
                                if not self.reminders[guild_id]:
                                    del self.reminders[guild_id]
                                
                                self.save_reminders()
                                
                            except Exception as e:
                                print(f"Error processing reminder {reminder_id}: {e}")
                                # Remove problematic reminder
                                try:
                                    del self.reminders[guild_id][reminder_id]
                                    if not self.reminders[guild_id]:
                                        del self.reminders[guild_id]
                                    self.save_reminders()
                                except:
                                    pass
                            
            except Exception as e:
                print(f"Error checking reminders: {e}")
            
            # Wait 1 minute before next check
            await asyncio.sleep(60)
    
    @app_commands.command(name="remind", description="Setze eine Erinnerung für dich selbst.")
    @app_commands.describe(
        time="Zeit (z.B. 1h, 30m, 2d, 1w)",
        message="Die Erinnerungsnachricht"
    )
    async def remind_command(self, interaction: discord.Interaction, time: str, message: str):
        try:
            # Parse time string
            time_delta = self.parse_time_string(time)
            if not time_delta:
                await interaction.response.send_message(
                    "❌ Ungültiges Zeitformat! Verwende: 1h, 30m, 2d, 1w",
                    ephemeral=True
                )
                return
            
            # Calculate reminder time
            reminder_time = datetime.datetime.now() + time_delta
            
            # Create reminder
            guild_id = str(interaction.guild.id)
            reminder_id = f"{interaction.user.id}_{reminder_time.timestamp()}"
            
            if guild_id not in self.reminders:
                self.reminders[guild_id] = {}
            
            self.reminders[guild_id][reminder_id] = {
                "user_id": str(interaction.user.id),
                "channel_id": str(interaction.channel.id),
                "message": message,
                "time": reminder_time.isoformat(),
                "created_at": datetime.datetime.now().isoformat()
            }
            
            self.save_reminders()
            
            # Create confirmation embed
            embed = discord.Embed(
                title="✅ Erinnerung gesetzt!",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="⏰ Erinnerungszeit",
                value=reminder_time.strftime("%d.%m.%Y %H:%M"),
                inline=True
            )
            
            embed.add_field(
                name="📝 Nachricht",
                value=message,
                inline=True
            )
            
            embed.add_field(
                name="⏱️ In",
                value=f"{time}",
                inline=True
            )
            
            embed.set_footer(text=VANTAX_FOOTER)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            print(f"Error setting reminder: {e}")
            await interaction.response.send_message(
                "❌ Fehler beim Setzen der Erinnerung!",
                ephemeral=True
            )
    
    def parse_time_string(self, time_str: str):
        """Parse time string like '1h', '30m', '2d', '1w'"""
        time_str = time_str.lower().strip()
        
        if not time_str:
            return None
        
        # Extract number and unit
        import re
        match = re.match(r'^(\d+)([hmwd])$', time_str)
        
        if not match:
            return None
        
        number = int(match.group(1))
        unit = match.group(2)
        
        # Convert to timedelta
        if unit == 'm':
            return datetime.timedelta(minutes=number)
        elif unit == 'h':
            return datetime.timedelta(hours=number)
        elif unit == 'd':
            return datetime.timedelta(days=number)
        elif unit == 'w':
            return datetime.timedelta(weeks=number)
        
        return None
    
    @app_commands.command(name="reminders", description="Zeigt deine aktiven Erinnerungen an.")
    async def list_reminders(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        user_id = str(interaction.user.id)
        
        if guild_id not in self.reminders:
            await interaction.response.send_message(
                "Du hast keine aktiven Erinnerungen!",
                ephemeral=True
            )
            return
        
        # Filter user's reminders
        user_reminders = []
        for reminder_id, reminder in self.reminders[guild_id].items():
            if reminder["user_id"] == user_id:
                user_reminders.append((reminder_id, reminder))
        
        if not user_reminders:
            await interaction.response.send_message(
                "Du hast keine aktiven Erinnerungen!",
                ephemeral=True
            )
            return
        
        # Create embed with reminders
        embed = discord.Embed(
            title="⏰ Deine aktiven Erinnerungen",
            color=VANTAX_COLOR
        )
        
        for reminder_id, reminder in user_reminders:
            reminder_time = datetime.datetime.fromisoformat(reminder["time"])
            time_left = reminder_time - datetime.datetime.now()
            
            if time_left.total_seconds() > 0:
                days = time_left.days
                hours, remainder = divmod(time_left.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                
                time_left_str = ""
                if days > 0:
                    time_left_str += f"{days}d "
                if hours > 0:
                    time_left_str += f"{hours}h "
                if minutes > 0:
                    time_left_str += f"{minutes}m"
                
                embed.add_field(
                    name=f"📝 {reminder['message'][:50]}{'...' if len(reminder['message']) > 50 else ''}",
                    value=f"**Zeit:** {reminder_time.strftime('%d.%m.%Y %H:%M')}\n**Verbleibend:** {time_left_str}",
                    inline=False
                )
        
        embed.set_footer(text=VANTAX_FOOTER)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="delreminder", description="Löscht eine deiner Erinnerungen.")
    @app_commands.describe(
        message="Teil der Erinnerungsnachricht zum Identifizieren"
    )
    async def delete_reminder(self, interaction: discord.Interaction, message: str):
        guild_id = str(interaction.guild.id)
        user_id = str(interaction.user.id)
        
        if guild_id not in self.reminders:
            await interaction.response.send_message(
                "Du hast keine aktiven Erinnerungen!",
                ephemeral=True
            )
            return
        
        # Find matching reminder
        deleted_count = 0
        reminders_to_delete = []
        
        for reminder_id, reminder in self.reminders[guild_id].items():
            if (reminder["user_id"] == user_id and 
                message.lower() in reminder["message"].lower()):
                reminders_to_delete.append(reminder_id)
        
        # Delete reminders
        for reminder_id in reminders_to_delete:
            del self.reminders[guild_id][reminder_id]
            deleted_count += 1
        
        if deleted_count == 0:
            await interaction.response.send_message(
                "Keine Erinnerung mit dieser Nachricht gefunden!",
                ephemeral=True
            )
        else:
            self.save_reminders()
            await interaction.response.send_message(
                f"✅ {deleted_count} Erinnerung(en) gelöscht!",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(Reminder(bot))
