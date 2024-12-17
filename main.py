import os
import discord
import asyncio
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("token")

class StarCaller(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="",  # No prefix as we're using slash commands
            intents=discord.Intents.all(),
        )

    async def setup_hook(self):
        # Sync slash commands on startup
        await self.tree.sync()
        #print("Commands synced!")

client = StarCaller()

# Table data to store event information
table_data = {
    "is_locked": False,  # Prevent updates when locked
    "entries": [],       # Holds all entries as rows
    "message_id": None,  # ID of the message containing the table
    "channel_id": None,   # ID of the channel where the table is posted
    "chunk_message_ids": []  # Add this line
}

# Original data
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
            world_name = f"\u001b[33m{world}\u001b[0m" 
        elif world in special_worlds:
            world_name = f"\u001b[36m{world}\u001b[0m" 
        else:
            world_name = f"{world}"

        table_rows.append(
            f"{world_name:<1} | {'?':<15} | {'s?':<3} | {'?':<4}"
        )

    chunk_size = 9 
    chunks = [table_rows[i:i + chunk_size] for i in range(0, len(table_rows), chunk_size)]

    table_data["chunk_message_ids"] = []

    for i, chunk in enumerate(chunks):
        formatted_table = "\n".join([f"{row}" for row in chunk])

        try:
            table_message = await interaction.channel.send(
                content=f"```ansi\n{formatted_table}\n```"
            )

            # Save each chunk's message ID
            table_data["chunk_message_ids"].append(table_message.id)

            # Store the first message ID and channel ID only once
            if i == 0:
                table_data["message_id"] = table_message.id
                table_data["channel_id"] = interaction.channel.id

                # Initialize table entries with the 'world' key in the entries list
                table_data["entries"] = [
                    {"world": world, "region": "?", "size": "s?", "game_time": "?"} 
                    for world in all_worlds
                ]
                #print(f"{table_data}")
        except Exception as e:
            # If sending fails, follow up with an error message
            await interaction.followup.send(
                f"Failed to create the table. Error: {str(e)}", 
                ephemeral=True
            )
            return
    await interaction.followup.send("Table(s) created successfully!", ephemeral=True)

# Add region list
REGIONS = [
    "Asgarnia", "Falador", "Lumbridge", "Varrock", 
    "Wilderness", "Karamja", "Misthalin", "Morytania", 
    "Tirannwn", "Kandarin", "Zeah"
]

@client.tree.command(name="call", description="Update world details in the table.")
async def call(interaction: discord.Interaction, world: int, region: str = None, size: int = None, game_time: int = None):
    # Retrieve the stored table data
    if not table_data.get("chunk_message_ids"):
        await interaction.response.send_message("Table does not exist. Use `/create` first.", ephemeral=True)
        return

    # Validate region if provided
    if region and region not in REGIONS:
        await interaction.response.send_message(f"Invalid region. Choose from: {', '.join(REGIONS)}", ephemeral=True)
        return

    # Locate the world row to update
    world_index = None
    for i, entry in enumerate(table_data["entries"]):
        if entry["world"] == world:
            world_index = i
            break
    
    if world_index is None:
        await interaction.response.send_message(f"World {world} not found.", ephemeral=True)
        return

    # Update the table entry with the new values
    if region is not None:
        table_data["entries"][world_index]["region"] = region
    if size is not None:
        table_data["entries"][world_index]["size"] = size
    if game_time is not None:
        table_data["entries"][world_index]["game_time"] = game_time

    # Prepare chunks with updated table rows
    chunk_size = 9
    table_rows = []
    for entry in table_data["entries"]:
        world_name = entry["world"]
        if entry["world"] in free_to_play_worlds:
            world_name = f"\u001b[33m{world_name}\u001b[0m" 
        elif entry["world"] in special_worlds:
            world_name = f"\u001b[36m{world_name}\u001b[0m" 
        
        table_rows.append(
            f"{world_name:<1} | {entry['region']:<15} | s{entry['size']:<3} | {entry['game_time']:<4}"
        )

    # Split into chunks
    chunks = [table_rows[i:i + chunk_size] for i in range(0, len(table_rows), chunk_size)]

    channel = interaction.channel

    # Update only the specific chunks containing the updated world
    chunk_index = world_index // chunk_size
    message_id = table_data["chunk_message_ids"][chunk_index]
    message = await channel.fetch_message(message_id)
    
    updated_chunk = "```ansi\n" + "\n".join(chunks[chunk_index]) + "```"
    await message.edit(content=updated_chunk)

    # Respond to the interaction
    await interaction.response.send_message(f"Updated world {world} details.", ephemeral=True)

client.run(token)