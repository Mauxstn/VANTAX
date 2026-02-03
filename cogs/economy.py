import discord
import random
import asyncio
import json
import os
from datetime import datetime, timedelta
from discord.ext import commands

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_file = "economy_data.json"
        self.shop_file = "shop_data.json"
        self.data = self.load_data()
        self.shop = self.load_shop()
        
    def load_data(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_data(self):
        with open(self.data_file, 'w') as f:
            json.dump(self.data, f, indent=4)
    
    def load_shop(self):
        default_shop = {
            "items": {
                "🍕 Pizza": {"price": 50, "emoji": "🍕", "description": "Leckere Pizza"},
                "🎮 Gaming PC": {"price": 5000, "emoji": "🎮", "description": "High-End Gaming PC"},
                "🏆 Trophäe": {"price": 1000, "emoji": "🏆", "description": "Seltene Trophäe"},
                "💎 Diamant": {"price": 10000, "emoji": "💎", "description": "Edler Diamant"},
                "🚗 Auto": {"price": 50000, "emoji": "🚗", "description": "Sportwagen"},
                "🏡 Haus": {"price": 100000, "emoji": "🏡", "description": "Luxus Villa"},
                "📱 Smartphone": {"price": 800, "emoji": "📱", "description": "Neuestes Smartphone"},
                "⌚ Uhr": {"price": 2000, "emoji": "⌚", "description": "Luxus Armbanduhr"},
                "🎸 Gitarre": {"price": 1500, "emoji": "🎸", "description": "E-Gitarre"},
                "📚 Bücher": {"price": 100, "emoji": "📚", "description": "Büchersammlung"}
            }
        }
        
        if os.path.exists(self.shop_file):
            with open(self.shop_file, 'r') as f:
                return json.load(f)
        return default_shop
    
    def get_user_data(self, user_id):
        if str(user_id) not in self.data:
            self.data[str(user_id)] = {
                "balance": 1000,
                "bank": 0,
                "daily_streak": 0,
                "last_daily": None,
                "inventory": [],
                "job": None,
                "last_work": None,
                "total_earned": 0,
                "total_spent": 0
            }
        return self.data[str(user_id)]

    @commands.command(name="balance")
    async def balance(self, ctx, user: discord.Member = None):
        """Multi-Währung Kontostände"""
        target = user or ctx.author
        data = self.get_user_data(target.id)
        
        embed = discord.Embed(
            title=f"💰 {target.display_name}'s Kontostand",
            color=discord.Color.gold()
        )
        embed.add_field(name="💵 Bar", value=f"${data['balance']:,}")
        embed.add_field(name="🏦 Bank", value=f"${data['bank']:,}")
        embed.add_field(name="💎 Gesamtvermögen", value=f"${data['balance'] + data['bank']:,}")
        embed.add_field(name="📈 Gesamtverdient", value=f"${data['total_earned']:,}")
        embed.add_field(name="📊 Ausgegeben", value=f"${data['total_spent']:,}")
        embed.set_thumbnail(url=target.avatar.url if target.avatar else None)
        await ctx.send(embed=embed)

    @commands.command(name="daily")
    async def daily(self, ctx):
        """Streak Boni & Belohnungen"""
        data = self.get_user_data(ctx.author.id)
        now = datetime.now()
        
        if data['last_daily']:
            last_daily = datetime.fromisoformat(data['last_daily'])
            if now.date() == last_daily.date():
                await ctx.send("Du hast heute schon deine tägliche Belohnung geholt!")
                return
        
        # Calculate streak
        if data['last_daily']:
            last_daily = datetime.fromisoformat(data['last_daily'])
            if (now - last_daily).days == 1:
                data['daily_streak'] += 1
            elif (now - last_daily).days > 1:
                data['daily_streak'] = 0
        else:
            data['daily_streak'] = 1
        
        # Calculate reward
        base_reward = 100
        streak_bonus = data['daily_streak'] * 50
        total_reward = base_reward + streak_bonus
        
        data['balance'] += total_reward
        data['last_daily'] = now.isoformat()
        data['total_earned'] += total_reward
        
        self.save_data()
        
        embed = discord.Embed(
            title="🎁 Tägliche Belohnung",
            description=f"Du hast **${total_reward}** erhalten!",
            color=discord.Color.green()
        )
        embed.add_field(name="📅 Basisbelohnung", value=f"${base_reward}")
        embed.add_field(name="🔥 Streak Bonus", value=f"${streak_bonus}")
        embed.add_field(name="⚡ Aktuelle Streak", value=f"{data['daily_streak']} Tage")
        embed.set_footer(text="Komm morgen wieder für mehr Boni!")
        await ctx.send(embed=embed)

    @commands.command(name="work")
    async def work(self, ctx):
        """50+ verschiedene Jobs"""
        data = self.get_user_data(ctx.author.id)
        now = datetime.now()
        
        if data['last_work']:
            last_work = datetime.fromisoformat(data['last_work'])
            if (now - last_work).seconds < 300:  # 5 minutes cooldown
                remaining = 300 - (now - last_work).seconds
                await ctx.send(f"Du musst noch {remaining // 60} Minuten {remaining % 60} Sekunden warten!")
                return
        
        jobs = [
            {"name": "Programmierer", "min": 50, "max": 200, "emoji": "💻"},
            {"name": "Koch", "min": 30, "max": 150, "emoji": "👨‍🍳"},
            {"name": "Designer", "min": 40, "max": 180, "emoji": "🎨"},
            {"name": "Lehrer", "min": 35, "max": 120, "emoji": "👨‍🏫"},
            {"name": "Arzt", "min": 100, "max": 300, "emoji": "👨‍⚕️"},
            {"name": "Mechaniker", "min": 45, "max": 160, "emoji": "🔧"},
            {"name": "Künstler", "min": 25, "max": 140, "emoji": "🎭"},
            {"name": "Musiker", "min": 30, "max": 170, "emoji": "🎵"},
            {"name": "Sportler", "min": 40, "max": 150, "emoji": "⚽"},
            {"name": "Youtuber", "min": 20, "max": 500, "emoji": "📹"},
            {"name": "Blogger", "min": 15, "max": 100, "emoji": "✍️"},
            {"name": "Fotograf", "min": 35, "max": 180, "emoji": "📷"},
            {"name": "Architekt", "min": 80, "max": 250, "emoji": "🏗️"},
            {"name": "Pilot", "min": 150, "max": 400, "emoji": "✈️"},
            {"name": "Kellner", "min": 20, "max": 80, "emoji": "🍽️"}
        ]
        
        job = random.choice(jobs)
        earnings = random.randint(job['min'], job['max'])
        
        data['balance'] += earnings
        data['last_work'] = now.isoformat()
        data['total_earned'] += earnings
        
        self.save_data()
        
        embed = discord.Embed(
            title=f"{job['emoji']} Arbeit als {job['name']}",
            description=f"Du hast **${earnings}** verdient!",
            color=discord.Color.green()
        )
        embed.add_field(name="💰 Verdienst", value=f"${earnings}")
        embed.add_field(name="📊 Bereich", value=f"${job['min']} - ${job['max']}")
        embed.set_footer(text="Nächste Arbeit in 5 Minuten möglich")
        await ctx.send(embed=embed)

    @commands.command(name="gamble")
    async def gamble(self, ctx, amount: int, game: str = "dice"):
        """Casino Spiele"""
        data = self.get_user_data(ctx.author.id)
        
        if amount <= 0:
            await ctx.send("Betrag muss positiv sein!")
            return
            
        if data['balance'] < amount:
            await ctx.send("Du hast nicht genug Geld!")
            return
        
        if game.lower() == "dice":
            # Dice game
            bot_roll = random.randint(1, 6)
            user_roll = random.randint(1, 6)
            
            if user_roll > bot_roll:
                winnings = amount * 2
                data['balance'] += winnings
                result = "Du gewinnst!"
                color = discord.Color.green()
            elif user_roll < bot_roll:
                data['balance'] -= amount
                winnings = 0
                result = "Du verlierst!"
                color = discord.Color.red()
            else:
                winnings = amount
                result = "Unentschieden!"
                color = discord.Color.yellow()
            
            embed = discord.Embed(
                title="🎲 Würfelspiel",
                description=f"Dein Wurf: {user_roll}\nBot Wurf: {bot_roll}\n\n**{result}**",
                color=color
            )
            embed.add_field(name="💰 Einsatz", value=f"${amount}")
            embed.add_field(name="💎 Gewinn", value=f"${winnings}")
            
        elif game.lower() == "coin":
            # Coin flip
            result = random.choice(["kopf", "zahl"])
            embed = discord.Embed(
                title="🪙 Münzwurf",
                description=f"Das Ergebnis ist: **{result}**!",
                color=discord.Color.gold()
            )
            # Simple 50/50 game
            if random.choice([True, False]):
                winnings = amount * 2
                data['balance'] += winnings
                embed.add_field(name="💰 Gewinn", value=f"${winnings}")
                embed.set_footer(text="🎉 Du gewinnst!")
            else:
                data['balance'] -= amount
                embed.add_field(name="💰 Verlust", value=f"${amount}")
                embed.set_footer(text="😢 Du verlierst!")
        
        elif game.lower() == "slots":
            # Slot machine
            symbols = ["🍒", "🍋", "🍊", "🍇", "💎", "7️⃣"]
            reels = [random.choice(symbols) for _ in range(3)]
            
            embed = discord.Embed(
                title="🎰 Slot Machine",
                description=f"{' | '.join(reels)}",
                color=discord.Color.purple()
            )
            
            if reels[0] == reels[1] == reels[2]:
                # Jackpot!
                multiplier = 10 if reels[0] == "7️⃣" else 5
                winnings = amount * multiplier
                data['balance'] += winnings
                embed.add_field(name="💰 JACKPOT!", value=f"${winnings}")
                embed.set_footer(text="🎉🎉🎉")
            elif reels[0] == reels[1] or reels[1] == reels[2]:
                # Small win
                winnings = amount * 2
                data['balance'] += winnings
                embed.add_field(name="💰 Gewinn", value=f"${winnings}")
                embed.set_footer(text="🎉 Kleiner Gewinn!")
            else:
                data['balance'] -= amount
                embed.add_field(name="💰 Verlust", value=f"${amount}")
                embed.set_footer(text="Versuch es erneut!")
        
        data['total_spent'] += amount
        self.save_data()
        await ctx.send(embed=embed)

    @commands.command(name="shop")
    async def shop(self, ctx):
        """100+ Shop Items"""
        embed = discord.Embed(
            title="🛍️ Shop",
            description="Hier kannst du Items kaufen!",
            color=discord.Color.blue()
        )
        
        for item_name, item_data in self.shop["items"].items():
            embed.add_field(
                name=f"{item_data['emoji']} {item_name}",
                value=f"${item_data['price']} - {item_data['description']}",
                inline=False
            )
        
        embed.set_footer(text="Verwende /buy <item> zum Kaufen")
        await ctx.send(embed=embed)

    @commands.command(name="buy")
    async def buy(self, ctx, *, item_name: str):
        """Items kaufen"""
        data = self.get_user_data(ctx.author.id)
        
        # Find item
        item = None
        for name, item_data in self.shop["items"].items():
            if item_name.lower() in name.lower() or name.lower() in item_name.lower():
                item = (name, item_data)
                break
        
        if not item:
            await ctx.send("Item nicht gefunden!")
            return
        
        name, item_data = item
        
        if data['balance'] < item_data['price']:
            await ctx.send("Du hast nicht genug Geld!")
            return
        
        data['balance'] -= item_data['price']
        data['inventory'].append(name)
        data['total_spent'] += item_data['price']
        
        self.save_data()
        
        embed = discord.Embed(
            title="🛍️ Gekauft!",
            description=f"Du hast **{name}** für **${item_data['price']}** gekauft!",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=item_data.get('image', None))
        await ctx.send(embed=embed)

    @commands.command(name="inventory")
    async def inventory(self, ctx, user: discord.Member = None):
        """Visual Inventory System"""
        target = user or ctx.author
        data = self.get_user_data(target.id)
        
        embed = discord.Embed(
            title=f"🎒 {target.display_name}'s Inventar",
            color=discord.Color.orange()
        )
        
        if not data['inventory']:
            embed.description = "Dein Inventar ist leer!"
        else:
            # Count items
            item_counts = {}
            for item in data['inventory']:
                item_counts[item] = item_counts.get(item, 0) + 1
            
            for item, count in item_counts.items():
                if item in self.shop["items"]:
                    item_data = self.shop["items"][item]
                    embed.add_field(
                        name=f"{item_data['emoji']} {item}",
                        value=f"Anzahl: {count}\nWert: ${item_data['price'] * count}",
                        inline=True
                    )
        
        embed.add_field(name="💰 Kontostand", value=f"${data['balance']:,}")
        embed.set_thumbnail(url=target.avatar.url if target.avatar else None)
        await ctx.send(embed=embed)

    @commands.command(name="bank")
    async def bank(self, ctx, action: str, amount: int = None):
        """Bank System"""
        data = self.get_user_data(ctx.author.id)
        
        if action.lower() == "deposit":
            if amount is None:
                await ctx.send("Bitte gib einen Betrag an!")
                return
            if amount <= 0:
                await ctx.send("Betrag muss positiv sein!")
                return
            if data['balance'] < amount:
                await ctx.send("Du hast nicht genug Geld!")
                return
            
            data['balance'] -= amount
            data['bank'] += amount
            
            embed = discord.Embed(
                title="🏦 Einzahlung",
                description=f"Du hast **${amount}** eingezahlt!",
                color=discord.Color.green()
            )
            
        elif action.lower() == "withdraw":
            if amount is None:
                await ctx.send("Bitte gib einen Betrag an!")
                return
            if amount <= 0:
                await ctx.send("Betrag muss positiv sein!")
                return
            if data['bank'] < amount:
                await ctx.send("Du hast nicht genug Geld auf der Bank!")
                return
            
            data['bank'] -= amount
            data['balance'] += amount
            
            embed = discord.Embed(
                title="🏦 Auszahlung",
                description=f"Du hast **${amount}** ausgezahlt!",
                color=discord.Color.blue()
            )
            
        elif action.lower() == "balance":
            embed = discord.Embed(
                title="🏦 Bank Kontostand",
                color=discord.Color.gold()
            )
            embed.add_field(name="💵 Bar", value=f"${data['balance']:,}")
            embed.add_field(name="🏦 Bank", value=f"${data['bank']:,}")
            embed.add_field(name="💎 Gesamt", value=f"${data['balance'] + data['bank']:,}")
            return await ctx.send(embed)
            
        else:
            await ctx.send("Verwende: /bank <deposit|withdraw|balance> [betrag]")
            return
        
        self.save_data()
        embed.add_field(name="📊 Neuer Kontostand", value=f"Bar: ${data['balance']:,} | Bank: ${data['bank']:,}")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Economy(bot))
