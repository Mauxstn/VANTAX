import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from datetime import datetime, date
import asyncio

# Constants
VANTAX_COLOR = discord.Color.blurple()
VANTAX_FOOTER = "VANTAX Discord Bot by Maurice"

class Birthday(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.birthdays_file = "birthdays.json"
        self.birthdays = self.load_birthdays()
        self.birthdays_channel_file = "birthday_channel.json"
        self.birthdays_channel = self.load_birthday_channel()
        self.birthday_role_file = "birthday_role.json"
        self.birthday_role = self.load_birthday_role()
        
        # Start birthday check task
        self.bot.loop.create_task(self.check_birthdays())
    
    def load_birthdays(self):
        try:
            if os.path.exists(self.birthdays_file):
                with open(self.birthdays_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"Error loading birthdays: {e}")
            return {}
    
    def save_birthdays(self):
        try:
            with open(self.birthdays_file, 'w', encoding='utf-8') as f:
                json.dump(self.birthdays, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving birthdays: {e}")
    
    def load_birthday_channel(self):
        try:
            if os.path.exists(self.birthdays_channel_file):
                with open(self.birthdays_channel_file, 'r') as f:
                    data = json.load(f)
                    return data.get("channel_id")
            return None
        except Exception as e:
            print(f"Error loading birthday channel: {e}")
            return None
    
    def save_birthday_channel(self, channel_id):
        try:
            with open(self.birthdays_channel_file, 'w') as f:
                json.dump({"channel_id": channel_id}, f)
            self.birthdays_channel = channel_id
        except Exception as e:
            print(f"Error saving birthday channel: {e}")
    
    def load_birthday_role(self):
        try:
            if os.path.exists(self.birthday_role_file):
                with open(self.birthday_role_file, 'r') as f:
                    data = json.load(f)
                    return data.get("role_id")
            return None
        except Exception as e:
            print(f"Error loading birthday role: {e}")
            return None
    
    def save_birthday_role(self, role_id):
        try:
            with open(self.birthday_role_file, 'w') as f:
                json.dump({"role_id": role_id}, f)
            self.birthday_role = role_id
        except Exception as e:
            print(f"Error saving birthday role: {e}")
    
    async def check_birthdays(self):
        """Check for birthdays daily"""
        await self.bot.wait_until_ready()
        
        while not self.bot.is_closed():
            try:
                now = datetime.now()
                today = now.strftime("%m-%d")
                
                for guild in self.bot.guilds:
                    guild_id = str(guild.id)
                    
                    # Check each member's birthday
                    for user_id, birthday_data in self.birthdays.items():
                        if birthday_data.get("date") == today:
                            member = guild.get_member(int(user_id))
                            if member and not birthday_data.get("celebrated_today", {}).get(guild_id):
                                await self.celebrate_birthday(member, guild)
                                
                                # Mark as celebrated today
                                if guild_id not in self.birthdays[user_id]["celebrated_today"]:
                                    self.birthdays[user_id]["celebrated_today"] = {}
                                self.birthdays[user_id]["celebrated_today"][guild_id] = True
                                self.save_birthdays()
                
                # Reset celebration flags at midnight
                if now.hour == 0 and now.minute == 0:
                    for user_id in self.birthdays:
                        if "celebrated_today" in self.birthdays[user_id]:
                            self.birthdays[user_id]["celebrated_today"] = {}
                    self.save_birthdays()
                
                # Check every hour
                await asyncio.sleep(3600)
                
            except Exception as e:
                print(f"Error checking birthdays: {e}")
                await asyncio.sleep(3600)
    
    async def celebrate_birthday(self, member, guild):
        """Celebrate a member's birthday"""
        try:
            # Get birthday channel
            channel = None
            if self.birthdays_channel:
                channel = guild.get_channel(self.birthdays_channel)
            
            if not channel:
                # Try to find a general channel
                channel = discord.utils.get(guild.text_channels, name="general") or \
                          discord.utils.get(guild.text_channels, name="allgemein") or \
                          guild.text_channels[0] if guild.text_channels else None
            
            if not channel:
                return
            
            # Create birthday embed
            embed = discord.Embed(
                title="🎉 Geburtstag! 🎂",
                description=f"**Alles Gute zum Geburtstag, {member.mention}!** 🎉🎂🎈",
                color=discord.Color.gold()
            )
            
            embed.add_field(
                name="🎁 Geburtstagswünsche",
                value="Wir wünschen dir alles Gute zum Geburtstag! 🎊\nMöge dein Tag voller Freude und Glück sein! ✨",
                inline=False
            )
            
            embed.add_field(
                name="🎈 Feier mit!",
                value="Kommt alle und gratuliert unserem Geburtstagskind! 🥳",
                inline=False
            )
            
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"Geburtstag von {member.display_name} • {datetime.now().strftime('%d.%m.%Y')}")
            
            await channel.send(f"@everyone 🎉 Geburtstag! {member.mention} wird heute älter! 🎂")
            await channel.send(embed=embed)
            
            # Assign birthday role if configured
            if self.birthday_role:
                role = guild.get_role(self.birthday_role)
                if role:
                    await member.add_roles(role)
                    print(f"Assigned birthday role to {member.name}")
            
            print(f"Celebrated birthday for {member.name} in {guild.name}")
            
        except Exception as e:
            print(f"Error celebrating birthday: {e}")
    
    @app_commands.command(name="birthday", description="Setze deinen Geburtstag")
    async def birthday_command(self, interaction: discord.Interaction, tag: int, monat: int, jahr: int):
        """Set your birthday"""
        try:
            # Validate date
            if not (1 <= tag <= 31):
                await interaction.response.send_message("❌ Tag muss zwischen 1 und 31 liegen!", ephemeral=True)
                return
            if not (1 <= monat <= 12):
                await interaction.response.send_message("❌ Monat muss zwischen 1 und 12 liegen!", ephemeral=True)
                return
            if not (1900 <= jahr <= datetime.now().year):
                await interaction.response.send_message("❌ Jahr muss zwischen 1900 und dem aktuellen Jahr liegen!", ephemeral=True)
                return
            
            # Format date
            birthday_date = f"{monat:02d}-{tag:02d}"
            user_id = str(interaction.user.id)
            
            # Save birthday
            if user_id not in self.birthdays:
                self.birthdays[user_id] = {}
            
            self.birthdays[user_id]["date"] = birthday_date
            self.birthdays[user_id]["year"] = jahr
            self.birthdays[user_id]["name"] = interaction.user.name
            self.birthdays[user_id]["celebrated_today"] = {}
            
            self.save_birthdays()
            
            # Calculate age
            today = date.today()
            birthday = date(jahr, monat, tag)
            age = today.year - birthday.year - ((today.month, today.day) < (birthday.month, birthday.day))
            
            embed = discord.Embed(
                title="🎂 Geburtstag gespeichert! 🎉",
                description=f"Dein Geburtstag ({tag}.{monat}.{jahr}) wurde gespeichert!",
                color=VANTAX_COLOR
            )
            
            embed.add_field(
                name="📅 Dein Geburtstag",
                value=f"**{tag}.{monat}.{jahr}**\nDu wirst dieses Jahr **{age}** Jahre alt! 🎈",
                inline=False
            )
            
            embed.add_field(
                name="🎁 Geburtstags-Benefits",
                value="Du wirst an deinem Geburtstag erwähnt und bekommst eventuell eine spezielle Rolle! 🎊",
                inline=False
            )
            
            embed.set_footer(text=VANTAX_FOOTER)
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            print(f"Error setting birthday: {e}")
            await interaction.response.send_message("❌ Ein Fehler ist aufgetreten. Bitte versuche es später erneut.", ephemeral=True)
    
    @app_commands.command(name="birthdays", description="Zeige alle Geburtstage")
    async def birthdays_command(self, interaction: discord.Interaction):
        """Show all birthdays"""
        try:
            if not self.birthdays:
                await interaction.response.send_message("❌ Keine Geburtstage gespeichert!", ephemeral=True)
                return
            
            embed = discord.Embed(
                title="🎂 Geburtstagsliste 🎉",
                description="Alle gespeicherten Geburtstage:",
                color=VANTAX_COLOR
            )
            
            birthday_list = []
            for user_id, data in self.birthdays.items():
                if data.get("date"):
                    try:
                        month_day = data["date"]
                        name = data.get("name", "Unbekannt")
                        year = data.get("year", "????")
                        
                        # Parse month and day
                        month, day = month_day.split("-")
                        birthday_list.append(f"**{name}**: {day}.{month}.{year}")
                    except:
                        continue
            
            if birthday_list:
                # Sort by month and day
                birthday_list.sort(key=lambda x: (x.split(":")[1].split(".")[1], x.split(":")[1].split(".")[0]))
                
                embed.description = "\n".join(birthday_list)
            else:
                embed.description = "Keine gültigen Geburtstage gefunden."
            
            embed.set_footer(text=VANTAX_FOOTER)
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            print(f"Error showing birthdays: {e}")
            await interaction.response.send_message("❌ Ein Fehler ist aufgetreten.", ephemeral=True)
    
    @app_commands.command(name="setbirthdaychannel", description="Setze den Geburtstags-Kanal")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_birthday_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Set the birthday announcement channel"""
        try:
            self.save_birthday_channel(channel.id)
            
            embed = discord.Embed(
                title="🎂 Geburtstags-Kanal gesetzt! 🎉",
                description=f"Geburtstagsnachrichten werden jetzt in {channel.mention} gesendet!",
                color=VANTAX_COLOR
            )
            
            embed.set_footer(text=VANTAX_FOOTER)
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            print(f"Error setting birthday channel: {e}")
            await interaction.response.send_message("❌ Ein Fehler ist aufgetreten.", ephemeral=True)
    
    @app_commands.command(name="setbirthdayrole", description="Setze die Geburtstags-Rolle")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_birthday_role(self, interaction: discord.Interaction, role: discord.Role):
        """Set the birthday role"""
        try:
            self.save_birthday_role(role.id)
            
            embed = discord.Embed(
                title="🎂 Geburtstags-Rolle gesetzt! 🎉",
                description=f"Die Rolle {role.mention} wird Geburtstagskindern zugewiesen!",
                color=VANTAX_COLOR
            )
            
            embed.set_footer(text=VANTAX_FOOTER)
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            print(f"Error setting birthday role: {e}")
            await interaction.response.send_message("❌ Ein Fehler ist aufgetreten.", ephemeral=True)

async def setup(bot):
    try:
        await bot.add_cog(Birthday(bot))
        print("Birthday cog loaded successfully!")
        return True
    except Exception as e:
        print(f"Error loading birthday cog: {e}")
        raise
