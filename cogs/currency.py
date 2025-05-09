import json
import os
from discord.ext import commands, tasks
import discord
from discord import app_commands
from discord.ui import Button, View, Modal, TextInput
import datetime
from utils.constants import MOLD_EMOJIS

class MoneyModal(Modal):
    def __init__(self, operation, cog):
        super().__init__(title=f"{operation} Money")
        self.operation = operation
        self.cog = cog
        
        self.user_id = TextInput(
            label="User ID (or 'me')",
            placeholder="Enter user ID or 'me'",
            required=True
        )
        
        self.currency_type = TextInput(
            label="Currency Type",
            placeholder="gem/credit/social/battle/dust",
            required=True
        )
        
        self.amount = TextInput(
            label="Amount",
            placeholder="Enter amount",
            required=True
        )
        
        self.add_item(self.user_id)
        self.add_item(self.currency_type)
        self.add_item(self.amount)

    async def on_submit(self, interaction: discord.Interaction):
        await self.cog.process_money_operation(interaction, self)

class VoucherModal(Modal):
    def __init__(self, operation, cog):
        super().__init__(title=f"{operation} Voucher")
        self.operation = operation
        self.cog = cog
        
        self.user_id = TextInput(
            label="User ID (or 'me')",
            placeholder="Enter user ID or 'me'",
            required=True
        )
        
        self.voucher_type = TextInput(
            label="Voucher Type",
            placeholder="normal/advanced",
            required=True
        )
        
        self.amount = TextInput(
            label="Amount",
            placeholder="Enter amount",
            required=True
        )
        
        self.add_item(self.user_id)
        self.add_item(self.voucher_type)
        self.add_item(self.amount)

    async def on_submit(self, interaction: discord.Interaction):
        await self.cog.process_voucher_operation(interaction, self)

class EconomyControlPanel(View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Add Money", style=discord.ButtonStyle.green, custom_id="add_money")
    async def add_money(self, interaction: discord.Interaction, button: Button):
        modal = MoneyModal("Add", self.cog)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Decrease Money", style=discord.ButtonStyle.red, custom_id="decrease_money")
    async def decrease_money(self, interaction: discord.Interaction, button: Button):
        modal = MoneyModal("Decrease", self.cog)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Set Money", style=discord.ButtonStyle.blurple, custom_id="set_money")
    async def set_money(self, interaction: discord.Interaction, button: Button):
        modal = MoneyModal("Set", self.cog)
        await interaction.response.send_modal(modal)

class VoucherControlPanel(View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Add Voucher", style=discord.ButtonStyle.green, custom_id="add_voucher")
    async def add_voucher(self, interaction: discord.Interaction, button: Button):
        modal = VoucherModal("Add", self.cog)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Decrease Voucher", style=discord.ButtonStyle.red, custom_id="decrease_voucher")
    async def decrease_voucher(self, interaction: discord.Interaction, button: Button):
        modal = VoucherModal("Decrease", self.cog)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Set Voucher", style=discord.ButtonStyle.blurple, custom_id="set_voucher")
    async def set_voucher(self, interaction: discord.Interaction, button: Button):
        modal = VoucherModal("Set", self.cog)
        await interaction.response.send_modal(modal)

class InventoryPageView(View):
    def __init__(self, cog, user_id: str, page: str = "materials"):
        super().__init__(timeout=300)
        self.cog = cog
        self.user_id = user_id
        self.page = page
        
        materials_button = Button(
            label="Materials", 
            style=discord.ButtonStyle.blurple if page != "materials" else discord.ButtonStyle.gray,
            custom_id="materials",
            disabled=page == "materials"
        )
        consume_button = Button(
            label="Consume", 
            style=discord.ButtonStyle.blurple if page != "consume" else discord.ButtonStyle.gray,
            custom_id="consume",
            disabled=page == "consume"
        )
        
        self.add_item(materials_button)
        self.add_item(consume_button)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This inventory belongs to another commander.", ephemeral=True)
            return False
            
        new_page = interaction.data["custom_id"]
        await self.cog.show_inventory_page(interaction, new_page, edit=True)
        return True

    async def on_timeout(self) -> None:
        try:
            await self.message.delete()
        except:
            pass

class BalanceView(View):
    def __init__(self):
        super().__init__(timeout=300)
        
    async def on_timeout(self) -> None:
        try:
            await self.message.delete()
        except:
            pass

class Currency(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.currency_file = 'data/currency.json'
        self.data = self.load_currency_data()
        self.social_point_task.start()

    def load_currency_data(self):
        if not os.path.exists(self.currency_file):
            return {"users": {}}
        with open(self.currency_file, 'r') as f:
            return json.load(f)

    def save_currency_data(self):
        with open(self.currency_file, 'w') as f:
            json.dump(self.data, f, indent=4)

    def get_user_currency(self, user_id):
        user_id = str(user_id)
        if user_id not in self.data["users"]:
            self.data["users"][user_id] = {
                "credits": 50000,
                "gems": 9000,
                "social_points": 100,
                "recruit_voucher": 20,
                "advanced_voucher": 20,
                "body_labels": 0,
                "silver_tickets": 0,
                "gold_tickets": 0,
                "battle_data": 0,
                "core_dust": 0
            }
            self.save_currency_data()
        
        currency = self.data["users"][user_id]
        for key, value in currency.items():
            if key not in ["last_claim", "last_wipe", "last_progress"]:
                try:
                    currency[key] = int(float(value))
                except (ValueError, TypeError):
                    currency[key] = 0
                    
        return currency

    @tasks.loop(hours=24)
    async def social_point_task(self):
        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7)))
        if now.hour >= 3:
            tomorrow = now + datetime.timedelta(days=1)
        else:
            tomorrow = now
        next_run = tomorrow.replace(hour=3, minute=0, second=0, microsecond=0)
        
        if now.hour != 3:
            await discord.utils.sleep_until(next_run)
        
        for user_id in self.data["users"]:
            if "social_points" not in self.data["users"][user_id]:
                self.data["users"][user_id]["social_points"] = 0
            self.data["users"][user_id]["social_points"] += 30
        self.save_currency_data()
        print(f"[{now}] Daily social points distributed!")

    @social_point_task.before_loop
    async def before_social_point_task(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="balance", description="Check your credit, gem, and social point balance")
    async def balance(self, interaction: discord.Interaction):
        user_currency = self.get_user_currency(interaction.user.id)
        embed = discord.Embed(
            title=f"{interaction.user.name}'s Balance",
            color=0x00b0f4
        )
        embed.add_field(
            name="Credits", 
            value=f"<:credit:1346650964118999052> {user_currency['credits']:,}",
            inline=True
        )
        embed.add_field(
            name="Gems", 
            value=f"<:gem:1346651000282550312> {user_currency['gems']:,}",
            inline=True
        )
        embed.add_field(
            name="Social Points", 
            value=f"<:socialpoint:1347015187198382274> {user_currency['social_points']:,}",
            inline=True
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        
        view = BalanceView()
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()

    async def show_inventory_page(self, interaction: discord.Interaction, page: str, edit: bool = False):
        user_currency = self.get_user_currency(interaction.user.id)
        molds_cog = self.bot.get_cog('Molds')

        embed = discord.Embed(
            title=f"{interaction.user.name}'s Inventory",
            color=0x00b0f4
        )

        if page == "materials":
            materials_lines = []
            materials_mapping = {
                'gems': ('<:gem:1346651000282550312>', 'Gems'),
                'credits': ('<:credit:1346650964118999052>', 'Credits'),
                'social_points': ('<:socialpoint:1347015187198382274>', 'Social Points'),
                'recruit_voucher': ('<:recruit:1346650987007311953>', 'Recruit Vouchers'),
                'advanced_voucher': ('<:recruit2:1346651073644855368>', 'Advanced Vouchers'),
                'body_labels': ('<:bodylabel:1347012359306215507>', 'Body Labels'),
                'silver_tickets': ('<:silverticket:1346714572186324994>', 'Silver Mileage Tickets'),
                'gold_tickets': ('<:goldenticket:1346714562342289408>', 'Gold Mileage Tickets'),
                'battle_data': ('<:battledataset:1347015196736225310>', 'Battle Data Set'),
                'core_dust': ('<:coredust:1347015208513703937>', 'Core Dust')
            }
            
            for key, (emoji, name) in materials_mapping.items():
                amount = int(user_currency.get(key, 0))
                if amount > 0:
                    materials_lines.append(f"{emoji} {amount:,} {name}")
            
            if materials_lines:
                embed.add_field(name="Materials", value="\n".join(materials_lines), inline=False)
            else:
                embed.add_field(name="Materials", value="No materials", inline=False)

        elif page == "consume":
            if molds_cog:
                mold_names = {
                    'mid': 'Mid-Quality Mold',
                    'high': 'High-Quality Mold',
                    'elysion': 'Elysion Mold',
                    'missilis': 'Missilis Mold',
                    'tetra': 'Tetra Mold',
                    'pilgrim': 'Pilgrim Mold'
                }
                
                user_molds = molds_cog.get_user_molds(str(interaction.user.id))
                mold_lines = []
                for mold_type, emoji in MOLD_EMOJIS.items():
                    amount = user_molds[mold_type]
                    if amount > 0:
                        mold_lines.append(f"{emoji} {amount}/50 | {mold_names[mold_type]}")
                
                if mold_lines:
                    embed.add_field(name="Consume", value="\n".join(mold_lines), inline=False)
                else:
                    embed.add_field(name="Consume", value="No consumable items", inline=False)

        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        view = InventoryPageView(self, str(interaction.user.id), page)
        
        if edit:
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            await interaction.response.send_message(embed=embed, view=view)
            view.message = await interaction.original_response()

    @app_commands.command(name="inventory", description="Check your inventory")
    async def inventory(self, interaction: discord.Interaction):
        """Check your inventory"""
        await self.show_inventory_page(interaction, "materials")

    @commands.command(name='setmoney', hidden=True)
    async def setmoney(self, ctx):
        if ctx.author.id != 312860306701418497:
            return

        embed = discord.Embed(
            title="Economy Control Panel",
            description="*Secure access granted. Welcome, Commander.*",
            color=0x00b0f4
        )
        embed.set_footer(text="Provided by Central Government")
        
        view = EconomyControlPanel(self)
        await ctx.send(embed=embed, view=view, ephemeral=True)

    @commands.command(name='setvoucher', hidden=True)
    async def setvoucher(self, ctx):
        if ctx.author.id != 312860306701418497:
            return

        embed = discord.Embed(
            title="Voucher Control Panel",
            description="*Secure access granted. Welcome, Commander.*",
            color=0x00b0f4
        )
        embed.set_footer(text="Provided by Central Government")
        
        view = VoucherControlPanel(self)
        await ctx.send(embed=embed, view=view, ephemeral=True)

    async def process_money_operation(self, interaction: discord.Interaction, modal: MoneyModal):
        if interaction.user.id != 312860306701418497:
            return
            
        try:
            user_id = modal.user_id.value
            currency_type = modal.currency_type.value.lower()
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

            currency_mapping = {
                'gem': ('gems', '<:gem:1346651000282550312>'),
                'credit': ('credits', '<:credit:1346650964118999052>'),
                'social': ('social_points', '<:socialpoint:1347015187198382274>'),
                'battle': ('battle_data', '<:battledataset:1347015196736225310>'),
                'dust': ('core_dust', '<:coredust:1347015208513703937>')
            }

            if currency_type not in currency_mapping:
                await interaction.response.send_message(
                    "*Adjusts glasses*\nCommander, please specify either 'gem', 'credit', 'social', 'battle', or 'dust' for the currency type.",
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

            user_data = self.get_user_currency(user_id)
            currency_key, currency_emoji = currency_mapping[currency_type]
            current_value = user_data[currency_key]
            
            if modal.operation == "Add":
                new_value = current_value + amount
            elif modal.operation == "Decrease":
                new_value = max(0, current_value - amount)
                if new_value != current_value - amount:
                    await interaction.response.send_message(
                        "Operation would result in negative balance. Setting to 0 instead.",
                        ephemeral=True
                    )
            else:
                new_value = amount

            user_data[currency_key] = new_value
            self.save_currency_data()

            embed = discord.Embed(
                title="Currency Modification Report",
                description=(
                    f"*Accessing secure database...*\n\n"
                    f"**Target ID:** `{user_id}`\n"
                    f"**Target Name:** {target_user.name}\n"
                    f"**Operation:** {modal.operation}\n"
                    f"**Currency Type:** {currency_type.upper()}\n"
                    f"**Previous Balance:** {currency_emoji} {current_value:,}\n"
                    f"**New Balance:** {currency_emoji} {new_value:,}\n\n"
                    f"*Transaction complete. Database has been updated successfully, commander!*"
                ),
                color=0x00b0f4,
                timestamp=interaction.created_at
            )
            embed.set_footer(text="Shifty Financial Services™")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            print(f"Error in process_money_operation: {str(e)}")
            await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)

    async def process_voucher_operation(self, interaction: discord.Interaction, modal: VoucherModal):
        if interaction.user.id != 312860306701418497:
            return
            
        try:
            user_id = modal.user_id.value
            voucher_type = modal.voucher_type.value.lower()
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

            voucher_mapping = {
                'normal': ('recruit_voucher', '<:recruit:1346650987007311953>'),
                'advanced': ('advanced_voucher', '<:recruit2:1346651073644855368>')
            }

            if voucher_type not in voucher_mapping:
                await interaction.response.send_message(
                    "*Adjusts glasses*\nCommander, please specify either 'normal' or 'advanced' for the voucher type.",
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

            user_data = self.get_user_currency(user_id)
            voucher_key, voucher_emoji = voucher_mapping[voucher_type]
            
            if voucher_key not in user_data:
                user_data[voucher_key] = 0
                
            current_value = user_data[voucher_key]

            if modal.operation == "Add":
                new_value = current_value + amount
            elif modal.operation == "Decrease":
                new_value = max(0, current_value - amount)
                if new_value != current_value - amount:
                    await interaction.response.send_message(
                        "Operation would result in negative balance. Setting to 0 instead.",
                        ephemeral=True
                    )
            else:
                new_value = amount

            user_data[voucher_key] = new_value
            self.save_currency_data()

            embed = discord.Embed(
                title="Voucher Modification Report",
                description=(
                    f"*Accessing secure database...*\n\n"
                    f"**Target ID:** `{user_id}`\n"
                    f"**Target Name:** {target_user.name}\n"
                    f"**Operation:** {modal.operation}\n"
                    f"**Voucher Type:** {voucher_type.upper()}\n"
                    f"**Previous Balance:** {voucher_emoji} {current_value:,}\n"
                    f"**New Balance:** {voucher_emoji} {new_value:,}\n\n"
                    f"*Transaction complete. Database has been updated successfully, commander!*"
                ),
                color=0x00b0f4,
                timestamp=interaction.created_at
            )
            embed.set_footer(text="Shifty Financial Services™")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            print(f"Error in process_voucher_operation: {str(e)}")
            await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Currency(bot))
