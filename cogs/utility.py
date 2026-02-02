import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
from datetime import datetime
import json
import os
import asyncio

VANTAX_COLOR = discord.Color.blurple()
VANTAX_FOOTER = "VANTAX Discord Bot by Maurice"

class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_data_file = 'user_data.json'
        self.load_user_data()

    def load_user_data(self):
        if os.path.exists(self.user_data_file):
            with open(self.user_data_file, 'r', encoding='utf-8') as f:
                self.user_data = json.load(f)
        else:
            self.user_data = {}
            self.save_user_data()

    def save_user_data(self):
        with open(self.user_data_file, 'w', encoding='utf-8') as f:
            json.dump(self.user_data, f, indent=4, ensure_ascii=False)

    @app_commands.command(name="weather", description="Zeigt das Wetter für eine Stadt an.")
    async def weather(self, interaction: discord.Interaction, stadt: str):
        # Show typing indicator while fetching data
        await interaction.response.defer()
        
        try:
            # Create a timeout for the request
            timeout = aiohttp.ClientTimeout(total=10)  # 10 seconds timeout
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # First try with HTTPS, then HTTP if that fails
                urls = [
                    f"https://wttr.in/{stadt}?format=j1",
                    f"http://wttr.in/{stadt}?format=j1"
                ]
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'application/json',
                    'Accept-Language': 'de,en;q=0.9'
                }
                
                data = None
                last_error = None
                
                # Try each URL until one works
                for url in urls:
                    try:
                        async with session.get(url, headers=headers, ssl=False) as response:
                            if response.status == 200:
                                data = await response.json()
                                break
                    except Exception as e:
                        last_error = e
                        continue
                
                if not data:
                    error_msg = "❌ Konnte keine Wetterdaten abrufen. "
                    if last_error:
                        error_msg += f"Fehler: {str(last_error)}"
                    else:
                        error_msg += "Bitte versuche es später erneut."
                    
                    await interaction.followup.send(error_msg, ephemeral=True)
                    return
                
                # Extract current weather data
                current = data['current_condition'][0]
                weather_desc = current['weatherDesc'][0]['value']
                temp_c = current['temp_C']
                feels_like_c = current['FeelsLikeC']
                humidity = current['humidity']
                wind_speed = current['windspeedKmph']
                wind_dir = current['winddir16Point']
                
                # Get location
                location = data['nearest_area'][0]
                area_name = location['areaName'][0]['value']
                region = location['region'][0]['value']
                country = location['country'][0]['value']
                
                # Weather emoji mapping
                weather_emoji = "🌤️"  # Default
                weather_lower = weather_desc.lower()
                
                if any(word in weather_lower for word in ['regen', 'rain', 'niederschlag']):
                    weather_emoji = "🌧️"
                elif any(word in weather_lower for word in ['wolken', 'cloud', 'bewölkt']):
                    weather_emoji = "☁️"
                elif any(word in weather_lower for word in ['sonne', 'sunny', 'klar', 'clear']):
                    weather_emoji = "☀️"
                elif any(word in weather_lower for word in ['schnee', 'snow']):
                    weather_emoji = "❄️"
                elif any(word in weather_lower for word in ['gewitter', 'thunder', 'sturm']):
                    weather_emoji = "⛈️"
                elif any(word in weather_lower for word in ['nebel', 'fog', 'dunst']):
                    weather_emoji = "🌫️"
                
                # Create embed
                embed = discord.Embed(
                    title=f"{weather_emoji} Wetter in {area_name}, {region}",
                    description=f"**{weather_desc}**",
                    color=VANTAX_COLOR
                )
                
                # Add weather details
                embed.add_field(name="🌡️ Temperatur", value=f"{temp_c}°C", inline=True)
                embed.add_field(name="🌡️ Gefühlt", value=f"{feels_like_c}°C", inline=True)
                embed.add_field(name="💧 Luftfeuchtigkeit", value=f"{humidity}%", inline=True)
                embed.add_field(name="💨 Wind", value=f"{wind_speed} km/h {wind_dir}", inline=True)
                
                # Add forecast for today
                today = data['weather'][0]
                max_temp = today['maxtempC']
                min_temp = today['mintempC']
                sunrise = today['astronomy'][0]['sunrise']
                sunset = today['astronomy'][0]['sunset']
                
                embed.add_field(name="📈 Heute", 
                             value=f"Höchst: {max_temp}°C\n"
                                   f"Tiefst: {min_temp}°C\n"
                                   f"🌅 {sunrise} | 🌇 {sunset}", 
                             inline=False)
                
                # Add footer with location and time
                embed.set_footer(text=f"{area_name}, {region}, {country} • {datetime.now().strftime('%d.%m.%Y %H:%M')}\n{VANTAX_FOOTER}")
                
                await interaction.followup.send(embed=embed)

        except aiohttp.ClientError as e:
            print(f"Weather API error: {e}")
            await interaction.followup.send(
                "❌ Wetter-API nicht erreichbar. Bitte versuche es später erneut.",
                ephemeral=True
            )
        except asyncio.TimeoutError:
            await interaction.followup.send(
                "❌ Zeitüberschreitung bei der Wetterabfrage.",
                ephemeral=True
            )
        except KeyError as e:
            print(f"Weather data parsing error: {e}")
            await interaction.followup.send(
                "❌ Wetterdaten konnten nicht verarbeitet werden.",
                ephemeral=True
            )
        except Exception as e:
            print(f"Unexpected weather command error: {e}")
            await interaction.followup.send(
                "❌ Ein unerwarteter Fehler ist aufgetreten.",
                ephemeral=True
            )

    @app_commands.command(name="userinfo", description="Zeigt detaillierte Informationen über einen Benutzer.")
    async def userinfo(self, interaction: discord.Interaction, mitglied: discord.Member = None):
        user = mitglied or interaction.user
        
        # Calculate time differences
        now = datetime.now()
        joined_days = (now - user.joined_at.replace(tzinfo=None)).days
        created_days = (now - user.created_at.replace(tzinfo=None)).days
        
        # Format dates
        joined_date = user.joined_at.strftime("%m/%d/%Y %H:%M")
        created_date = user.created_at.strftime("%m/%d/%Y %H:%M")
        
        # Calculate time ago strings
        def time_ago(days):
            years = days // 365
            months = (days % 365) // 30
            remaining_days = days % 30
            
            parts = []
            if years > 0:
                parts.append(f"{years} year{'s' if years != 1 else ''}")
            if months > 0:
                parts.append(f"{months} month{'s' if months != 1 else ''}")
            if remaining_days > 0 or not parts:
                parts.append(f"{remaining_days} day{'s' if remaining_days != 1 else ''}")
            
            return " and ".join(parts) + " ago"
        
        # Get roles (limit to 10)
        roles = [role.name for role in user.roles[1:]]  # Skip @everyone
        roles_display = roles[:10] if roles else ["No roles"]
        roles_text = "\n".join(f"• {role}" for role in roles_display)
        if len(roles) > 10:
            roles_text += f"\n... and {len(roles) - 10} more"
        
        # Get permissions
        if user.guild_permissions.administrator:
            permissions = "👑 Administrator (all permissions)"
        else:
            perm_list = []
            for perm, value in user.guild_permissions:
                if value and perm not in ['administrator']:
                    perm_list.append(perm.replace('_', ' ').title())
            permissions = ", ".join(perm_list[:5]) if perm_list else "No special permissions"
            if len(perm_list) > 5:
                permissions += f" (+{len(perm_list) - 5} more)"
        
        # Create embed in the style from the image
        embed = discord.Embed(
            title=":busts_in_silhouette: USER INFORMATION :busts_in_silhouette:",
            color=VANTAX_COLOR
        )
        
        embed.add_field(name="Username", value=f"**{user.name}**", inline=True)
        embed.add_field(name="User ID", value=f"`{user.id}`", inline=True)
        embed.add_field(name=f"Roles [{len(roles)}]", value=roles_text, inline=False)
        embed.add_field(name="Nickname", value=user.nick or "No nickname", inline=True)
        
        # Simple location based on available info
        location_parts = []
        if user.public_flags.verified_bot:
            location_parts.append("🤖 Bot")
        if user.premium_since:
            location_parts.append("💎 Server Booster")
        if user.public_flags.early_supporter:
            location_parts.append("🌟 Early Supporter")
        if user.public_flags.hypesquad:
            location_parts.append("⚡ HypeSquad")
        
        location = " | ".join(location_parts) if location_parts else "🌍 Not specified"
        embed.add_field(name="Location", value=location, inline=True)
        embed.add_field(name="Is Boosting", value="Yes" if user.premium_since else "No", inline=True)
        
        # Simple status with emoji - improved detection
        status_map = {
            discord.Status.online: "🟢 Online",
            discord.Status.idle: "🌙 Idle",
            discord.Status.dnd: "⛔ Do Not Disturb", 
            discord.Status.offline: "⚫ Offline",
            discord.Status.invisible: "⚫ Invisible"
        }
        
        # Get status with fallback
        try:
            status = status_map.get(user.status, "❔ Unknown")
            
            # Add activity if available
            if user.activity:
                activity_emoji = {
                    discord.ActivityType.playing: "🎮",
                    discord.ActivityType.streaming: "📺", 
                    discord.ActivityType.listening: "🎵",
                    discord.ActivityType.watching: "📺",
                    discord.ActivityType.custom: "🎨"
                }.get(user.activity.type, "📌")
                
                activity_name = user.activity.name
                if hasattr(user.activity, 'details') and user.activity.details:
                    activity_name = f"{user.activity.name} - {user.activity.details}"
                
                status += f"\n{activity_emoji} {activity_name}"
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Ich habe keine Berechtigung, diese Aktion auszuführen.",
                ephemeral=True
            )
        except discord.HTTPException as e:
            print(f"Discord API error in userinfo: {e}")
            await interaction.response.send_message(
                "❌ Fehler beim Abrufen der Benutzerinformationen.",
                ephemeral=True
            )
        except Exception as e:
            print(f"Unexpected userinfo error: {e}")
            await interaction.response.send_message(
                "❌ Ein unerwarteter Fehler ist aufgetreten.",
                ephemeral=True
            )
            
        embed.add_field(name="Status", value=status, inline=True)
        embed.add_field(name="Global Permissions", value=permissions, inline=False)
        embed.add_field(name="Joined this server on (MM/DD/YYYY)", value=f"{joined_date} ({time_ago(joined_days)})", inline=False)
        embed.add_field(name="Account created on (MM/DD/YYYY)", value=f"{created_date} ({time_ago(created_days)})", inline=False)
        
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text=VANTAX_FOOTER)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="addnote", description="Fügt eine Notiz zu einem Benutzer hinzu.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def add_note(self, interaction: discord.Interaction, mitglied: discord.Member, notiz: str):
        try:
            user_id = str(mitglied.id)
            if user_id not in self.user_data:
                self.user_data[user_id] = {'notes': notiz, 'warnings': 0}
            else:
                self.user_data[user_id]['notes'] = notiz
            self.save_user_data()
            await interaction.response.send_message(
                f"📝 Notiz für {mitglied.mention} wurde hinzugefügt/aktualisiert.",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Ich habe keine Berechtigung, Notizen hinzuzufügen.",
                ephemeral=True
            )
        except Exception as e:
            print(f"Add note error: {e}")
            await interaction.response.send_message(
                "❌ Fehler beim Hinzufügen der Notiz.",
                ephemeral=True
            )

    @app_commands.command(name="warn", description="Verwarnt einen Benutzer.")
    @app_commands.checks.has_permissions(kick_members=True)
    async def warn_user(self, interaction: discord.Interaction, mitglied: discord.Member, grund: str = "Kein Grund angegeben"):
        user_id = str(mitglied.id)
        if user_id not in self.user_data:
            self.user_data[user_id] = {'notes': '', 'warnings': 1}
        else:
            self.user_data[user_id]['warnings'] = self.user_data[user_id].get('warnings', 0) + 1
        self.save_user_data()
        
        warnings = self.user_data[user_id]['warnings']
        warning_emoji = "⚠️" * min(warnings, 5)  # Show up to 5 warning emojis
        
        await interaction.response.send_message(
            f"{warning_emoji} {mitglied.mention} wurde verwarnt.\n"
            f"**Grund:** {grund}\n"
            f"**Anzahl der Verwarnungen:** {warnings}",
            ephemeral=True
        )

    @warn_user.error
    async def warn_user_error(self, interaction: discord.Interaction, error):
        if isinstance(error, discord.app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung, Mitglieder zu verwarnen.",
                ephemeral=True
            )
        elif isinstance(error, discord.app_commands.CommandInvokeError):
            print(f"Warn command error: {error.original}")
            await interaction.response.send_message(
                "❌ Fehler beim Verwarnen des Benutzers.",
                ephemeral=True
            )
        else:
            print(f"Unexpected warn error: {error}")
            await interaction.response.send_message(
                "❌ Ein unerwarteter Fehler ist aufgetreten.",
                ephemeral=True
            )

    @app_commands.command(name="love", description="Sende eine Liebesnachricht an jemanden ❤️")
    async def love_command(self, interaction: discord.Interaction, person: discord.Member):
        import random
        
        love_messages = [
            "I LOVE YOU! 💖",
            "You mean everything to me! 💑",
            "You're my sunshine! ☀️",
            "I can't stop thinking about you! 💭",
            "You make my heart race! 💓",
            "You're my one and only! 💍",
            "Forever yours! 💕",
            "You complete me! 🧩",
            "My heart belongs to you! ❤️",
            "You're my dream come true! ✨"
        ]
        
        romantic_quotes = [
            "You make every moment special! ⭐",
            "Being with you feels like magic! 🪄", 
            "You're the best thing in my life! 🌟",
            "I fall for you more every day! 🌹",
            "You're my happiness! 😊",
            "Together we're unstoppable! 💪",
            "You light up my world! 💡",
            "I'm so lucky to have you! 🍀",
            "You make my dreams come true! 🌙",
            "With you, everything is perfect! 🌈"
        ]
        
        embed = discord.Embed(
            title="💕 Love Message 💕",
            description=f"**To my dear {person.mention}** 💝",
            color=discord.Color.pink()
        )
        
        embed.add_field(
            name="❤️ From the Heart ❤️",
            value=f"**{random.choice(love_messages)}**",
            inline=False
        )
        
        embed.add_field(
            name="💖 Special Words 💖", 
            value=random.choice(romantic_quotes),
            inline=False
        )
        
        embed.set_footer(text=f"Sent with all my love by {interaction.user.display_name} 💕")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="heart", description="Sende ein großes Herz mit Liebesnachricht 💝")
    async def heart_command(self, interaction: discord.Interaction, person: discord.Member):
        embed = discord.Embed(
            title="💝 I LOVE YOU 💝",
            description=f"**To my dear {person.mention}**",
            color=discord.Color.red()
        )
        
        # Local high resolution heart image
        file = discord.File("img/heart-png-38780(1).png", filename="heart.png")
        embed.set_image(url="attachment://heart.png")
        embed.set_footer(text=f"Sent with all my love by {interaction.user.display_name} 💕")
        await interaction.response.send_message(file=file, embed=embed)

    @app_commands.command(name="iloveyou", description="Sende ein riesiges Herz mit 'I LOVE YOU' Nachricht 💕")
    async def iloveyou_command(self, interaction: discord.Interaction, person: discord.Member):
        embed = discord.Embed(
            title="💕 I LOVE YOU 💕",
            description=f"To my dear {person.mention}",
            color=discord.Color.from_rgb(255, 0, 0)  # #ff0000
        )
        
        # Local high resolution heart image
        file = discord.File("img/heart-png-38780(1).png", filename="heart.png")
        embed.set_image(url="attachment://heart.png")
        embed.set_thumbnail(url="attachment://heart.png")
        
        embed.add_field(
            name="❤️ From My Heart ❤️",
            value="I LOVE YOU! 💕\nI LOVE YOU! 💖\nI LOVE YOU! 💗",
            inline=False
        )
        
        embed.set_footer(text=f"Sent with all my love by {interaction.user.display_name} 💕")
        await interaction.response.send_message(file=file, embed=embed)

    @app_commands.command(name="cuddle", description="Sende eine süße Kuschelnachricht 🤗")
    async def cuddle_command(self, interaction: discord.Interaction, person: discord.Member):
        import random
        
        cuddle_messages = [
            f"**{interaction.user.mention} kuschelt ganz fest mit {person.mention} 🤗**",
            f"**{person.mention} wird von {interaction.user.mention} liebevoll gekuschelt! 🥰**",
            f"**{interaction.user.mention} gibt {person.mention} eine warme Umarmung! 🫂**",
            f"**{person.mention} bekommt von {interaction.user.mention} die süßeste Kuscheleinheit! 💕**",
            f"**{interaction.user.mention} und {person.mention} kuscheln sich glücklich! 🌟**"
        ]
        
        embed = discord.Embed(
            title="🤗 Süße Kuschelei! 🤗",
            description=random.choice(cuddle_messages),
            color=discord.Color.from_rgb(255, 182, 193)  # Light pink
        )
        
        embed.add_field(
            name="💕 Kuschel-Faktor",
            value="Über 9000% süß! 🥰",
            inline=True
        )
        
        embed.add_field(
            name="🌈 Glücks-Level",
            value="Maximum erreicht! ✨",
            inline=True
        )
        
        embed.add_field(
            name="🎀 Extra süß",
            value="Herz-Regen inklusive! 💕💖💗",
            inline=False
        )
        
        embed.set_footer(text=f"Kuschel-Zeit mit {interaction.user.display_name} 🤗")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="hug", description="Sende eine liebevolle Umarmung 🫂")
    async def hug_command(self, interaction: discord.Interaction, person: discord.Member):
        embed = discord.Embed(
            description=f"{interaction.user.mention} umarmt {person.mention} 🫂",
            color=discord.Color.from_rgb(255, 160, 122)  # Light coral
        )
        
        # Local hug GIF
        file = discord.File("img/hug-cute.gif", filename="hug.gif")
        embed.set_image(url="attachment://hug.gif")
        embed.set_footer(text=f"Umarmung von {interaction.user.display_name} 🫂")
        await interaction.response.send_message(file=file, embed=embed)

    @app_commands.command(name="fuck", description="Sende eine explizite Nachricht 🔞")
    async def fuck_command(self, interaction: discord.Interaction, person: discord.Member):
        embed = discord.Embed(
            description=f"{interaction.user.mention} WANTS TO FUCK WITH YOU {person.mention}",
            color=discord.Color.from_rgb(255, 0, 255)  # Magenta
        )
        
        # Local neck-grab GIF
        file = discord.File("img/neck-grab.gif", filename="neck.gif")
        embed.set_image(url="attachment://neck.gif")
        await interaction.response.send_message(file=file, embed=embed)

    @app_commands.command(name="kiss", description="Sende einen Kuss 💋")
    async def kiss_command(self, interaction: discord.Interaction, person: discord.Member):
        embed = discord.Embed(
            description=f"{interaction.user.mention} KISSES YOU {person.mention}",
            color=discord.Color.from_rgb(255, 105, 180)  # Hot pink
        )
        
        # Local make-out-kiss GIF
        file = discord.File("img/make-out-kiss.gif", filename="kiss.gif")
        embed.set_image(url="attachment://kiss.gif")
        await interaction.response.send_message(file=file, embed=embed)

async def setup(bot):
    try:
        await bot.add_cog(Utility(bot))
        print("Utility cog loaded successfully!")
        return True
    except Exception as e:
        print(f"Error loading utility cog: {e}")
        raise
