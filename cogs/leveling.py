import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View
from data.level_requirements import get_level_cost, get_max_affordable_level
from data.nikke_r import R_CHARACTERS
from data.nikke_sr import SR_CHARACTERS
from data.nikke_ssr import SSR_CHARACTERS

class LevelingButtons(View):
    def __init__(self, cog, nikke_data: dict, current_target: int, owner_id: int):
        super().__init__(timeout=300)
        self.cog = cog
        self.nikke_data = nikke_data
        self.current_target = current_target
        self.owner_id = owner_id
        self.update_buttons()
        
    def update_buttons(self):
        self.clear_items()
        
        user_currency = self.cog.currency_cog.get_user_currency(self.owner_id)
        next_level_costs = get_level_cost(self.nikke_data["level"], self.current_target)
        
        has_enough = (
            user_currency["credits"] >= next_level_costs[0] and
            user_currency["battle_data"] >= next_level_costs[1] and
            user_currency["core_dust"] >= next_level_costs[2]
        )

        next_level_affordable = True
        if self.current_target < self.nikke_data["max_level"]:
            next_costs = get_level_cost(self.nikke_data["level"], self.current_target + 1)
            next_level_affordable = (
                user_currency["credits"] >= next_costs[0] and
                user_currency["battle_data"] >= next_costs[1] and
                user_currency["core_dust"] >= next_costs[2]
            )
        
        min_button = Button(
            label="Min", 
            style=discord.ButtonStyle.grey,
            custom_id="min",
            disabled=self.current_target <= self.nikke_data["level"] + 1
        )
        decrease_button = Button(
            label="-",
            style=discord.ButtonStyle.red,
            custom_id="decrease",
            disabled=self.current_target <= self.nikke_data["level"] + 1
        )
        upgrade_button = Button(
            label="Upgrade",
            style=discord.ButtonStyle.green,
            custom_id="upgrade",
            disabled=not has_enough or self.current_target <= self.nikke_data["level"]
        )
        increase_button = Button(
            label="+",
            style=discord.ButtonStyle.blurple,
            custom_id="increase",
            disabled=self.current_target >= self.nikke_data["max_level"] or not next_level_affordable
        )
        max_button = Button(
            label="Max",
            style=discord.ButtonStyle.grey,
            custom_id="max",
            disabled=self.current_target >= self.nikke_data["max_level"] or not next_level_affordable
        )
        
        self.add_item(min_button)
        self.add_item(decrease_button)
        self.add_item(upgrade_button)
        self.add_item(increase_button)
        self.add_item(max_button)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("This upgrade menu belongs to another commander.", ephemeral=True)
            return False

        button_id = interaction.data["custom_id"]

        try:
            if button_id == "upgrade":
                if self.nikke_data["level"] >= self.nikke_data["max_level"]:
                    await interaction.response.send_message("You have selected the NIKKE with the highest level.", ephemeral=True)
                    return False

                await interaction.response.defer()
                await self.cog.perform_upgrade(interaction, self.nikke_data, self.current_target)
                return True

            elif button_id in ["min", "decrease", "increase", "max"]:
                original_target = self.current_target

                if button_id == "min":
                    self.current_target = self.nikke_data["level"] + 1
                elif button_id == "decrease":
                    self.current_target = max(self.nikke_data["level"] + 1, self.current_target - 1)
                elif button_id == "increase":
                    if self.current_target >= self.nikke_data["max_level"]:
                        await interaction.response.send_message("Maximum level reached.", ephemeral=True)
                        return False
                    self.current_target = min(self.nikke_data["max_level"], self.current_target + 1)
                elif button_id == "max":
                    if self.current_target >= self.nikke_data["max_level"]:
                        await interaction.response.send_message("Already at maximum level.", ephemeral=True)
                        return False
                    
                    currency = self.cog.currency_cog.get_user_currency(self.owner_id)
                    self.current_target = get_max_affordable_level(
                        self.nikke_data["level"],
                        self.nikke_data["max_level"],
                        currency["credits"],
                        currency["battle_data"],
                        currency["core_dust"]
                    )

                if original_target != self.current_target:
                    await self.cog.show_upgrade_cost(interaction, self.nikke_data, self.current_target, edit=True)
                else:
                    await interaction.response.defer()

            return True
            
        except Exception as e:
            print(f"Error in interaction_check: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("An error occurred.", ephemeral=True)
            return False

class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.currency_cog = None
        self.inventory_cog = None

    def get_required_cogs(self):
        if not self.currency_cog:
            self.currency_cog = self.bot.get_cog('Currency')
        if not self.inventory_cog:
            self.inventory_cog = self.bot.get_cog('Inventory')
        return self.currency_cog and self.inventory_cog
    
    async def show_upgrade_cost(self, interaction: discord.Interaction, nikke_data: dict, target_level: int, edit: bool = False, is_followup: bool = False):
        if not self.get_required_cogs():
            await interaction.response.send_message("System error. Please try again.", ephemeral=True)
            return

        credits_needed, battle_data_needed, core_dust_needed = get_level_cost(
            nikke_data["level"], 
            target_level
        )

        user_currency = self.currency_cog.get_user_currency(interaction.user.id)

        embed = discord.Embed(
            title=f"Level Up: {nikke_data['name']}",
            description=f"Current Level: {nikke_data['level']} → Target Level: {target_level}",
            color=0x00b0f4
        )

        embed.add_field(
            name="Credits",
            value=f"Required: <:credit:1346650964118999052> {credits_needed:,}\n"
                  f"Owned: <:credit:1346650964118999052> {user_currency['credits']:,}",
            inline=False
        )
        
        embed.add_field(
            name="Battle Data",
            value=f"Required: <:battledataset:1347015196736225310> {battle_data_needed:,}\n"
                  f"Owned: <:battledataset:1347015196736225310> {user_currency['battle_data']:,}",
            inline=False
        )

        if core_dust_needed > 0:
            embed.add_field(
                name="Core Dust",
                value=f"Required: <:coredust:1347015208513703937> {core_dust_needed:,}\n"
                      f"Owned: <:coredust:1347015208513703937> {user_currency['core_dust']:,}",
                inline=False
            )

        if nikke_data["name"].lower() in R_CHARACTERS:
            embed.set_thumbnail(url=R_CHARACTERS[nikke_data["name"].lower()]["icon_url"])
        elif nikke_data["name"].lower() in SR_CHARACTERS:
            embed.set_thumbnail(url=SR_CHARACTERS[nikke_data["name"].lower()]["icon_url"])
        elif nikke_data["name"].lower() in SSR_CHARACTERS:
            embed.set_thumbnail(url=SSR_CHARACTERS[nikke_data["name"].lower()]["icon_url"])

        view = LevelingButtons(self, nikke_data, target_level, interaction.user.id)
        
        if edit or is_followup:
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            await interaction.response.send_message(embed=embed, view=view)

    async def perform_upgrade(self, interaction: discord.Interaction, nikke_data: dict, target_level: int):
        try:
            credits_needed, battle_data_needed, core_dust_needed = get_level_cost(
                nikke_data["level"], 
                target_level
            )
            
            user_currency = self.currency_cog.get_user_currency(interaction.user.id)
            
            if (user_currency["credits"] < credits_needed or
                user_currency["battle_data"] < battle_data_needed or
                user_currency["core_dust"] < core_dust_needed):
                await interaction.followup.send("Insufficient resources.", ephemeral=True)
                return
                
            user_currency["credits"] -= credits_needed
            user_currency["battle_data"] -= battle_data_needed
            user_currency["core_dust"] -= core_dust_needed
            self.currency_cog.save_currency_data()
            
            inventory = self.inventory_cog.get_user_inventory(str(interaction.user.id))
            inventory[nikke_data["name"].lower()]["level"] = target_level
            self.inventory_cog.save_inventory_data()
            
            nikke_data["level"] = target_level

            if target_level >= nikke_data["max_level"]:
                embed = discord.Embed(
                    title=f"Level Up: {nikke_data['name']}",
                    description=f"{nikke_data['name']} has reached maximum level {target_level}!",
                    color=0x00ff00
                )
                
                if nikke_data["name"].lower() in SSR_CHARACTERS:
                    embed.set_thumbnail(url=SSR_CHARACTERS[nikke_data["name"].lower()]["icon_url"])
                elif nikke_data["name"].lower() in SR_CHARACTERS:
                    embed.set_thumbnail(url=SR_CHARACTERS[nikke_data["name"].lower()]["icon_url"])
                elif nikke_data["name"].lower() in R_CHARACTERS:
                    embed.set_thumbnail(url=R_CHARACTERS[nikke_data["name"].lower()]["icon_url"])

                await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed, view=None)
            else:
                nikke_data_next = {
                    "name": nikke_data["name"],
                    "level": target_level,
                    "max_level": nikke_data["max_level"],
                    "rarity": nikke_data["rarity"]
                }
                
                credits, battle_data, core_dust = get_level_cost(target_level, target_level + 1)
                embed = discord.Embed(
                    title=f"Level Up: {nikke_data['name']}",
                    description=f"Current Level: {target_level} → Target Level: {target_level + 1}",
                    color=0x00b0f4
                )

                embed.add_field(
                    name="Credits",
                    value=f"Required: <:credit:1346650964118999052> {credits:,}\n"
                          f"Owned: <:credit:1346650964118999052> {user_currency['credits']:,}",
                    inline=False
                )
                
                embed.add_field(
                    name="Battle Data",
                    value=f"Required: <:battledataset:1347015196736225310> {battle_data:,}\n"
                          f"Owned: <:battledataset:1347015196736225310> {user_currency['battle_data']:,}",
                    inline=False
                )

                if core_dust > 0:
                    embed.add_field(
                        name="Core Dust",
                        value=f"Required: <:coredust:1347015208513703937> {core_dust:,}\n"
                              f"Owned: <:coredust:1347015208513703937> {user_currency['core_dust']:,}",
                        inline=False
                    )

                if nikke_data["name"].lower() in SSR_CHARACTERS:
                    embed.set_thumbnail(url=SSR_CHARACTERS[nikke_data["name"].lower()]["icon_url"])
                elif nikke_data["name"].lower() in SR_CHARACTERS:
                    embed.set_thumbnail(url=SR_CHARACTERS[nikke_data["name"].lower()]["icon_url"])
                elif nikke_data["name"].lower() in R_CHARACTERS:
                    embed.set_thumbnail(url=R_CHARACTERS[nikke_data["name"].lower()]["icon_url"])

                view = LevelingButtons(self, nikke_data_next, target_level + 1, interaction.user.id)
                await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed, view=view)

        except Exception as e:
            print(f"Error in perform_upgrade: {e}")
            try:
                await interaction.followup.send("An error occurred during upgrade.", ephemeral=True)
            except:
                pass

    @app_commands.command(name="upgrade", description="Level up your NIKKE")
    async def upgrade(self, interaction: discord.Interaction, name: str):
        if not self.get_required_cogs():
            await interaction.response.send_message("System error. Please try again.", ephemeral=True)
            return

        inventory_cog = self.inventory_cog
        user_id = str(interaction.user.id)
        inventory = inventory_cog.get_user_inventory(user_id)
        name = name.lower()

        similar_names = inventory_cog.find_similar_nikke_names(name)
        if similar_names:
            owned_matches = []
            for similar in similar_names:
                nikke_key = similar.lower()
                if nikke_key in inventory:
                    owned_matches.append(similar)
            
            if not owned_matches:
                suggestion_list = "\n".join([f"{i+1}. {name}" for i, name in enumerate(similar_names)])
                await interaction.response.send_message(
                    f"Commander, you don't own any NIKKE with the name you were searching for.\n\n"
                    f"Similar NIKKEs found in database:\n{suggestion_list}",
                    ephemeral=True
                )
                return
            elif name not in inventory:
                suggestion_list = "\n".join([f"{i+1}. {name}" for i, name in enumerate(owned_matches)])
                await interaction.response.send_message(
                    f"Commander, I couldn't find an exact match. Were you trying to search for one of these NIKKEs you own?\n{suggestion_list}",
                    ephemeral=True
                )
                return

        nikke_data = None
        if name in R_CHARACTERS:
            nikke_data = R_CHARACTERS[name]
        elif name in SR_CHARACTERS:
            nikke_data = SR_CHARACTERS[name]
        elif name in SSR_CHARACTERS:
            nikke_data = SSR_CHARACTERS[name]

        if not nikke_data:
            await interaction.response.send_message("Error fetching NIKKE data.", ephemeral=True)
            return

        inventory_data = inventory[name]
        max_level = inventory_cog.get_max_level(inventory_data["rarity"], inventory_data["limit_break"])
        current_level = inventory_data["level"]

        if current_level >= max_level:
            embed = discord.Embed(
                title=f"Level Up: {nikke_data['name']}",
                description=f"{nikke_data['name']} is already at maximum level {current_level}!",
                color=0x00ff00
            )
            
            if name in SSR_CHARACTERS:
                embed.set_thumbnail(url=SSR_CHARACTERS[name]["icon_url"])
            elif name in SR_CHARACTERS:
                embed.set_thumbnail(url=SR_CHARACTERS[name]["icon_url"])
            elif name in R_CHARACTERS:
                embed.set_thumbnail(url=R_CHARACTERS[name]["icon_url"])

            await interaction.response.send_message(embed=embed)
            return

        await self.show_upgrade_cost(
            interaction,
            {
                "name": nikke_data["name"],
                "level": current_level,
                "max_level": max_level,
                "rarity": nikke_data["rarity"]
            },
            current_level + 1
        )

async def setup(bot):
    await bot.add_cog(Leveling(bot))
