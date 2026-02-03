import discord
import random
import aiohttp
import asyncio
from discord.ext import commands
import json
import datetime

class Gaming(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.quiz_active = False
        self.current_quiz = None

    @commands.command(name="meme")
    async def meme(self, ctx):
        """Zufällige Memes von Reddit"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://meme-api.com/gimme") as response:
                    data = await response.json()
                    
                    embed = discord.Embed(
                        title=data["title"],
                        url=data["postLink"],
                        color=discord.Color.random()
                    )
                    embed.set_image(url=data["url"])
                    embed.set_footer(text=f"👍 {data['ups']} | r/{data['subreddit']} | Requested by {ctx.author.name}")
                    await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"Fehler beim Laden des Memes: {e}")

    @commands.command(name="dice")
    async def dice(self, ctx, sides: int = 6):
        """Würfeln mit Animationen"""
        if sides < 2 or sides > 100:
            await ctx.send("Bitte wähle eine Zahl zwischen 2 und 100")
            return
            
        result = random.randint(1, sides)
        
        # Animation
        msg = await ctx.send("🎲 Würfel rollt...")
        await asyncio.sleep(1)
        await msg.edit(content="🎲🎲 Würfel rollt...")
        await asyncio.sleep(1)
        await msg.edit(content="🎲🎲🎲 Würfel rollt...")
        await asyncio.sleep(1)
        
        embed = discord.Embed(
            title="🎲 Würfelwurf",
            description=f"Du hast eine **{result}** gewürfelt!",
            color=discord.Color.gold()
        )
        embed.add_field(name="Würfel", value=f"🎲 d{sides}")
        embed.add_field(name="Glück", value="🍀" if result > sides//2 else "😅")
        await msg.edit(content="", embed=embed)

    @commands.command(name="8ball")
    async def eight_ball(self, ctx, *, question: str):
        """Magic 8 Ball"""
        responses = [
            "Ja, definitiv!", "Nein, niemals!", "Vielleicht", "Frage später nochmal",
            "Sehr wahrscheinlich", "Zweifelhaft", "Gewiss!", "Meine Quellen sagen nein",
            "Perspektive gut", "Nicht so gut", "Zähle darauf!", "Meine Antwort ist nein",
            "Absolut!", "Keine Chance!", "Sehr gut möglich", "Ich denke nicht"
        ]
        
        embed = discord.Embed(
            title="🔮 Magic 8 Ball",
            description=f"Frage: {question}\n\nAntwort: **{random.choice(responses)}**",
            color=discord.Color.purple()
        )
        embed.set_thumbnail(url="https://i.imgur.com/8ball.png")
        embed.set_footer(text="🔮 Schicksal wurde geweissagt")
        await ctx.send(embed=embed)

    @commands.command(name="coinflip")
    async def coinflip(self, ctx):
        """Münzwurf mit Animationen"""
        msg = await ctx.send("🪙 Münze wird geworfen...")
        
        # Animation
        for _ in range(3):
            await asyncio.sleep(0.5)
            await msg.edit(content="🪙🪙 Münze dreht sich...")
        
        result = random.choice(["Kopf", "Zahl"])
        coin_emoji = "👑" if result == "Kopf" else "🔢"
        
        embed = discord.Embed(
            title="🪙 Münzwurf",
            description=f"Das Ergebnis ist: **{result}**! {coin_emoji}",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url="https://i.imgur.com/coin.png")
        await msg.edit(content="", embed=embed)

    @commands.command(name="rps")
    async def rps(self, ctx, choice: str):
        """Schere Stein Papier"""
        choices = {"schere": "✂️", "stein": "🪨", "papier": "📄"}
        choice_lower = choice.lower()
        
        if choice_lower not in choices:
            embed = discord.Embed(
                title="✂️ Schere Stein Papier",
                description="Bitte wähle: schere, stein oder papier",
                color=discord.Color.red()
            )
            embed.add_field(name="Verfügbare Optionen", value="✂️ Schere\n🪨 Stein\n📄 Papier")
            return await ctx.send(embed=embed)
            
        bot_choice = random.choice(list(choices.keys()))
        
        # Game logic
        if choice_lower == bot_choice:
            result = "Unentschieden!"
            color = discord.Color.yellow()
        elif (choice_lower == "schere" and bot_choice == "papier") or \
             (choice_lower == "stein" and bot_choice == "schere") or \
             (choice_lower == "papier" and bot_choice == "stein"):
            result = "🎉 Du gewinnst!"
            color = discord.Color.green()
        else:
            result = "😢 Ich gewinne!"
            color = discord.Color.red()
            
        embed = discord.Embed(
            title="✂️ Schere Stein Papier",
            description=f"Du: {choices[choice_lower]} {choice_lower}\n"
                       f"Bot: {choices[bot_choice]} {bot_choice}\n\n"
                       f"**{result}**",
            color=color
        )
        await ctx.send(embed=embed)

    @commands.command(name="lottery")
    async def lottery(self, ctx, *, numbers: str = None):
        """Lotto System mit Jackpot"""
        if numbers is None:
            embed = discord.Embed(
                title="🎰 Lotto System",
                description="Verwende: `/lottery 1 5 12 23 34 45`",
                color=discord.Color.gold()
            )
            embed.add_field(name="Wie spielen", value="Gib 6 Zahlen zwischen 1 und 49 an")
            return await ctx.send(embed=embed)
            
        try:
            nums = [int(n.strip()) for n in numbers.split()]
            if len(nums) != 6 or any(n < 1 or n > 49 for n in nums):
                raise ValueError
        except:
            await ctx.send("Bitte gib genau 6 gültige Zahlen (1-49) ein")
            return
            
        winning_numbers = random.sample(range(1, 50), 6)
        matches = len(set(nums) & set(winning_numbers))
        
        prizes = {0: 0, 1: 0, 2: 5, 3: 25, 4: 100, 5: 1000, 6: 1000000}
        prize = prizes[matches]
        
        embed = discord.Embed(
            title="🎰 Lotto Ergebnis",
            color=discord.Color.gold() if prize > 0 else discord.Color.red()
        )
        embed.add_field(name="Deine Zahlen", value=", ".join(map(str, nums)))
        embed.add_field(name="Gewinnzahlen", value=", ".join(map(str, winning_numbers)))
        embed.add_field(name="Treffer", value=f"{matches} von 6")
        embed.add_field(name="Gewinn", value=f"💰 ${prize:,}")
        
        if prize > 0:
            embed.set_footer(text="🎉 Glückwunsch!")
        else:
            embed.set_footer(text="🍀 Viel Glück beim nächsten Mal!")
            
        await ctx.send(embed=embed)

    @commands.command(name="quiz")
    async def quiz(self, ctx, category: str = "general"):
        """Multiplayer Quiz Spiele"""
        if self.quiz_active:
            await ctx.send("Ein Quiz läuft bereits!")
            return
            
        self.quiz_active = True
        
        questions = {
            "general": [
                {"question": "Was ist die Hauptstadt von Deutschland?", "answer": "Berlin"},
                {"question": "Wie viele Kontinente gibt es?", "answer": "7"},
                {"question": "Was ist das größte Tier der Welt?", "answer": "Blauwal"},
                {"question": "Wie viele Planeten hat unser Sonnensystem?", "answer": "8"},
                {"question": "Was ist die chemische Formel für Wasser?", "answer": "H2O"}
            ],
            "science": [
                {"question": "Was ist die Lichtgeschwindigkeit?", "answer": "299792458"},
                {"question": "Wie heißt das größte Knochen im menschlichen Körper?", "answer": "Oberschenkelknochen"},
                {"question": "Was ist die kleinste Einheit der Materie?", "answer": "Atom"}
            ]
        }
        
        if category not in questions:
            category = "general"
            
        self.current_quiz = random.choice(questions[category])
        
        embed = discord.Embed(
            title="🧠 Quiz Zeit!",
            description=self.current_quiz["question"],
            color=discord.Color.blue()
        )
        embed.set_footer(text="Du hast 30 Sekunden Zeit! Schreibe die Antwort in den Chat.")
        
        quiz_msg = await ctx.send(embed=embed)
        
        def check(m):
            return m.channel == ctx.channel and m.author == ctx.author
        
        try:
            response = await self.bot.wait_for('message', check=check, timeout=30.0)
            
            if response.content.lower().strip() == self.current_quiz["answer"].lower():
                await ctx.send(f"🎉 Richtig! Die Antwort war: {self.current_quiz['answer']}")
            else:
                await ctx.send(f"❌ Falsch! Die richtige Antwort war: {self.current_quiz['answer']}")
                
        except asyncio.TimeoutError:
            await ctx.send(f"⏰ Zeit abgelaufen! Die richtige Antwort war: {self.current_quiz['answer']}")
        finally:
            self.quiz_active = False
            self.current_quiz = None

async def setup(bot):
    await bot.add_cog(Gaming(bot))
