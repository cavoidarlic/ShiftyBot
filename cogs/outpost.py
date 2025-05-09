import json
import os
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View
import datetime
from typing import Dict, List, Tuple
import asyncio

class OutpostView(View):
    def __init__(self, cog, user_id: int):
        super().__init__(timeout=300)
        self.cog = cog
        self.user_id = user_id
        
        self.add_item(Button(label="Claim", style=discord.ButtonStyle.green, custom_id="claim"))
        self.add_item(Button(label="Wipe Out", style=discord.ButtonStyle.blurple, custom_id="wipe_out"))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This outpost belongs to another commander.", ephemeral=True)
            return False
            
        if interaction.data["custom_id"] == "claim":
            await self.cog.claim_rewards(interaction)
        else:
            await self.cog.show_wipe_out(interaction)
        return True

    async def on_timeout(self) -> None:
        try:
            await self.message.delete()
        except:
            pass

class WipeOutView(View):
    def __init__(self, cog, user_id: int):
        super().__init__(timeout=300)
        self.cog = cog
        self.user_id = user_id
        
        self.add_item(Button(label="Wipe Out!", style=discord.ButtonStyle.green, custom_id="confirm_wipe"))
        self.add_item(Button(label="Cancel", style=discord.ButtonStyle.red, custom_id="cancel_wipe"))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This outpost belongs to another commander.", ephemeral=True)
            return False
            
        if interaction.data["custom_id"] == "confirm_wipe":
            await self.cog.perform_wipe_out(interaction)
        else:
            await interaction.message.delete()
        return True

    async def on_timeout(self) -> None:
        try:
            await self.message.delete()
        except:
            pass

class Outpost(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.outpost_file = 'data/outpost.json'
        self.rates_file = 'outpost_cleaned.txt'
        self.data = self.load_outpost_data()
        self.rates = self.load_rates_data()
        self.currency_cog = None

    def get_required_cogs(self):
        if not self.currency_cog:
            self.currency_cog = self.bot.get_cog('Currency')
        return self.currency_cog is not None

    def load_outpost_data(self):
        if os.path.exists(self.outpost_file):
            with open(self.outpost_file, 'r') as f:
                return json.load(f)
        return {"users": {}}

    def load_rates_data(self):
        rates = {}
        with open(self.rates_file, 'r') as f:
            headers = f.readline().strip().split('\t')
            for line in f:
                values = line.strip().split('\t')
                level = int(values[0])
                rates[level] = {
                    "credit_rate": float(values[1]),
                    "battle_data_rate": float(values[3]),
                    "core_dust_rate": float(values[5])
                }
        return rates

    def save_outpost_data(self):
        with open(self.outpost_file, 'w') as f:
            json.dump(self.data, f, indent=4)

    def get_user_outpost(self, user_id: str) -> Dict:
        if user_id not in self.data["users"]:
            self.data["users"][user_id] = {
                "level": 1,
                "progress": 0,
                "last_claim": 0,
                "last_wipe": 0,
                "wipe_attempts": 1,
                "last_progress": 0
            }
            self.save_outpost_data()
        return self.data["users"][user_id]

    def calculate_rewards(self, level: int, minutes: float) -> Tuple[int, int, float]:
        rates = self.rates[level]
        credits = int(rates["credit_rate"] * minutes)
        battle_data = int(rates["battle_data_rate"] * minutes)
        core_dust = int(rates["core_dust_rate"] * minutes)
        return credits, battle_data, core_dust

    def format_time_remaining(self, seconds: int) -> str:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        if hours >= 24:
            return "24:00"
        return f"{hours:02d}:{minutes:02d}"

    def reset_daily_wipe(self, user_data: Dict):
        now = datetime.datetime.now(datetime.timezone.utc)
        last_wipe = datetime.datetime.fromtimestamp(user_data["last_wipe"], datetime.timezone.utc)
        
        if now.date() > last_wipe.date():
            user_data["wipe_attempts"] = 1

    @app_commands.command(name="outpost", description="Check your Outpost status")
    async def outpost(self, interaction: discord.Interaction):
        if not self.get_required_cogs():
            await interaction.response.send_message("System error. Please try again.", ephemeral=True)
            return

        user_id = str(interaction.user.id)
        outpost = self.get_user_outpost(user_id)
        
        now = datetime.datetime.now(datetime.timezone.utc).timestamp()
        time_diff = min(now - outpost["last_claim"], 86400)
        minutes_passed = time_diff / 60
        
        credits, battle_data, core_dust = self.calculate_rewards(outpost["level"], minutes_passed)
        
        embed = discord.Embed(
            title="Outpost Defense",
            color=0x00b0f4
        )
        
        embed.add_field(
            name="Level",
            value=f"{outpost['level']}",
            inline=True
        )
        
        if outpost['level'] < 400:
            embed.add_field(
                name="Level Progression",
                value=f"{outpost['progress']}/3",
                inline=True
            )
            
            embed.add_field(name="\u200b", value="\u200b", inline=True)
        
        time_display = self.format_time_remaining(int(time_diff))
        embed.add_field(
            name="Storage Progress",
            value=time_display,
            inline=True if outpost['level'] == 400 else False
        )
        
        rates = self.rates[outpost["level"]]
        embed.add_field(
            name="Accumulation Rate",
            value=(
                f"<:credit:1346650964118999052> {rates['credit_rate']:.0f}/M\n"
                f"<:battledataset:1347015196736225310> {rates['battle_data_rate']:.0f}/M\n"
                f"<:coredust:1347015208513703937> {int(rates['core_dust_rate']*60)}/H"
            ),
            inline=False
        )
        
        if credits > 0 or battle_data > 0 or core_dust > 0:
            rewards_text = f"<:credit:1346650964118999052> {credits:,}\n" \
                         f"<:battledataset:1347015196736225310> {battle_data:,}"
            if core_dust >= 1:
                rewards_text += f"\n<:coredust:1347015208513703937> {core_dust:,}"
            
            embed.add_field(
                name="Rewards",
                value=rewards_text,
                inline=False
            )
        else:
            embed.add_field(
                name="Rewards",
                value="No rewards obtained",
                inline=False
            )

        view = OutpostView(self, interaction.user.id)
        response = await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()

    async def claim_rewards(self, interaction: discord.Interaction):
        """Process claiming rewards"""
        user_id = str(interaction.user.id)
        outpost = self.get_user_outpost(user_id)
        now = datetime.datetime.now(datetime.timezone.utc)
        
        time_diff = min(now.timestamp() - outpost["last_claim"], 86400)
        minutes_passed = time_diff / 60
        credits, battle_data, core_dust = self.calculate_rewards(outpost["level"], minutes_passed)
        
        if credits == 0 and battle_data == 0 and core_dust == 0:
            await interaction.response.send_message("No rewards to claim yet, commander.", ephemeral=True)
            return

        last_progress = datetime.datetime.fromtimestamp(outpost["last_progress"], datetime.timezone.utc)
        can_progress = now.date() > last_progress.date()
        
        currency = self.currency_cog.get_user_currency(interaction.user.id)
        currency["credits"] = int(currency["credits"] + credits)
        currency["battle_data"] = int(currency["battle_data"] + battle_data)
        currency["core_dust"] = int(currency["core_dust"] + core_dust)
        self.currency_cog.save_currency_data()
        
        outpost["last_claim"] = now.timestamp()
        if can_progress:
            outpost["progress"] += 1
            outpost["last_progress"] = now.timestamp()
            if outpost["progress"] >= 3:
                outpost["level"] = min(outpost["level"] + 1, 400)
                outpost["progress"] = 0
                
                await self.show_updated_outpost(interaction, f"🎉 Congratulations commander! Your outpost has leveled up to level {outpost['level']}!\n\nClaimed rewards:", credits, battle_data, core_dust)
            else:
                if outpost['level'] < 400:
                    await self.show_updated_outpost(interaction, f"Rewards claimed successfully! ({outpost['progress']}/3 to next level)", credits, battle_data, core_dust)
                else:
                    await self.show_updated_outpost(interaction, "Rewards claimed successfully!", credits, battle_data, core_dust)
        else:
            await self.show_updated_outpost(interaction, "Rewards claimed successfully!", credits, battle_data, core_dust)
        self.save_outpost_data()

    async def show_updated_outpost(self, interaction: discord.Interaction, message: str, credits: int, battle_data: int, core_dust: float):
        """Show updated outpost status after claiming rewards"""
        user_id = str(interaction.user.id)
        outpost = self.get_user_outpost(user_id)
        
        success_text = f"{message}\n" \
                     f"<:credit:1346650964118999052> {credits:,}\n" \
                     f"<:battledataset:1347015196736225310> {battle_data:,}"
        if core_dust >= 1:
            success_text += f"\n<:coredust:1347015208513703937> {core_dust:,}"
            
        await interaction.response.send_message(success_text, ephemeral=True)
        
        embed = discord.Embed(
            title="Outpost Defense",
            color=0x00b0f4
        )
        
        embed.add_field(
            name="Level",
            value=f"{outpost['level']}",
            inline=True
        )
        
        if outpost['level'] < 400:
            embed.add_field(
                name="Level Progression",
                value=f"{outpost['progress']}/3",
                inline=True
            )
            
            embed.add_field(name="\u200b", value="\u200b", inline=True)
        
        embed.add_field(
            name="Storage Progress",
            value="00:00",
            inline=True if outpost['level'] == 400 else False
        )
        
        rates = self.rates[outpost["level"]]
        embed.add_field(
            name="Accumulation Rate",
            value=(
                f"<:credit:1346650964118999052> {rates['credit_rate']:.0f}/M\n"
                f"<:battledataset:1347015196736225310> {rates['battle_data_rate']:.0f}/M\n"
                f"<:coredust:1347015208513703937> {int(rates['core_dust_rate']*60)}/H"
            ),
            inline=False
        )
        
        embed.add_field(
            name="Rewards",
            value="No rewards obtained",
            inline=False
        )

        view = OutpostView(self, interaction.user.id)
        await interaction.message.edit(embed=embed, view=view)

    async def show_wipe_out(self, interaction: discord.Interaction):
        """Show wipe out confirmation with rewards preview"""
        user_id = str(interaction.user.id)
        outpost = self.get_user_outpost(user_id)
        
        self.reset_daily_wipe(outpost)
        
        if outpost["wipe_attempts"] > 11:
            await interaction.response.send_message(
                "You have reached the daily wipe out limit (11 times), commander. Please try again tomorrow!",
                ephemeral=True
            )
            return
            
        credits, battle_data, core_dust = self.calculate_rewards(outpost["level"], 120)
        
        now = datetime.datetime.now(datetime.timezone.utc)
        next_reset = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        time_until_reset = next_reset - now
        hours, remainder = divmod(time_until_reset.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        embed = discord.Embed(
            title="Wipe Out",
            description="Quickly wipe out all enemies around the Outpost to obtain rewards equivalent to defending the base for 120 mins. (First attempt is free every day)",
            color=0x00b0f4
        )
        
        embed.add_field(
            name="Refresh in",
            value=f"{hours:02d}:{minutes:02d}:{seconds:02d}",
            inline=False
        )
        
        embed.add_field(
            name="Rewards Preview",
            value=(
                f"<:credit:1346650964118999052> {credits:,}\n"
                f"<:battledataset:1347015196736225310> {battle_data:,}\n"
                f"<:coredust:1347015208513703937> {core_dust:,}"
            ),
            inline=False
        )

        embed.add_field(
            name="Attempts",
            value=f"Daily: {outpost['wipe_attempts'] - 1}/11",
            inline=False
        )
        
        if outpost["wipe_attempts"] > 1:
            embed.add_field(
                name="Cost",
                value="<:gem:1346651000282550312> 50",
                inline=False
            )
        else:
            embed.add_field(
                name="Cost",
                value="Free!",
                inline=False
            )

        view = WipeOutView(self, interaction.user.id)
        await interaction.response.edit_message(embed=embed, view=view)
        view.message = interaction.message

    async def perform_wipe_out(self, interaction: discord.Interaction):
        """Process wipe out action"""
        user_id = str(interaction.user.id)
        outpost = self.get_user_outpost(user_id)
        
        if outpost["wipe_attempts"] > 11:
            await interaction.response.send_message(
                "You have reached the daily wipe out limit (11 times), commander. Please try again tomorrow!",
                ephemeral=True
            )
            return
            
        currency = self.currency_cog.get_user_currency(interaction.user.id)
        
        needs_gems = True
        if outpost["wipe_attempts"] == 1:
            needs_gems = False    
        
        if needs_gems and currency["gems"] < 50:
            await interaction.response.send_message(
                "Insufficient amounts of gem, commander...",
                ephemeral=True
            )
            return
            
        credits, battle_data, core_dust = self.calculate_rewards(outpost["level"], 120)
        
        if needs_gems:
            currency["gems"] -= 50
        currency["credits"] = int(currency["credits"] + credits)
        currency["battle_data"] = int(currency["battle_data"] + battle_data)
        currency["core_dust"] = int(currency["core_dust"] + core_dust)
        self.currency_cog.save_currency_data()
        
        outpost["wipe_attempts"] += 1
        outpost["last_wipe"] = datetime.datetime.now(datetime.timezone.utc).timestamp()
        self.save_outpost_data()
        
        await interaction.response.send_message(
            f"Wipe out successful! Rewards obtained:\n"
            f"<:credit:1346650964118999052> {credits:,}\n"
            f"<:battledataset:1347015196736225310> {battle_data:,}\n"
            f"<:coredust:1347015208513703937> {core_dust:,}",
            ephemeral=True
        )
        
        embed = interaction.message.embeds[0]
        for i, field in enumerate(embed.fields):
            if field.name == "Cost" and not needs_gems:
                embed.set_field_at(
                    i,
                    name="Cost",
                    value="<:gem:1346651000282550312> 50",
                    inline=False
                )
            elif field.name == "Attempts":
                embed.set_field_at(
                    i,
                    name="Attempts",
                    value=f"Daily: {outpost['wipe_attempts'] - 1}/11",
                    inline=False
                )
            elif field.name == "Refresh in":
                now = datetime.datetime.now(datetime.timezone.utc)
                next_reset = (now + datetime.timedelta(days=1)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                time_until_reset = next_reset - now
                hours, remainder = divmod(time_until_reset.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                embed.set_field_at(
                    i,
                    name="Refresh in",
                    value=f"{hours:02d}:{minutes:02d}:{seconds:02d}",
                    inline=False
                )
            
        view = WipeOutView(self, interaction.user.id)
        await interaction.message.edit(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Outpost(bot))
