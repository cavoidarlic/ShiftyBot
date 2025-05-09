try:
    import discord
    from discord.ext import commands, tasks
    from discord import Intents
    import random
    from colorama import init, Fore, Style
    import datetime
    from dotenv import load_dotenv
    import os
    import json
    import pathlib
    from data.nikke_r import R_CHARACTERS
    from data.nikke_sr import SR_CHARACTERS
    from data.nikke_ssr import SSR_CHARACTERS
    from difflib import get_close_matches
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please ensure you're using Python 3.11 and have run: pip install -r requirements.txt")
    exit(1)

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

init()  # Initialize colorama

SHIFTY_ASCII = r"""
   _____ _     _  __ _         ____        _   
  / ____| |   (_)/ _| |       |  _ \      | |  
 | (___ | |__  _| |_| |_ _   _| |_) | ___ | |_ 
  \___ \| '_ \| |  _| __| | | |  _ < / _ \| __|
  ____) | | | | | | | |_| |_| | |_) | (_) | |_ 
 |_____/|_| |_|_|_|  \__|\__, |____/ \___/ \__|
                          __/ |                 
                         |___/                  
"""

intents = Intents.default()
intents.message_content = True  # This is a privileged intent, needs to be enabled in Discord Developer Portal

class ShiftyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None,  # Disable default help command
            activity=discord.Activity(type=discord.ActivityType.listening, name="Starting up...")
        )
        self.status_index = 0
        self.status_list = [
            (discord.ActivityType.listening, "Your Commands"),
            (discord.ActivityType.playing, "Memory Of Goddess (MOG)"),
            (discord.ActivityType.watching, "Ark Rangers"),
            (discord.ActivityType.listening, "I'M NOT SYUEN!"),
            (discord.ActivityType.listening, "/help"),
            (discord.ActivityType.listening, "I FEEL SO ALIVE")
        ]

    async def setup_hook(self):
        # Ensure data directory exists
        data_dir = pathlib.Path('data')
        data_dir.mkdir(exist_ok=True)

        # Ensure inventory.json exists
        inventory_file = data_dir / 'inventory.json'
        if not inventory_file.exists():
            with open(inventory_file, 'w') as f:
                json.dump({"users": {}}, f, indent=4)

        print(Fore.CYAN + "[STATUS] Setting up extensions..." + Style.RESET_ALL)
        
        # Load all cogs
        await self.load_extension('cogs.currency')
        await self.load_extension('cogs.gacha')
        await self.load_extension('cogs.inventory')  # Add inventory cog
        await self.load_extension('cogs.molds')  # Add molds cog
        await self.load_extension('cogs.leveling')  # Add leveling cog
        await self.load_extension('cogs.outpost')  # Add outpost cog
        await self.load_extension('cogs.manager')  # Add manager cog
        
        print(Fore.CYAN + "[STATUS] Syncing slash commands..." + Style.RESET_ALL)
        await self.tree.sync()
        print(Fore.CYAN + "[STATUS] Slash commands synced successfully!" + Style.RESET_ALL)

        # Start status rotation after bot is ready
        self.rotate_status.start()

    @tasks.loop(minutes=5)  # Change status every 5 minutes
    async def rotate_status(self):
        current = self.status_list[self.status_index]
        activity = discord.Activity(type=current[0], name=current[1])
        try:
            await self.change_presence(activity=activity)
            self.status_index = (self.status_index + 1) % len(self.status_list)
        except Exception as e:
            print(f"Error changing presence: {e}")

    @rotate_status.before_loop
    async def before_rotate_status(self):
        await self.wait_until_ready()  # Wait until bot is ready before starting the task

    async def on_ready(self):
        # Start the status rotation task
        if not self.rotate_status.is_running():
            self.rotate_status.start()

        print(Fore.CYAN + SHIFTY_ASCII + Style.RESET_ALL)
        print(Fore.CYAN + f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Initializing systems..." + Style.RESET_ALL)
        print(Fore.CYAN + f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Logged in as {self.user.name}" + Style.RESET_ALL)
        print(Fore.CYAN + f"[STATUS] Message Content Intent: {'Enabled' if intents.message_content else 'Disabled'}" + Style.RESET_ALL)
        print(Fore.CYAN + "[STATUS] All systems operational, Commander." + Style.RESET_ALL)

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            # Ignore command not found errors silently
            return
        # Log other errors
        print(f"Error: {error}")

bot = ShiftyBot()

CITY_MAPPINGS = {}  # Remove since it's no longer needed

RARITY_COLORS = {
    "R": 0x00b0f4,  # Light blue
    "SR": 0x9400d3,  # Purple
    "SSR": 0xffd700  # Gold
}

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

def find_similar_names(search_term, all_characters):
    """Find similar character names using partial matching and fuzzy matching"""
    matches = set()  # Use set to avoid duplicates
    
    # Convert search term to lowercase
    search_term = search_term.lower()
    
    # Collect all character names (both display names and dictionary keys)
    for chars in [R_CHARACTERS, SR_CHARACTERS, SSR_CHARACTERS]:
        for key, char in chars.items():
            # Check if search term is in the key or display name
            if search_term in key.lower() or search_term in char['name'].lower():
                matches.add(char['name'])
            # Also check each word in the name separately
            name_parts = char['name'].lower().split()
            if any(search_term in part for part in name_parts):
                matches.add(char['name'])
    
    # If no matches found, try fuzzy matching
    if not matches:
        all_names = []
        for chars in [R_CHARACTERS, SR_CHARACTERS, SSR_CHARACTERS]:
            for char in chars.values():
                all_names.append(char['name'])
        fuzzy_matches = get_close_matches(search_term, all_names, n=3, cutoff=0.4)  # Lowered cutoff for more matches
        matches.update(fuzzy_matches)
    
    return list(matches)

@bot.tree.command(name="info", description="Search for NIKKE character information")
async def info(interaction: discord.Interaction, name: str):
    name = name.lower().strip()
    
    # Search in all rarity pools
    character = None
    if name in R_CHARACTERS:
        character = R_CHARACTERS[name]
    elif name in SR_CHARACTERS:
        character = SR_CHARACTERS[name]
    elif name in SSR_CHARACTERS:
        character = SSR_CHARACTERS[name]
    
    if not character:
        # Find similar names
        similar_names = find_similar_names(name, [R_CHARACTERS, SR_CHARACTERS, SSR_CHARACTERS])
        if similar_names:
            suggestion_list = "\n".join([f"{i+1}. {name}" for i, name in enumerate(similar_names)])
            await interaction.response.send_message(
                f"Commander, I couldn't find an exact match. Were you trying to search for...\n{suggestion_list}"
            )
            return
        await interaction.response.send_message(
            "Commander, I couldn't find that NIKKE in my database. Please check the name and try again."
        )
        return

    try:
        embed = discord.Embed(
            title=f"Nikke Profile: {character['name']}",
            color=RARITY_COLORS[character['rarity']],
            timestamp=interaction.created_at
        )
        
        embed.add_field(
            name="Rarity", 
            value=f"{EMOJI_MAPPING[character['rarity']]} {character['rarity']}", 
            inline=True
        )
        embed.add_field(
            name="Manufacturer", 
            value=f"{EMOJI_MAPPING[character['manufacturer']]} {character['manufacturer']}", 
            inline=True
        )
        embed.add_field(
            name="Class", 
            value=f"{EMOJI_MAPPING[character['class']]} {character['class']}", 
            inline=True
        )
        embed.add_field(
            name="Weapon", 
            value=f"{EMOJI_MAPPING[character['weapon']]} {character['weapon']}", 
            inline=True
        )
        embed.add_field(
            name="Element", 
            value=f"{EMOJI_MAPPING[character['element']]} {character['element']}", 
            inline=True
        )
        embed.add_field(
            name="Burst Type", 
            value=f"{EMOJI_MAPPING[character['burst']]} Burst {character['burst']}", 
            inline=True
        )
        
        embed.set_thumbnail(url=character['icon_url'])
        embed.set_footer(text=f"Requested by Commander {interaction.user.name}")
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        print(f"Error creating embed: {e}")  # Debug print
        await interaction.response.send_message("Error creating character profile. Please try again.")

if TOKEN is None:
    print(Fore.RED + "Error: DISCORD_TOKEN not found in .env file" + Style.RESET_ALL)
    exit(1)
    
bot.run(TOKEN)
