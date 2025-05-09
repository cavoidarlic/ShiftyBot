import json
import os
import random
from discord.ext import commands
import discord
from discord import app_commands
from discord.ui import Button, View, Modal, TextInput
from utils.constants import MOLD_EMOJIS, MOLD_RATES, STARTING_MOLDS, MAX_LIMIT_BREAKS
from data.nikke_r import R_CHARACTERS
from data.nikke_sr import SR_CHARACTERS
from data.nikke_ssr import SSR_CHARACTERS
from utils.limited_nikkes import LIMITED_SR, LIMITED_SSR

class MoldModal(Modal):
    def __init__(self, operation, cog):
        super().__init__(title=f"{operation} Mold")
        self.operation = operation
        self.cog = cog
        
        self.user_id = TextInput(
            label="User ID (or 'me')",
            placeholder="Enter user ID or 'me'",
            required=True
        )
        
        self.mold_type = TextInput(
            label="Mold Type",
            placeholder="mid/high/elysion/missilis/tetra/pilgrim",
            required=True
        )
        
        self.amount = TextInput(
            label="Amount",
            placeholder="Enter amount",
            required=True
        )
        
        self.add_item(self.user_id)
        self.add_item(self.mold_type)
        self.add_item(self.amount)

    async def on_submit(self, interaction: discord.Interaction):
        await self.cog.process_mold_operation(interaction, self)

class MoldControlPanel(View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Add Mold", style=discord.ButtonStyle.green, custom_id="add_mold")
    async def add_mold(self, interaction: discord.Interaction, button: Button):
        modal = MoldModal("Add", self.cog)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Decrease Mold", style=discord.ButtonStyle.red, custom_id="decrease_mold")
    async def decrease_mold(self, interaction: discord.Interaction, button: Button):
        modal = MoldModal("Decrease", self.cog)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Set Mold", style=discord.ButtonStyle.blurple, custom_id="set_mold")
    async def set_mold(self, interaction: discord.Interaction, button: Button):
        modal = MoldModal("Set", self.cog)
        await interaction.response.send_modal(modal)

class Molds(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.molds_file = 'data/molds.json'
        self.data = self.load_molds_data()

    def load_molds_data(self):
        if os.path.exists(self.molds_file):
            with open(self.molds_file, 'r') as f:
                return json.load(f)
        return {"users": {}}

    def save_molds_data(self):
        with open(self.molds_file, 'w') as f:
            json.dump(self.data, f, indent=4)

    def get_user_molds(self, user_id: str):
        if user_id not in self.data["users"]:
            self.data["users"][user_id] = STARTING_MOLDS.copy()
            self.save_molds_data()
        return self.data["users"][user_id]

    def get_random_nikke(self, mold_type: str):
        rate = random.random()
        rates = MOLD_RATES[mold_type]
        
        manufacturer = mold_type if mold_type in ['elysion', 'missilis', 'tetra', 'pilgrim'] else None
        
        if manufacturer == 'pilgrim':
            if rate < 0.50:
                valid_ssrs = []
                for name, ssr in SSR_CHARACTERS.items():
                    if name not in LIMITED_SSR and ssr['manufacturer'].lower() == 'pilgrim':
                        valid_ssrs.append(ssr)
                return random.choice(valid_ssrs) if valid_ssrs else None
            else:
                return random.choice(list(R_CHARACTERS.values()))
                
        if rate < rates['SSR']:
            valid_ssrs = []
            for name, ssr in SSR_CHARACTERS.items():
                if mold_type in ['mid', 'high']:
                    if name in LIMITED_SSR or ssr['manufacturer'].lower() == 'pilgrim':
                        continue
                elif manufacturer:
                    if name in LIMITED_SSR or ssr['manufacturer'].lower() != manufacturer:
                        continue
                valid_ssrs.append(ssr)
            
            return random.choice(valid_ssrs) if valid_ssrs else None
            
        elif rate < rates['SSR'] + rates['SR']:
            valid_srs = []
            for name, sr in SR_CHARACTERS.items():
                if name in LIMITED_SR:
                    continue
                if manufacturer and sr['manufacturer'].lower() != manufacturer:
                    continue
                valid_srs.append(sr)
            
            if not valid_srs:
                return random.choice(list(R_CHARACTERS.values()))
            return random.choice(valid_srs)
        
        return random.choice(list(R_CHARACTERS.values()))

    @commands.command(name='setmold', hidden=True)
    async def setmold(self, ctx):
        if ctx.author.id != 312860306701418497:
            return

        embed = discord.Embed(
            title="Mold Control Panel",
            description="*Secure access granted. Welcome, Commander.*",
            color=0x00b0f4
        )
        embed.set_footer(text="Provided by Central Government")
        
        view = MoldControlPanel(self)
        await ctx.send(embed=embed, view=view)

    async def process_mold_operation(self, interaction: discord.Interaction, modal: MoldModal):
        if interaction.user.id != 312860306701418497:
            return
            
        try:
            user_id = modal.user_id.value
            mold_type = modal.mold_type.value.lower()
            amount = modal.amount.value

            if user_id.lower() == 'me':
                user_id = '312860306701418497'
                target_user = interaction.user
            else:
                try:
                    target_user = await self.bot.fetch_user(int(user_id))
                    if not target_user:
                        await interaction.response.send_message("Invalid user ID.", ephemeral=True)
                        return
                except ValueError:
                    await interaction.response.send_message("Invalid user ID format.", ephemeral=True)
                    return

            if mold_type != "all" and mold_type not in MOLD_EMOJIS:
                await interaction.response.send_message(
                    "*Adjusts glasses*\nCommander, please specify a valid mold type or 'all'.",
                    ephemeral=True
                )
                return

            try:
                amount = int(amount)
                if amount < 0:
                    await interaction.response.send_message(
                        "*Types on keyboard*\nNegative values detected. Operation cancelled.",
                        ephemeral=True
                    )
                    return
            except ValueError:
                await interaction.response.send_message("Invalid amount.", ephemeral=True)
                return

            user_molds = self.get_user_molds(user_id)
            changes = []

            if mold_type == "all":
                for mold_key in MOLD_EMOJIS.keys():
                    current_value = user_molds[mold_key]
                    if modal.operation == "Add":
                        new_value = current_value + amount
                    elif modal.operation == "Decrease":
                        new_value = max(0, current_value - amount)
                    else:
                        new_value = amount
                    user_molds[mold_key] = new_value
                    changes.append((mold_key, current_value, new_value))
            else:
                current_value = user_molds[mold_type]
                if modal.operation == "Add":
                    new_value = current_value + amount
                elif modal.operation == "Decrease":
                    new_value = max(0, current_value - amount)
                else:
                    new_value = amount
                user_molds[mold_type] = new_value
                changes.append((mold_type, current_value, new_value))

            self.save_molds_data()

            embed = discord.Embed(
                title="Mold Modification Report",
                description=f"*Accessing secure database...*\n\n**Target ID:** `{user_id}`\n**Target Name:** {target_user.name}\n**Operation:** {modal.operation}",
                color=0x00b0f4,
                timestamp=interaction.created_at
            )

            for mold_key, old_val, new_val in changes:
                embed.add_field(
                    name=f"Mold Type: {MOLD_EMOJIS[mold_key]}",
                    value=f"Previous Amount: {old_val}\nNew Amount: {new_val}",
                    inline=True
                )

            embed.set_footer(text="Shifty Logistics™")
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            print(f"Error in process_mold_operation: {str(e)}")
            await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)

    @app_commands.command(name="mold", description="Open NIKKE molds")
    @app_commands.choices(mold_type=[
        app_commands.Choice(name="Mid-Quality Mold", value="mid"),
        app_commands.Choice(name="High-Quality Mold", value="high"),
        app_commands.Choice(name="Elysion Mold", value="elysion"),
        app_commands.Choice(name="Missilis Mold", value="missilis"),
        app_commands.Choice(name="Tetra Mold", value="tetra"),
        app_commands.Choice(name="Pilgrim Mold", value="pilgrim")
    ])
    async def mold(self, interaction: discord.Interaction, mold_type: str, amount: int = 1):
        if amount > 10:
            await interaction.response.send_message(
                "Commander, you can only open up to 10 molds at a time.",
                ephemeral=True
            )
            return
            
        if amount < 1:
            await interaction.response.send_message(
                "Commander, please specify a valid amount (1-10).",
                ephemeral=True
            )
            return

        user_id = str(interaction.user.id)
        user_molds = self.get_user_molds(user_id)
        
        if user_molds[mold_type] < 50 * amount:
            await interaction.response.send_message(
                f"Insufficient mold pieces. You need {50 * amount} pieces but have {user_molds[mold_type]}.",
                ephemeral=True
            )
            return

        inventory_cog = self.bot.get_cog('Inventory')
        currency_cog = self.bot.get_cog('Currency')
        if not inventory_cog or not currency_cog:
            await interaction.response.send_message("System error. Please try again.", ephemeral=True)
            return

        user_molds[mold_type] -= 50 * amount
        self.save_molds_data()

        results = []
        for _ in range(amount):
            if nikke := self.get_random_nikke(mold_type):
                results.append(nikke)
                await inventory_cog.add_nikke_to_inventory(user_id, nikke['name'].lower(), nikke)

        embed = discord.Embed(
            title=f"Mold Opening Results ({amount} {'mold' if amount == 1 else 'molds'})",
            description="*Processing recruitment data...*",
            color=0x00b0f4
        )

        if not results:
            embed.description = "No NIKKEs were obtained. This might be due to rate restrictions."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if amount == 1:
            nikke = results[0]
            rarity_emoji = inventory_cog.EMOJI_MAPPING[nikke['rarity']]
            class_emoji = inventory_cog.EMOJI_MAPPING[nikke['class']]
            manu_emoji = inventory_cog.EMOJI_MAPPING[nikke['manufacturer']]
            weapon_emoji = inventory_cog.EMOJI_MAPPING[nikke['weapon']]
            element_emoji = inventory_cog.EMOJI_MAPPING[nikke['element']]
            burst_emoji = inventory_cog.EMOJI_MAPPING[nikke['burst']]
            
            embed.add_field(
                name=f"{nikke['name']} [{rarity_emoji}]",
                value=f"{manu_emoji} • {class_emoji} • {weapon_emoji}\n{element_emoji} • {burst_emoji}",
                inline=False
            )
            embed.set_image(url=nikke['image_url'])
        else:
            for nikke in results:
                rarity_emoji = inventory_cog.EMOJI_MAPPING[nikke['rarity']]
                class_emoji = inventory_cog.EMOJI_MAPPING[nikke['class']]
                manu_emoji = inventory_cog.EMOJI_MAPPING[nikke['manufacturer']]
                embed.add_field(
                    name=f"{nikke['name']} [{rarity_emoji}]",
                    value=f"{manu_emoji} • {class_emoji}",
                    inline=True
                )

        total_labels = 0
        for nikke in results:
            nikke_key = nikke['name'].lower()
            inventory = inventory_cog.get_user_inventory(user_id)
            if nikke_key in inventory:
                current_lb = inventory[nikke_key]["limit_break"]
                if nikke['rarity'] == 'SSR' and current_lb >= 10:
                    total_labels += 6000
                elif nikke['rarity'] == 'SR' and current_lb >= MAX_LIMIT_BREAKS['SR']:
                    total_labels += 200
                elif nikke['rarity'] == 'R' and current_lb >= MAX_LIMIT_BREAKS['R']:
                    total_labels += 150

        if total_labels > 0:
            user_currency = currency_cog.get_user_currency(user_id)
            user_currency['body_labels'] += total_labels
            currency_cog.save_currency_data()
            embed.set_footer(text=f"Acquired {total_labels:,} Body Labels")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    def get_molds_display(self, user_id: str) -> str:
        """Get formatted molds display for inventory"""
        molds = self.get_user_molds(user_id)
        display_lines = []
        for mold_type, emoji in MOLD_EMOJIS.items():
            amount = molds[mold_type]
            display_lines.append(f"{emoji} {amount}/50")
        return "\n".join(display_lines)

async def setup(bot):
    await bot.add_cog(Molds(bot))
