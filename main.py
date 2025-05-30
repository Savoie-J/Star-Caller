import os
import discord
import asyncio
import datetime
import json
import pytz
import time
import requests
from datetime import timezone
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("token")
DATA_FILE = "star_caller_data.json"
api = os.getenv("api")

AUTHORIZED_SERVER_IDS = [
    1274620800896339968,  #development
    282907227017183232,   #star-find
]

class StarCaller(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="", 
            intents=discord.Intents.all(),
        )

    async def setup_hook(self):
        self.auto_clear_restricted.start()
        await self.tree.sync()

    async def on_ready(self):
        await self.change_presence(
            activity=discord.CustomActivity(name="invoke /call to spot a star!")
        )

    async def close(self):
        if hasattr(self, 'message_queue'):
            await self.message_queue.stop()
        await super().close()

    def cog_unload(self):
        self.auto_clear_restricted.cancel()

    @tasks.loop(minutes=15)
    async def auto_clear_restricted(self):
        try:
            class DummyResponse:
                async def send_message(self, content, ephemeral=False):
                    return None
                
                async def defer(self):
                    pass

            class DummyFollowup:
                async def send(self, content):
                    class DummyMessage:
                        async def edit(self, content):
                            pass
                    return DummyMessage()

            class DummyInteraction:
                def __init__(self, client):
                    self.client = client
                    self.response = DummyResponse()
                    self.followup = DummyFollowup()

            dummy_interaction = DummyInteraction(self)

            command = self.tree.get_command("clear-restricted")
            if command:
                await command.callback(dummy_interaction)
                #print(f"[{datetime.datetime.now(pytz.UTC)}] Invoked clear-restricted.")
            else:
                print("Clear-restricted command not found")

        except Exception as e:
            print(f"Error in auto_clear_restricted: {str(e)}")
            import traceback
            traceback.print_exc()

    @auto_clear_restricted.before_loop
    async def before_auto_clear(self):
        await self.wait_until_ready()

client = StarCaller()
client.clear_lock = asyncio.Lock()

class MessageQueue:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.task = None
        self.running = True

    async def process_queue(self):
        while self.running:
            try:
                message, content = await self.queue.get()
                await message.edit(content=content)
                self.queue.task_done()
                await asyncio.sleep(6)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error processing message edit: {e}")

    def start(self):
        self.task = asyncio.create_task(self.process_queue())

    async def stop(self):
        self.running = False
        if self.task:
            await self.queue.join()
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

def load_table_data():
    try:
        with open(DATA_FILE, 'r') as f:
            loaded_data = json.load(f)
        return loaded_data
    except FileNotFoundError:
        return {
            "is_locked": False, 
            "entries": [],      
            "message_id": None, 
            "channel_id": None,  
            "chunk_message_ids": []  
        }

def save_table_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f)

def check_authorized_server():
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.guild_id not in AUTHORIZED_SERVER_IDS:
            await interaction.response.send_message(
                "This command can only be used in authorized servers.", 
                ephemeral=True
            )
            return False
        return True
    return app_commands.check(predicate)

def is_valid_size(size_value):
        return size_value.startswith('s') and size_value[1:].isdigit()

def is_valid_game_time(time_str: str) -> bool:
    try:
        if len(time_str.split(':')) != 2:
            return False
        hours, minutes = map(int, time_str.split(':'))
        return 0 <= hours <= 23 and 0 <= minutes <= 59
    except (ValueError, AttributeError):
        return False

def is_valid_game_time_full(time_str: str) -> bool:
    try:
        datetime.datetime.fromisoformat(time_str)
        return True
    except (ValueError, TypeError):
        return False

def get_region_url(region):
    region_urls = {
        "Anachronia": "https://runescape.wiki/w/Shooting_Star#Anachronia",
        "Asgarnia": "https://runescape.wiki/w/Shooting_Star#Asgarnia",
        "Ashdale": "https://runescape.wiki/w/Shooting_Star#Ashdale",
        "Crandor/Karamja": "https://runescape.wiki/w/Shooting_Star#Crandor_or_Karamja",
        "Daemonheim": "https://runescape.wiki/w/Shooting_Star#The_Daemonheim_peninsula",
        "Feldip Hills": "https://runescape.wiki/w/Shooting_Star#The_Feldip_Hills",
        "Frem/Lunar": "https://runescape.wiki/w/Shooting_Star#Fremennik_lands_or_Lunar_Isle",
        "Kandarin": "https://runescape.wiki/w/Shooting_Star#Kandarin",
        "Kharidian Desert": "https://runescape.wiki/w/Shooting_Star#The_Kharidian_Desert",
        "Lost Grove": "https://runescape.wiki/w/Shooting_Star#The_Lost_Grove",
        "Menaphos": "https://runescape.wiki/w/Shooting_Star#Menaphos",
        "Misthalin": "https://runescape.wiki/w/Shooting_Star#Misthalin",
        "Morytania/Mos": "https://runescape.wiki/w/Shooting_Star#Morytania_or_Mos_Le'Harmless",
        "Pisc/Gnome/Tir": "https://runescape.wiki/w/Shooting_Star#Piscatoris,_the_Gnome_Stronghold_or_Tirannwn",
        "Tuska": "https://runescape.wiki/w/Shooting_Star#Tuska",
        "Wilderness": "https://runescape.wiki/w/Shooting_Star#The_Wilderness",
    }
    return region_urls.get(region, f"https://runescape.wiki/w/Shooting_Star#Locations")

@client.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.errors.CheckFailure):
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "You are not authorized to use this command.", 
                ephemeral=True
            )
    else:
        print(f"Slash command error occurred: {str(error)}")
        if not interaction.response.is_done():
            await interaction.response.send_message(
                f"An error occurred while processing the command: \n{error}", 
                ephemeral=True
            )

@client.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    print(f"Message command error occurred: {str(error)}")

def make_post_request(url, data):
    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        #print(f"Error making POST request: {e}")
        if response := getattr(e, 'response', None):
            print(f"Response status code: {response.status_code}")
            print(f"Response body: {response.text}")
        return None

table_data = load_table_data()

world_data = [
    (1, "Members"),
    (2, "Members"),
    (3, "Free-to-play"),
    (4, "Members"),
    (5, "Members"),
    (6, "Members"),
    (7, "Free-to-play"),
    (8, "Free-to-play"),
    (9, "Members"),
    (10, "Members"),
    (11, "Free-to-play"),
    (12, "Members"),
    (14, "Members"),
    (15, "Members"),
    (16, "Members"),
    (17, "Free-to-play"),
    (18, "Members"),
    (19, "Free-to-play"),
    (20, "Free-to-play"),
    (21, "Members"),
    (22, "Members"),
    (23, "Members"),
    (24, "Members"),
    (25, "Members"),
    (26, "Members"),
    (27, "Members"),
    (28, "Members"),
    (29, "Free-to-play"),
    (30, "Members", "Special"),
    (31, "Members"),
    (32, "Members"),
    (33, "Free-to-play"),
    (34, "Free-to-play"),
    (35, "Members"),
    (36, "Members"),
    (37, "Members"),
    (38, "Free-to-play"),
    (39, "Members"),
    (40, "Members"),
    (41, "Free-to-play"),
    (42, "Members"),
    (43, "Free-to-play"),
    (44, "Members"),
    (45, "Members"),
    (46, "Members"),
    (47, "Members", "Local"),
    (48, "Members", "Special"),
    (49, "Members"),
    (50, "Members"),
    (51, "Members"),
    (52, "Members", "Special"),
    (53, "Members"),
    (54, "Members"),
    (55, "Free-to-play", "Local"),
    (56, "Members"),
    (57, "Free-to-play"),
    (58, "Members"),
    (59, "Members"),
    (60, "Members"),
    (61, "Free-to-play"),
    (62, "Members"),
    (63, "Members"),
    (64, "Members"),
    (65, "Members"),
    (66, "Members"),
    (67, "Members"),
    (68, "Members"),
    (69, "Members"),
    (70, "Members"),
    (71, "Members"),
    (72, "Members"),
    (73, "Members"),
    (74, "Members"),
    (75, "Members", "Local"),
    (76, "Members"),
    (77, "Members"),
    (78, "Members"),
    (79, "Members"),
    (80, "Free-to-play"),
    (81, "Free-to-play"),
    (82, "Members"),
    (83, "Members"),
    (84, "Members"),
    (85, "Members"),
    (86, "Members", "Special"),
    (87, "Members"),
    (88, "Members"),
    (89, "Members"),
    (91, "Members"),
    (92, "Members"),
    (94, "Free-to-play", "Local"),
    (96, "Members"),
    (97, "Members"),
    (98, "Members"),
    (99, "Members"),
    (100, "Members"),
    (101, "Members", "Local"),
    (102, "Members", "Local"),
    (103, "Members"),
    (104, "Members"),
    (105, "Members"),
    (106, "Members"),
    (108, "Free-to-play"),
    (114, "Members", "Special"),
    (115, "Members"),
    (116, "Members"),
    (117, "Members"),
    (118, "Members", "Local"),
    (119, "Members"),
    (120, "Free-to-play"),
    (121, "Members", "Local"),
    (122, "Free-to-play", "Local"),
    (123, "Members"),
    (124, "Members"),
    (134, "Members"),
    (135, "Free-to-play"),
    (136, "Free-to-play"),
    (137, "Members"),
    (138, "Members"),
    (139, "Members"),
    (140, "Members"),
    (141, "Free-to-play"),
    (210, "Free-to-play"),
    (215, "Free-to-play"),
    (225, "Free-to-play"),
    (236, "Free-to-play"),
    (239, "Free-to-play"),
    (245, "Free-to-play"),
    (249, "Free-to-play"),
    (250, "Free-to-play"),
    (251, "Free-to-play", "Local"),
    (252, "Members"),
    (255, "Free-to-play"),
    (256, "Free-to-play"),
    (257, "Members"),
    (258, "Members"),
    (259, "Members"),
]

all_worlds = [world for world, *_ in world_data]
members_worlds = [world for world, status, *_ in world_data if status == "Members"]
free_to_play_worlds = [world for world, status, *_ in world_data if status == "Free-to-play"]
special_worlds = [world for world, status, *rest in world_data if len(rest) > 0 and rest[0] == "Special"]
local_worlds = [world for world, status, *rest in world_data if len(rest) > 0 and rest[0] == "Local"]

@client.tree.command(name="lock", description="Lock the star call table to prevent modifications.")
@app_commands.default_permissions(manage_events=True)
@check_authorized_server()
async def lock(interaction: discord.Interaction):
    current_table_data = load_table_data()

    if not current_table_data.get("message_id"):
        await interaction.response.send_message("No table exists to lock.", ephemeral=True)
        return
    
    if current_table_data["is_locked"]:
        await interaction.response.send_message("Table is already locked.", ephemeral=True)
        return
    
    table_data["is_locked"] = True
    save_table_data(table_data)

    await interaction.response.send_message("Star call table has been locked.", ephemeral=True)

@client.tree.command(name="unlock", description="Unlock the star call table to allow modifications.")
@app_commands.default_permissions(manage_events=True)
@check_authorized_server()
async def unlock(interaction: discord.Interaction):
    current_table_data = load_table_data()

    if not current_table_data.get("message_id"):
        await interaction.response.send_message("No table exists to unlock.", ephemeral=True)
        return
    
    if not current_table_data["is_locked"]:
        await interaction.response.send_message("Table is already unlocked.", ephemeral=True)
        return
    
    table_data["is_locked"] = False
    save_table_data(table_data)

    await interaction.response.send_message("Star call table has been unlocked.", ephemeral=True)

@client.tree.command(name="clear-all", description="Clear all entries in the star call table.")
@app_commands.default_permissions(manage_events=True)
@check_authorized_server()
async def clear(interaction: discord.Interaction):
    if not table_data.get("chunk_message_ids"):
        await interaction.response.send_message("No table exists to clear.", ephemeral=True)
        return
    
    if table_data["is_locked"] and not interaction.user.guild_permissions.manage_events:
        await interaction.response.send_message("Table is locked. Cannot clear entries.", ephemeral=True)
        return

    await interaction.response.defer()
    progress_message = await interaction.followup.send(
        "Starting table clear..."
    )

    table_data["entries"] = [
        {"world": world, "region": "", "size": "", "game_time": "", "game_time_full": ""} 
        for world in all_worlds
    ]

    table_rows = []
    for entry in table_data["entries"]:
        world_name = entry["world"]
        if entry["world"] in special_worlds:
            world_name = f"\u001b[36m{world_name}\u001b[0m"
        elif entry["world"] in local_worlds and entry["world"] in free_to_play_worlds:
            world_name = f"\u001b[32m{world_name}\u001b[0m"
        elif entry["world"] in local_worlds:
            world_name = f"\u001b[30m{world_name}\u001b[0m"
        elif entry["world"] in free_to_play_worlds:
            world_name = f"\u001b[33m{world_name}\u001b[0m" 
        else:
            world_name = f"\u001b[37m{world_name}\u001b[0m"
        
        table_rows.append(
            f"{world_name:<1} {entry['region']:<17} {entry['size']:<4} {entry['game_time']:<4}"
        )

    chunk_size = 32
    chunks = [table_rows[i:i + chunk_size] for i in range(0, len(table_rows), chunk_size)]
    channel = interaction.client.get_channel(table_data["channel_id"])
    total_chunks = len(chunks)

    async def process_chunk(chunk_index: int, chunk: list) -> None:
        max_retries = 3
        base_delay = 12.0
        
        for attempt in range(max_retries):
            try:
                message_id = table_data["chunk_message_ids"][chunk_index]
                message = await channel.fetch_message(message_id)
                
                updated_chunk = "```ansi\n" + "\n".join(chunk) + "```"
                await message.edit(content=updated_chunk)
                
                return
                
            except discord.HTTPException as e:
                if e.code == 429:
                    retry_after = float(e.response.headers.get('Retry-After', 5))
                    print(f"Rate limited on chunk {chunk_index}, waiting {retry_after} seconds")
                    await asyncio.sleep(retry_after + 1) 
                    base_delay = max(base_delay, retry_after + 2)
                else:
                    print(f"Error editing chunk {chunk_index} (attempt {attempt + 1}): {e}")
                    await asyncio.sleep(base_delay)
                    
            except Exception as e:
                print(f"Unexpected error on chunk {chunk_index} (attempt {attempt + 1}): {e}")
                await asyncio.sleep(base_delay)
        
        print(f"Failed to process chunk {chunk_index} after {max_retries} attempts")

    last_progress_update = time.time()

    for i, chunk in enumerate(chunks):
        await process_chunk(i, chunk)
        
        current_time = time.time()
        if current_time - last_progress_update >= 5:
            progress = f"Clearing table... ({i + 1}/{total_chunks} chunks)"
            try:
                await progress_message.edit(content=progress)
                last_progress_update = current_time
            except discord.HTTPException:
                pass

        await asyncio.sleep(12.0) 

    save_table_data(table_data)
    
    try:
        await progress_message.edit(content="Table cleared successfully!")
    except discord.HTTPException:
        pass

@client.tree.command(name="clear-old", description="Clear expired entries in the star call table.")
@app_commands.default_permissions(manage_events=True)
@check_authorized_server()
async def clear_old(interaction: discord.Interaction):
    if not table_data.get("chunk_message_ids"):
        await interaction.response.send_message("No table exists to clear.", ephemeral=True)
        return
    
    if table_data["is_locked"] and not interaction.user.guild_permissions.manage_events:
        await interaction.response.send_message("Table is locked. Cannot clear entries.", ephemeral=True)
        return

    await interaction.response.defer()
    progress_message = await interaction.followup.send(
        "Starting table clear of expired entries..."
    )

    current_time = datetime.datetime.now(pytz.UTC)
    
    new_entries = []
    for entry in table_data["entries"]:
        if entry["game_time_full"]:
            try:
                entry_time = datetime.datetime.fromisoformat(entry["game_time_full"])
                if entry_time > current_time:
                    new_entries.append(entry)
                    continue
            except ValueError:
                pass
        
        new_entries.append({
            "world": entry["world"],
            "region": "",
            "size": "",
            "game_time": "",
            "game_time_full": ""
        })

    table_data["entries"] = new_entries

    table_rows = []
    for entry in table_data["entries"]:
        world_name = entry["world"]
        if entry["world"] in special_worlds:
            world_name = f"\u001b[36m{world_name}\u001b[0m"
        elif entry["world"] in local_worlds and entry["world"] in free_to_play_worlds:
            world_name = f"\u001b[32m{world_name}\u001b[0m"
        elif entry["world"] in local_worlds:
            world_name = f"\u001b[30m{world_name}\u001b[0m"
        elif entry["world"] in free_to_play_worlds:
            world_name = f"\u001b[33m{world_name}\u001b[0m" 
        else:
            world_name = f"\u001b[37m{world_name}\u001b[0m"
        
        table_rows.append(
            f"{world_name:<1} {entry['region']:<17} {entry['size']:<4} {entry['game_time']:<4}"
        )

    chunk_size = 32
    chunks = [table_rows[i:i + chunk_size] for i in range(0, len(table_rows), chunk_size)]
    channel = interaction.client.get_channel(table_data["channel_id"])
    total_chunks = len(chunks)

    async def process_chunk(chunk_index: int, chunk: list) -> None:
        max_retries = 3
        base_delay = 12.0
        
        for attempt in range(max_retries):
            try:
                message_id = table_data["chunk_message_ids"][chunk_index]
                message = await channel.fetch_message(message_id)
                
                updated_chunk = "```ansi\n" + "\n".join(chunk) + "```"
                await message.edit(content=updated_chunk)
                
                return
                
            except discord.HTTPException as e:
                if e.code == 429:
                    retry_after = float(e.response.headers.get('Retry-After', 5))
                    print(f"Rate limited on chunk {chunk_index}, waiting {retry_after} seconds")
                    await asyncio.sleep(retry_after + 1) 
                    base_delay = max(base_delay, retry_after + 2)
                else:
                    print(f"Error editing chunk {chunk_index} (attempt {attempt + 1}): {e}")
                    await asyncio.sleep(base_delay)
                    
            except Exception as e:
                print(f"Unexpected error on chunk {chunk_index} (attempt {attempt + 1}): {e}")
                await asyncio.sleep(base_delay)
        
        print(f"Failed to process chunk {chunk_index} after {max_retries} attempts")

    last_progress_update = time.time()

    for i, chunk in enumerate(chunks):
        await process_chunk(i, chunk)
        
        current_time = time.time()
        if current_time - last_progress_update >= 5:
            progress = f"Clearing expired entries... ({i + 1}/{total_chunks} chunks)"
            try:
                await progress_message.edit(content=progress)
                last_progress_update = current_time
            except discord.HTTPException:
                pass

        await asyncio.sleep(12.0) 

    save_table_data(table_data)
    
    try:
        await progress_message.edit(content="Expired entries cleared successfully!")
    except discord.HTTPException:
        pass

@client.tree.command(name="clear-restricted", description="Clear entries that expired over 30 minutes ago.")
@check_authorized_server()
async def clear_restricted(interaction: discord.Interaction):
    is_real_interaction = hasattr(interaction.response, 'is_done')
    
    if is_real_interaction and not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)
    
    async with interaction.client.clear_lock:
        if not hasattr(clear_restricted, "last_run"):
            clear_restricted.last_run = None
        
        current_time = datetime.datetime.now(pytz.UTC)
        if clear_restricted.last_run is not None:
            time_diff = (current_time - clear_restricted.last_run).total_seconds() / 60
            if time_diff < 5:
                wait_time = round(5 - time_diff)
                if is_real_interaction:
                    await interaction.followup.send(
                        f"In order to combat abuse, this command can only be used once every 5 minutes. Please wait `{wait_time}` minutes before invoking it again."
                    )
                return

        if not table_data.get("chunk_message_ids"):
            if is_real_interaction:
                await interaction.followup.send("No table exists to clear.")
            return

        if table_data["is_locked"]:
            if is_real_interaction:
                await interaction.followup.send("Table is locked. Cannot clear entries.")
            return    

        if is_real_interaction:
            await interaction.followup.send("Clear-restricted has been invoked successfully.")
            progress_message = await interaction.channel.send(
                "Starting table clear of entries that expired 30 minutes ago..."
            )
        else:
            progress_message = None

        clear_restricted.last_run = current_time
        
        new_entries = []
        for entry in table_data["entries"]:
            if entry["game_time_full"]:
                try:
                    entry_time = datetime.datetime.fromisoformat(entry["game_time_full"])
                    if entry_time + datetime.timedelta(minutes=30) > current_time:
                        new_entries.append(entry)
                        continue
                except ValueError:
                    pass
            
            new_entries.append({
                "world": entry["world"],
                "region": "",
                "size": "",
                "game_time": "",
                "game_time_full": ""
            })

        table_data["entries"] = new_entries

        table_rows = []
        for entry in table_data["entries"]:
            world_name = entry["world"]
            if entry["world"] in special_worlds:
                world_name = f"\u001b[36m{world_name}\u001b[0m"
            elif entry["world"] in local_worlds and entry["world"] in free_to_play_worlds:
                world_name = f"\u001b[32m{world_name}\u001b[0m"
            elif entry["world"] in local_worlds:
                world_name = f"\u001b[30m{world_name}\u001b[0m"
            elif entry["world"] in free_to_play_worlds:
                world_name = f"\u001b[33m{world_name}\u001b[0m" 
            else:
                world_name = f"\u001b[37m{world_name}\u001b[0m"
            
            table_rows.append(
                f"{world_name:<1} {entry['region']:<17} {entry['size']:<4} {entry['game_time']:<4}"
            )

        chunk_size = 32
        chunks = [table_rows[i:i + chunk_size] for i in range(0, len(table_rows), chunk_size)]
        channel = interaction.client.get_channel(table_data["channel_id"])
        total_chunks = len(chunks)

        async def process_chunk(chunk_index: int, chunk: list) -> None:
            max_retries = 3
            base_delay = 24.0
            
            for attempt in range(max_retries):
                try:
                    message_id = table_data["chunk_message_ids"][chunk_index]
                    message = await channel.fetch_message(message_id)
                    
                    updated_chunk = "```ansi\n" + "\n".join(chunk) + "```"
                    
                    await message.edit(content=updated_chunk)
                    return
                    
                except discord.RateLimited as e:
                    retry_after = e.retry_after
                    print(f"Rate limited on chunk {chunk_index}, waiting {retry_after} seconds.")
                    await asyncio.sleep(retry_after + 1)
                    continue
                    
                except discord.HTTPException as e:
                    print(f"HTTP Error on chunk {chunk_index} (attempt {attempt + 1}): {e}")
                    if e.code == 429:
                        retry_after = float(e.response.headers.get('Retry-After', base_delay))
                        print(f"Rate limited (HTTP 429) on chunk {chunk_index}, waiting {retry_after} seconds.")
                        await asyncio.sleep(retry_after + 1)
                        base_delay = max(base_delay, retry_after + 2)
                    else:
                        await asyncio.sleep(base_delay)
                        
                except Exception as e:
                    print(f"Unexpected error on chunk {chunk_index} (attempt {attempt + 1}): {str(e)}")
                    await asyncio.sleep(base_delay)
            
            print(f"Failed to process chunk {chunk_index} after {max_retries} attempts")

        last_progress_update = time.time()
        chunks_processed = 0
        total_chunks = len(chunks)
        chunk_delay = 24.0 

        for i, chunk in enumerate(chunks):
            if i > 0:
                await asyncio.sleep(chunk_delay)
            
            await process_chunk(i, chunk)
            chunks_processed += 1
            
            if is_real_interaction:
                current_time = time.time()
                if current_time - last_progress_update >= 5:
                    progress = f"Clearing expired entries... ({chunks_processed}/{total_chunks} chunks)"
                    try:
                        await progress_message.edit(content=progress)
                        last_progress_update = current_time
                    except discord.HTTPException as e:
                        print(f"Failed to update progress message: {e}")

        save_table_data(table_data)

        if is_real_interaction:
            try:
                await progress_message.edit(content=f"Entries that expired over 30 minutes ago have been cleared!")
            except discord.HTTPException as e:
                print(f"Failed to send completion message: {e}")

@client.tree.command(name="prune", description="Clear data for a specific world.")
@app_commands.describe(world="What world do you plan to prune entries for?")
@app_commands.default_permissions(manage_events=True)
@check_authorized_server()
async def prune(interaction: discord.Interaction, world: int):
    if not table_data.get("chunk_message_ids"):
        await interaction.response.send_message("No table exists to prune.", ephemeral=True)
        return
    
    if table_data["is_locked"] and not interaction.user.guild_permissions.manage_events:
        await interaction.response.send_message("Table is locked. Cannot prune entries.", ephemeral=True)
        return

    world_index = None
    for i, entry in enumerate(table_data["entries"]):
        if entry["world"] == world:
            world_index = i
            break
    
    if world_index is None:
        await interaction.response.send_message(f"World {world} not found.", ephemeral=True)
        return

    table_data["entries"][world_index] = {
        "world": world, "region": "", "size": "", "game_time": "", "game_time_full": ""
    }

    table_rows = []
    for entry in table_data["entries"]:
        world_name = entry["world"] 
        if entry["world"] in special_worlds:
            world_name = f"\u001b[36m{world_name}\u001b[0m"
        elif entry["world"] in local_worlds and entry["world"] in free_to_play_worlds:
            world_name = f"\u001b[32m{world_name}\u001b[0m"
        elif entry["world"] in local_worlds:
            world_name = f"\u001b[30m{world_name}\u001b[0m"
        elif entry["world"] in free_to_play_worlds:
            world_name = f"\u001b[33m{world_name}\u001b[0m"
        else:
            world_name = f"\u001b[37m{world_name}\u001b[0m"
        
        table_rows.append(
            f"{world_name:<1} {entry['region']:<17} {entry['size']:<4} {entry['game_time']:<4}"
        )

    chunk_size = 32
    chunks = [table_rows[i:i + chunk_size] for i in range(0, len(table_rows), chunk_size)]

    chunk_index = world_index // chunk_size
    channel = interaction.client.get_channel(table_data["channel_id"])
    message_id = table_data["chunk_message_ids"][chunk_index]
    message = await channel.fetch_message(message_id)
    
    updated_chunk = "```ansi\n" + "\n".join(chunks[chunk_index]) + "```"
    await message.edit(content=updated_chunk)

    save_table_data(table_data)

    await interaction.response.send_message(f"Pruned data for world {world}.")

@client.tree.command(name="create", description="Create a star call table.")
@app_commands.default_permissions(administrator=True)
@check_authorized_server()
async def create(interaction: discord.Interaction):
    if table_data["message_id"]:
        try:
            channel = interaction.client.get_channel(table_data["channel_id"])
            if channel:
                try:
                    existing_message = await channel.fetch_message(table_data["message_id"])
                    await channel.fetch_message(table_data["message_id"])
                    await interaction.response.send_message(
                        f"A table already exists. Click [`here`]({existing_message.jump_url}) to view it or use `/clear` to reset its data.\nIf you wish to generate a new table, delete any part of the original.", ephemeral=True
                    )
                    return
                except discord.NotFound:
                    pass
        except Exception:
            pass

    await interaction.response.defer(ephemeral=True)

    table_rows = []
    for world in all_worlds:
        world_name = world 
        if world in special_worlds:
            world_name = f"\u001b[36m{world_name}\u001b[0m"
        elif world in local_worlds and world in free_to_play_worlds:
            world_name = f"\u001b[32m{world_name}\u001b[0m"
        elif world in local_worlds:
            world_name = f"\u001b[30m{world_name}\u001b[0m"
        elif world in free_to_play_worlds:
            world_name = f"\u001b[33m{world_name}\u001b[0m" 
        else:
            world_name = f"\u001b[37m{world_name}\u001b[0m"

        table_rows.append(
            f"{world_name:<1} {'':<17} {'':<4} {'':<4}"
        )

    chunk_size = 32 
    chunks = [table_rows[i:i + chunk_size] for i in range(0, len(table_rows), chunk_size)]

    table_data["chunk_message_ids"] = []

    for i, chunk in enumerate(chunks):
        formatted_table = "\n".join([f"{row}" for row in chunk])

        try:
            table_message = await interaction.channel.send(
                content=f"```ansi\n{formatted_table}\n```"
            )

            table_data["chunk_message_ids"].append(table_message.id)

            if i == 0:
                table_data["message_id"] = table_message.id
                table_data["channel_id"] = interaction.channel.id

                if not table_data["entries"]:
                    table_data["entries"] = [
                        {"world": world, "region": "", "size": "", "game_time": "", "game_time_full": ""} 
                        for world in all_worlds
                    ]
        except Exception as e:
            await interaction.followup.send(
                f"Failed to create the table. Error: {str(e)}", 
                ephemeral=True
            )
            return
    
    save_table_data(table_data)
    
    await interaction.followup.send("Table(s) created successfully!", ephemeral=True)

@client.tree.command(name="call", description="Call-out shooting stars.")
@app_commands.describe(
    world = "What world will this star fall on?",
    region = "What's the general location of the falling star?", 
    size = "What size will the falling star be?",
    game_time = "How many minutes from now will the star fall? (Use the lower bound)",
    )
@app_commands.rename(game_time="relative-time")
@app_commands.choices(
    region=[
        app_commands.Choice(name="Anachronia", value="Anachronia"),
        app_commands.Choice(name="Asgarnia", value="Asgarnia"),
        app_commands.Choice(name="Ashdale", value="Ashdale"),
        app_commands.Choice(name="Crandor/Karamja", value="Crandor/Karamja"),
        app_commands.Choice(name="Daemonheim", value="Daemonheim"),
        app_commands.Choice(name="Feldip Hills", value="Feldip Hills"),
        app_commands.Choice(name="Fremennik/Lunar Isle", value="Frem/Lunar"),
        app_commands.Choice(name="Kandarin", value="Kandarin"),
        app_commands.Choice(name="Kharidian Desert", value="Kharidian Desert"),
        app_commands.Choice(name="Lost Grove", value="Lost Grove"),
        app_commands.Choice(name="Menaphos", value="Menaphos"),
        app_commands.Choice(name="Misthalin", value="Misthalin"),
        app_commands.Choice(name="Morytania/Mos Le'Harmless", value="Morytania/Mos"),
        app_commands.Choice(name="Piscatoris/Gnome/Tirannwn", value="Pisc/Gnome/Tir"),
        app_commands.Choice(name="Tuska", value="Tuska"),
        app_commands.Choice(name="Wilderness", value="Wilderness"),
    ],
    size=[
        app_commands.Choice(name="Small", value="sm"),
        app_commands.Choice(name="Average", value="avg"),
        app_commands.Choice(name="Big", value="big"),
        app_commands.Choice(name="1", value="s1"),
        app_commands.Choice(name="2", value="s2"),
        app_commands.Choice(name="3", value="s3"),        
        app_commands.Choice(name="4", value="s4"),
        app_commands.Choice(name="5", value="s5"),
        app_commands.Choice(name="6", value="s6"),
        app_commands.Choice(name="7", value="s7"),
        app_commands.Choice(name="8", value="s8"),
        app_commands.Choice(name="9", value="s9"),
        app_commands.Choice(name="10", value="s10"),
    ]
)
@check_authorized_server()
async def call(interaction: discord.Interaction, world: int, region: str, size: str, game_time: app_commands.Range[int, 1, 128]):
    try:
        await interaction.response.defer()
    except (discord.NotFound, discord.HTTPException) as e:
        print(f"Failed to defer interaction: {e}")
        return

    async with interaction.client.clear_lock:
        if not hasattr(interaction.client, 'message_queue'):
            interaction.client.message_queue = MessageQueue()
            interaction.client.message_queue.start()

        if not table_data.get("message_id"):
            await interaction.followup.send("No table exists. Use `/create` first.", ephemeral=True)
            return

        if table_data["is_locked"] and not interaction.user.guild_permissions.manage_events:
            await interaction.followup.send("Table is locked. Invoke `/unlock` to modify entries.", ephemeral=True)
            return

        world_index = next((i for i, entry in enumerate(table_data["entries"]) if entry["world"] == world), None)
        if world_index is None:
            await interaction.followup.send(f"World `{world}` not found.", ephemeral=True)
            return

        try:
            entry_updates = {}
            if region is not None:
                entry_updates["region"] = region
            if size is not None:
                entry_updates["size"] = size
            if game_time is not None:
                current_utc = datetime.datetime.now(pytz.UTC)
                game_end_time = current_utc + datetime.timedelta(minutes=game_time)

                entry_updates["game_time"] = game_end_time.strftime("%H:%M")
                entry_updates["game_time_full"] = game_end_time.isoformat()
                
                game_time_unix = int(game_end_time.timestamp())

            table_data["entries"][world_index].update(entry_updates)

            channel = interaction.client.get_channel(table_data["channel_id"])
            if not channel:
                await interaction.followup.send("Error: Could not find the channel.", ephemeral=True)
                return

            if datetime.datetime.now(datetime.timezone.utc) >= interaction.expires_at:
                print(f"Interaction expired for user {interaction.user.id} - command for world {world} completed silently.")
                return

            table_rows = []
            for entry in table_data["entries"]:
                world_name = entry["world"]
                if entry["world"] in special_worlds:
                    world_name = f"\u001b[36m{world_name}\u001b[0m"
                elif entry["world"] in local_worlds and entry["world"] in free_to_play_worlds:
                    world_name = f"\u001b[32m{world_name}\u001b[0m"
                elif entry["world"] in local_worlds:
                    world_name = f"\u001b[30m{world_name}\u001b[0m"
                elif entry["world"] in free_to_play_worlds:
                    world_name = f"\u001b[33m{world_name}\u001b[0m"
                else:
                    world_name = f"\u001b[37m{world_name}\u001b[0m"

                table_rows.append(
                    f"{world_name:<1} {entry['region']:<17} {entry['size']:<4} {entry['game_time']:<4}"
                )

            chunk_size = 32
            chunks = [table_rows[i:i + chunk_size] for i in range(0, len(table_rows), chunk_size)]
            chunk_index = world_index // chunk_size

            message_id = table_data["chunk_message_ids"][chunk_index]
            
            try:
                message = await channel.fetch_message(message_id)
            except discord.NotFound:
                await interaction.followup.send("Error: Table segment not found. It may have been deleted.", ephemeral=True)
                return

            updated_chunk = "```ansi\n" + "\n".join(chunks[chunk_index]) + "```"
            
            if message:
                await interaction.client.message_queue.queue.put((message, updated_chunk))

            save_table_data(table_data)

            await interaction.followup.send(
                f"Spotted a `{size}` star in `{region}` on world `{world}`!\n"
                f"It will fall <t:{game_time_unix}:R> (`{entry_updates['game_time']}`)."
            )

            if is_valid_size(size):
                try:
                    size_number = int(size.lstrip('s'))
                    data = {
                        "world": world,
                        "location": region,
                        "createdBy": str(interaction.user.id),
                        "time": game_time_unix,
                        "size": size_number
                    }
                    #response_data = make_post_request(api, data)
                except Exception as api_error:
                    #print(f"API Error occurred while reporting star: {api_error}")
                    #print(f"API Data: {response_data}")
                    pass

        except discord.NotFound as e:
            if "Unknown Webhook" in str(e):
                print(f"Interaction webhook expired - command execution still continued for user {interaction.user.id}")
                print(f"Error: {str(e)}")
            elif "Unknown interaction" in str(e):
                print(f"Interaction expired for user {interaction.user.id}")
                print(f"Error: {str(e)}")
            else:
                print(f"Error: {str(e)}")
        except discord.HTTPException as e:
            print(f"Error executing call command: {str(e)}")
            try:
                await interaction.followup.send(f"Error updating message: {str(e)}", ephemeral=True)
            except:
                print(f"Couldn't send error notification to user {interaction.user.id}")
        except Exception as e:
            print(f"Error executing call command: {str(e)}")
            try:
                await interaction.user.send(f"An error occurred with your command: {str(e)}")
            except:
                print(f"Couldn't send error notification to user {interaction.user.id}")

@client.tree.command(name="find", description="Find the highest size stars currently in the table.")
async def find(interaction: discord.Interaction):
    try:
        await interaction.response.defer()
        
        if not table_data.get("chunk_message_ids"):
            await interaction.followup.send("Table does not exist. Use `/create` first.", ephemeral=True)
            return

        valid_entries = [
            entry for entry in table_data["entries"]
            if entry['size'] != "" and
            entry['region'] != "" and
            entry['game_time'] != "" and
            entry['game_time_full'] != "" and
            is_valid_size(entry['size']) and
            is_valid_game_time(entry['game_time']) and
            is_valid_game_time_full(entry['game_time_full'])
        ]

        if not valid_entries:
            await interaction.followup.send("No stars have been fully called yet.")
            return

        def extract_size(entry):
            return int(entry['size'][1:])

        max_size = max(extract_size(entry) for entry in valid_entries)
        smaller_sizes = [size for size in [extract_size(entry) for entry in valid_entries] if size < max_size]

        if smaller_sizes:
            second_max_size = max(smaller_sizes)
            found_entries = [
                entry for entry in valid_entries 
                if extract_size(entry) in [max_size, second_max_size]
            ]
        else:
            found_entries = [
                entry for entry in valid_entries 
                if extract_size(entry) == max_size
            ]

        found_entries.sort(key=extract_size, reverse=True)

        star_details = []
        current_size = None
        
        for star in found_entries:
            game_time_unix = int(datetime.datetime.fromisoformat(star['game_time_full']).timestamp())
            world_status = ""
            match star['world']:
                case 30:
                    world_status = " `[2000 Total]`"
                case 48:
                    world_status = " `[2600 Total]`"
                case 52:
                    world_status = " `[VIP]`"
                case 86 | 114:
                    world_status = " `[1500 Total]`"
                case 47 | 75:
                    world_status = " `[Português]`"
                case 101:
                    world_status = " `[Português Legacy]`"
                case 94 | 251:
                    world_status = " `[Português F2P]`"
                case 118:
                    world_status = " `[Français]`"
                case 55:
                    world_status = " `[Français F2P]`"
                case 102 | 121:
                    world_status = " `[Deutsch]`"
                case 122:
                    world_status = " `[Deutsch F2P]`"
                case 18 | 33 | 57 | 115 | 120 | 136 | 137:
                    world_status = " `[Legacy]`"
                case _:
                    if star['world'] in free_to_play_worlds:
                        world_status = " `[Free-to-play]`"
                    else:
                        world_status = ""

            size = extract_size(star)
            if size != current_size:
                star_details.append(f"\n`Size {size}:`")
                current_size = size
                
            try:
                region_link = get_region_url(star['region'])
                region_display = f"[{star['region']}](<{region_link}>)"
            except Exception:
                region_display = f"`{star['region']}`"
            
            star_details.append(
                f"World `{star['world']}` in {region_display}, <t:{game_time_unix}:R> (`{star['game_time']}`){world_status}"
            )

        DISCORD_CHAR_LIMIT = 1800
        header = "⁂ Notable stars found:"
        messages = []
        current_message = header

        message = header + "\n".join(star_details)
        if len(message) > DISCORD_CHAR_LIMIT:
            star_details = []
            current_size = None
            
            for star in found_entries:
                game_time_unix = int(datetime.datetime.fromisoformat(star['game_time_full']).timestamp())
                world_status = ""
                match star['world']:
                    case 30:
                        world_status = " `[2000 Total]`"
                    case 48:
                        world_status = " `[2600 Total]`"
                    case 52:
                        world_status = " `[VIP]`"
                    case 86 | 114:
                        world_status = " `[1500 Total]`"
                    case 47 | 75:
                        world_status = " `[Português]`"
                    case 101:
                        world_status = " `[Português Legacy]`"
                    case 94 | 251:
                        world_status = " `[Português F2P]`"
                    case 118:
                        world_status = " `[Français]`"
                    case 55:
                        world_status = " `[Français F2P]`"
                    case 102 | 121:
                        world_status = " `[Deutsch]`"
                    case 122:
                        world_status = " `[Deutsch F2P]`"
                    case 18 | 33 | 57 | 115 | 120 | 136 | 137:
                        world_status = " `[Legacy]`"
                    case _:
                        if star['world'] in free_to_play_worlds:
                            world_status = " `[Free-to-play]`"
                        else:
                            world_status = ""

                size = extract_size(star)
                if size != current_size:
                    star_details.append(f"\n`Size {size}:`")
                    current_size = size

                star_details.append(
                    f"World `{star['world']}` in `{star['region']}`, <t:{game_time_unix}:R> (`{star['game_time']}`){world_status}"
                )

            for detail in star_details:
                if len(current_message + detail + "\n") > DISCORD_CHAR_LIMIT:
                    messages.append(current_message)
                    current_message = f"`Size {size}:`" + "\n" + detail + "\n"
                else:
                    current_message += detail + "\n"
            
            if current_message != header:
                messages.append(current_message)
        else:
            messages = [message]

        await interaction.followup.send(messages[0])
        
        for message in messages[1:]:
            await interaction.followup.send(message)
            
    except Exception as e:
        print(f"Error in find command: {e}")
        try:
            await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)
        except:
            print(f"Couldn't send error notification to user {interaction.user.id}")

@client.tree.command(name="find-size", description="Find stars of a specific size.")
@app_commands.describe(size="What size of star are you looking for?")
@app_commands.choices(
    size=[
        app_commands.Choice(name="1", value="s1"),
        app_commands.Choice(name="2", value="s2"),
        app_commands.Choice(name="3", value="s3"),
        app_commands.Choice(name="4", value="s4"),
        app_commands.Choice(name="5", value="s5"),
        app_commands.Choice(name="6", value="s6"),
        app_commands.Choice(name="7", value="s7"),
        app_commands.Choice(name="8", value="s8"),
        app_commands.Choice(name="9", value="s9"),
        app_commands.Choice(name="10", value="s10")
    ]
)
async def find_size(interaction: discord.Interaction, size: str):
    try:
        await interaction.response.defer(ephemeral=True)
        
        if not table_data.get("chunk_message_ids"):
            await interaction.followup.send("Table does not exist. Use `/create` first.", ephemeral=True)
            return
            
        valid_entries = [
            entry for entry in table_data["entries"]
            if entry['size'] == size and
               entry['region'] != "" and
               entry['game_time'] != "" and
               entry['game_time_full'] != "" and
               is_valid_size(entry['size']) and
               is_valid_game_time(entry['game_time']) and
               is_valid_game_time_full(entry['game_time_full'])
        ]
        
        if not valid_entries:
            await interaction.followup.send(f"No stars of size `{size[1:]}` have been fully called yet.", ephemeral=True)
            return
            
        star_details = []
        for star in valid_entries:
            game_time_unix = int(datetime.datetime.fromisoformat(star['game_time_full']).timestamp())
            world_status = ""
            match star['world']:
                case 30:
                    world_status = " `[2000 Total]`"
                case 48:
                    world_status = " `[2600 Total]`"
                case 52:
                    world_status = " `[VIP]`"
                case 86 | 114:
                    world_status = " `[1500 Total]`"
                case 47 | 75:
                    world_status = " `[Português]`"
                case 101:
                    world_status = " `[Português Legacy]`"
                case 94 | 251:
                    world_status = " `[Português F2P]`"
                case 118:
                    world_status = " `[Français]`"
                case 55:
                    world_status = " `[Français F2P]`"
                case 102 | 121:
                    world_status = " `[Deutsch]`"
                case 122:
                    world_status = " `[Deutsch F2P]`"
                case 18 | 33 | 57 | 115 | 120 | 136 | 137:
                    world_status = " `[Legacy]`"
                case _:
                    if star['world'] in free_to_play_worlds:
                        world_status = " `[Free-to-play]`"
                    else:
                        world_status = " `[Members]`"
                        
            star_details.append(
                f"World `{star['world']}` [{star['region']}](<{get_region_url(star['region'])}>), <t:{game_time_unix}:R> (`{star['game_time']}`).{world_status}"
            )
            
        header = f"Star(s) of size `{size[1:]}` called:\n"
       
        DISCORD_CHAR_LIMIT = 1800
        messages = []
        current_message = header
       
        for detail in star_details:
            if len(current_message + detail + "\n") > DISCORD_CHAR_LIMIT:
                messages.append(current_message)
                current_message = header + detail + "\n"
            else:
                current_message += detail + "\n"
       
        if current_message != header:
            messages.append(current_message)
            
        await interaction.followup.send(messages[0], ephemeral=True)
       
        for message in messages[1:]:
            await interaction.followup.send(message, ephemeral=True)
            
    except Exception as e:
        print(f"Error in find_size command for size {size}: {str(e)}")
        try:
            await interaction.followup.send("An error occurred while processing your command.", ephemeral=True)
        except Exception as follow_up_error:
            print(f"Failed to send error message: {str(follow_up_error)}")

@client.tree.command(name="find-region", description="Find stars in a specific region.")
@app_commands.describe(region="What region are you looking for stars in?")
@app_commands.choices(
    region=[
        app_commands.Choice(name="Anachronia", value="Anachronia"),
        app_commands.Choice(name="Asgarnia", value="Asgarnia"),
        app_commands.Choice(name="Ashdale", value="Ashdale"),
        app_commands.Choice(name="Crandor/Karamja", value="Crandor/Karamja"),
        app_commands.Choice(name="Daemonheim", value="Daemonheim"),
        app_commands.Choice(name="Feldip Hills", value="Feldip Hills"),
        app_commands.Choice(name="Fremennik/Lunar Isle", value="Frem/Lunar"),
        app_commands.Choice(name="Kandarin", value="Kandarin"),
        app_commands.Choice(name="Kharidian Desert", value="Kharidian Desert"),
        app_commands.Choice(name="Lost Grove", value="Lost Grove"),
        app_commands.Choice(name="Menaphos", value="Menaphos"),
        app_commands.Choice(name="Misthalin", value="Misthalin"),
        app_commands.Choice(name="Morytania/Mos Le'Harmless", value="Morytania/Mos"),
        app_commands.Choice(name="Piscatoris/Gnome/Tirannwn", value="Pisc/Gnome/Tir"),
        app_commands.Choice(name="Tuska", value="Tuska"),
        app_commands.Choice(name="Wilderness", value="Wilderness"),
    ]
)
async def find_region(interaction: discord.Interaction, region: str):
    try:
        await interaction.response.defer(ephemeral=True)
        
        if not table_data.get("chunk_message_ids"):
            await interaction.followup.send("Table does not exist. Use `/create` first.", ephemeral=True)
            return
            
        valid_entries = [
            entry for entry in table_data["entries"]
            if entry['region'] == region and
               entry['size'] != "" and
               entry['game_time'] != "" and
               entry['game_time_full'] != "" and
               is_valid_size(entry['size']) and
               is_valid_game_time(entry['game_time']) and
               is_valid_game_time_full(entry['game_time_full'])
        ]
        
        if not valid_entries:
            await interaction.followup.send(f"No stars in `{region}` have been fully called yet.", ephemeral=True)
            return
            
        star_details = []
        for star in valid_entries:
            game_time_unix = int(datetime.datetime.fromisoformat(star['game_time_full']).timestamp())
            world_status = ""
            match star['world']:
                case 30:
                    world_status = " `[2000 Total]`"
                case 48:
                    world_status = " `[2600 Total]`"
                case 52:
                    world_status = " `[VIP]`"
                case 86 | 114:
                    world_status = " `[1500 Total]`"
                case 47 | 75:
                    world_status = " `[Português]`"
                case 101:
                    world_status = " `[Português Legacy]`"
                case 94 | 251:
                    world_status = " `[Português F2P]`"
                case 118:
                    world_status = " `[Français]`"
                case 55:
                    world_status = " `[Français F2P]`"
                case 102 | 121:
                    world_status = " `[Deutsch]`"
                case 122:
                    world_status = " `[Deutsch F2P]`"
                case 18 | 33 | 57 | 115 | 120 | 136 | 137:
                    world_status = " `[Legacy]`"
                case _:
                    if star['world'] in free_to_play_worlds:
                        world_status = " `[Free-to-play]`"
                    else:
                        world_status = " `[Members]`"
                        
            star_details.append(
                f"Size `{star['size'][1:]}` on world `{star['world']}`, <t:{game_time_unix}:R> (`{star['game_time']}`).{world_status}"
            )
            
        header = f"Star(s) called for [{region}](<{get_region_url(region)}>):\n"
        DISCORD_CHAR_LIMIT = 1800
        messages = []
        current_message = header
       
        for detail in star_details:
            if len(current_message + detail + "\n") > DISCORD_CHAR_LIMIT:
                messages.append(current_message)
                current_message = header + detail + "\n"
            else:
                current_message += detail + "\n"
       
        if current_message != header:
            messages.append(current_message)
            
        await interaction.followup.send(messages[0], ephemeral=True)
       
        for message in messages[1:]:
            await interaction.followup.send(message, ephemeral=True)
            
    except Exception as e:
        print(f"Error in find_region command for region {region}: {str(e)}")
        try:
            await interaction.followup.send("An error occurred while processing your command.", ephemeral=True)
        except Exception as follow_up_error:
            print(f"Failed to send error message: {str(follow_up_error)}")

@client.tree.command(name="find-world", description="Find stars on a specific world.")
@app_commands.describe(world="What world are you looking for stars in?")
async def find_world(interaction: discord.Interaction, world: int):
    if not table_data.get("chunk_message_ids"):
        await interaction.response.send_message("Table does not exist. Use `/create` first.", ephemeral=True)
        return
    
    if not any(entry["world"] == world for entry in table_data["entries"]):
        await interaction.response.send_message(f"World `{world}` not found.", ephemeral=True)
        return

    valid_entries = [
        entry for entry in table_data["entries"]
        if entry['world'] == world and
        entry['size'] != "" and
        entry['region'] != "" and
        entry['game_time'] != "" and
        entry['game_time_full'] != "" and
        is_valid_size(entry['size']) and
        is_valid_game_time(entry['game_time']) and
        is_valid_game_time_full(entry['game_time_full'])
    ]

    if not valid_entries:  
        await interaction.response.send_message(
            f"No stars have been called on world `{world}`.", 
            ephemeral=True
        )
        return

    star_details = []
    for star in valid_entries:
        game_time_unix = int(datetime.datetime.fromisoformat(star['game_time_full']).timestamp())
        world_status = ""
        match star['world']:
            case 30:
                world_status = " `[2000 Total]`"
            case 48:
                world_status = " `[2600 Total]`"
            case 52:
                world_status = " `[VIP]`"
            case 86 | 114:
                world_status = " `[1500 Total]`"
            case 47 | 75:
                world_status = " `[Português]`"
            case 101:
                world_status = " `[Português Legacy]`"
            case 94 | 251:
                world_status = " `[Português F2P]`"
            case 118:
                world_status = " `[Français]`"
            case 55:
                world_status = " `[Français F2P]`"
            case 102 | 121:
                world_status = " `[Deutsch]`"
            case 122:
                world_status = " `[Deutsch F2P]`"
            case 18 | 33 | 57 | 115 | 120 | 136 | 137:
                world_status = " `[Legacy]`"
            case _:
                if star['world'] in free_to_play_worlds:
                    world_status = " `[Free-to-play]`"
                else:
                    world_status = " `[Members]`"

        star_details.append(
            f"Size `{star['size'][1:]}` in [{star['region']}](<{get_region_url(star['region'])}>), <t:{game_time_unix}:R> (`{star['game_time']}`)."
        )

    await interaction.response.send_message(
        f"World `{world}`{world_status}:\n" +
        "\n".join(star_details),
        ephemeral=True
    )

@client.tree.command(name="find-f2p", description="Find the highest size f2p stars currently in the table.")
async def find_f2p(interaction: discord.Interaction):
    try:
        await interaction.response.defer()
        
        if not table_data.get("chunk_message_ids"):
            await interaction.followup.send("Table does not exist. Use `/create` first.", ephemeral=True)
            return
            
        valid_entries = [
            entry for entry in table_data["entries"]
            if entry['size'] != "" and
            entry['region'] != "" and
            entry['game_time'] != "" and
            entry['game_time_full'] != "" and
            is_valid_size(entry['size']) and
            is_valid_game_time(entry['game_time']) and
            is_valid_game_time_full(entry['game_time_full']) and
            int(entry['world']) in free_to_play_worlds
        ]
        
        if not valid_entries:
            await interaction.followup.send("No stars have been fully called in free-to-play worlds yet.")
            return
            
        def extract_size(entry):
            return int(entry['size'][1:])
            
        max_size = max(extract_size(entry) for entry in valid_entries)
        highest_stars = [
            entry for entry in valid_entries
            if extract_size(entry) == max_size
        ]
        
        header = f"Largest free-to-play star(s) called is of size `{max_size}`:\n"
       
        star_details = []
        for star in highest_stars:
            game_time_unix = int(datetime.datetime.fromisoformat(star['game_time_full']).timestamp())
            world_status = ""
            match star['world']:
                case 94 | 251:
                    world_status = " `[Português]`"
                case 55:
                    world_status = " `[Français]`"
                case 122:
                    world_status = " `[Deutsch]`"
                case 33 | 57 | 120 | 136:
                    world_status = " `[Legacy]`"
            try:
                region_link = get_region_url(star['region'])
                region_display = f"[{star['region']}](<{region_link}>)"
            except Exception:
                region_display = f"`{star['region']}`"
           
            star_details.append(
                f"World `{star['world']}` {region_display}, <t:{game_time_unix}:R> (`{star['game_time']}`).{world_status}"
            )
            
        DISCORD_CHAR_LIMIT = 1800
        message = header + "\n".join(star_details)
        if len(message) > DISCORD_CHAR_LIMIT:
            star_details = []
            for star in highest_stars:
                game_time_unix = int(datetime.datetime.fromisoformat(star['game_time_full']).timestamp())
                world_status = ""
                match star['world']:
                    case 94 | 251:
                        world_status = " `[Português]`"
                    case 55:
                        world_status = " `[Français]`"
                    case 122:
                        world_status = " `[Deutsch]`"
                    case 33 | 57 | 120 | 136:
                        world_status = " `[Legacy]`"
                star_details.append(
                    f"World `{star['world']}` `{star['region']}`, <t:{game_time_unix}:R> (`{star['game_time']}`).{world_status}"
                )
            message = header + "\n".join(star_details)
            
        if len(message) > DISCORD_CHAR_LIMIT:
            messages = []
            current_message = header
           
            for detail in star_details:
                if len(current_message + detail + "\n") > DISCORD_CHAR_LIMIT:
                    messages.append(current_message)
                    current_message = header + detail + "\n"
                else:
                    current_message += detail + "\n"
           
            if current_message != header:
                messages.append(current_message)
        else:
            messages = [message]
            
        await interaction.followup.send(messages[0])
       
        for message in messages[1:]:
            await interaction.followup.send(message)
            
    except Exception as e:
        print(f"Error in find_f2p command: {e}")
        try:
            await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)
        except:
            print(f"Couldn't send error notification to user {interaction.user.id}")

@client.tree.command(name="find-size-f2p", description="Find f2p stars of a specific size.")
@app_commands.describe(size="What size of star are you looking for?")
@app_commands.choices(
    size=[
        app_commands.Choice(name="1", value="s1"),
        app_commands.Choice(name="2", value="s2"),
        app_commands.Choice(name="3", value="s3"),
        app_commands.Choice(name="4", value="s4"),
        app_commands.Choice(name="5", value="s5")
    ]
)
async def find_size_f2p(interaction: discord.Interaction, size: str):
    try:
        await interaction.response.defer(ephemeral=True)
        
        if not table_data.get("chunk_message_ids"):
            await interaction.followup.send("Table does not exist. Use `/create` first.", ephemeral=True)
            return
            
        valid_entries = [
            entry for entry in table_data["entries"]
            if entry['size'] == size and
               entry['region'] != "" and
               entry['game_time'] != "" and
               entry['game_time_full'] != "" and
               is_valid_size(entry['size']) and
               is_valid_game_time(entry['game_time']) and
               is_valid_game_time_full(entry['game_time_full']) and
               int(entry['world']) in free_to_play_worlds
        ]
        
        if not valid_entries:
            await interaction.followup.send(f"No stars of size `{size[1:]}` have been fully called yet.", ephemeral=True)
            return
            
        star_details = []
        for star in valid_entries:
            game_time_unix = int(datetime.datetime.fromisoformat(star['game_time_full']).timestamp())
            world_status = ""
            match star['world']:
                case 94 | 251:
                    world_status = " `[Português]`"
                case 55:
                    world_status = " `[Français]`"
                case 122:
                    world_status = " `[Deutsch]`"
                case 33 | 57 | 120 | 136:
                    world_status = " `[Legacy]`"
                   
            star_details.append(
                f"World `{star['world']}` [{star['region']}](<{get_region_url(star['region'])}>), <t:{game_time_unix}:R> (`{star['game_time']}`).{world_status}"
            )
            
        header = f"Free-to-play star(s) of size `{size[1:]}` called:\n"
       
        DISCORD_CHAR_LIMIT = 1800
        messages = []
        current_message = header
       
        for detail in star_details:
            if len(current_message + detail + "\n") > DISCORD_CHAR_LIMIT:
                messages.append(current_message)
                current_message = header + detail + "\n"
            else:
                current_message += detail + "\n"
       
        if current_message != header:
            messages.append(current_message)
            
        await interaction.followup.send(messages[0], ephemeral=True)
       
        for message in messages[1:]:
            await interaction.followup.send(message, ephemeral=True)
            
    except Exception as e:
        print(f"Error in find_size_f2p: {e}")
        try:
            error_message = f"An error occurred while processing your request: {str(e)}"
            await interaction.followup.send(error_message, ephemeral=True)
        except Exception as followup_error:
            print(f"Failed to send error message: {followup_error}")

@client.tree.command(name="find-region-f2p", description="Find f2p stars in a specific region.")
@app_commands.describe(region="What region are you looking for stars in?")
@app_commands.choices(
    region=[
        app_commands.Choice(name="Asgarnia", value="Asgarnia"),
        app_commands.Choice(name="Ashdale", value="Ashdale"),
        app_commands.Choice(name="Crandor/Karamja", value="Crandor/Karamja"),
        app_commands.Choice(name="Daemonheim", value="Daemonheim"),
        app_commands.Choice(name="Kharidian Desert", value="Kharidian Desert"),
        app_commands.Choice(name="Misthalin", value="Misthalin"),
        app_commands.Choice(name="Wilderness", value="Wilderness"),
    ]
)
async def find_region_f2p(interaction: discord.Interaction, region: str):
    try:
        await interaction.response.defer(ephemeral=True)
        
        if not table_data.get("chunk_message_ids"):
            await interaction.followup.send("Table does not exist. Use `/create` first.", ephemeral=True)
            return
            
        valid_entries = [
            entry for entry in table_data["entries"]
            if entry['region'] == region and
               entry['size'] != "" and
               entry['game_time'] != "" and
               entry['game_time_full'] != "" and
               is_valid_size(entry['size']) and
               is_valid_game_time(entry['game_time']) and
               is_valid_game_time_full(entry['game_time_full']) and
               int(entry['world']) in free_to_play_worlds
        ]
        
        if not valid_entries:
            await interaction.followup.send(f"No stars in `{region}` have been fully called yet.", ephemeral=True)
            return
            
        star_details = []
        for star in valid_entries:
            game_time_unix = int(datetime.datetime.fromisoformat(star['game_time_full']).timestamp())
            world_status = ""
            match star['world']:
                case 94 | 251:
                    world_status = " `[Português]`"
                case 55:
                    world_status = " `[Français]`"
                case 122:
                    world_status = " `[Deutsch]`"
                case 33 | 57 | 120 | 136:
                    world_status = " `[Legacy]`"
            star_details.append(
                f"Size `{star['size'][1:]}` on world `{star['world']}`, <t:{game_time_unix}:R> (`{star['game_time']}`).{world_status}"
            )
            
        header = f"Free-to-play star(s) called for [{region}](<{get_region_url(region)}>):\n"
        DISCORD_CHAR_LIMIT = 1800
        messages = []
        current_message = header
       
        for detail in star_details:
            if len(current_message + detail + "\n") > DISCORD_CHAR_LIMIT:
                messages.append(current_message)
                current_message = header + detail + "\n"
            else:
                current_message += detail + "\n"
       
        if current_message != header:
            messages.append(current_message)
            
        await interaction.followup.send(messages[0], ephemeral=True)
       
        for message in messages[1:]:
            await interaction.followup.send(message, ephemeral=True)
            
    except Exception as e:
        print(f"Error in find_region_f2p command for region {region}: {str(e)}")
        try:
            await interaction.followup.send("An error occurred while processing your command.", ephemeral=True)
        except Exception as follow_up_error:
            print(f"Failed to send error message: {str(follow_up_error)}")

@client.tree.command(name="starstruck", description="Find stars in the Feldip Hills region.")
async def starstruck(interaction: discord.Interaction):
    try:
        await interaction.response.defer(ephemeral=False)
       
        if not table_data.get("chunk_message_ids"):
            await interaction.followup.send("Table does not exist. Use `/create` first.")
            return
        region = "Feldip Hills"
        valid_entries = [
            entry for entry in table_data["entries"]
            if entry['region'] == region and
            entry['size'] != "" and
            entry['game_time'] != "" and
            entry['game_time_full'] != "" and
            is_valid_size(entry['size']) and
            is_valid_game_time(entry['game_time']) and
            is_valid_game_time_full(entry['game_time_full'])
        ]
        if not valid_entries:
            await interaction.followup.send(f"No stars in `Feldip Hills`, for the starstruck achievement have been fully called yet.")
            return
        star_details = []
        for star in valid_entries:
            game_time_unix = int(datetime.datetime.fromisoformat(star['game_time_full']).timestamp())
            world_status = ""
            match star['world']:
                case 30:
                    world_status = " `[2000 Total]`"
                case 48:
                    world_status = " `[2600 Total]`"
                case 52:
                    world_status = " `[VIP]`"
                case 86 | 114:
                    world_status = " `[1500 Total]`"
                case 47 | 75:
                    world_status = " `[Português]`"
                case 101:
                    world_status = " `[Português Legacy]`"
                case 94 | 251:
                    world_status = " `[Português F2P]`"
                case 118:
                    world_status = " `[Français]`"
                case 55:
                    world_status = " `[Français F2P]`"
                case 102 | 121:
                    world_status = " `[Deutsch]`"
                case 122:
                    world_status = " `[Deutsch F2P]`"
                case 18 | 33 | 57 | 115 | 120 | 136 | 137:
                    world_status = " `[Legacy]`"
                case _:
                    if star['world'] in free_to_play_worlds:
                        world_status = " `[Free-to-play]`"
                    else:
                        world_status = " `[Members]`"
            star_details.append(
                f"Size `{star['size'][1:]}` on world `{star['world']}`, <t:{game_time_unix}:R> (`{star['game_time']}`).{world_status}"
            )
        header = f"Star(s) called for the [Starstruck](<https://runescape.wiki/w/Starstruck>) achievement in [Feldip Hills](<{get_region_url('Feldip Hills')}>):\n"
        DISCORD_CHAR_LIMIT = 1800
        messages = []
        current_message = header
       
        for detail in star_details:
            if len(current_message + detail + "\n") > DISCORD_CHAR_LIMIT:
                messages.append(current_message)
                current_message = header + detail + "\n"
            else:
                current_message += detail + "\n"
       
        if current_message != header:
            messages.append(current_message)
        await interaction.followup.send(messages[0])
       
        for message in messages[1:]:
            await interaction.followup.send(message)
    except Exception as e:
        print(f"Error in starstruck command: {str(e)}")
        try:
            await interaction.followup.send("An error occurred while processing your command.")
        except Exception as follow_up_error:
            print(f"Failed to send error message: {str(follow_up_error)}")

@client.tree.command(name="starstruck-f2p", description="Find f2p stars in Crandor/Karamja.")
async def starstruck_f2p(interaction: discord.Interaction):
    try:
        await interaction.response.defer(ephemeral=False)
       
        if not table_data.get("chunk_message_ids"):
            await interaction.followup.send("Table does not exist. Use `/create` first.", ephemeral=False)
            return
           
        valid_entries = [
            entry for entry in table_data["entries"]
            if entry['region'] == "Crandor/Karamja" and
               entry['size'] != "" and
               entry['game_time'] != "" and
               entry['game_time_full'] != "" and
               is_valid_size(entry['size']) and
               is_valid_game_time(entry['game_time']) and
               is_valid_game_time_full(entry['game_time_full']) and
               int(entry['world']) in free_to_play_worlds
        ]
       
        if not valid_entries:
            await interaction.followup.send(f"No free-to-play stars in `Crandor/Karamja`, for the starstruck achievement have been fully called yet.", ephemeral=False)
            return
           
        star_details = []
        for star in valid_entries:
            game_time_unix = int(datetime.datetime.fromisoformat(star['game_time_full']).timestamp())
            world_status = ""
            match star['world']:
                case 94 | 251:
                    world_status = " `[Português]`"
                case 55:
                    world_status = " `[Français]`"
                case 122:
                    world_status = " `[Deutsch]`"
                case 33 | 57 | 120 | 136:
                    world_status = " `[Legacy]`"
            star_details.append(
                f"Size `{star['size'][1:]}` on world `{star['world']}`, <t:{game_time_unix}:R> (`{star['game_time']}`).{world_status}"
            )
           
        header = f"Free-to-play star(s) called for the [Starstruck](<https://runescape.wiki/w/Starstruck>) achievement in [Crandor/Karamja](<{get_region_url('Crandor/Karamja')}>):\n"
        DISCORD_CHAR_LIMIT = 1800
        messages = []
        current_message = header
       
        for detail in star_details:
            if len(current_message + detail + "\n") > DISCORD_CHAR_LIMIT:
                messages.append(current_message)
                current_message = header + detail + "\n"
            else:
                current_message += detail + "\n"
       
        if current_message != header:
            messages.append(current_message)
           
        await interaction.followup.send(messages[0], ephemeral=False)
       
        for message in messages[1:]:
            await interaction.followup.send(message, ephemeral=False)
           
    except Exception as e:
        print(f"Error in starstruck_f2p command: {str(e)}")
        try:
            await interaction.followup.send("An error occurred while processing your command.", ephemeral=False)
        except Exception as follow_up_error:
            print(f"Failed to send error message: {str(follow_up_error)}")

client.run(token)