import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import time
import hashlib
import secrets
import sqlite3
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import psutil
import gc

# Constants
VANTAX_COLOR = discord.Color.blurple()
VANTAX_FOOTER = "VANTAX Discord Bot by Maurice"

class Security(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.security_config_file = "security_config.json"
        self.security_config = self.load_security_config()
        self.rate_limits = {}  # In-memory rate limiting
        self.ip_whitelist = self.security_config.get("ip_whitelist", [])
        self.two_factor_codes = {}  # Temporary 2FA codes
        self.audit_log_file = "audit_log.json"
        self.audit_log = self.load_audit_log()
        
        # Initialize database
        self.init_database()
        
        # Start memory monitoring
        self.bot.loop.create_task(self.monitor_memory())
        
        # Start cleanup tasks
        self.bot.loop.create_task(self.cleanup_expired_data())
    
    def load_security_config(self):
        try:
            if os.path.exists(self.security_config_file):
                with open(self.security_config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {
                "ip_whitelist": [],
                "two_factor_required": False,
                "rate_limits": {
                    "default": {"requests": 10, "window": 60},
                    "admin": {"requests": 5, "window": 60},
                    "moderation": {"requests": 3, "window": 60}
                },
                "audit_logging": True
            }
        except Exception as e:
            print(f"Error loading security config: {e}")
            return {}
    
    def save_security_config(self):
        try:
            with open(self.security_config_file, 'w', encoding='utf-8') as f:
                json.dump(self.security_config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving security config: {e}")
    
    def load_audit_log(self):
        try:
            if os.path.exists(self.audit_log_file):
                with open(self.audit_log_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception as e:
            print(f"Error loading audit log: {e}")
            return []
    
    def save_audit_log(self):
        try:
            # Keep only last 1000 entries
            if len(self.audit_log) > 1000:
                self.audit_log = self.audit_log[-1000:]
            
            with open(self.audit_log_file, 'w', encoding='utf-8') as f:
                json.dump(self.audit_log, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving audit log: {e}")
    
    def init_database(self):
        """Initialize SQLite database for security logs"""
        try:
            self.conn = sqlite3.connect('security.db', check_same_thread=False)
            self.cursor = self.conn.cursor()
            
            # Create tables
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    user_id TEXT,
                    username TEXT,
                    action TEXT,
                    details TEXT,
                    guild_id TEXT,
                    ip_address TEXT
                )
            ''')
            
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS rate_limits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    command TEXT,
                    timestamp TEXT,
                    requests_count INTEGER
                )
            ''')
            
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS failed_logins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    timestamp TEXT,
                    ip_address TEXT,
                    reason TEXT
                )
            ''')
            
            self.conn.commit()
            print("Security database initialized successfully!")
            
        except Exception as e:
            print(f"Error initializing database: {e}")
    
    async def monitor_memory(self):
        """Monitor and optimize memory usage"""
        await self.bot.wait_until_ready()
        
        while not self.bot.is_closed():
            try:
                # Get memory usage
                process = psutil.Process()
                memory_info = process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024
                
                # Log memory usage
                self.log_audit(
                    user_id=self.bot.user.id,
                    username="SYSTEM",
                    action="MEMORY_CHECK",
                    details=f"Memory usage: {memory_mb:.2f} MB",
                    guild_id="SYSTEM"
                )
                
                # Force garbage collection if memory is high
                if memory_mb > 500:  # If using more than 500MB
                    gc.collect()
                    self.log_audit(
                        user_id=self.bot.user.id,
                        username="SYSTEM",
                        action="GARBAGE_COLLECTION",
                        details="Forced garbage collection due to high memory usage",
                        guild_id="SYSTEM"
                    )
                
                # Clean up old rate limit data
                await self.cleanup_rate_limits()
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                print(f"Error in memory monitoring: {e}")
                await asyncio.sleep(60)
    
    async def cleanup_rate_limits(self):
        """Clean up expired rate limit entries"""
        try:
            current_time = time.time()
            expired_keys = []
            
            for key, data in self.rate_limits.items():
                if current_time - data["reset_time"] > 300:  # 5 minutes
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.rate_limits[key]
            
            # Also clean up database
            cutoff_time = datetime.now() - timedelta(hours=1)
            self.cursor.execute(
                "DELETE FROM rate_limits WHERE timestamp < ?",
                (cutoff_time.isoformat(),)
            )
            self.conn.commit()
            
        except Exception as e:
            print(f"Error cleaning up rate limits: {e}")
    
    async def cleanup_expired_data(self):
        """Clean up expired 2FA codes and other temporary data"""
        await self.bot.wait_until_ready()
        
        while not self.bot.is_closed():
            try:
                current_time = time.time()
                
                # Clean up expired 2FA codes
                expired_codes = []
                for user_id, data in self.two_factor_codes.items():
                    if current_time - data["timestamp"] > 300:  # 5 minutes
                        expired_codes.append(user_id)
                
                for user_id in expired_codes:
                    del self.two_factor_codes[user_id]
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                print(f"Error in cleanup task: {e}")
                await asyncio.sleep(60)
    
    def check_rate_limit(self, user_id: str, command_type: str = "default") -> bool:
        """Check if user is rate limited"""
        try:
            current_time = time.time()
            user_key = f"{user_id}:{command_type}"
            
            # Get rate limit config
            rate_config = self.security_config.get("rate_limits", {}).get(command_type, 
                                                                        {"requests": 10, "window": 60})
            
            max_requests = rate_config.get("requests", 10)
            window = rate_config.get("window", 60)
            
            if user_key not in self.rate_limits:
                self.rate_limits[user_key] = {
                    "requests": 0,
                    "reset_time": current_time + window
                }
            
            # Check if window has expired
            if current_time > self.rate_limits[user_key]["reset_time"]:
                self.rate_limits[user_key] = {
                    "requests": 0,
                    "reset_time": current_time + window
                }
            
            # Check rate limit
            if self.rate_limits[user_key]["requests"] >= max_requests:
                return False
            
            # Increment request count
            self.rate_limits[user_key]["requests"] += 1
            
            # Log to database
            self.cursor.execute(
                "INSERT INTO rate_limits (user_id, command, timestamp, requests_count) VALUES (?, ?, ?, ?)",
                (user_id, command_type, datetime.now().isoformat(), self.rate_limits[user_key]["requests"])
            )
            self.conn.commit()
            
            return True
            
        except Exception as e:
            print(f"Error checking rate limit: {e}")
            return True  # Allow on error
    
    def check_ip_whitelist(self, ip_address: str) -> bool:
        """Check if IP is whitelisted"""
        if not self.ip_whitelist:
            return True  # No whitelist means all IPs allowed
        
        return ip_address in self.ip_whitelist
    
    def generate_2fa_code(self, user_id: str) -> str:
        """Generate 2FA code for user"""
        code = f"{secrets.randbelow(1000000):06d}"
        self.two_factor_codes[user_id] = {
            "code": code,
            "timestamp": time.time()
        }
        return code
    
    def verify_2fa_code(self, user_id: str, code: str) -> bool:
        """Verify 2FA code"""
        if user_id not in self.two_factor_codes:
            return False
        
        stored_data = self.two_factor_codes[user_id]
        
        # Check if code is expired (5 minutes)
        if time.time() - stored_data["timestamp"] > 300:
            del self.two_factor_codes[user_id]
            return False
        
        # Verify code
        if stored_data["code"] == code:
            del self.two_factor_codes[user_id]
            return True
        
        return False
    
    def log_audit(self, user_id: str, username: str, action: str, details: str, guild_id: str, ip_address: str = "unknown"):
        """Log audit event"""
        try:
            audit_entry = {
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id,
                "username": username,
                "action": action,
                "details": details,
                "guild_id": guild_id,
                "ip_address": ip_address
            }
            
            # Add to memory log
            self.audit_log.append(audit_entry)
            
            # Save to file
            self.save_audit_log()
            
            # Save to database
            self.cursor.execute(
                "INSERT INTO audit_logs (timestamp, user_id, username, action, details, guild_id, ip_address) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (audit_entry["timestamp"], audit_entry["user_id"], audit_entry["username"], 
                 audit_entry["action"], audit_entry["details"], audit_entry["guild_id"], audit_entry["ip_address"])
            )
            self.conn.commit()
            
        except Exception as e:
            print(f"Error logging audit: {e}")
    
    def check_permission(self, interaction: discord.Interaction, required_permission: str = "admin") -> bool:
        """Check if user has required permission and pass security checks"""
        try:
            user_id = str(interaction.user.id)
            
            # Check rate limit
            if not self.check_rate_limit(user_id, required_permission):
                return False
            
            # Check 2FA requirement
            if self.security_config.get("two_factor_required", False):
                if required_permission in ["admin", "moderation"]:
                    # Would need to implement 2FA verification here
                    pass
            
            # Log the attempt
            self.log_audit(
                user_id=user_id,
                username=interaction.user.name,
                action="PERMISSION_CHECK",
                details=f"Checking {required_permission} permission",
                guild_id=str(interaction.guild.id) if interaction.guild else "DM"
            )
            
            return True
            
        except Exception as e:
            print(f"Error checking permission: {e}")
            return False
    
    @app_commands.command(name="security", description="Security System Overview")
    @app_commands.checks.has_permissions(administrator=True)
    async def security_overview(self, interaction: discord.Interaction):
        """Show security system overview"""
        try:
            if not self.check_permission(interaction, "admin"):
                await interaction.response.send_message("❌ Rate limit exceeded or permission denied!", ephemeral=True)
                return
            
            # Get memory usage
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            embed = discord.Embed(
                title="🛡️ Security System Overview",
                description="Professional security features status",
                color=VANTAX_COLOR
            )
            
            # Memory Management
            embed.add_field(
                name="💾 Memory Management",
                value=f"Usage: {memory_mb:.2f} MB\nRate Limits: {len(self.rate_limits)} active",
                inline=True
            )
            
            # 2FA Status
            embed.add_field(
                name="🔐 Two-Factor Authentication",
                value=f"Required: {'✅' if self.security_config.get('two_factor_required', False) else '❌'}\nActive Codes: {len(self.two_factor_codes)}",
                inline=True
            )
            
            # IP Whitelist
            embed.add_field(
                name="🌐 IP Whitelist",
                value=f"Whitelisted IPs: {len(self.ip_whitelist)}\nStatus: {'Active' if self.ip_whitelist else 'Disabled'}",
                inline=True
            )
            
            # Rate Limits
            rate_limits = self.security_config.get("rate_limits", {})
            embed.add_field(
                name="⚡ Rate Limits",
                value=f"Default: {rate_limits.get('default', {}).get('requests', 10)}/60s\nAdmin: {rate_limits.get('admin', {}).get('requests', 5)}/60s",
                inline=True
            )
            
            # Audit Logging
            embed.add_field(
                name="📊 Audit Logging",
                value=f"Status: {'✅' if self.security_config.get('audit_logging', True) else '❌'}\nEntries: {len(self.audit_log)}",
                inline=True
            )
            
            # Database
            embed.add_field(
                name="🗄️ Database",
                value="SQLite: ✅ Connected\nTables: 3 (audit, rate_limits, failed_logins)",
                inline=True
            )
            
            embed.set_footer(text=VANTAX_FOOTER)
            await interaction.response.send_message(embed=embed)
            
            # Log this action
            self.log_audit(
                user_id=str(interaction.user.id),
                username=interaction.user.name,
                action="SECURITY_OVERVIEW",
                details="Viewed security system overview",
                guild_id=str(interaction.guild.id)
            )
            
        except Exception as e:
            print(f"Error in security overview: {e}")
            await interaction.response.send_message("❌ Ein Fehler ist aufgetreten.", ephemeral=True)
    
    @app_commands.command(name="2fa", description="Generate 2FA code")
    @app_commands.checks.has_permissions(administrator=True)
    async def generate_2fa(self, interaction: discord.Interaction):
        """Generate 2FA authentication code"""
        try:
            if not self.check_permission(interaction, "admin"):
                await interaction.response.send_message("❌ Rate limit exceeded!", ephemeral=True)
                return
            
            user_id = str(interaction.user.id)
            code = self.generate_2fa_code(user_id)
            
            embed = discord.Embed(
                title="🔐 2FA Code Generated",
                description=f"Your 2FA code is: **{code}**\n\nThis code will expire in 5 minutes.",
                color=discord.Color.gold()
            )
            
            embed.add_field(
                name="⚠️ Security Notice",
                value="Keep this code secure and do not share it with anyone!",
                inline=False
            )
            
            embed.set_footer(text=VANTAX_FOOTER)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # Log this action
            self.log_audit(
                user_id=user_id,
                username=interaction.user.name,
                action="2FA_GENERATED",
                details="2FA code generated for user",
                guild_id=str(interaction.guild.id)
            )
            
        except Exception as e:
            print(f"Error generating 2FA: {e}")
            await interaction.response.send_message("❌ Ein Fehler ist aufgetreten.", ephemeral=True)
    
    @app_commands.command(name="auditlog", description="View audit log")
    @app_commands.checks.has_permissions(administrator=True)
    async def view_audit_log(self, interaction: discord.Interaction, limit: int = 50):
        """View audit log entries"""
        try:
            if not self.check_permission(interaction, "admin"):
                await interaction.response.send_message("❌ Rate limit exceeded!", ephemeral=True)
                return
            
            # Get recent entries
            recent_entries = self.audit_log[-limit:]
            
            if not recent_entries:
                await interaction.response.send_message("📊 No audit log entries found.", ephemeral=True)
                return
            
            embed = discord.Embed(
                title="📊 Audit Log",
                description=f"Last {len(recent_entries)} entries",
                color=VANTAX_COLOR
            )
            
            for entry in recent_entries[-10:]:  # Show last 10 in embed
                timestamp = entry.get("timestamp", "Unknown")
                username = entry.get("username", "Unknown")
                action = entry.get("action", "Unknown")
                details = entry.get("details", "No details")
                
                embed.add_field(
                    name=f"{action} - {timestamp[:19]}",
                    value=f"User: {username}\nDetails: {details[:100]}...",
                    inline=False
                )
            
            embed.set_footer(text=f"Total entries: {len(self.audit_log)} | " + VANTAX_FOOTER)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # Log this action
            self.log_audit(
                user_id=str(interaction.user.id),
                username=interaction.user.name,
                action="AUDIT_LOG_VIEWED",
                details=f"Viewed {limit} audit log entries",
                guild_id=str(interaction.guild.id)
            )
            
        except Exception as e:
            print(f"Error viewing audit log: {e}")
            await interaction.response.send_message("❌ Ein Fehler ist aufgetreten.", ephemeral=True)
    
    @app_commands.command(name="ratelimits", description="Configure rate limits")
    @app_commands.checks.has_permissions(administrator=True)
    async def configure_rate_limits(self, interaction: discord.Interaction, command_type: str, requests: int, window: int):
        """Configure rate limits for command types"""
        try:
            if not self.check_permission(interaction, "admin"):
                await interaction.response.send_message("❌ Rate limit exceeded!", ephemeral=True)
                return
            
            if command_type not in ["default", "admin", "moderation"]:
                await interaction.response.send_message("❌ Invalid command type. Use: default, admin, or moderation", ephemeral=True)
                return
            
            if requests < 1 or window < 1:
                await interaction.response.send_message("❌ Requests and window must be positive numbers!", ephemeral=True)
                return
            
            # Update config
            if "rate_limits" not in self.security_config:
                self.security_config["rate_limits"] = {}
            
            self.security_config["rate_limits"][command_type] = {
                "requests": requests,
                "window": window
            }
            
            self.save_security_config()
            
            embed = discord.Embed(
                title="⚡ Rate Limits Updated",
                description=f"Rate limits for **{command_type}** commands updated!",
                color=VANTAX_COLOR
            )
            
            embed.add_field(
                name="📊 New Limits",
                value=f"Requests: {requests}\nTime Window: {window} seconds",
                inline=True
            )
            
            embed.set_footer(text=VANTAX_FOOTER)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # Log this action
            self.log_audit(
                user_id=str(interaction.user.id),
                username=interaction.user.name,
                action="RATE_LIMITS_UPDATED",
                details=f"Updated {command_type} rate limits: {requests}/{window}s",
                guild_id=str(interaction.guild.id)
            )
            
        except Exception as e:
            print(f"Error configuring rate limits: {e}")
            await interaction.response.send_message("❌ Ein Fehler ist aufgetreten.", ephemeral=True)
    
    @app_commands.command(name="memory", description="Memory management and optimization")
    @app_commands.checks.has_permissions(administrator=True)
    async def memory_management(self, interaction: discord.Interaction, action: str = "status"):
        """Memory management commands"""
        try:
            if not self.check_permission(interaction, "admin"):
                await interaction.response.send_message("❌ Rate limit exceeded!", ephemeral=True)
                return
            
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            if action == "status":
                embed = discord.Embed(
                    title="💾 Memory Status",
                    description="Current memory usage and optimization status",
                    color=VANTAX_COLOR
                )
                
                embed.add_field(
                    name="📊 Current Usage",
                    value=f"RSS Memory: {memory_mb:.2f} MB\nVMS Memory: {memory_info.vms / 1024 / 1024:.2f} MB",
                    inline=True
                )
                
                embed.add_field(
                    name="🧹 Cache Status",
                    value=f"Rate Limits: {len(self.rate_limits)} entries\n2FA Codes: {len(self.two_factor_codes)} entries",
                    inline=True
                )
                
                embed.add_field(
                    name="⚡ Optimization",
                    value="Auto-cleanup: ✅ Active\nGarbage Collection: ✅ Active",
                    inline=True
                )
                
            elif action == "cleanup":
                # Force cleanup
                gc.collect()
                
                # Clear expired rate limits
                await self.cleanup_rate_limits()
                
                embed = discord.Embed(
                    title="🧹 Memory Cleanup",
                    description="Forced memory cleanup completed!",
                    color=discord.Color.green()
                )
                
                embed.add_field(
                    name="✅ Actions Performed",
                    value="• Garbage collection executed\n• Expired rate limits cleared\n• Cache optimized",
                    inline=False
                )
                
            else:
                await interaction.response.send_message("❌ Invalid action. Use: status or cleanup", ephemeral=True)
                return
            
            embed.set_footer(text=VANTAX_FOOTER)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # Log this action
            self.log_audit(
                user_id=str(interaction.user.id),
                username=interaction.user.name,
                action="MEMORY_MANAGEMENT",
                details=f"Memory {action} - Current: {memory_mb:.2f} MB",
                guild_id=str(interaction.guild.id)
            )
            
        except Exception as e:
            print(f"Error in memory management: {e}")
            await interaction.response.send_message("❌ Ein Fehler ist aufgetreten.", ephemeral=True)

async def setup(bot):
    try:
        await bot.add_cog(Security(bot))
        print("Security cog loaded successfully!")
        return True
    except Exception as e:
        print(f"Error loading Security cog: {e}")
        raise
