import os
import discord
import asyncio
import datetime
import pytz
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("token")

class StarCaller(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="", 
            intents=discord.Intents.all(),
        )

    async def setup_hook(self):
        await self.tree.sync()

client = StarCaller()

table_data = {
    "is_locked": False, 
    "entries": [],      
    "message_id": None, 
    "channel_id": None,  
    "chunk_message_ids": []  
}

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
    (47, "Members"),
    (48, "Members", "Special"),
    (49, "Members"),
    (50, "Members"),
    (51, "Members"),
    (52, "Members", "Special"),
    (53, "Members"),
    (54, "Members"),
    (55, "Free-to-play"),
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
    (75, "Members"),
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
    (94, "Free-to-play"),
    (96, "Members"),
    (97, "Members"),
    (98, "Members"),
    (99, "Members"),
    (100, "Members"),
    (101, "Members"),
    (102, "Members"),
    (103, "Members"),
    (104, "Members"),
    (105, "Members"),
    (106, "Members"),
    (108, "Free-to-play"),
    (114, "Members", "Special"),
    (115, "Members"),
    (116, "Members"),
    (117, "Members"),
    (118, "Members"),
    (119, "Members"),
    (120, "Free-to-play"),
    (121, "Members"),
    (122, "Free-to-play"),
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
    (251, "Free-to-play"),
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

@client.tree.command(name="lock", description="Lock the star call table to prevent modifications.")
@app_commands.default_permissions(administrator=True)
async def lock(interaction: discord.Interaction):
    if not table_data.get("message_id"):
        await interaction.response.send_message("No table exists to lock.", ephemeral=True)
        return
    
    if table_data["is_locked"]:
        await interaction.response.send_message("Table is already locked.", ephemeral=True)
        return
    
    table_data["is_locked"] = True
    await interaction.response.send_message("Star call table has been locked.", ephemeral=True)

@client.tree.command(name="unlock", description="Unlock the star call table to allow modifications.")
@app_commands.default_permissions(administrator=True)
async def unlock(interaction: discord.Interaction):
    if not table_data.get("message_id"):
        await interaction.response.send_message("No table exists to unlock.", ephemeral=True)
        return
    
    if not table_data["is_locked"]:
        await interaction.response.send_message("Table is already unlocked.", ephemeral=True)
        return
    
    table_data["is_locked"] = False
    await interaction.response.send_message("Star call table has been unlocked.", ephemeral=True)

@client.tree.command(name="clear", description="Clear all entries in the star call table.")
@app_commands.default_permissions(administrator=True)
async def clear(interaction: discord.Interaction):
    if not table_data.get("chunk_message_ids"):
        await interaction.response.send_message("No table exists to clear.", ephemeral=True)
        return
    
    if table_data["is_locked"]:
        await interaction.response.send_message("Table is locked. Cannot clear entries.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    # Reset entries to default state
    table_data["entries"] = [
        {"world": world, "region": "?", "size": "s?", "game_time": "?"} 
        for world in all_worlds
    ]

    # Recreate the table with default entries
    table_rows = []
    for entry in table_data["entries"]:
        world_name = entry["world"]
        if entry["world"] in free_to_play_worlds:
            world_name = f"\u001b[33m{world_name}\u001b[0m" 
        elif entry["world"] in special_worlds:
            world_name = f"\u001b[36m{world_name}\u001b[0m" 
        
        table_rows.append(
            f"{world_name:<1} | {entry['region']:<17} | {entry['size']:<4} | {entry['game_time']:<4}"
        )

    chunk_size = 32
    chunks = [table_rows[i:i + chunk_size] for i in range(0, len(table_rows), chunk_size)]

    # Update each chunk message
    channel = interaction.channel
    for i, chunk in enumerate(chunks):
        message_id = table_data["chunk_message_ids"][i]
        message = await channel.fetch_message(message_id)
        
        updated_chunk = "```ansi\n" + "\n".join(chunk) + "```"
        await message.edit(content=updated_chunk)

    await interaction.followup.send("Table cleared successfully!", ephemeral=True)

@client.tree.command(name="prune", description="Clear data for a specific world.")
@app_commands.default_permissions(administrator=True)
async def prune(interaction: discord.Interaction, world: int):
    if not table_data.get("chunk_message_ids"):
        await interaction.response.send_message("No table exists to prune.", ephemeral=True)
        return
    
    if table_data["is_locked"]:
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

    # Reset the specific world's entry
    table_data["entries"][world_index] = {
        "world": world, "region": "", "size": "", "game_time": ""
    }

    # Recreate table rows with updated entry
    table_rows = []
    for entry in table_data["entries"]:
        world_name = entry["world"]
        if entry["world"] in free_to_play_worlds:
            world_name = f"\u001b[33m{world_name}\u001b[0m" 
        elif entry["world"] in special_worlds:
            world_name = f"\u001b[36m{world_name}\u001b[0m" 
        
        table_rows.append(
            f"{world_name:<1} | {entry['region']:<17} | {entry['size']:<4} | {entry['game_time']:<4}"
        )

    chunk_size = 32
    chunks = [table_rows[i:i + chunk_size] for i in range(0, len(table_rows), chunk_size)]

    # Determine which chunk contains the world and update that specific message
    chunk_index = world_index // chunk_size
    channel = interaction.channel
    message_id = table_data["chunk_message_ids"][chunk_index]
    message = await channel.fetch_message(message_id)
    
    updated_chunk = "```ansi\n" + "\n".join(chunks[chunk_index]) + "```"
    await message.edit(content=updated_chunk)

    await interaction.response.send_message(f"Cleared data for world {world}.", ephemeral=True)

@client.tree.command(name="create", description="Create a star call table.")
@app_commands.default_permissions(administrator=True)
async def create(interaction: discord.Interaction):
    if table_data["message_id"]:
        await interaction.response.send_message(
            "A table already exists. Use `/clear` to reset it.", ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    table_rows = []
    for world in all_worlds:
        world_name = world
        if world in free_to_play_worlds:
            world_name = f"\u001b[33m{world_name}\u001b[0m" 
        elif world in special_worlds:
            world_name = f"\u001b[36m{world_name}\u001b[0m" 
        else:
            world_name = f"{world}"

        table_rows.append(
            f"{world_name:<1} | {'':<17} | {'':<4} | {'':<4}"
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

                table_data["entries"] = [
                    {"world": world, "region": "", "size": "", "game_time": ""} 
                    for world in all_worlds
                ]
        except Exception as e:
            await interaction.followup.send(
                f"Failed to create the table. Error: {str(e)}", 
                ephemeral=True
            )
            return
    await interaction.followup.send("Table(s) created successfully!", ephemeral=True)

@client.tree.command(name="call", description="Call-out shooting stars.")
@app_commands.describe(
    world = "What world will this star fall on?",
    region = "What's the general location of the falling star?", 
    size = "What size will the falling star be?",
    game_time = "How many minutes from now will the star fall? (Use the lower bound)",
    )
@app_commands.choices(
    region=[
        app_commands.Choice(name="Asgarnia", value="Asgarnia"),
        app_commands.Choice(name="Crandor", value="Crandor"),
        app_commands.Choice(name="Karamja", value="Karamja"),
        app_commands.Choice(name="Fremennik", value="Fremennik"),
        app_commands.Choice(name="Lunar Isle", value="Lunar Isle"),
        app_commands.Choice(name="Kandarin", value="Kandarin"),
        app_commands.Choice(name="Kharidian Desert", value="Kharidian Desert"),
        app_commands.Choice(name="Misthalin", value="Misthalin"),
        app_commands.Choice(name="Morytania", value="Morytania"),
        app_commands.Choice(name="Mos Le'Harmless", value="Mos Le'Harmless"),
        app_commands.Choice(name="Piscatoris", value="Piscatoris"),
        app_commands.Choice(name="Gnome Stronghold", value="Gnome Stronghold"),
        app_commands.Choice(name="Tirannwn", value="Tirannwn"),
        app_commands.Choice(name="Wilderness", value="Wilderness")
    ],
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
async def call(interaction: discord.Interaction, world: int, region: str = None, size: str = None, game_time: int = None):
    if not table_data.get("chunk_message_ids"):
        await interaction.response.send_message("Table does not exist. Use `/create` first.", ephemeral=True)
        return

    if table_data["is_locked"]:
        await interaction.response.send_message("Table is locked. Cannot modify entries.", ephemeral=True)
        return

    world_index = None
    for i, entry in enumerate(table_data["entries"]):
        if entry["world"] == world:
            world_index = i
            break
    
    if world_index is None:
        await interaction.response.send_message(f"World {world} not found.", ephemeral=True)
        return

    if region is not None:
        table_data["entries"][world_index]["region"] = region
    if size is not None:
        table_data["entries"][world_index]["size"] = size
    
    if game_time is not None:
        current_utc = datetime.datetime.now(pytz.UTC)
        game_end_time = current_utc + datetime.timedelta(minutes=game_time)
        formatted_time = game_end_time.strftime("%H:%M")
        table_data["entries"][world_index]["game_time"] = formatted_time

    chunk_size = 32
    table_rows = []
    for entry in table_data["entries"]:
        world_name = entry["world"]
        if entry["world"] in free_to_play_worlds:
            world_name = f"\u001b[33m{world_name}\u001b[0m" 
        elif entry["world"] in special_worlds:
            world_name = f"\u001b[36m{world_name}\u001b[0m" 
        
        # Add red color for size 9 & 10 stars
        size_display = entry['size']
        if size_display in ['s9', 's10']:
            size_display = f"\u001b[31m{size_display}\u001b[0m"
        
        table_rows.append(
            f"{world_name:<1} | {entry['region']:<17} | {size_display:<4} | {entry['game_time']:<4}"
        )

    chunks = [table_rows[i:i + chunk_size] for i in range(0, len(table_rows), chunk_size)]
    channel = interaction.channel
    chunk_index = world_index // chunk_size
    message_id = table_data["chunk_message_ids"][chunk_index]
    message = await channel.fetch_message(message_id)
    
    updated_chunk = "```ansi\n" + "\n".join(chunks[chunk_index]) + "```"
    await message.edit(content=updated_chunk)

    await interaction.response.send_message(f"Updated world {world} details.", ephemeral=True)

@client.tree.command(name="find", description="Find the highest size stars currently in the table.")
async def find(interaction: discord.Interaction):
    if not table_data.get("chunk_message_ids"):
        await interaction.response.send_message("Table does not exist. Use `/create` first.", ephemeral=True)
        return

    # Filter out entries that have a valid size and are not the default "s?"
    valid_entries = [
        entry for entry in table_data["entries"] 
        if entry['size'] != "" and 
           entry['region'] != "" and 
           entry['game_time'] != ""
    ]

    if not valid_entries:
        await interaction.response.send_message("No stars have been called yet.", ephemeral=True)
        return

    # Extract the numeric size from the size string
    def extract_size(entry):
        return int(entry['size'][1:])

    # Find the maximum star size
    max_size = max(extract_size(entry) for entry in valid_entries)

    # Collect all entries with the maximum size
    highest_stars = [
        entry for entry in valid_entries 
        if extract_size(entry) == max_size
    ]

    # Format the output message
    star_details = []
    for star in highest_stars:
        star_details.append(
            f"World `{star['world']}` in `{star['region']}` size `{max_size}` at `{star['game_time']}`."
        )

    # Send the ephemeral message
    await interaction.response.send_message(
        f"Largest stars `{max_size}` found:\n" + 
        "\n".join(star_details),
        ephemeral=True
    )

client.run(token)