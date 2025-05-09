import json
import os
import random
from difflib import get_close_matches
from discord.ext import commands
import discord
from discord import app_commands
from discord.ui import Button, View
from data.nikke_r import R_CHARACTERS
from data.nikke_sr import SR_CHARACTERS
from data.nikke_ssr import SSR_CHARACTERS
from utils.constants import MAX_LIMIT_BREAKS
from utils.limited_nikkes import LIMITED_SR, LIMITED_SSR

EMOJI_MAPPING = {
    # Rarity
    'R': '<:R_:1347121611832164352>',
    'SR': '<:Sr:1347121626763755560>',
    'SSR': '<:Ssr:1347121643029266534>',
    # Class
    'Attacker': '<:Attacker:1347172718482554930>',
    'Defender': '<:Defender:1347172728767254590>',
    'Supporter': '<:Supporter:1347172743845777509>',
    # Burst
    'I': '<:Burst1:1347172759708368936>',
    'II': '<:Burst2:1347172769074516018>',
    'III': '<:Burst3:1347172780809912340>',
    'All': '<:BurstAll:1347172791946051594>',
    # Manufacturer
    'Elysion': '<:Elysion_Icon:1347172814796623952>',
    'Missilis': '<:Missilis_Icon:1347172829304590376>',
    'Tetra': '<:Tetra_Icon:1347172846270414891>',
    'Pilgrim': '<:Pilgrim_Icon:1347172860732375060>',
    # Weapon
    'AR': '<:ar:1347173993756753930>',
    'MG': '<:mg:1347174014207922196>',
    'RL': '<:rl:1347174027348807803>',
    'SG': '<:sg:1347174041294868540>',
    'SMG': '<:smg:1347174054452265011>',
    'SNR': '<:sr:1347174065713975316>',
    # Element
    'Wind': '<:wind:1347175032203247626>',
    'Iron': '<:iron:1347175057205755905>',
    'Fire': '<:fire:1347175079330578453>',
    'Water': '<:water:1347175102198059078>',
    'Electric': '<:electric:1347175120216657970>'
}

class ConfirmPull(View):
    def __init__(self, cog, banner_type, amount, vouchers, gems_needed):
        super().__init__(timeout=60)
        self.cog = cog
        self.banner_type = banner_type
        self.amount = amount
        self.vouchers = vouchers
        self.gems_needed = gems_needed

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey)
    async def cancel(self, interaction: discord.Interaction, button: Button):
        # Instead of deleting, we'll edit the message to show cancelled state
        embed = discord.Embed(
            title="Recruitment Cancelled",
            description="Operation has been cancelled.",
            color=0x00b0f4
        )
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.blurple)
    async def confirm(self, interaction: discord.Interaction, button: Button):
        # First edit the message to remove buttons and show processing state
        embed = discord.Embed(
            title="Processing Recruitment",
            description="*Please wait...*",
            color=0x00b0f4
        )
        await interaction.response.edit_message(embed=embed, view=None)
        
        # Then use followup to send the recruitment results
        await self.cog.execute_recruitment(interaction, self.banner_type, self.amount, self.vouchers, self.gems_needed)

class RecruitButtons(View):
    def __init__(self, cog, banner_type, user_currency=None):
        super().__init__(timeout=None)
        self.cog = cog
        self.banner_type = banner_type
        
        # Set up buttons with proper labels
        if (banner_type == "social"):
            self.add_item(Button(label="Recruit 1 - 10 SP", style=discord.ButtonStyle.blurple, custom_id="recruit_one"))
            self.add_item(Button(label="Recruit 10 - 100 SP", style=discord.ButtonStyle.blurple, custom_id="recruit_ten"))
        else:
            available_vouchers = user_currency.get('advanced_voucher' if banner_type == "special" else 'recruit_voucher', 0) if user_currency else 0
            
            if (available_vouchers > 0):
                self.add_item(Button(label="Recruit 1 - 1 Voucher", style=discord.ButtonStyle.blurple, custom_id="recruit_one"))
                self.add_item(Button(label="Recruit 10 - 10 Vouchers", style=discord.ButtonStyle.blurple, custom_id="recruit_ten"))
            else:
                self.add_item(Button(label="Recruit 1 - 300 Gems", style=discord.ButtonStyle.blurple, custom_id="recruit_one"))
                self.add_item(Button(label="Recruit 10 - 3000 Gems", style=discord.ButtonStyle.blurple, custom_id="recruit_ten"))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if (interaction.data["custom_id"] == "recruit_one"):
            await self.cog.start_recruitment(interaction, 1, self.banner_type)
        elif (interaction.data["custom_id"] == "recruit_ten"):
            await self.cog.start_recruitment(interaction, 10, self.banner_type)
        return True

class GachaResultView(View):
    def __init__(self, cog, results, current_index=0):
        super().__init__(timeout=300)  # 5 minute timeout
        self.cog = cog
        self.results = results
        self.current_index = current_index
        
        # Always add both buttons
        self.add_item(Button(label="Next", style=discord.ButtonStyle.blurple, custom_id="next"))
        self.add_item(Button(label="Skip", style=discord.ButtonStyle.grey, custom_id="skip"))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.data["custom_id"] == "next":
            self.current_index += 1
            # Show final results when we've shown all pulls
            if self.current_index > len(self.results) - 1:
                await self.cog.show_final_results(interaction, self.results)
            else:
                # Show next pull
                await self.cog.show_single_pull(interaction, self.results, self.current_index, edit=True)
        elif interaction.data["custom_id"] == "skip":
            # Skip to final results
            await self.cog.show_final_results(interaction, self.results)
        return True

class Gacha(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.special_file = 'data/special_nikke.json'
        self.special_nikke = self.load_special_nikke()
        self.currency_cog = None  # Initialize as None
        self.inventory_cog = None  # Initialize as None
        self.default_special_banner = "https://images4.alphacoders.com/128/1286571.png"

    def get_required_cogs(self):
        """Get required cogs if they're not loaded yet"""
        if not self.currency_cog:
            self.currency_cog = self.bot.get_cog('Currency')
        if not self.inventory_cog:
            self.inventory_cog = self.bot.get_cog('Inventory')
        return self.currency_cog and self.inventory_cog

    async def cog_load(self):
        """This runs after the cog is loaded"""
        if not self.get_required_cogs():
            print("Note: Some cogs not loaded yet. They will be loaded when needed.")

    def load_special_nikke(self):
        if os.path.exists(self.special_file):
            with open(self.special_file, 'r') as f:
                data = json.load(f)
                if 'banner_image' not in data:
                    data['banner_image'] = self.default_special_banner
                return data
        return {
            "name": "heim",
            "banner_image": self.default_special_banner
        }

    def save_special_nikke(self):
        with open(self.special_file, 'w') as f:
            json.dump(self.special_nikke, f, indent=4)

    @commands.command(name='setspecial', hidden=True)
    async def setspecial(self, ctx, nikke_name: str, banner_image: str = None):
        if ctx.author.id != 312860306701418497:
            return

        nikke_name = nikke_name.lower().strip('"')
        # Allow setting special banner for both limited and non-limited SSRs
        if nikke_name in SSR_CHARACTERS:
            self.special_nikke["name"] = nikke_name
            if banner_image:
                self.special_nikke["banner_image"] = banner_image.strip('"')
            else:
                self.special_nikke["banner_image"] = self.default_special_banner
            
            self.save_special_nikke()
            
            embed = discord.Embed(
                title="Special Recruitment Update",
                description=(
                    f"*Updating recruitment parameters...*\n\n"
                    f"Special recruitment rate-up has been set to **{SSR_CHARACTERS[nikke_name]['name']}**\n"
                    f"*Banner image has been {'updated' if banner_image else 'set to default'}*"
                ),
                color=0x00b0f4
            )
            embed.set_thumbnail(url=SSR_CHARACTERS[nikke_name]['icon_url'])
            if banner_image:
                embed.set_image(url=banner_image)
            await ctx.send(embed=embed)
        else:
            similar = get_close_matches(nikke_name, SSR_CHARACTERS.keys(), n=3, cutoff=0.6)
            if similar:
                suggestions = "\n".join([f"• {SSR_CHARACTERS[name]['name']}" for name in similar])
                await ctx.send(
                    f"Invalid NIKKE name. Did you mean:\n{suggestions}",
                    ephemeral=True
                )
            else:
                await ctx.send(
                    "Invalid NIKKE name. Please check the name and try again.",
                    ephemeral=True
                )

    def get_random_nikke(self, banner_type="standard"):
        rate = random.random() * 100

        if banner_type == "social":
            if rate < 2:  # 2% SSR
                ssrs = [ssr for name, ssr in SSR_CHARACTERS.items() if name not in LIMITED_SSR]
                return random.choice(ssrs)
            elif rate < 45:  # 43% SR
                srs = [sr for name, sr in SR_CHARACTERS.items() if name not in LIMITED_SR]
                return random.choice(srs)
            else:  # 55% R
                return random.choice(list(R_CHARACTERS.values()))
        elif banner_type == "special" and rate < 6:  # 4% base + 2% rate up
            if rate < 2:  # 2% rate up
                return SSR_CHARACTERS[self.special_nikke["name"]]
            # Remaining 4% split among non-limited SSRs
            ssrs = [ssr for name, ssr in SSR_CHARACTERS.items() 
                   if name not in LIMITED_SSR or name == self.special_nikke["name"]]
            return random.choice(ssrs)
        elif rate < 4:  # Standard SSR rate 4%
            ssrs = [ssr for name, ssr in SSR_CHARACTERS.items() if name not in LIMITED_SSR]
            return random.choice(ssrs)
        elif rate < 40:  # SR rate 36%
            srs = [sr for name, sr in SR_CHARACTERS.items() if name not in LIMITED_SR]
            return random.choice(srs)
        else:  # R rate 60%
            return random.choice(list(R_CHARACTERS.values()))

    @app_commands.command(name="recruit", description="Recruit NIKKEs from various banners")
    @app_commands.choices(banner=[
        discord.app_commands.Choice(name="Standard", value="standard"),
        discord.app_commands.Choice(name="Special", value="special"),
        discord.app_commands.Choice(name="Social", value="social")
    ])
    async def recruit(self, interaction: discord.Interaction, banner: str):
        if not self.get_required_cogs():
            await interaction.response.send_message(
                "System initialization error. Please try again.", 
                ephemeral=True
            )
            return

        user_currency = self.currency_cog.get_user_currency(interaction.user.id)
        
        # Set color based on banner type
        embed_color = (0x00b0f4 if banner == "standard" else 0xffd700 if banner == "special" else 0xff69b4)

        embed = discord.Embed(
            title=("Ordinary Recruit" if banner == "standard" else 
                  "Pick Up Recruitment" if banner == "special" else 
                  "Social Point Recruit"),
            color=embed_color
        )
        
        if banner == "special":
            special_name = SSR_CHARACTERS[self.special_nikke["name"]]['name']
            embed.description = f"Rate Up NIKKE: **{special_name}**\n*Chance to obtain: 2%*"
        elif banner == "social":
            embed.description = "*SSR: 2% | SR: 43% | R: 55%*"

        # Set banner image
        banner_images = {
            "standard": "https://twinfinite.net/wp-content/uploads/2022/10/Goddess-of-Victory-Nikke-2.jpg?fit=1200%2C675",
            "special": self.special_nikke["banner_image"],
            "social": "https://i0.wp.com/uploads.saigacdn.com/2022/10/level-infinite-nikke-rapi-trailer-00.jpg"
        }
        embed.set_image(url=banner_images[banner])

        view = RecruitButtons(self, banner, user_currency)
        await interaction.response.send_message(embed=embed, view=view)

    async def start_recruitment(self, interaction: discord.Interaction, amount: int, banner_type: str):
        user_currency = self.currency_cog.get_user_currency(interaction.user.id)
        
        # Determine voucher type and gem cost
        if banner_type == "special":
            voucher_key = "advanced_voucher"
            voucher_name = "Advanced Recruit Voucher"
            voucher_emoji = "<:recruit2:1346651073644855368>"
        elif banner_type == "standard":
            voucher_key = "recruit_voucher"
            voucher_name = "Recruit Voucher"
            voucher_emoji = "<:recruit:1346650987007311953>"
        else:  # social banner
            return await self.process_recruitment(interaction, amount, banner_type)

        available_vouchers = user_currency.get(voucher_key, 0)
        if amount == 1:
            if available_vouchers >= 1:
                return await self.execute_recruitment(interaction, banner_type, amount, 1, 0)
            elif user_currency['gems'] >= 300:
                return await self.execute_recruitment(interaction, banner_type, amount, 0, 300)
            else:
                return await interaction.response.send_message("Insufficient gems and vouchers.", ephemeral=True)

        # Handle 10-pull case
        usable_vouchers = min(available_vouchers, 10)
        gems_needed = (10 - usable_vouchers) * 300

        if usable_vouchers < 10 and user_currency['gems'] < gems_needed:
            return await interaction.response.send_message(
                f"Insufficient resources. You need {10 - usable_vouchers} more vouchers or {gems_needed} gems.",
                ephemeral=True
            )

        if usable_vouchers < 10:
            embed = discord.Embed(
                title="Notice",
                description=(
                    f"Not enough {voucher_name}s. Gems will be consumed if you recruit NIKKEs now. Recruit anyway?\n\n"
                    f"Cost: {voucher_emoji} {usable_vouchers} + <:gem:1346651000282550312> {gems_needed:,}"
                ),
                color=0x00b0f4
            )
            view = ConfirmPull(self, banner_type, amount, usable_vouchers, gems_needed)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        else:
            await self.execute_recruitment(interaction, banner_type, amount, 10, 0)

    async def add_nikke_to_inventory(self, user_id: str, nikke_name: str, nikke_data: dict):
        inventory = self.inventory_cog.get_user_inventory(user_id)
        nikke_key = nikke_name.lower()
        
        if nikke_key in inventory:
            # Handle limit breaks
            current_lb = inventory[nikke_key]["limit_break"]
            max_lb = MAX_LIMIT_BREAKS[nikke_data["rarity"]]
            
            # For SSR, allow up to max_lb + 7 (core enhancements)
            # For others, stick to their max limit break
            max_allowed = max_lb + 7 if nikke_data["rarity"] == "SSR" else max_lb
            
            if current_lb < max_allowed:
                inventory[nikke_key]["limit_break"] += 1
        else:
            # Add new NIKKE
            inventory[nikke_key] = {
                "rarity": nikke_data["rarity"],
                "limit_break": 0,
                "level": 1
            }
        
        self.inventory_cog.save_inventory_data()

    async def show_single_pull(self, interaction: discord.Interaction, results: list, index: int, edit: bool = False, is_followup: bool = False):
        nikke = results[index]
        rarity_color = {
            'R': 0x00b0f4,  # Cyan
            'SR': 0x9400d3,  # Purple
            'SSR': 0xffd700  # Gold
        }[nikke['rarity']]

        embed = discord.Embed(
            title=f"Recruitment Result ({index + 1}/{len(results)})",
            description=f"*Processing recruitment data...*",
            color=rarity_color
        )

        rarity_emoji = EMOJI_MAPPING[nikke['rarity']]
        class_emoji = EMOJI_MAPPING[nikke['class']]
        manu_emoji = EMOJI_MAPPING[nikke['manufacturer']]
        weapon_emoji = EMOJI_MAPPING[nikke['weapon']]
        element_emoji = EMOJI_MAPPING[nikke['element']]
        burst_emoji = EMOJI_MAPPING[nikke['burst']]

        embed.add_field(
            name=f"{nikke['name']} [{rarity_emoji}]",
            value=f"{manu_emoji} • {class_emoji} • {weapon_emoji}\n{element_emoji} • {burst_emoji}",
            inline=False
        )

        embed.set_image(url=nikke['image_url'])
        
        view = GachaResultView(self, results, index)
        
        if edit:
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            if is_followup:
                await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def show_final_results(self, interaction: discord.Interaction, results: list):
        has_ssr = any(nikke['rarity'] == 'SSR' for nikke in results)
        has_sr = any(nikke['rarity'] == 'SR' for nikke in results)
        
        color = 0xffd700 if has_ssr else 0x9400d3 if has_sr else 0x00b0f4

        embed = discord.Embed(
            title=f"Final Recruitment Results ({len(results)} {'pull' if len(results) == 1 else 'pulls'})",
            description="*Processing recruitment data...*\n\n",
            color=color
        )

        # Track body labels earned
        total_labels = 0
        for nikke in results:
            rarity_emoji = EMOJI_MAPPING[nikke['rarity']]
            class_emoji = EMOJI_MAPPING[nikke['class']]
            manu_emoji = EMOJI_MAPPING[nikke['manufacturer']]
            embed.add_field(
                name=f"{nikke['name']} [{rarity_emoji}]",
                value=f"{manu_emoji} • {class_emoji}",
                inline=True
            )
            
            # Calculate body labels if it was a dupe that exceeded limit break
            inventory = self.inventory_cog.get_user_inventory(str(interaction.user.id))
            nikke_key = nikke['name'].lower()
            if nikke_key in inventory:
                current_lb = inventory[nikke_key]["limit_break"]
                if nikke['rarity'] == 'SSR' and current_lb >= 10:  # SSR at max CE
                    total_labels += 6000
                elif nikke['rarity'] == 'SR' and current_lb >= MAX_LIMIT_BREAKS['SR']:
                    total_labels += 200
                elif nikke['rarity'] == 'R' and current_lb >= MAX_LIMIT_BREAKS['R']:
                    total_labels += 150

        # Add body labels to user's currency if any were earned
        if total_labels > 0:
            user_currency = self.currency_cog.get_user_currency(interaction.user.id)
            user_currency['body_labels'] += total_labels
            self.currency_cog.save_currency_data()
            embed.set_footer(text=f"Acquired {total_labels:,} Body Labels")

        await interaction.response.edit_message(embed=embed, view=None)

    async def execute_recruitment(self, interaction: discord.Interaction, banner_type: str, amount: int, vouchers: int, gems: int):
        # Add cog check at the start
        if not self.inventory_cog:
            self.inventory_cog = self.bot.get_cog('Inventory')
        if not self.currency_cog:
            self.currency_cog = self.bot.get_cog('Currency')
            
        if not self.inventory_cog or not self.currency_cog:
            await interaction.response.send_message(
                "System initialization error. Please try again.", 
                ephemeral=True
            )
            return

        user_currency = self.currency_cog.get_user_currency(interaction.user.id)
        
        # Verify resources again
        if gems > 0 and user_currency['gems'] < gems:
            await interaction.response.send_message("Insufficient gems.", ephemeral=True)
            return

        voucher_key = "advanced_voucher" if banner_type == "special" else "recruit_voucher"
        if vouchers > 0 and user_currency[voucher_key] < vouchers:
            await interaction.response.send_message("Insufficient vouchers.", ephemeral=True)
            return

        # Deduct resources
        if gems > 0:
            user_currency['gems'] -= gems
        if vouchers > 0:
            user_currency[voucher_key] -= vouchers
        self.currency_cog.save_currency_data()

        # Perform recruitment and add to inventory
        results = [self.get_random_nikke(banner_type) for _ in range(amount)]
        for nikke in results:
            await self.add_nikke_to_inventory(str(interaction.user.id), nikke['name'].lower(), nikke)

        # Add mileage tickets
        if banner_type != "social":  # Don't award tickets for social pulls
            user_currency = self.currency_cog.get_user_currency(interaction.user.id)
            if banner_type == "standard":
                user_currency["silver_tickets"] += amount
            else:  # special banner
                user_currency["gold_tickets"] += amount
            self.currency_cog.save_currency_data()

        # Continue with showing results
        if not interaction.response.is_done():
            await self.show_single_pull(interaction, results, 0)
        else:
            try:
                # Create a follow-up message instead of using channel.send
                await interaction.followup.send(
                    embed=await self.create_single_pull_embed(results, 0),
                    view=GachaResultView(self, results, 0),
                    ephemeral=True
                )
            except discord.errors.NotFound:
                # If followup fails, try to DM the user
                try:
                    await interaction.user.send(
                        embed=await self.create_single_pull_embed(results, 0),
                        view=GachaResultView(self, results, 0)
                    )
                except discord.errors.Forbidden:
                    # If we can't DM either, just show the final results
                    await self.show_final_results(interaction, results)

    async def create_single_pull_embed(self, results: list, index: int):
        nikke = results[index]
        rarity_color = {
            'R': 0x00b0f4,  # Cyan
            'SR': 0x9400d3,  # Purple
            'SSR': 0xffd700  # Gold
        }[nikke['rarity']]

        embed = discord.Embed(
            title=f"Recruitment Result ({index + 1}/{len(results)})",
            description=f"*Processing recruitment data...*",
            color=rarity_color
        )

        try:
            rarity_emoji = EMOJI_MAPPING[nikke['rarity']]
            embed.add_field(
                name=f"{nikke['name']} [{rarity_emoji}]",
                value="\u200b",  # Invisible character to keep spacing
                inline=False
            )
        except KeyError as e:
            print(f"Error accessing emoji mapping: {e} for NIKKE: {nikke['name']}")
            embed.add_field(
                name=f"{nikke['name']} [{nikke['rarity']}]",
                value="\u200b",
                inline=False
            )

        embed.set_image(url=nikke['image_url'])
        return embed

    async def show_single_pull(self, interaction: discord.Interaction, results: list, index: int, edit: bool = False):
        embed = await self.create_single_pull_embed(results, index)
        view = GachaResultView(self, results, index)
        
        try:
            if edit:
                await interaction.response.edit_message(embed=embed, view=view)
            else:
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        except Exception as e:
            print(f"Error in show_single_pull: {e}")
            # Fallback to final results if showing single pull fails
            await self.show_final_results(interaction, results)

    async def process_recruitment(self, interaction: discord.Interaction, amount: int, banner_type: str):
        user_currency = self.currency_cog.get_user_currency(interaction.user.id)
        
        if banner_type == "social":
            cost = 10 if amount == 1 else 100
            currency_key = "social_points"
            currency_name = "Social Points"
        else:
            cost = 300 if amount == 1 else 3000
            currency_key = "gems"
            currency_name = "Gems"

        if user_currency[currency_key] < cost:
            await interaction.response.send_message(
                f"*Checking financial status...*\n\n"
                f"Insufficient {currency_name} for recruitment. Please check your balance, commander.",
                ephemeral=True
            )
            return

        # Update user's currency first
        user_currency[currency_key] -= cost
        self.currency_cog.save_currency_data()

        # Perform recruitment and add to inventory
        results = [self.get_random_nikke(banner_type) for _ in range(amount)]
        for nikke in results:
            await self.add_nikke_to_inventory(str(interaction.user.id), nikke['name'].lower(), nikke)
        
        # Start with first pull like in execute_recruitment
        await self.show_single_pull(interaction, results, 0)

async def setup(bot):
    await bot.add_cog(Gacha(bot))
