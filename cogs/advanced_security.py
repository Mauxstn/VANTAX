import discord
import aiohttp
import json
import asyncio
import re
import hashlib
import time
from datetime import datetime, timedelta
from discord.ext import commands
import os

class AdvancedSecurity(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.virustotal_key = os.getenv("VIRUSTOTAL_API_KEY", "")
        self.security_data = {}
        self.threat_levels = {}
        self.scan_results = {}
        
    @commands.command(name="antivirus")
    async def antivirus(self, ctx, *, url_or_text: str):
        """Link Scanner mit VirusTotal"""
        if not self.virustotal_key:
            await ctx.send("VirusTotal API Key nicht konfiguriert!")
            return
            
        # Check if it's a URL
        url_pattern = re.compile(
            r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:\w*))?'
        )
        urls = url_pattern.findall(url_or_text)
        
        if not urls:
            await ctx.send("Keine URL gefunden zum Scannen!")
            return
            
        async with ctx.typing():
            try:
                for url in urls[:3]:  # Limit to 3 URLs per command
                    headers = {
                        "x-apikey": self.virustotal_key
                    }
                    
                    data = {
                        "resource": url
                    }
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            "https://www.virustotal.com/vtapi/v2/url/scan",
                            headers=headers,
                            data=data
                        ) as response:
                            if response.status == 200:
                                result = await response.json()
                                scan_id = result['scan_id']
                                
                                # Wait a bit and get results
                                await asyncio.sleep(3)
                                
                                async with session.get(
                                    f"https://www.virustotal.com/vtapi/v2/url/report",
                                    headers=headers,
                                    params={"resource": scan_id}
                                ) as report_response:
                                    if report_response.status == 200:
                                        report = await report_response.json()
                                        
                                        positives = report.get('positives', 0)
                                        total = report.get('total', 1)
                                        threat_level = "Sicher" if positives == 0 else f"⚠️ {positives}/{total} Bedrohungen"
                                        
                                        color = discord.Color.green() if positives == 0 else discord.Color.orange() if positives < 5 else discord.Color.red()
                                        
                                        embed = discord.Embed(
                                            title="🛡️ Antivirus Scan",
                                            url=url,
                                            color=color
                                        )
                                        embed.add_field(name="🔗 URL", value=url[:100] + "..." if len(url) > 100 else url, inline=False)
                                        embed.add_field(name="🛡️ Scan Ergebnis", value=threat_level)
                                        embed.add_field(name="📊 Scan Datum", value=report.get('scan_date', 'Unbekannt'))
                                        embed.add_field(name="🔍 Positiv", value=f"{positives}/{total}")
                                        
                                        if positives > 0:
                                            malicious_engines = []
                                            for engine, result in report.get('scans', {}).items():
                                                if result.get('detected', False):
                                                    malicious_engines.append(f"{engine}: {result.get('result', 'Detected')}")
                                            
                                            if malicious_engines:
                                                embed.add_field(name="⚠️ Erkannt von", value="\n".join(malicious_engines[:5]), inline=False)
                                        
                                        embed.set_footer(text="Powered by VirusTotal | Requested by " + ctx.author.name)
                                        await ctx.send(embed=embed)
                                    else:
                                        await ctx.send("Fehler beim Abrufen der Scan-Ergebnisse!")
                            else:
                                await ctx.send(f"Fehler beim Scannen: {response.status}")
                                
            except Exception as e:
                await ctx.send(f"Fehler beim Antivirus-Scan: {e}")

    @commands.command(name="ip_lookup")
    async def ip_lookup(self, ctx, ip_address: str):
        """IP Geolocation & Security"""
        async with ctx.typing():
            try:
                # IP Geolocation
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"http://ip-api.com/json/{ip_address}") as response:
                        if response.status == 200:
                            geo_data = await response.json()
                            
                            if geo_data.get('status') == 'fail':
                                await ctx.send(f"Ungültige IP-Adresse: {geo_data.get('message', 'Unbekannter Fehler')}")
                                return
                            
                            embed = discord.Embed(
                                title="🌍 IP Lookup",
                                description=f"**{ip_address}**",
                                color=discord.Color.blue()
                            )
                            
                            embed.add_field(name="🌍 Land", value=geo_data.get('country', 'Unbekannt'))
                            embed.add_field(name="🏙️ Stadt", value=geo_data.get('city', 'Unbekannt'))
                            embed.add_field(name="📍 Region", value=geo_data.get('regionName', 'Unbekannt'))
                            embed.add_field(name="🏢 ISP", value=geo_data.get('isp', 'Unbekannt'))
                            embed.add_field(name="🌐 Zeitzone", value=geo_data.get('timezone', 'Unbekannt'))
                            embed.add_field(name="📍 Koordinaten", value=f"{geo_data.get('lat', 'N/A')}, {geo_data.get('lon', 'N/A')}")
                            
                            # Security assessment
                            is_proxy = geo_data.get('proxy', False)
                            is_mobile = geo_data.get('mobile', False)
                            
                            security_status = "✅ Sicher"
                            security_color = discord.Color.green()
                            
                            if is_proxy:
                                security_status = "⚠️ Proxy/VPN"
                                security_color = discord.Color.orange
                            
                            embed.add_field(name="🛡️ Sicherheitsstatus", value=security_status, inline=False)
                            embed.color = security_color
                            
                            embed.set_footer(text="Powered by IP-API | Requested by " + ctx.author.name)
                            await ctx.send(embed=embed)
                        else:
                            await ctx.send("Fehler bei der IP-Abfrage!")
                            
            except Exception as e:
                await ctx.send(f"Fehler bei der IP-Lookup: {e}")

    @commands.command(name="user_scan")
    async def user_scan(self, ctx, user: discord.Member = None):
        """Benutzer Sicherheitsanalyse"""
        target = user or ctx.author
        
        async with ctx.typing():
            try:
                embed = discord.Embed(
                    title="🔍 Benutzer Sicherheitsanalyse",
                    description=f"**{target.display_name}** ({target.mention})",
                    color=discord.Color.blue()
                )
                
                # Account information
                created_at = target.created_at.strftime("%d.%m.%Y %H:%M")
                joined_at = target.joined_at.strftime("%d.%m.%Y %H:%M") if target.joined_at else "Unbekannt"
                
                embed.add_field(name="📅 Account erstellt", value=created_at)
                embed.add_field(name="🎮 Server beigetreten", value=joined_at)
                
                # Account age analysis
                account_age = (datetime.now() - target.created_at).days
                if account_age < 7:
                    risk_level = "⚠️ Hoch (Neues Account)"
                    risk_color = discord.Color.red()
                elif account_age < 30:
                    risk_level = "🟡 Mittel (Junges Account)"
                    risk_color = discord.Color.orange
                else:
                    risk_level = "✅ Niedrig (Altes Account)"
                    risk_color = discord.Color.green()
                
                embed.add_field(name="🎯 Risiko Level", value=risk_level, inline=False)
                embed.color = risk_color
                
                # Role analysis
                roles = [role.name for role in target.roles if role.name != "@everyone"]
                if roles:
                    embed.add_field(name="👥 Rollen", value=", ".join(roles[:10]))
                
                # Permission analysis
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
                
                # Avatar analysis
                if target.avatar:
                    embed.set_thumbnail(url=target.avatar.url)
                
                # Status
                status_emoji = {
                    discord.Status.online: "🟢",
                    discord.Status.idle: "🟡",
                    discord.Status.dnd: "🔴",
                    discord.Status.offline: "⚫"
                }
                
                embed.add_field(name="💬 Status", value=f"{status_emoji.get(target.status, '⚫')} {target.status}")
                
                embed.set_footer(text="Sicherheitsanalyse | Requested by " + ctx.author.name)
                await ctx.send(embed=embed)
                
            except Exception as e:
                await ctx.send(f"Fehler bei der Benutzer-Analyse: {e}")

    @commands.command(name="server_security")
    async def server_security(self, ctx):
        """Kompletter Security Audit"""
        async with ctx.typing():
            try:
                guild = ctx.guild
                embed = discord.Embed(
                    title="🛡️ Server Sicherheitsaudit",
                    description=f"**{guild.name}**",
                    color=discord.Color.gold()
                )
                
                # Basic server info
                embed.add_field(name="📊 Server ID", value=guild.id)
                embed.add_field(name="👥 Mitglieder", value=guild.member_count)
                embed.add_field(name="📅 Erstellt", value=guild.created_at.strftime("%d.%m.%Y"))
                
                # Security settings
                verification_levels = {
                    discord.VerificationLevel.none: "Keine",
                    discord.VerificationLevel.low: "Niedrig",
                    discord.VerificationLevel.medium: "Mittel",
                    discord.VerificationLevel.high: "Hoch",
                    discord.VerificationLevel.highest: "Höchste"
                }
                
                content_filter = {
                    discord.ContentFilter.disabled: "Deaktiviert",
                    discord.ContentFilter.no_role: "Keine Rolle",
                    discord.ContentFilter.all_members: "Alle Mitglieder"
                }
                
                embed.add_field(name="🔐 Verifizierungslevel", value=verification_levels[guild.verification_level])
                embed.add_field(name="🛡️ Content Filter", value=content_filter[guild.explicit_content_filter])
                
                # Role analysis
                admin_roles = [role for role in guild.roles if role.permissions.administrator]
                dangerous_roles = [role for role in guild.roles if role.permissions.kick_members or role.permissions.ban_members]
                
                embed.add_field(name="👑 Admin Rollen", value=len(admin_roles))
                embed.add_field(name="⚠️ Gefährliche Rollen", value=len(dangerous_roles))
                
                # Channel security
                text_channels = len([c for c in guild.channels if isinstance(c, discord.TextChannel)])
                voice_channels = len([c for c in guild.channels if isinstance(c, discord.VoiceChannel)])
                
                embed.add_field(name="💬 Text Channels", value=text_channels)
                embed.add_field(name="🎤 Voice Channels", value=voice_channels)
                
                # Member security
                new_accounts = len([m for m in guild.members if (datetime.now() - m.created_at).days < 7])
                embed.add_field(name="🆕 Neue Accounts (< 7 Tage)", value=new_accounts)
                
                # Security score
                security_score = 100
                
                if guild.verification_level == discord.VerificationLevel.none:
                    security_score -= 20
                elif guild.verification_level == discord.VerificationLevel.low:
                    security_score -= 10
                    
                if guild.explicit_content_filter == discord.ContentFilter.disabled:
                    security_score -= 15
                    
                if len(admin_roles) > 5:
                    security_score -= 10
                    
                if new_accounts > guild.member_count * 0.1:  # More than 10% new accounts
                    security_score -= 15
                
                security_score = max(0, security_score)
                
                if security_score >= 80:
                    security_status = "🟢 Sehr Sicher"
                    color = discord.Color.green()
                elif security_score >= 60:
                    security_status = "🟡 Sicher"
                    color = discord.Color.orange
                elif security_score >= 40:
                    security_status = "🟠 Mittelmäßig"
                    color = discord.Color.orange
                else:
                    security_status = "🔴 Unsicher"
                    color = discord.Color.red()
                
                embed.add_field(name="📊 Sicherheits-Score", value=f"{security_score}/100 - {security_status}", inline=False)
                embed.color = color
                
                embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
                embed.set_footer(text="Server Sicherheitsaudit | Requested by " + ctx.author.name)
                await ctx.send(embed=embed)
                
            except Exception as e:
                await ctx.send(f"Fehler beim Security Audit: {e}")

    @commands.command(name="threat_level")
    async def threat_level(self, ctx):
        """Echtzeit Bedrohungsanalyse"""
        async with ctx.typing():
            try:
                guild = ctx.guild
                
                # Calculate threat indicators
                new_accounts = len([m for m in guild.members if (datetime.now() - m.created_at).days < 7])
                very_new_accounts = len([m for m in guild.members if (datetime.now() - m.created_at).days < 1])
                
                # Check for suspicious patterns
                total_members = guild.member_count
                new_account_ratio = new_accounts / total_members if total_members > 0 else 0
                
                # Calculate threat level
                threat_score = 0
                
                if very_new_accounts > 10:
                    threat_score += 30
                elif very_new_accounts > 5:
                    threat_score += 20
                elif very_new_accounts > 2:
                    threat_score += 10
                    
                if new_account_ratio > 0.2:  # More than 20% new accounts
                    threat_score += 25
                elif new_account_ratio > 0.1:  # More than 10% new accounts
                    threat_score += 15
                elif new_account_ratio > 0.05:  # More than 5% new accounts
                    threat_score += 5
                
                # Recent joins in last hour
                recent_joins = len([m for m in guild.members if m.joined_at and (datetime.now() - m.joined_at).seconds < 3600])
                if recent_joins > 20:
                    threat_score += 25
                elif recent_joins > 10:
                    threat_score += 15
                elif recent_joins > 5:
                    threat_score += 5
                
                # Determine threat level
                if threat_score >= 70:
                    threat_level = "🔴 KRITISCH"
                    color = discord.Color.red()
                    recommendation = "⚠️ Sofortige Maßnahmen erforderlich! Überprüfe neue Mitglieder und erwarte einen möglichen Raid!"
                elif threat_score >= 40:
                    threat_level = "🟠 ERHÖHT"
                    color = discord.Color.orange()
                    recommendation = "🔍 Erhöhte Wachsamkeit erforderlich. Überwache neue Mitglieder aktiv."
                elif threat_score >= 20:
                    threat_level = "🟡 NORMAL"
                    color = discord.Color.yellow()
                    recommendation = "✅ Normale Sicherheit. Regelmäßige Überwachung empfohlen."
                else:
                    threat_level = "🟢 NIEDRIG"
                    color = discord.Color.green()
                    recommendation = "🛡️ Geringe Bedrohung. Server ist sicher."
                
                embed = discord.Embed(
                    title="🚨 Echtzeit Bedrohungsanalyse",
                    description=f"**{guild.name}**",
                    color=color
                )
                
                embed.add_field(name="📊 Bedrohungs-Level", value=f"**{threat_level}** ({threat_score}/100)", inline=False)
                embed.add_field(name="🆕 Sehr neue Accounts (< 1 Tag)", value=very_new_accounts)
                embed.add_field(name="📅 Neue Accounts (< 7 Tage)", value=new_accounts)
                embed.add_field(name="👥 Neue Accounts Ratio", value=f"{new_account_ratio:.1%}")
                embed.add_field(name="⏰ Kürzliche Joins (< 1h)", value=recent_joins)
                embed.add_field(name="💡 Empfehlung", value=recommendation, inline=False)
                
                # Add timestamp
                embed.set_footer(text=f"Analyse vom {datetime.now().strftime('%d.%m.%Y %H:%M:%S')} | Requested by {ctx.author.name}")
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                await ctx.send(f"Fehler bei der Bedrohungsanalyse: {e}")

    @commands.command(name="security_report")
    async def security_report(self, ctx, days: int = 7):
        """Sicherheitsbericht"""
        if days < 1 or days > 30:
            await ctx.send("Bitte wähle einen Zeitraum zwischen 1 und 30 Tagen!")
            return
            
        async with ctx.typing():
            try:
                guild = ctx.guild
                cutoff_date = datetime.now() - timedelta(days=days)
                
                # Analyze member joins
                new_members = [m for m in guild.members if m.joined_at and m.joined_at > cutoff_date]
                very_new_members = [m for m in new_members if (datetime.now() - m.created_at).days < 7]
                
                # Analyze roles and permissions
                admin_count = len([r for r in guild.roles if r.permissions.administrator])
                
                embed = discord.Embed(
                    title="📊 Sicherheitsbericht",
                    description=f"**{guild.name}** - Letzte {days} Tage",
                    color=discord.Color.blue()
                )
                
                embed.add_field(name="📊 Zeitraum", value=f"{days} Tage")
                embed.add_field(name="👥 Neue Mitglieder", value=len(new_members))
                embed.add_field(name="⚠️ Verdächtige Accounts", value=len(very_new_members))
                embed.add_field(name="👑 Admin Rollen", value=admin_count)
                embed.add_field(name="📈 Wachstumsrate", value=f"{len(new_members)} Mitglieder")
                
                # Security recommendations
                recommendations = []
                
                if len(very_new_members) > len(new_members) * 0.3:
                    recommendations.append("🔍 Hoher Anteil an sehr neuen Accounts - erhöhte Wachsamkeit empfohlen")
                
                if guild.verification_level == discord.VerificationLevel.none:
                    recommendations.append("🔐 Keine Verifizierung - erwarte erhöhtes Sicherheitsrisiko")
                
                if admin_count > 10:
                    recommendations.append("👂 Viele Admin Rollen - überprüfe Berechtigungen")
                
                if recommendations:
                    embed.add_field(name="💡 Empfehlungen", value="\n".join(recommendations), inline=False)
                else:
                    embed.add_field(name="✅ Status", value="Keine Sicherheitsbedenken festgestellt", inline=False)
                
                embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
                embed.set_footer(text=f"Bericht erstellt am {datetime.now().strftime('%d.%m.%Y %H:%M:%S')} | Requested by {ctx.author.name}")
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                await ctx.send(f"Fehler beim Sicherheitsbericht: {e}")

async def setup(bot):
    await bot.add_cog(AdvancedSecurity(bot))
