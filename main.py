import os
import discord
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
    "channel_id": None   # ID of the channel where the table is posted
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
    (30, "Members"),
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
    (48, "Members"),
    (49, "Members"),
    (50, "Members"),
    (51, "Members"),
    (52, "Members"),
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
    (86, "Members"),
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
    (114, "Members"),
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

# Create the three lists
all_worlds = [world for world, _ in world_data]
members_worlds = [world for world, status in world_data if status == "Members"]
free_to_play_worlds = [world for world, status in world_data if status == "Free-to-play"]


@client.tree.command(name="create", description="Create an event table.")
@app_commands.default_permissions(administrator=True)
async def create(interaction: discord.Interaction):
    """
    Slash command to create a table with predefined columns:
    World, Region, Size, Game Time.
    The table is initially empty, and data is added using the `/call` command.
    """
    # Check if a table already exists
    if table_data["message_id"]:
        await interaction.response.send_message(
            "A table already exists. Use `/clear` to reset it.", ephemeral=True
        )
        return

    # Define the table headers
    table_headers = ["World", "Region", "Size", "Game Time"]

    # Prepare the table rows with blank spaces
    table_rows = []
    for world in all_worlds:
        # Set text color based on the type of world (Free-to-Play or Member)
        world_name = world
        if world in free_to_play_worlds:
            # Color the text for Free-to-Play worlds, you could also bold them or change their style
            world_name = f"{world}"  # You can change this to color as needed
        else:
            world_name = f"{world}"

        # Add a row for this world
        # We'll format the columns to make them more evenly spaced
        table_rows.append(
            f"{world_name:<12}"
        )

    # Limit the number of rows per table message to avoid exceeding size limit
    chunk_size = 50  # Adjust this if necessary
    chunks = [table_rows[i:i + chunk_size] for i in range(0, len(table_rows), chunk_size)]

    # Send multiple embeds if necessary
    for i, chunk in enumerate(chunks):
        # Format the full table
        formatted_table = "\n".join([f"{row}" for row in chunk])

        # Create the embed with the table and headers
        embed = discord.Embed(
            title=f"Star Table {i + 1}",
            description=(
                f"{' | '.join(table_headers)}\n"  # Headers are only included once at the top
                f"{'-' * 50}\n"  # Divider between header and rows
                f"```{formatted_table}```"
            ),
            color=discord.Color.blue(),  # Embed color can be adjusted
        )
        embed.set_footer(text="Use /call to add details to the table!")

        try:
            table_message = await interaction.channel.send(embed=embed)
            table_data["message_id"] = table_message.id
            table_data["channel_id"] = interaction.channel.id

            # Initialize table entries as empty
            table_data["entries"] = [
                {"region": None, "size": None, "game_time": None}
                for _ in all_worlds
            ]

            # Send an ephemeral response to the user confirming success
            if i == 0:
                await interaction.response.send_message("Table created successfully!", ephemeral=True)
        except Exception as e:
            # Send an ephemeral response indicating failure
            await interaction.response.send_message(
                f"Failed to create the table. Error: {str(e)}", ephemeral=True
            )

# Run the bot
client.run(token)