import json
import os
from discord.ext import commands
import discord
from discord import app_commands
from discord.ui import Button, View
from typing import Dict, List
from difflib import get_close_matches

from data.nikke_r import R_CHARACTERS
from data.nikke_sr import SR_CHARACTERS
from data.nikke_ssr import SSR_CHARACTERS
from utils.constants import MAX_LIMIT_BREAKS, LEVEL_CAPS, STARTING_NIKKES

EMOJI_MAPPING = {
    'R': '<:R_:1347121611832164352>',
    'SR': '<:Sr:1347121626763755560>',
    'SSR': '<:Ssr:1347121643029266534>',
    'Attacker': '<:Attacker:1347172718482554930>',
    'Defender': '<:Defender:1347172728767254590>',
    'Supporter': '<:Supporter:1347172743845777509>',
    'I': '<:Burst1:1347172759708368936>',
    'II': '<:Burst2:1347172769074516018>',
    'III': '<:Burst3:1347172780809912340>',
    'All': '<:BurstAll:1347172791946051594>',
    'Elysion': '<:Elysion_Icon:1347172814796623952>',
    'Missilis': '<:Missilis_Icon:1347172829304590376>',
    'Tetra': '<:Tetra_Icon:1347172846270414891>',
    'Pilgrim': '<:Pilgrim_Icon:1347172860732375060>',
    'AR': '<:ar:1347173993756753930>',
    'MG': '<:mg:1347174014207922196>',
    'RL': '<:rl:1347174027348807803>',
    'SG': '<:sg:1347174041294868540>',
    'SMG': '<:smg:1347174054452265011>',
    'SNR': '<:sr:1347174065713975316>',
    'Wind': '<:wind:1347175032203247626>',
    'Iron': '<:iron:1347175057205755905>',
    'Fire': '<:fire:1347175079330578453>',
    'Water': '<:water:1347175102198059078>',
    'Electric': '<:electric:1347175120216657970>'
}

CORE_ENHANCEMENT_EMOJIS = {
    1: '<:lb1:1347571129145102408>',
    2: '<:lb2:1347571137768325211>',
    3: '<:lb3:1347571147117690942>',
    4: '<:lb4:1347571157662175334>',
    5: '<:lb5:1347571166285402175>',
    6: '<:lb6:1347571174523142238>',
    7: '<:lb7:1347571185285726310>'
}

ITEMS_PER_PAGE = 5

class PageSelectModal(discord.ui.Modal, title="Page Navigation"):
    def __init__(self, max_pages: int, view):
        super().__init__()
        self.view = view
        self.page_input = discord.ui.TextInput(
            label=f'Which page, commander? (1-{max_pages})',
            placeholder='Enter a page number',
            min_length=1,
            max_length=3,
            required=True
        )
        self.add_item(self.page_input)
        self.max_pages = max_pages

    async def on_submit(self, interaction: discord.Interaction):
        try:
            page = int(self.page_input.value) - 1
            if 0 <= page < self.max_pages:
                await self.view.cog.show_nikke_page(interaction, page, edit=True)
            else:
                await interaction.response.send_message(
                    f"Please enter a number between 1 and {self.max_pages}.", 
                    ephemeral=True
                )
        except ValueError:
            await interaction.response.send_message(
                "Please enter a valid number.", 
                ephemeral=True
            )

class NikkePageView(View):
    def __init__(self, cog, user_id: int, nikkes: List[dict], page: int = 0, sort_by: str = "default"):
        super().__init__(timeout=300)
        self.cog = cog
        self.user_id = user_id
        self.nikkes = nikkes
        self.page = page
        self.sort_by = sort_by
        self.max_pages = (len(nikkes) - 1) // ITEMS_PER_PAGE + 1
        
        self.add_item(Button(
            label=f"Sort: {sort_by.title()}", 
            style=discord.ButtonStyle.grey, 
            custom_id="sort"
        ))
        
        if page > 0:
            self.add_item(Button(label="Previous", style=discord.ButtonStyle.blurple, custom_id="prev"))
        self.add_item(Button(label="Go to", style=discord.ButtonStyle.grey, custom_id="goto"))
        if page < self.max_pages - 1:
            self.add_item(Button(label="Next", style=discord.ButtonStyle.blurple, custom_id="next"))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This inventory belongs to another commander.", ephemeral=True)
            return False
            
        button_id = interaction.data["custom_id"]
        
        if button_id == "sort":
            sort_options = ["default", "level", "limit break", "rarity"]
            current_index = sort_options.index(self.sort_by)
            next_sort = sort_options[(current_index + 1) % len(sort_options)]
            await self.cog.show_nikke_page(interaction, 0, self.nikkes, edit=True, sort_by=next_sort)
        elif button_id == "prev":
            await self.cog.show_nikke_page(interaction, self.page - 1, self.nikkes, edit=True, sort_by=self.sort_by)
        elif button_id == "next":
            await self.cog.show_nikke_page(interaction, self.page + 1, self.nikkes, edit=True, sort_by=self.sort_by)
        elif button_id == "goto":
            modal = PageSelectModal(self.max_pages, self)
            await interaction.response.send_modal(modal)
            
        return True

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        
        try:
            await self.message.edit(view=self)
        except:
            pass

class Inventory(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.inventory_file = 'data/inventory.json'
        self.data = self.load_inventory_data()
        self.max_limit_breaks = MAX_LIMIT_BREAKS
        self.level_caps = LEVEL_CAPS
        self.EMOJI_MAPPING = EMOJI_MAPPING

    def load_inventory_data(self):
        if os.path.exists(self.inventory_file):
            with open(self.inventory_file, 'r') as f:
                return json.load(f)
        return {"users": {}}

    def save_inventory_data(self):
        with open(self.inventory_file, 'w') as f:
            json.dump(self.data, f, indent=4)

    def get_user_inventory(self, user_id: str) -> Dict:
        if user_id not in self.data["users"]:
            self.data["users"][user_id] = STARTING_NIKKES.copy()
            self.save_inventory_data()
        return self.data["users"][user_id]

    def format_limit_break(self, rarity: str, current_lb: int) -> str:
        if max_lb := self.max_limit_breaks[rarity]:
            result = []
            if rarity == "SSR":
                for i in range(3):
                    if i < min(current_lb, 3):
                        result.append("<:limit1:1347233105873997844>")
                    else:
                        result.append("<:limit0:1347233405355560981>")
                
                if current_lb >= 4:
                    core_level = current_lb - 3
                    if 0 < core_level <= 7:
                        result.append(CORE_ENHANCEMENT_EMOJIS[core_level])
            else:
                for i in range(max_lb):
                    if i < current_lb:
                        result.append("<:limit1:1347233105873997844>")
                    else:
                        result.append("<:limit0:1347233405355560981>")
                
            return " ".join(result)
        return ""

    def get_max_level(self, rarity: str, limit_break: int) -> int:
        if rarity == "R":
            return self.level_caps["R"]
        
        if rarity == "SSR" and limit_break > 3:
            return self.level_caps[rarity][3]
        
        return self.level_caps[rarity][min(limit_break, len(self.level_caps[rarity])-1)]

    def get_proper_nikke_name(self, key: str) -> str:
        """Get proper NIKKE name from character data"""
        if key in R_CHARACTERS:
            return R_CHARACTERS[key]['name']
        elif key in SR_CHARACTERS:
            return SR_CHARACTERS[key]['name']
        elif key in SSR_CHARACTERS:
            return SSR_CHARACTERS[key]['name']
        return key.title()

    def find_similar_nikke_names(self, search_term: str) -> list:
        """Find similar NIKKE names from character data"""
        matches = set()
        search_term = search_term.lower()
        
        for chars in [R_CHARACTERS, SR_CHARACTERS, SSR_CHARACTERS]:
            for key, char in chars.items():
                if search_term in key.lower() or search_term in char['name'].lower():
                    matches.add(char['name'])
                name_parts = char['name'].lower().split()
                if any(search_term in part for part in name_parts):
                    matches.add(char['name'])
        
        if not matches:
            all_names = []
            for chars in [R_CHARACTERS, SR_CHARACTERS, SSR_CHARACTERS]:
                for char in chars.values():
                    all_names.append(char['name'])
            fuzzy_matches = get_close_matches(search_term, all_names, n=3, cutoff=0.4)
            matches.update(fuzzy_matches)
        
        return list(matches)

    async def add_nikke_to_inventory(self, user_id: str, nikke_name: str, nikke_data: dict):
        inventory = self.get_user_inventory(user_id)
        nikke_key = nikke_name.lower()
        
        if nikke_key in inventory:
            current_lb = inventory[nikke_key]["limit_break"]
            max_lb = self.max_limit_breaks[nikke_data["rarity"]]
            
            max_allowed = max_lb + 7 if nikke_data["rarity"] == "SSR" else max_lb
            
            if current_lb < max_allowed:
                inventory[nikke_key]["limit_break"] += 1
        else:
            inventory[nikke_key] = {
                "rarity": nikke_data["rarity"],
                "limit_break": 0,
                "level": 1
            }
        
        self.save_inventory_data()

    @app_commands.command(name="nikke", description="View your NIKKE collection")
    async def nikke(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        inventory = self.get_user_inventory(user_id)
        
        molds_cog = self.bot.get_cog('Molds')
        if molds_cog:
            molds_display = molds_cog.get_molds_display(user_id)
            embed_description = f"**Molds:**\n{molds_display}\n\n**Collection:**"
        else:
            embed_description = "**Collection:**"

        nikkes = []
        for name, data in inventory.items():
            nikkes.append({
                "name": name,
                **data
            })
            
        nikkes.sort(key=lambda x: (
            -{"SSR": 2, "SR": 1, "R": 0}[x["rarity"]],
            -x["limit_break"],
            x["name"]
        ))
        
        await self.show_nikke_page(interaction, 0, nikkes)

    def sort_nikkes(self, nikkes: List[dict], sort_by: str = "default") -> List[dict]:
        if sort_by == "default":
            return sorted(nikkes, key=lambda x: (
                -{"SSR": 2, "SR": 1, "R": 0}[x["rarity"]],
                -x["limit_break"],
                x["name"]
            ))
        elif sort_by == "level":
            return sorted(nikkes, key=lambda x: (
                -x["level"],
                -{"SSR": 2, "SR": 1, "R": 0}[x["rarity"]],
                x["name"]
            ))
        elif sort_by == "limit break":
            return sorted(nikkes, key=lambda x: (
                -x["limit_break"],
                -{"SSR": 2, "SR": 1, "R": 0}[x["rarity"]],
                x["name"]
            ))
        elif sort_by == "rarity":
            return sorted(nikkes, key=lambda x: (
                -{"SSR": 2, "SR": 1, "R": 0}[x["rarity"]],
                x["name"]
            ))
        return nikkes

    async def show_nikke_page(self, interaction: discord.Interaction, page: int, nikkes: List[dict] = None, edit: bool = False, sort_by: str = "default"):
        if nikkes is None:
            inventory = self.get_user_inventory(str(interaction.user.id))
            nikkes = [{"name": k, **v} for k, v in inventory.items()]
        
        sorted_nikkes = self.sort_nikkes(nikkes, sort_by)
        
        start_idx = page * ITEMS_PER_PAGE
        page_nikkes = sorted_nikkes[start_idx:start_idx + ITEMS_PER_PAGE]

        embed = discord.Embed(
            title=f"{interaction.user.name}'s NIKKE Collection",
            description=f"**Sort by:** {sort_by.title()}\n\n**Collection:**",
            color=0x00b0f4
        )

        for nikke in page_nikkes:
            max_level = self.get_max_level(nikke["rarity"], nikke["limit_break"])
            rarity_emoji = EMOJI_MAPPING[nikke["rarity"]]
            proper_name = self.get_proper_nikke_name(nikke["name"])
            lb_display = self.format_limit_break(nikke["rarity"], nikke["limit_break"])
            
            embed.add_field(
                name=f"{proper_name} {rarity_emoji}",
                value=f"Level: {nikke['level']}/{max_level}\n{lb_display}",
                inline=False
            )

        embed.set_footer(text=f"Page {page + 1}/{(len(nikkes)-1)//ITEMS_PER_PAGE + 1} • Use /mynikke <name> for details")

        view = NikkePageView(self, interaction.user.id, sorted_nikkes, page, sort_by)
        
        if edit:
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            await interaction.response.send_message(embed=embed, view=view)

    class NikkeDetailsView(View):
        def __init__(self, cog, nikke_data: dict):
            super().__init__(timeout=300)
            self.cog = cog
            self.nikke_data = nikke_data

    @app_commands.command(name="mynikke", description="View details of a specific NIKKE you own")
    async def mynikke(self, interaction: discord.Interaction, name: str):
        user_id = str(interaction.user.id)
        inventory = self.get_user_inventory(user_id)
        name = name.lower()
        
        similar_names = self.find_similar_nikke_names(name)
        
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
        max_level = self.get_max_level(inventory_data["rarity"], inventory_data["limit_break"])
        lb_display = self.format_limit_break(inventory_data["rarity"], inventory_data["limit_break"])

        embed = discord.Embed(
            title=f"NIKKE Details: {nikke_data['name']}",
            color=0x00b0f4
        )
        
        embed.add_field(
            name="Level", 
            value=f"{inventory_data['level']}/{max_level}", 
            inline=True
        )
        embed.add_field(
            name="Limit Break", 
            value=lb_display if lb_display else "N/A", 
            inline=True
        )
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        
        embed.add_field(
            name="Rarity", 
            value=f"{EMOJI_MAPPING[nikke_data['rarity']]} {nikke_data['rarity']}", 
            inline=True
        )
        embed.add_field(
            name="Manufacturer", 
            value=f"{EMOJI_MAPPING[nikke_data['manufacturer']]} {nikke_data['manufacturer']}", 
            inline=True
        )
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        
        embed.add_field(
            name="Class", 
            value=f"{EMOJI_MAPPING[nikke_data['class']]} {nikke_data['class']}", 
            inline=True
        )
        embed.add_field(
            name="Weapon", 
            value=f"{EMOJI_MAPPING[nikke_data['weapon']]} {nikke_data['weapon']}", 
            inline=True
        )
        embed.add_field(name="\u200b", value="\u200b", inline=True)

        embed.add_field(
            name="Element", 
            value=f"{EMOJI_MAPPING[nikke_data['element']]} {nikke_data['element']}", 
            inline=True
        )
        embed.add_field(
            name="Burst Type", 
            value=f"{EMOJI_MAPPING[nikke_data['burst']]} Burst {nikke_data['burst']}", 
            inline=True
        )
        embed.add_field(name="\u200b", value="\u200b", inline=True)

        embed.set_thumbnail(url=nikke_data['icon_url'])
        
        view = self.NikkeDetailsView(self, {
            "name": nikke_data["name"],
            "level": inventory_data["level"],
            "max_level": max_level,
            "rarity": nikke_data["rarity"]
        })
        await interaction.response.send_message(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Inventory(bot))
