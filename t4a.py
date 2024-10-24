import discord
from discord.ext import commands
import asyncio
import os
import json
import re
from random import randint
from discord.ui import Button, View
from datetime import datetime, timedelta


CREDITS_PER_LOOKUP = 1
BLACKLIST_FILE = "blacklist.json"

with open('config.json') as f:
    config = json.load(f)

def load_credits():
    if not os.path.exists("credits.json"):
        return {}
    with open("credits.json", "r") as f:
        return json.load(f)



def save_credits(credits):
    with open("credits.json", "w") as f:
        json.dump(credits, f, indent=4)


def load_blacklist():
    if not os.path.exists(BLACKLIST_FILE):
        return []
    with open(BLACKLIST_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_blacklist(blacklist):
    with open(BLACKLIST_FILE, 'w', encoding='utf-8') as f:
        json.dump(blacklist, f, indent=4)


async def check_and_deduct_credits(ctx, credits_required):
    credits = load_credits()
    user_credits = credits.get(str(ctx.author.id), 0)
    if user_credits < credits_required:
        await ctx.send("Vous n'avez pas assez de crédits pour effectuer cette recherche.")
        return False
    credits[str(ctx.author.id)] = user_credits - credits_required
    save_credits(credits)
    return True

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=config['prefix'], intents=intents)


@bot.event
async def on_ready():
    print(f'Connecté en tant que {bot.user}')

bot.remove_command('help')


@bot.command()
async def unbl(ctx, discord_id: int):
    """Déblackliste un ID Discord spécifique."""
    owner_role_id = int(config['owner_role_id']) 
    owner_role = discord.utils.get(ctx.guild.roles, id=owner_role_id)

    if owner_role not in ctx.author.roles:
        await ctx.send("Vous n'êtes pas autorisé à utiliser cette commande.")
        return

    blacklist = load_blacklist()

    if str(discord_id) not in blacklist:
        await ctx.send("Cet ID Discord n'est pas dans la liste des blacklists.")
        return

    blacklist.remove(str(discord_id))
    save_blacklist(blacklist)
    await ctx.send(f"L'ID Discord {discord_id} a été déblacklisté avec succès.")

async def fetch_user(discord_id):
    try:
        user = await bot.fetch_user(discord_id)
        return user
    except discord.NotFound:
        return None
    except discord.HTTPException:
        return None

async def fetch_user_name(discord_id):
    user = await fetch_user(discord_id)
    if user:
        return user.name
    return "Utilisateur inconnu"


@bot.command(name='lookup')
async def lookup(ctx, discord_id: str):
    if not re.match(r'^\d{17,19}$', discord_id):
        await ctx.send("L'ID doit être un ID Discord valide.")
        return

    if not await check_and_deduct_credits(ctx, CREDITS_PER_LOOKUP):
        return

    blacklist = load_blacklist()
    if f"discord:{discord_id}" in blacklist:
        await ctx.send("Cet ID est blacklisté et les informations ne peuvent pas être affichées.")
        return

    dump_directories = [
        "dump"
    ]

    results = []

    def get_random_color():
        return randint(0, 0xFFFFFF)

    user = await fetch_user(discord_id)
    if user:
        avatar_url = user.avatar.url 
    else:
        avatar_url = "https://cdn.discordapp.com/embed/avatars/0.png" 
    user_name = await fetch_user_name(discord_id)

    searching_embed = discord.Embed(
        title="",
        description="**<:loupe:1270171976308228187> Recherche dans la base de donnée**",
        color=get_random_color()
    )
    message = await ctx.send(embed=searching_embed)

    async def search_file(file_path, discord_id):
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                for line in file:
                    try:
                        data = json.loads(line)
                        identifiers = data.get("identifiers", [])
                        if f"discord:{discord_id}" in identifiers:
                            results.append({
                                "Server Name": os.path.splitext(os.path.basename(file_path))[0],
                                "Name": data.get("name", "?"),
                                "Discord ID": discord_id,
                                "Steam ID": next((id.split(":")[1] for id in identifiers if id.startswith("steam:")),
                                                 "?"),
                                "Xbox Live ID": next((id.split(":")[1] for id in identifiers if id.startswith("xbl:")),
                                                     "?"),
                                "Microsoft Live ID": next(
                                    (id.split(":")[1] for id in identifiers if id.startswith("live:")), "?"),
                                "FiveM ID": next((id.split(":")[1] for id in identifiers if id.startswith("fivem:")),
                                                 "?"),
                                "License ID": next(
                                    (id.split(":")[1] for id in identifiers if id.startswith("license:")), "?"),
                                "License 2 ID": next(
                                    (id.split(":")[1] for id in identifiers if id.startswith("license2:")), "?")
                            })
                    except json.JSONDecodeError:
                        pass
        except FileNotFoundError:
            pass

    tasks = []
    for dump_directory in dump_directories:
        for file_name in os.listdir(dump_directory):
            file_path = os.path.join(dump_directory, file_name)
            if not os.path.isdir(file_path):
                tasks.append(search_file(file_path, discord_id))

    await asyncio.gather(*tasks)

    credits = load_credits()
    remaining_credits = credits.get(str(ctx.author.id), 0)

    if results:
        current_page = 0

        def create_embed(page):
            result = results[page]
            embed = discord.Embed(
                title=f'<:loupe:1270171976308228187> Information de {user_name} ({discord_id})',
                color=get_random_color()
            )
            embed.add_field(name="📌 Server Name", value=f"`{result['Server Name']}`", inline=False)
            embed.add_field(name="📋 Name", value=f"`{result['Name']}`", inline=False)
            embed.add_field(name="<:n_id:1270174904712433788> Discord ID", value=f"`{result['Discord ID']}`", inline=False)
            embed.add_field(name="<:Steam_Logo:1271448222027616350> Steam ID", value=f"`{result['Steam ID']}`", inline=False)
            embed.add_field(name="<:Xbox_Player:1271448220685434910> Xbox Live ID", value=f"`{result['Xbox Live ID']}`", inline=False)
            embed.add_field(name="<:microsoft:1271448223692886079> Microsoft Live ID", value=f"`{result['Microsoft Live ID']}`", inline=False)
            embed.add_field(name="<:fivem:1270194510789345401> FiveM ID", value=f"`{result['FiveM ID']}`", inline=False)
            embed.add_field(name="<:list:1270174911444422728> License ID", value=f"`{result['License ID']}`", inline=False)
            embed.add_field(name="<:list:1270174911444422728> License 2 ID", value=f"`{result['License 2 ID']}`", inline=False)
            embed.set_footer(text=f"Crédits restants : {remaining_credits} | Page: {page + 1}/{len(results)} | © t4a#0001 ")
            embed.set_thumbnail(url=avatar_url)
            return embed

        embed = create_embed(current_page)
        await message.delete()
        message = await ctx.send(embed=embed)

        class LookupView(View):
            def __init__(self, *, timeout=60):
                super().__init__(timeout=timeout)

            @discord.ui.button(label="⬅️", style=discord.ButtonStyle.primary)
            async def previous_button(self, interaction: discord.Interaction, button: Button):
                nonlocal current_page
                if interaction.user != ctx.author:
                    await interaction.response.send_message("Vous n'êtes pas autorisé à utiliser ce bouton.", ephemeral=True)
                    return
                if current_page > 0:
                    current_page -= 1
                    await interaction.response.edit_message(embed=create_embed(current_page))

            @discord.ui.button(label="🗑", style=discord.ButtonStyle.danger)
            async def delete_button(self, interaction: discord.Interaction, button: Button):
                if interaction.user != ctx.author:
                    await interaction.response.send_message("Vous n'êtes pas autorisé à utiliser ce bouton.", ephemeral=True)
                    return
                await message.delete()
                await interaction.response.defer()
                self.stop()

            @discord.ui.button(label="📤", style=discord.ButtonStyle.secondary)
            async def private_message_button(self, interaction: discord.Interaction, button: Button):
                if interaction.user != ctx.author:
                    await interaction.response.send_message("Vous n'êtes pas autorisé à utiliser ce bouton.", ephemeral=True)
                    return
                await ctx.author.send(embed=embed)
                await interaction.response.send_message("Les informations ont été envoyées en message privé.", ephemeral=True)
                self.stop()

            @discord.ui.button(label="➡️", style=discord.ButtonStyle.primary)
            async def next_button(self, interaction: discord.Interaction, button: Button):
                nonlocal current_page
                if interaction.user != ctx.author:
                    await interaction.response.send_message("Vous n'êtes pas autorisé à utiliser ce bouton.", ephemeral=True)
                    return
                if current_page < len(results) - 1:
                    current_page += 1
                    await interaction.response.edit_message(embed=create_embed(current_page))

            @discord.ui.button(label="🔵", style=discord.ButtonStyle.secondary)
            async def steam_button(self, interaction: discord.Interaction, button: Button):
                if interaction.user != ctx.author:
                    await interaction.response.send_message("Vous n'êtes pas autorisé à utiliser ce bouton.", ephemeral=True)
                    return
                steam_id = results[current_page].get('Steam ID')
                if steam_id:
                    await interaction.response.send_message(f"Voici le lien Steam : https://steamcommunity.com/profiles/{steam_id}", ephemeral=True)
                else:
                    await interaction.response.send_message("Aucun Steam ID trouvé pour cet utilisateur.", ephemeral=True)

            @discord.ui.button(label="🟢", style=discord.ButtonStyle.secondary)
            async def xbox_button(self, interaction: discord.Interaction, button: Button):
                if interaction.user != ctx.author:
                    await interaction.response.send_message("Vous n'êtes pas autorisé à utiliser ce bouton.", ephemeral=True)
                    return
                xbox_id = results[current_page].get('Xbox Live ID')
                if xbox_id:
                    await interaction.response.send_message(f"Voici le lien Xbox Live : https://xboxgamertag.com/{xbox_id}", ephemeral=True)
                else:
                    await interaction.response.send_message("Aucun Xbox Live ID trouvé pour cet utilisateur.", ephemeral=True)

        view = LookupView()
        await message.edit(view=view)
    else:
        no_info_embed = discord.Embed(
            title="",
            description=f"**<:loupe:1270171976308228187> Aucun résultat trouvé pour {discord_id}**",
            color=0x808080
        )
        await message.delete()
        await ctx.send(embed=no_info_embed)

@bot.command()
async def balance(ctx, member: discord.Member = None):
    """Affiche le solde de crédits d'un utilisateur."""
    member = member or ctx.author
    credits = load_credits()
    user_id = str(member.id)
    embed = discord.Embed(title="Nombre de crédit au total :", color=0xffffff)
    embed.add_field(name="Membre :", value=member.mention)
    embed.add_field(name="Crédits :", value=credits.get(user_id, 0))
    await ctx.send(embed=embed)


@bot.command()
async def add(ctx, member: discord.Member, amount: int):
    """Ajoute des crédits à un utilisateur."""
    owner_role_id = int(config['owner_role_id'])
    owner_role = discord.utils.get(ctx.guild.roles, id=owner_role_id)

    if owner_role not in ctx.author.roles:
        await ctx.send("Vous n'êtes pas autorisé à utiliser cette commande.")
        return

    if amount <= 0:
        await ctx.send("Le montant doit être supérieur à zéro.")
        return

    credits = load_credits()
    user_id = str(member.id)
    credits[user_id] = credits.get(user_id, 0) + amount 
    save_credits(credits)
    await ctx.send(f"**{amount} crédits ont été ajoutés à {member.mention}.**")


@bot.command()
async def remove(ctx, member: discord.Member, amount: int):
    """Retire des crédits à un utilisateur."""
    owner_role_id = int(config['owner_role_id'])
    owner_role = discord.utils.get(ctx.guild.roles, id=owner_role_id)

    if owner_role not in ctx.author.roles:
        await ctx.send("Vous n'êtes pas autorisé à utiliser cette commande !")
        return

    if amount <= 0:
        await ctx.send("Le montant doit être supérieur à zéro.")
        return

    credits = load_credits() 
    user_id = str(member.id)
    
    if user_id not in credits or credits[user_id] < amount:
        await ctx.send(f"{member.mention} n'a pas assez de crédits.")
        return

    credits[user_id] -= amount  
    save_credits(credits)  
    await ctx.send(f"{amount} crédits ont été retirés à {member.mention}.")


@bot.command()
async def help(ctx):
    embed = discord.Embed(title="Liste Des Commandes", description="**Voici les Commandes disponible de ce bot :**",
                          color=0xffffff)
    embed.set_footer(text="")
    embed.add_field(name="lookup <id>", value="*Rechercher quelqu'un dans La Base de donnés.*", inline=False)
    embed.add_field(name="claim", value="*Permet de recevoir ses 10 crédits journaliers.*", inline=False)
    embed.add_field(name="balance", value="*Permet de voir combien de crédits nous avons.*", inline=False)
    embed.add_field(name="helpown", value="*Voir les commandes d'aide Owner*.", inline=False)
    await ctx.send(embed=embed)


@bot.command()
async def helpown(ctx):
    embed = discord.Embed(title="**__Liste Des Commandes Owners :__**", description="**Voici les Commandes Admins :**",
                          color=0xffffff)
    embed.set_footer(text="by t4a#0001")
    embed.add_field(name="add <@id> <nombre>", value="*Ajouté des crédits à quelqu'un.*", inline=False)
    embed.add_field(name="remove <@id> <nombre>", value="*Supprimé un nombre défini de crédits sur quelqu'un.*",
                    inline=False)
    embed.add_field(name="bl <id>", value="*Permet de blacklist une id.*", inline=False)
    embed.add_field(name="unbl <id>", value="*Permet de unblacklist une id.*", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def blacklist(ctx, member: discord.Member):
    """Ajoute un utilisateur à la blacklist."""
    owner_role_id = int(config['owner_role_id'])  
    owner_role = discord.utils.get(ctx.guild.roles, id=owner_role_id)

    if owner_role not in ctx.author.roles:
        await ctx.send("Vous n'êtes pas autorisé à utiliser cette commande.")
        return

    blacklist = load_blacklist()
    user_id = str(member.id)

    if user_id in blacklist:
        await ctx.send(f"{member.mention} est déjà dans la blacklist.")
        return

    blacklist.append(user_id)
    save_blacklist(blacklist)  
    await ctx.send(f"**{member.mention} a été ajouté à la blacklist.**")


@bot.command()
async def claim(ctx):
    """Réclame des crédits toutes les 12 heures."""
    user_id = str(ctx.author.id)
    credits = load_credits()

    if user_id not in credits:
        credits[user_id] = 0

    last_claim_time = credits.get(user_id + "_last_claim", None)

    if last_claim_time is not None:
        last_claim_time = datetime.fromisoformat(last_claim_time)
        if datetime.now() - last_claim_time < timedelta(hours=12):
            await ctx.send("Vous avez déjà réclamé vos crédits pour les 12 dernières heures.")
            return

    credits[user_id] += 10
    credits[user_id + "_last_claim"] = datetime.now().isoformat()

    save_credits(credits)
    await ctx.send("**Vous avez reçu vos `10` crédits avec succès.**")


async def check_and_deduct_credits(ctx, amount):
    user_id = str(ctx.author.id)
    credits = load_credits()

    if credits.get(user_id, 0) < amount:
        await ctx.send("Vous n'avez pas assez de crédits pour effectuer cette action.")
        return False

    credits[user_id] -= amount
    save_credits(credits)
    return True
@bot.event
async def on_ready():
    activity = discord.Streaming(name="by t4a#0001", url="https://www.twitch.tv/amouranth")
    await bot.change_presence(activity=activity)
    print(f'Logged in as {bot.user.name}')


bot.run(config['token'])
