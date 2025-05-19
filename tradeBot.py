import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput
import json
import os

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

DATA_FILE = "shop_data.json"
points_file = 'points.json'
INFINITE_USER_ID = 1279782282919678006  # Replace with your user ID

# ----- Modal for Purchase Info + Custom Role Selection -----


# ----- File Loaders & Savers -----
def load_shop_items():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            return [item for item in data if isinstance(item, dict) and 'name' in item and 'price' in item]
    return []

def save_shop_items():
    with open(DATA_FILE, "w") as f:
        json.dump(shop_items, f)

shop_items = load_shop_items()

if os.path.exists(points_file):
    with open(points_file, 'r') as f:
        user_points = json.load(f)
        user_points = {int(k): v for k, v in user_points.items()}
else:
    user_points = {}

def save_points():
    with open(points_file, 'w') as f:
        json.dump(user_points, f)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    isEvent = input("Is this a new event? (y/n): ").strip().lower()
    if isEvent == 'y':
        Channel = bot.get_channel(1358681114784432289)
        await Channel.send("📢 @everyone you can now farm xp")  # Replace with your channel ID


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    user_id = message.author.id
    user_points[user_id] = user_points.get(user_id, 0) + 1
    save_points()
    await bot.process_commands(message)

class AddItemModal(Modal, title="🛍️ Add Shop Item"):
    item_name = TextInput(label="Item Name", placeholder="Enter the item name...", max_length=50)
    item_price = TextInput(label="Item Price", placeholder="Enter the price of the item...", max_length=10)

    async def on_submit(self, interaction: discord.Interaction):
        item_name = self.item_name.value
        item_price = self.item_price.value

        try:
            price = float(item_price)
            if price <= 0:
                await interaction.response.send_message("❌ The price must be greater than 0!", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("❌ The price must be a valid number!", ephemeral=True)
            return

        item = {"name": item_name, "price": price}
        shop_items.append(item)
        save_shop_items()
        await interaction.response.send_message(f"✅ Added `{item_name}` with price `{price}` to the shop!", ephemeral=True)

class AddItemView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Add Item", style=discord.ButtonStyle.green)
    async def add_item(self, interaction: discord.Interaction):
        await interaction.response.send_modal(AddItemModal())

@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="🛠️ Help Menu",
        description="Here are the commands you can use:",
        color=discord.Color.blue()
    )
    embed.add_field(name="!shop", value="View the shop items.", inline=False)
    embed.add_field(name="!buy <item_number> <role_name>", value="Buy an item from the shop.", inline=False)
    embed.add_field(name="!score", value="Check your current points.", inline=False)
    embed.add_field(name="!shop_add", value="Add an item to the shop (Admin only).", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def score(ctx):
    user_id = ctx.author.id
    points = "∞" if user_id == INFINITE_USER_ID else user_points.get(user_id, 0)

    embed = discord.Embed(
        title="📊 Your Score",
        description=f"{ctx.author.mention}, you have **{points}** points!",
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def shop_add(ctx):
    view = AddItemView()
    await ctx.send("🛒 Click below to add an item to the shop!", view=view)

@bot.command()
async def shop(ctx):
    if not shop_items:
        await ctx.send("🛒 The shop is currently empty.")
        return

    embed = discord.Embed(
        title="🛍️ Item Shop",
        description="Here’s what you can buy with your points:",
        color=discord.Color.blurple()
    )

    for index, item in enumerate(shop_items, start=1):
        embed.add_field(
            name=f"{index}. {item['name']}",
            value=f"💰 **Price:** {item['price']} points",
            inline=False
        )

    await ctx.send(embed=embed)

@bot.command()
async def buy(ctx, item_number: int, *, role_name: str):
    # Check if the item number is valid
    if item_number < 1 or item_number > len(shop_items):
        await ctx.send("❌ Invalid item number!")
        return

    item = shop_items[item_number - 1]  # Get the item based on the user's input
    price = item['price']
    guild = ctx.guild
    user_id = ctx.author.id
    member = guild.get_member(user_id)

    if not member:
        await ctx.send("❌ Could not find your member object in this guild.")
        return

    # Try to find the role by name, or create it if it doesn't exist
    role = discord.utils.find(lambda r: r.name.lower() == role_name.lower(), guild.roles)
    if not role:
        try:
            role = await guild.create_role(name=role_name, mentionable=True)
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to create roles!")
            return
        except discord.HTTPException as e:
            await ctx.send(f"❌ Failed to create role: {e}")
            return

    # If the user has infinite points (you can bypass the price)
    if user_id == INFINITE_USER_ID:
        try:
            await member.add_roles(role)
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to assign roles!")
            return
        except discord.HTTPException as e:
            await ctx.send(f"❌ Failed to assign role: {e}")
            return

        embed = discord.Embed(
            title="📦 Order Summary",
            description="Here are your purchase details:",
            color=discord.Color.gold()
        )
        embed.add_field(name="🛍️ Item", value=item['name'], inline=True)
        embed.add_field(name="💰 Price", value=f"{price} points", inline=True)
        embed.add_field(name="🏷️ Role Assigned", value=role.name, inline=True)
        embed.set_footer(text="Thank you for shopping!")
        await ctx.send(embed=embed)
        return

    # Check if the user has enough points to make the purchase
    if user_points.get(user_id, 0) < price:
        await ctx.send("❌ You don't have enough points to buy this item!")
        return

    # Deduct points for the purchase
    user_points[user_id] -= price
    save_points()

    # Assign the role to the user
    try:
        await member.add_roles(role)
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to assign roles!")
        return
    except discord.HTTPException as e:
        await ctx.send(f"❌ Failed to assign role: {e}")
        return

    # Create an embed with the purchase details
    embed = discord.Embed(
        title="📦 Order Summary",
        description="Here are your purchase details:",
        color=discord.Color.green()
    )
    embed.add_field(name="🛍️ Item", value=item['name'], inline=True)
    embed.add_field(name="💰 Price", value=f"{price} points", inline=True)
    embed.add_field(name="🏷️ Role Assigned", value=role.name, inline=True)
    embed.set_footer(text="Thank you for shopping!")
    
    # Send the confirmation embed to the user
    await ctx.send(embed=embed)




bot.run("")
