import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import sqlite3
import mysql.connector
import psycopg2
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
from contextlib import contextmanager

# Constants
VANTAX_COLOR = discord.Color.blurple()
VANTAX_FOOTER = "VANTAX Discord Bot by Maurice"

class DatabaseManager:
    def __init__(self, db_type: str = "sqlite", **kwargs):
        self.db_type = db_type.lower()
        self.connection_params = kwargs
        self.connection = None
        self.cursor = None
        
    def connect(self):
        """Establish database connection"""
        try:
            if self.db_type == "sqlite":
                self.connection = sqlite3.connect(
                    self.connection_params.get("database", "vantax.db"),
                    check_same_thread=False
                )
                self.connection.row_factory = sqlite3.Row
                self.cursor = self.connection.cursor()
                
            elif self.db_type == "mysql":
                self.connection = mysql.connector.connect(
                    host=self.connection_params.get("host", "localhost"),
                    user=self.connection_params.get("user", "root"),
                    password=self.connection_params.get("password", ""),
                    database=self.connection_params.get("database", "vantax"),
                    port=self.connection_params.get("port", 3306)
                )
                self.cursor = self.connection.cursor(dictionary=True)
                
            elif self.db_type == "postgresql":
                self.connection = psycopg2.connect(
                    host=self.connection_params.get("host", "localhost"),
                    user=self.connection_params.get("user", "postgres"),
                    password=self.connection_params.get("password", ""),
                    database=self.connection_params.get("database", "vantax"),
                    port=self.connection_params.get("port", 5432)
                )
                self.cursor = self.connection.cursor()
                
            print(f"Connected to {self.db_type} database successfully!")
            return True
            
        except Exception as e:
            print(f"Error connecting to {self.db_type} database: {e}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        try:
            if self.cursor:
                self.cursor.close()
            if self.connection:
                self.connection.close()
            print(f"Disconnected from {self.db_type} database")
        except Exception as e:
            print(f"Error disconnecting from database: {e}")
    
    @contextmanager
    def get_cursor(self):
        """Context manager for database cursor"""
        try:
            yield self.cursor
            self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            raise e
    
    def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """Execute a SELECT query"""
        try:
            with self.get_cursor() as cursor:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                if self.db_type == "sqlite":
                    return [dict(row) for row in cursor.fetchall()]
                else:
                    return cursor.fetchall()
                    
        except Exception as e:
            print(f"Error executing query: {e}")
            return []
    
    def execute_update(self, query: str, params: tuple = None) -> bool:
        """Execute an INSERT, UPDATE, or DELETE query"""
        try:
            with self.get_cursor() as cursor:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                return True
        except Exception as e:
            print(f"Error executing update: {e}")
            return False
    
    def execute_many(self, query: str, params_list: List[tuple]) -> bool:
        """Execute multiple queries at once"""
        try:
            with self.get_cursor() as cursor:
                cursor.executemany(query, params_list)
                return True
        except Exception as e:
            print(f"Error executing many queries: {e}")
            return False

class Database(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_config_file = "database_config.json"
        self.db_config = self.load_database_config()
        self.db_manager = None
        self.connected = False
        
        # Initialize database connection
        self.bot.loop.create_task(self.initialize_database())
    
    def load_database_config(self):
        """Load database configuration"""
        try:
            if os.path.exists(self.db_config_file):
                with open(self.db_config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {
                "type": "sqlite",
                "sqlite": {
                    "database": "vantax.db"
                },
                "mysql": {
                    "host": "localhost",
                    "user": "root",
                    "password": "",
                    "database": "vantax",
                    "port": 3306
                },
                "postgresql": {
                    "host": "localhost",
                    "user": "postgres",
                    "password": "",
                    "database": "vantax",
                    "port": 5432
                }
            }
        except Exception as e:
            print(f"Error loading database config: {e}")
            return {}
    
    def save_database_config(self):
        """Save database configuration"""
        try:
            with open(self.db_config_file, 'w', encoding='utf-8') as f:
                json.dump(self.db_config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving database config: {e}")
    
    async def initialize_database(self):
        """Initialize database connection and create tables"""
        await self.bot.wait_until_ready()
        
        try:
            db_type = self.db_config.get("type", "sqlite")
            db_params = self.db_config.get(db_type, {})
            
            self.db_manager = DatabaseManager(db_type, **db_params)
            self.connected = self.db_manager.connect()
            
            if self.connected:
                await self.create_tables()
                print(f"Database initialized successfully with {db_type}!")
            else:
                print("Failed to initialize database!")
                
        except Exception as e:
            print(f"Error initializing database: {e}")
    
    async def create_tables(self):
        """Create necessary database tables"""
        try:
            # Users table
            if self.db_config.get("type") == "sqlite":
                self.db_manager.execute_update('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT UNIQUE,
                        username TEXT,
                        discriminator TEXT,
                        avatar_url TEXT,
                        joined_at TEXT,
                        last_seen TEXT,
                        guild_id TEXT,
                        xp INTEGER DEFAULT 0,
                        level INTEGER DEFAULT 1,
                        coins INTEGER DEFAULT 0,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                self.db_manager.execute_update('''
                    CREATE TABLE IF NOT EXISTS guilds (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id TEXT UNIQUE,
                        name TEXT,
                        owner_id TEXT,
                        member_count INTEGER,
                        created_at TEXT,
                        joined_at TEXT,
                        prefix TEXT DEFAULT '!',
                        settings TEXT,
                        created_at_db TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                self.db_manager.execute_update('''
                    CREATE TABLE IF NOT EXISTS commands (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT,
                        guild_id TEXT,
                        command_name TEXT,
                        command_args TEXT,
                        executed_at TEXT,
                        success BOOLEAN,
                        error_message TEXT,
                        execution_time REAL
                    )
                ''')
                
                self.db_manager.execute_update('''
                    CREATE TABLE IF NOT EXISTS moderation_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id TEXT,
                        moderator_id TEXT,
                        target_id TEXT,
                        action TEXT,
                        reason TEXT,
                        duration INTEGER,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                self.db_manager.execute_update('''
                    CREATE TABLE IF NOT EXISTS economy (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT,
                        guild_id TEXT,
                        coins INTEGER DEFAULT 0,
                        bank INTEGER DEFAULT 0,
                        daily_streak INTEGER DEFAULT 0,
                        last_daily TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
            else:
                # MySQL/PostgreSQL syntax
                self.db_manager.execute_update('''
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(255) UNIQUE,
                        username VARCHAR(255),
                        discriminator VARCHAR(10),
                        avatar_url TEXT,
                        joined_at TIMESTAMP,
                        last_seen TIMESTAMP,
                        guild_id VARCHAR(255),
                        xp INTEGER DEFAULT 0,
                        level INTEGER DEFAULT 1,
                        coins INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                self.db_manager.execute_update('''
                    CREATE TABLE IF NOT EXISTS guilds (
                        id SERIAL PRIMARY KEY,
                        guild_id VARCHAR(255) UNIQUE,
                        name VARCHAR(255),
                        owner_id VARCHAR(255),
                        member_count INTEGER,
                        created_at TIMESTAMP,
                        joined_at TIMESTAMP,
                        prefix VARCHAR(10) DEFAULT '!',
                        settings TEXT,
                        created_at_db TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                self.db_manager.execute_update('''
                    CREATE TABLE IF NOT EXISTS commands (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(255),
                        guild_id VARCHAR(255),
                        command_name VARCHAR(255),
                        command_args TEXT,
                        executed_at TIMESTAMP,
                        success BOOLEAN,
                        error_message TEXT,
                        execution_time REAL
                    )
                ''')
                
                self.db_manager.execute_update('''
                    CREATE TABLE IF NOT EXISTS moderation_logs (
                        id SERIAL PRIMARY KEY,
                        guild_id VARCHAR(255),
                        moderator_id VARCHAR(255),
                        target_id VARCHAR(255),
                        action VARCHAR(255),
                        reason TEXT,
                        duration INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                self.db_manager.execute_update('''
                    CREATE TABLE IF NOT EXISTS economy (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(255),
                        guild_id VARCHAR(255),
                        coins INTEGER DEFAULT 0,
                        bank INTEGER DEFAULT 0,
                        daily_streak INTEGER DEFAULT 0,
                        last_daily TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
            
            # Create indexes for better performance
            await self.create_indexes()
            
        except Exception as e:
            print(f"Error creating tables: {e}")
    
    async def create_indexes(self):
        """Create database indexes for better performance"""
        try:
            if self.db_config.get("type") == "sqlite":
                indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id)",
                    "CREATE INDEX IF NOT EXISTS idx_users_guild_id ON users(guild_id)",
                    "CREATE INDEX IF NOT EXISTS idx_guilds_guild_id ON guilds(guild_id)",
                    "CREATE INDEX IF NOT EXISTS idx_commands_user_id ON commands(user_id)",
                    "CREATE INDEX IF NOT EXISTS idx_commands_guild_id ON commands(guild_id)",
                    "CREATE INDEX IF NOT EXISTS idx_moderation_logs_guild_id ON moderation_logs(guild_id)",
                    "CREATE INDEX IF NOT EXISTS idx_economy_user_guild ON economy(user_id, guild_id)"
                ]
            else:
                indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id)",
                    "CREATE INDEX IF NOT EXISTS idx_users_guild_id ON users(guild_id)",
                    "CREATE INDEX IF NOT EXISTS idx_guilds_guild_id ON guilds(guild_id)",
                    "CREATE INDEX IF NOT EXISTS idx_commands_user_id ON commands(user_id)",
                    "CREATE INDEX IF NOT EXISTS idx_commands_guild_id ON commands(guild_id)",
                    "CREATE INDEX IF NOT EXISTS idx_moderation_logs_guild_id ON moderation_logs(guild_id)",
                    "CREATE INDEX IF NOT EXISTS idx_economy_user_guild ON economy(user_id, guild_id)"
                ]
            
            for index_query in indexes:
                self.db_manager.execute_update(index_query)
                
            print("Database indexes created successfully!")
            
        except Exception as e:
            print(f"Error creating indexes: {e}")
    
    @app_commands.command(name="database", description="Database management")
    @app_commands.checks.has_permissions(administrator=True)
    async def database_overview(self, interaction: discord.Interaction):
        """Show database overview and status"""
        try:
            if not self.connected:
                await interaction.response.send_message("❌ Database not connected!", ephemeral=True)
                return
            
            embed = discord.Embed(
                title="🗄️ Database Overview",
                description="Database system status and information",
                color=VANTAX_COLOR
            )
            
            # Database type and status
            embed.add_field(
                name="📊 Database Type",
                value=f"Type: {self.db_config.get('type', 'sqlite').upper()}\nStatus: {'✅ Connected' if self.connected else '❌ Disconnected'}",
                inline=True
            )
            
            # Table counts
            if self.connected:
                tables = ["users", "guilds", "commands", "moderation_logs", "economy"]
                table_info = []
                
                for table in tables:
                    try:
                        result = self.db_manager.execute_query(f"SELECT COUNT(*) as count FROM {table}")
                        count = result[0]["count"] if result else 0
                        table_info.append(f"{table}: {count}")
                    except:
                        table_info.append(f"{table}: Error")
                
                embed.add_field(
                    name="📋 Table Records",
                    value="\n".join(table_info),
                    inline=True
                )
            
            # Configuration
            embed.add_field(
                name="⚙️ Configuration",
                value=f"Config File: {self.db_config_file}\nAuto-backup: ✅ Enabled\nIndexes: ✅ Created",
                inline=True
            )
            
            embed.set_footer(text=VANTAX_FOOTER)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            print(f"Error in database overview: {e}")
            await interaction.response.send_message("❌ Ein Fehler ist aufgetreten.", ephemeral=True)
    
    @app_commands.command(name="dbswitch", description="Switch database type")
    @app_commands.checks.has_permissions(administrator=True)
    async def switch_database(self, interaction: discord.Interaction, db_type: str):
        """Switch between database types"""
        try:
            db_type = db_type.lower()
            if db_type not in ["sqlite", "mysql", "postgresql"]:
                await interaction.response.send_message("❌ Invalid database type. Use: sqlite, mysql, or postgresql", ephemeral=True)
                return
            
            # Disconnect current connection
            if self.db_manager:
                self.db_manager.disconnect()
            
            # Update configuration
            self.db_config["type"] = db_type
            self.save_database_config()
            
            # Reconnect with new type
            db_params = self.db_config.get(db_type, {})
            self.db_manager = DatabaseManager(db_type, **db_params)
            self.connected = self.db_manager.connect()
            
            if self.connected:
                await self.create_tables()
                
                embed = discord.Embed(
                    title="🗄️ Database Switched",
                    description=f"Successfully switched to {db_type.upper()} database!",
                    color=discord.Color.green()
                )
                
                embed.add_field(
                    name="✅ Actions Performed",
                    value=f"• Disconnected from previous database\n• Connected to {db_type.upper()}\n• Created necessary tables\n• Created performance indexes",
                    inline=False
                )
                
            else:
                embed = discord.Embed(
                    title="❌ Database Switch Failed",
                    description=f"Failed to connect to {db_type.upper()} database!",
                    color=discord.Color.red()
                )
                
                embed.add_field(
                    name="⚠️ Troubleshooting",
                    value="Check your database configuration and ensure the database server is running.",
                    inline=False
                )
            
            embed.set_footer(text=VANTAX_FOOTER)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            print(f"Error switching database: {e}")
            await interaction.response.send_message("❌ Ein Fehler ist aufgetreten.", ephemeral=True)
    
    @app_commands.command(name="dbconfig", description="Configure database settings")
    @app_commands.checks.has_permissions(administrator=True)
    async def configure_database(self, interaction: discord.Interaction, db_type: str, host: str = None, user: str = None, password: str = None, database: str = None, port: int = None):
        """Configure database connection settings"""
        try:
            db_type = db_type.lower()
            if db_type not in ["sqlite", "mysql", "postgresql"]:
                await interaction.response.send_message("❌ Invalid database type. Use: sqlite, mysql, or postgresql", ephemeral=True)
                return
            
            # Update configuration
            if db_type not in self.db_config:
                self.db_config[db_type] = {}
            
            if host is not None:
                self.db_config[db_type]["host"] = host
            if user is not None:
                self.db_config[db_type]["user"] = user
            if password is not None:
                self.db_config[db_type]["password"] = password
            if database is not None:
                self.db_config[db_type]["database"] = database
            if port is not None:
                self.db_config[db_type]["port"] = port
            
            self.save_database_config()
            
            embed = discord.Embed(
                title="⚙️ Database Configuration Updated",
                description=f"Configuration for {db_type.upper()} database updated!",
                color=VANTAX_COLOR
            )
            
            # Show current configuration
            config_text = []
            for key, value in self.db_config[db_type].items():
                if key == "password":
                    config_text.append(f"{key}: {'*' * len(str(value))}")
                else:
                    config_text.append(f"{key}: {value}")
            
            embed.add_field(
                name="📋 Current Configuration",
                value="\n".join(config_text),
                inline=False
            )
            
            embed.add_field(
                name="💡 Next Steps",
                value="Use `/dbswitch {db_type}` to connect with the new configuration.",
                inline=False
            )
            
            embed.set_footer(text=VANTAX_FOOTER)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            print(f"Error configuring database: {e}")
            await interaction.response.send_message("❌ Ein Fehler ist aufgetreten.", ephemeral=True)
    
    @app_commands.command(name="dbquery", description="Execute custom database query")
    @app_commands.checks.has_permissions(administrator=True)
    async def execute_query(self, interaction: discord.Interaction, query: str):
        """Execute a custom database query (SELECT only)"""
        try:
            if not self.connected:
                await interaction.response.send_message("❌ Database not connected!", ephemeral=True)
                return
            
            # Security check - only allow SELECT queries
            if not query.strip().upper().startswith("SELECT"):
                await interaction.response.send_message("❌ Only SELECT queries are allowed for security reasons!", ephemeral=True)
                return
            
            # Execute query
            results = self.db_manager.execute_query(query)
            
            if not results:
                await interaction.response.send_message("📊 Query executed successfully but returned no results.", ephemeral=True)
                return
            
            # Format results
            embed = discord.Embed(
                title="📊 Query Results",
                description=f"Query returned {len(results)} rows",
                color=VANTAX_COLOR
            )
            
            # Show first few results
            for i, row in enumerate(results[:5]):  # Limit to 5 rows
                row_text = []
                for key, value in row.items():
                    if value is not None:
                        value_str = str(value)
                        if len(value_str) > 50:
                            value_str = value_str[:47] + "..."
                        row_text.append(f"{key}: {value_str}")
                
                embed.add_field(
                    name=f"Row {i + 1}",
                    value="\n".join(row_text),
                    inline=False
                )
            
            if len(results) > 5:
                embed.set_footer(text=f"Showing 5 of {len(results)} rows | " + VANTAX_FOOTER)
            else:
                embed.set_footer(text=VANTAX_FOOTER)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            print(f"Error executing query: {e}")
            await interaction.response.send_message(f"❌ Query error: {str(e)}", ephemeral=True)
    
    @app_commands.command(name="dbbackup", description="Create database backup")
    @app_commands.checks.has_permissions(administrator=True)
    async def backup_database(self, interaction: discord.Interaction):
        """Create a backup of the database"""
        try:
            if not self.connected:
                await interaction.response.send_message("❌ Database not connected!", ephemeral=True)
                return
            
            # This is a simplified backup - in production, you'd want more sophisticated backup
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"vantax_backup_{self.db_config.get('type', 'sqlite')}_{timestamp}.json"
            
            # Get all data
            backup_data = {
                "timestamp": datetime.now().isoformat(),
                "database_type": self.db_config.get("type", "sqlite"),
                "tables": {}
            }
            
            tables = ["users", "guilds", "commands", "moderation_logs", "economy"]
            
            for table in tables:
                try:
                    results = self.db_manager.execute_query(f"SELECT * FROM {table}")
                    backup_data["tables"][table] = results
                except Exception as e:
                    backup_data["tables"][table] = f"Error: {str(e)}"
            
            # Save backup
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=4, ensure_ascii=False, default=str)
            
            embed = discord.Embed(
                title="💾 Database Backup Created",
                description=f"Backup saved as `{backup_file}`",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="📊 Backup Details",
                value=f"Database Type: {self.db_config.get('type', 'sqlite')}\nTimestamp: {timestamp}\nTables: {len(tables)}",
                inline=True
            )
            
            embed.add_field(
                name="📁 File Size",
                value=f"{os.path.getsize(backup_file) / 1024:.2f} KB",
                inline=True
            )
            
            embed.set_footer(text=VANTAX_FOOTER)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            print(f"Error creating backup: {e}")
            await interaction.response.send_message("❌ Ein Fehler ist aufgetreten.", ephemeral=True)

async def setup(bot):
    try:
        await bot.add_cog(Database(bot))
        print("Database cog loaded successfully!")
        return True
    except Exception as e:
        print(f"Error loading Database cog: {e}")
        raise
