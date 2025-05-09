import json
import os
from discord.ext import commands, tasks
import datetime

class Manager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_check = None
        self.check_files.start()
        
    def cog_unload(self):
        self.check_files.cancel()

    @tasks.loop(minutes=30)
    async def check_files(self):
        try:
            await self.sanitize_currency_file()
            await self.sanitize_inventory_file()
            await self.sanitize_outpost_file()
            print(f"[{datetime.datetime.now()}] Data files sanitized successfully.")
        except Exception as e:
            print(f"Error during file sanitization: {e}")

    async def sanitize_currency_file(self):
        currency_file = 'data/currency.json'
        if not os.path.exists(currency_file):
            return
            
        with open(currency_file, 'r') as f:
            data = json.load(f)
            
        modified = False
        for user_id, currency in data.get("users", {}).items():
            integer_fields = [
                "credits", "gems", "social_points", "recruit_voucher", 
                "advanced_voucher", "body_labels", "silver_tickets", 
                "gold_tickets", "battle_data", "core_dust"
            ]
            
            for field in integer_fields:
                if field in currency:
                    old_value = currency[field]
                    new_value = int(float(currency[field]))
                    if old_value != new_value:
                        currency[field] = new_value
                        modified = True
        
        if modified:
            with open(currency_file, 'w') as f:
                json.dump(data, f, indent=4)
            
            currency_cog = self.bot.get_cog('Currency')
            if currency_cog:
                currency_cog.data = data
                currency_cog.save_currency_data()

    async def sanitize_inventory_file(self):
        inventory_file = 'data/inventory.json'
        if not os.path.exists(inventory_file):
            return
            
        with open(inventory_file, 'r') as f:
            data = json.load(f)
            
        modified = False
        for user_id, inventory in data.get("users", {}).items():
            for nikke, stats in inventory.items():
                if "level" in stats:
                    old_level = stats["level"]
                    new_level = int(float(stats["level"]))
                    if old_level != new_level:
                        stats["level"] = new_level
                        modified = True
                        
                if "limit_break" in stats:
                    old_lb = stats["limit_break"]
                    new_lb = int(float(stats["limit_break"]))
                    if old_lb != new_lb:
                        stats["limit_break"] = new_lb
                        modified = True
        
        if modified:
            with open(inventory_file, 'w') as f:
                json.dump(data, f, indent=4)

    async def sanitize_outpost_file(self):
        outpost_file = 'data/outpost.json'
        if not os.path.exists(outpost_file):
            return
            
        with open(outpost_file, 'r') as f:
            data = json.load(f)
            
        modified = False
        for user_id, outpost in data.get("users", {}).items():
            integer_fields = ["level", "progress", "wipe_attempts"]
            float_fields = ["last_claim", "last_wipe", "last_progress"]
            
            for field in integer_fields:
                if field in outpost:
                    old_value = outpost[field]
                    new_value = int(float(outpost[field]))
                    if old_value != new_value:
                        outpost[field] = new_value
                        modified = True
        
        if modified:
            with open(outpost_file, 'w') as f:
                json.dump(data, f, indent=4)

    @check_files.before_loop
    async def before_check_files(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Manager(bot))
