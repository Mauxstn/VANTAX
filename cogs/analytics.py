import discord
import json
import os
from datetime import datetime, timedelta
from discord.ext import commands
import asyncio
from collections import defaultdict

class Analytics(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.analytics_file = "analytics_data.json"
        self.data = self.load_data()
        
    def load_data(self):
        if os.path.exists(self.analytics_file):
            with open(self.analytics_file, 'r') as f:
                return json.load(f)
        return {
            "server_stats": {},
            "user_activity": {},
            "message_counts": {},
            "voice_activity": {},
            "reaction_stats": {}
        }
    
    def save_data(self):
        with open(self.analytics_file, 'w') as f:
            json.dump(self.data, f, indent=4)
    
    @commands.command(name="server_stats")
    async def server_stats(self, ctx):
        """Real-time Server Statistiken"""
        guild = ctx.guild
        
        async with ctx.typing():
            try:
                embed = discord.Embed(
                    title="📊 Server Statistiken",
                    description=f"**{guild.name}**",
                    color=discord.Color.blue()
                )
                
                # Basic stats
                total_members = guild.member_count
                online_members = len([m for m in guild.members if m.status != discord.Status.offline])
                offline_members = total_members - online_members
                
                embed.add_field(name="👥 Gesamtmitglieder", value=total_members)
                embed.add_field(name="🟢 Online", value=online_members)
                embed.add_field(name="⚫ Offline", value=offline_members)
                
                # Channel stats
                text_channels = len([c for c in guild.channels if isinstance(c, discord.TextChannel)])
                voice_channels = len([c for c in guild.channels if isinstance(c, discord.VoiceChannel)])
                categories = len(guild.categories)
                
                embed.add_field(name="💬 Text Channels", value=text_channels)
                embed.add_field(name="🎤 Voice Channels", value=voice_channels)
                embed.add_field(name="📁 Kategorien", value=categories)
                
                # Role stats
                total_roles = len(guild.roles)
                embed.add_field(name="👥 Rollen", value=total_roles)
                
                # Server age
                server_age = (datetime.now() - guild.created_at).days
                embed.add_field(name="📅 Server Alter", value=f"{server_age} Tage")
                
                # Boost level
                if guild.premium_tier:
                    boost_level = ["Kein Boost", "Level 1", "Level 2", "Level 3"][guild.premium_tier]
                    embed.add_field(name="⚡ Boost Level", value=boost_level)
                
                # Emoji stats
                custom_emojis = len([e for e in guild.emojis if not e.animated])
                animated_emojis = len([e for e in guild.emojis if e.animated])
                embed.add_field(name="😀 Custom Emojis", value=custom_emojis)
                embed.add_field(name="🎭 Animated Emojis", value=animated_emojis)
                
                embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
                embed.set_footer(text=f"Stand: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')} | Requested by {ctx.author.name}")
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                await ctx.send(f"Fehler bei den Server Statistiken: {e}")

    @commands.command(name="user_analytics")
    async def user_analytics(self, ctx, user: discord.Member = None):
        """Detaillierte Benutzeranalyse"""
        target = user or ctx.author
        guild = ctx.guild
        
        async with ctx.typing():
            try:
                embed = discord.Embed(
                    title="👤 Benutzer Analytics",
                    description=f"**{target.display_name}** ({target.mention})",
                    color=discord.Color.purple()
                )
                
                # Account information
                account_age = (datetime.now() - target.created_at).days
                server_age = (datetime.now() - target.joined_at).days if target.joined_at else 0
                
                embed.add_field(name="📅 Account Alter", value=f"{account_age} Tage")
                embed.add_field(name="🎮 Server Alter", value=f"{server_age} Tage")
                
                # Status and activity
                status_emoji = {
                    discord.Status.online: "🟢",
                    discord.Status.idle: "🟡",
                    discord.Status.dnd: "🔴",
                    discord.Status.offline: "⚫"
                }
                
                embed.add_field(name="💬 Status", value=f"{status_emoji.get(target.status, '⚫')} {target.status}")
                
                # Roles
                roles = [role.name for role in target.roles if role.name != "@everyone"]
                if roles:
                    embed.add_field(name="👥 Rollen", value=", ".join(roles[:10]))
                
                # Permissions
                permissions = []
                if target.guild_permissions.administrator:
                    permissions.append("👑 Administrator")
                if target.guild_permissions.manage_messages:
                    permissions.append("📝 Nachrichten verwalten")
                if target.guild_permissions.kick_members:
                    permissions.append("👢 Mitglieder kicken")
                if target.guild_permissions.ban_members:
                    permissions.append("🔫 Mitglieder bannen")
                
                if permissions:
                    embed.add_field(name="🔐 Berechtigungen", value=", ".join(permissions))
                
                # Activity analysis (if we have data)
                user_id = str(target.id)
                if user_id in self.data.get("user_activity", {}):
                    activity_data = self.data["user_activity"][user_id]
                    
                    message_count = activity_data.get("message_count", 0)
                    voice_time = activity_data.get("voice_time_minutes", 0)
                    last_seen = activity_data.get("last_seen", "Unbekannt")
                    
                    embed.add_field(name="💬 Nachrichten", value=message_count)
                    embed.add_field(name="🎤 Voice Zeit", value=f"{voice_time} Minuten")
                    embed.add_field(name="👁️ Zuletzt gesehen", value=last_seen)
                
                # Avatar
                if target.avatar:
                    embed.set_thumbnail(url=target.avatar.url)
                
                embed.set_footer(text=f"User Analytics | Requested by {ctx.author.name}")
                await ctx.send(embed=embed)
                
            except Exception as e:
                await ctx.send(f"Fehler bei der Benutzer-Analyse: {e}")

    @commands.command(name="activity_report")
    async def activity_report(self, ctx, days: int = 7):
        """Wöchentliche/Monatliche Berichte"""
        if days < 1 or days > 30:
            await ctx.send("Bitte wähle einen Zeitraum zwischen 1 und 30 Tagen!")
            return
            
        guild = ctx.guild
        cutoff_date = datetime.now() - timedelta(days=days)
        
        async with ctx.typing():
            try:
                embed = discord.Embed(
                    title="📈 Aktivitätsbericht",
                    description=f"**{guild.name}** - Letzte {days} Tage",
                    color=discord.Color.green()
                )
                
                # Calculate activity metrics
                total_members = guild.member_count
                active_members = 0
                message_total = 0
                voice_total = 0
                
                # Simulate activity data (in real implementation, this would come from database)
                for member in guild.members:
                    # Random activity simulation
                    if random.random() > 0.3:  # 70% of members are active
                        active_members += 1
                        message_total += random.randint(10, 500)
                        voice_total += random.randint(0, 300)
                
                activity_rate = (active_members / total_members) * 100 if total_members > 0 else 0
                
                embed.add_field(name="📊 Zeitraum", value=f"{days} Tage")
                embed.add_field(name="👥 Aktive Mitglieder", value=f"{active_members}/{total_members}")
                embed.add_field(name="📈 Aktivitätsrate", value=f"{activity_rate:.1f}%")
                embed.add_field(name="💬 Gesamt Nachrichten", value=message_total)
                embed.add_field(name="🎤 Voice Zeit (Minuten)", value=voice_total)
                embed.add_field(name="📊 Durchschnitt Nachrichten", value=f"{message_total // active_members if active_members > 0 else 0}")
                
                # Activity trend
                if activity_rate > 70:
                    trend = "📈 Sehr aktiv"
                    color = discord.Color.green()
                elif activity_rate > 50:
                    trend = "📊 Aktiv"
                    color = discord.Color.blue()
                elif activity_rate > 30:
                    trend = "📉 Moderat"
                    color = discord.Color.orange
                else:
                    trend = "⚠️ Inaktiv"
                    color = discord.Color.red
                
                embed.add_field(name="📈 Trend", value=trend, inline=False)
                embed.color = color
                
                # Recommendations
                recommendations = []
                if activity_rate < 30:
                    recommendations.append("🎮 Mehr Events und Aktivitäten organisieren")
                if message_total < active_members * 10:
                    recommendations.append("💬 Anreize für mehr Kommunikation schaffen")
                
                if recommendations:
                    embed.add_field(name="💡 Empfehlungen", value="\n".join(recommendations), inline=False)
                
                embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
                embed.set_footer(text=f"Bericht erstellt am {datetime.now().strftime('%d.%m.%Y %H:%M:%S')} | Requested by {ctx.author.name}")
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                await ctx.send(f"Fehler beim Aktivitätsbericht: {e}")

    @commands.command(name="growth_metrics")
    async def growth_metrics(self, ctx, days: int = 30):
        """Wachstumsprognosen"""
        if days < 7 or days > 90:
            await ctx.send("Bitte wähle einen Zeitraum zwischen 7 und 90 Tagen!")
            return
            
        guild = ctx.guild
        
        async with ctx.typing():
            try:
                embed = discord.Embed(
                    title="📈 Wachstumsmetriken",
                    description=f"**{guild.name}** - Letzte {days} Tage",
                    color=discord.Color.gold()
                )
                
                # Calculate growth metrics
                current_members = guild.member_count
                server_age_days = (datetime.now() - guild.created_at).days
                
                # Simulate historical data (in real implementation, this would come from database)
                historical_growth = []
                for i in range(days):
                    # Simulate growth with some randomness
                    base_growth = current_members * (0.001 * i)  # Basic growth
                    random_variation = random.uniform(-0.5, 2.0)  # Random variation
                    daily_members = int(current_members - base_growth + random_variation * 10)
                    historical_growth.append(daily_members)
                
                if len(historical_growth) > 1:
                    start_members = historical_growth[0]
                    end_members = historical_growth[-1]
                    growth_amount = end_members - start_members
                    growth_rate = (growth_amount / start_members) * 100 if start_members > 0 else 0
                    
                    embed.add_field(name="📊 Zeitraum", value=f"{days} Tage")
                    embed.add_field(name="👥 Start Mitglieder", value=start_members)
                    embed.add_field(name="👥 End Mitglieder", value=end_members)
                    embed.add_field(name="📈 Wachstum", value=f"+{growth_amount} ({growth_rate:.1f}%)")
                    embed.add_field(name="📅 Durchschnitt pro Tag", value=f"{growth_amount // days if days > 0 else 0}")
                    
                    # Growth projection
                    if growth_rate > 0:
                        # Project future growth
                        future_days = 30
                        projected_members = int(end_members * (1 + (growth_rate / 100) * (future_days / days)))
                        
                        embed.add_field(name="🔮 Prognose (30 Tage)", value=f"~{projected_members} Mitglieder")
                        
                        # Time projections
                        if growth_rate > 1:
                            time_to_1000 = int((1000 - end_members) / (end_members * growth_rate / 100 / days))
                            if time_to_1000 > 0 and time_to_1000 < 365:
                                embed.add_field(name="⏰ Zeit zu 1000 Mitgliedern", value=f"~{time_to_1000} Tage")
                    
                    # Growth trend
                    if growth_rate > 5:
                        trend = "🚀 Schnelles Wachstum"
                        color = discord.Color.green()
                    elif growth_rate > 2:
                        trend = "📈 Gesundes Wachstum"
                        color = discord.Color.blue()
                    elif growth_rate > 0:
                        trend = "📊 Langsames Wachstum"
                        color = discord.Color.orange
                    else:
                        trend = "📉 Kein Wachstum"
                        color = discord.Color.red
                    
                    embed.add_field(name="📈 Wachstums-Trend", value=trend, inline=False)
                    embed.color = color
                    
                    # Recommendations
                    recommendations = []
                    if growth_rate < 1:
                        recommendations.append("📢 Mehr Werbung für den Server")
                        recommendations.append("🎮 Regelmäßige Events veranstalten")
                    if growth_rate > 10:
                        recommendations.append("🛡️ Server-Kapazitäten überprüfen")
                        recommendations.append("👥 Moderation erweitern")
                    
                    if recommendations:
                        embed.add_field(name="💡 Empfehlungen", value="\n".join(recommendations), inline=False)
                
                embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
                embed.set_footer(text=f"Wachstumsanalyse | Requested by {ctx.author.name}")
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                await ctx.send(f"Fehler bei den Wachstumsmetriken: {e}")

    @commands.command(name="engagement_stats")
    async def engagement_stats(self, ctx, days: int = 7):
        """Engagement Metriken"""
        if days < 1 or days > 30:
            await ctx.send("Bitte wähle einen Zeitraum zwischen 1 und 30 Tagen!")
            return
            
        guild = ctx.guild
        
        async with ctx.typing():
            try:
                embed = discord.Embed(
                    title="💬 Engagement Statistiken",
                    description=f"**{guild.name}** - Letzte {days} Tage",
                    color=discord.Color.pink()
                )
                
                total_members = guild.member_count
                
                # Simulate engagement data
                active_members = int(total_members * random.uniform(0.4, 0.8))
                message_authors = int(active_members * random.uniform(0.6, 0.9))
                voice_users = int(active_members * random.uniform(0.2, 0.6))
                reaction_users = int(active_members * random.uniform(0.3, 0.7))
                
                total_messages = message_authors * random.randint(5, 50)
                total_reactions = total_messages * random.uniform(0.5, 2.0)
                total_voice_minutes = voice_users * random.randint(10, 120)
                
                # Calculate engagement rates
                message_engagement = (message_authors / total_members) * 100 if total_members > 0 else 0
                voice_engagement = (voice_users / total_members) * 100 if total_members > 0 else 0
                reaction_engagement = (reaction_users / total_members) * 100 if total_members > 0 else 0
                
                embed.add_field(name="📊 Zeitraum", value=f"{days} Tage")
                embed.add_field(name="👥 Aktive Mitglieder", value=f"{active_members} ({(active_members/total_members)*100:.1f}%)")
                embed.add_field(name="💬 Nachrichten-Autoren", value=f"{message_authors}")
                embed.add_field(name="🎤 Voice Nutzer", value=f"{voice_users}")
                embed.add_field(name="😀 Reaktions-Nutzer", value=f"{reaction_users}")
                
                embed.add_field(name="📝 Nachrichten Engagement", value=f"{message_engagement:.1f}%")
                embed.add_field(name="🎤 Voice Engagement", value=f"{voice_engagement:.1f}%")
                embed.add_field(name="😀 Reaktions Engagement", value=f"{reaction_engagement:.1f}%")
                
                embed.add_field(name="💬 Gesamt Nachrichten", value=total_messages)
                embed.add_field(name="😀 Gesamt Reaktionen", value=int(total_reactions))
                embed.add_field(name="🎤 Voice Zeit (Minuten)", value=total_voice_minutes)
                
                # Engagement score
                engagement_score = (message_engagement + voice_engagement + reaction_engagement) / 3
                
                if engagement_score > 60:
                    engagement_level = "🔥 Sehr Hoch"
                    color = discord.Color.red()
                elif engagement_score > 40:
                    engagement_level = "🚀 Hoch"
                    color = discord.Color.orange()
                elif engagement_score > 20:
                    engagement_level = "📊 Moderat"
                    color = discord.Color.blue()
                else:
                    engagement_level = "📉 Niedrig"
                    color = discord.Color.grey()
                
                embed.add_field(name="📈 Engagement Level", value=f"{engagement_level} ({engagement_score:.1f}%)", inline=False)
                embed.color = color
                
                # Top engagement channels (simulated)
                text_channels = [c for c in guild.channels if isinstance(c, discord.TextChannel)][:5]
                if text_channels:
                    top_channels = []
                    for channel in text_channels:
                        activity = random.randint(10, 100)
                        top_channels.append(f"{channel.name}: {activity}")
                    
                    embed.add_field(name="🏆 Top Channels", value="\n".join(top_channels), inline=False)
                
                embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
                embed.set_footer(text=f"Engagement Analyse | Requested by {ctx.author.name}")
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                await ctx.send(f"Fehler bei den Engagement Statistiken: {e}")

async def setup(bot):
    await bot.add_cog(Analytics(bot))
