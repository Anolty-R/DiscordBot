import discord
from discord.ext import tasks, commands
from datetime import datetime
import os
from dotenv import load_dotenv
import json

load_dotenv()

# Récupérer le token depuis le fichier .env
TOKEN = os.getenv("DISCORD_TOKEN")

def load_users():
    try:
        with open("users.json", "r") as file:
            return set(json.load(file))  # Convertit en set pour éviter les doublons
    except (FileNotFoundError, json.JSONDecodeError):
        return set()

def save_users():
    with open("users.json", "w") as file:
        json.dump(list(MENTIONED_USERS), file, indent=4)

def load_weekly_users():
    try:
        with open("weekly_users.json", "r") as file:
            return set(json.load(file))
    except (FileNotFoundError, json.JSONDecodeError):
        return set(MENTIONED_USERS)

def save_weekly_users():
    with open("weekly_users.json", "w") as file:
        json.dump(list(users_to_mention), file, indent=4)

intents = discord.Intents.default()
intents.members = True
intents.reactions = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

CHANNEL_ID = 0
MENTIONED_USERS = load_users()
users_to_mention = load_weekly_users()
users_who_reacted = set()
congrats_sent = False

# Événement déclenché quand le bot est prêt
@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user}")
    try:
        await bot.tree.sync()  # ✅ Force la synchronisation des commandes slash
        print("✅ Commandes slash synchronisées pour TOUS les serveurs !")
        commands = await bot.tree.fetch_commands()
        print("📜 Commandes disponibles :", [cmd.name for cmd in commands])
    except Exception as e:
        print(f"⚠️ Erreur de synchronisation des commandes : {e}")

    check_time.start()  # Démarrer la tâche dans on_ready()

# Commande pour se retirer des mentions de la semaine
@bot.tree.command(name="clear", description="Se retirer des mentions de la semaine")
async def clear(interaction: discord.Interaction):
    print(f"❌ {interaction.user} a retiré sa mention de la semaine")
    if interaction.user.id in users_to_mention:
        users_to_mention.remove(interaction.user.id)
        save_weekly_users()
        await interaction.response.send_message(f"✅ {interaction.user.mention} retiré des mentions cette semaine.", ephemeral=True)
    else:
        await interaction.response.send_message(f"⚠️ Tu n'es pas dans la liste des mentions.", ephemeral=True)

# Commande pour afficher le message journalier
@bot.tree.command(name="dailymessage", description="Renvoi (en message éphémère) l'exemple du message journalier")
async def dailymassage(interaction: discord.Interaction):
    print(f"📜 {interaction.user} a demandé l'exemple du message journalier")
    global congrats_sent

    channel = bot.get_channel(CHANNEL_ID)

    if users_to_mention:
        mentions = " ".join([f"<@{user_id}>" for user_id in users_to_mention])
        message = await interaction.response.send_message(f"📢 Rappel quotidien ! 📢\n Vous devez ajouter vos offres d'emplois sur iziA !! \n{mentions}", ephemeral=True)
    else:
        await interaction.response.send_message("🥳 Bien joué la TEAM ! 🥳\n Vous avez tous ajouté vos offres d'emplois sur iziA !!", ephemeral=True)

# Commande pour definir le channel pour le rappel
@bot.tree.command(name="setchannel", description="Définit le channel pour les rappels")
async def setchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    print(f"✅ {interaction.user} a défini le channel sur {channel}")
    global CHANNEL_ID
    CHANNEL_ID = channel.id
    await interaction.response.send_message(f"✅ Channel défini sur {channel.mention} !", ephemeral=True)

# Commande pour ajouter un utilisateur à la liste des mentions
@bot.tree.command(name="adduser", description="Ajoute un utilisateur à la liste des mentions")
async def adduser(interaction: discord.Interaction, member: discord.Member):
    if member.id not in MENTIONED_USERS:
        MENTIONED_USERS.add(member.id)
        users_to_mention.add(member.id)
        save_users()
        save_weekly_users()
        await interaction.response.send_message(f"✅ {member.mention} ajouté aux mentions !", ephemeral=True)
    else:
        await interaction.response.send_message(f"⚠️ {member.mention} est déjà dans la liste !", ephemeral=True)

# Commande pour lister les utilisateurs qui veulent etre mentionnés
@bot.tree.command(name="listuser", description="Liste des personnes mentionnées chaque semaine")
async def listuser(interaction: discord.Interaction):
    mentions = "\n".join([f"<@{user_id}>" for user_id in MENTIONED_USERS])
    await interaction.response.send_message(f"📜 Liste des mentions :\n{mentions}", ephemeral=True)

# Commande pour lister les utilisateurs mentionnés cette semaine
@bot.tree.command(name="listweekuser", description="Liste des mentions pour la semaine en cours")
async def listweekuser(interaction: discord.Interaction):
    mentions = "\n".join([f"<@{user_id}>" for user_id in users_to_mention])
    await interaction.response.send_message(f"📜 Mentions de la semaine :\n{mentions}", ephemeral=True)

# Commande pour retirer un utilisateur de la liste des mentions
@bot.tree.command(name="deluser", description="Supprime un utilisateur des mentions")
async def deluser(interaction: discord.Interaction, member: discord.Member):
    if member.id in MENTIONED_USERS:
        MENTIONED_USERS.remove(member.id)
        users_to_mention.discard(member.id)
        save_users()
        save_weekly_users()
        await interaction.response.send_message(f"✅ {member.mention} retiré des mentions !", ephemeral=True)
    else:
        await interaction.response.send_message(f"⚠️ {member.mention} n'est pas dans la liste !", ephemeral=True)

# Check toutes les minutes pour envoyer les messages aux bonnes heures
@tasks.loop(minutes=1)
async def check_time():
    now = datetime.now()
    if now.hour == 18 and now.minute == 0: # 18:00
        await send_daily_message()
    if now.weekday() == 6 and now.hour == 18 and now.minute == 0: # Dimanche 18:00
        await send_last_day_message()
    if now.weekday() == 6 and now.hour == 20 and now.minute == 0: # Dimanche 20:00
        await send_congrats_message()
    if now.weekday() == 0 and now.hour == 0 and now.minute == 0: # Lundi 00:00
        reset_mentions()

# Réinitialiser les mentions
def reset_mentions():
    global users_to_mention, users_who_reacted, congrats_sent
    users_to_mention = set(MENTIONED_USERS)
    users_who_reacted.clear()
    congrats_sent = False
    save_weekly_users()
    print("🔄 Mentions réinitialisées !")

# Envoyer le message quotidien
async def send_daily_message():
    global congrats_sent
    channel = bot.get_channel(CHANNEL_ID)
    if users_to_mention:
        mentions = " ".join([f"<@{user_id}>" for user_id in users_to_mention])
        message = await channel.send(f"📢 Rappel quotidien ! \n {mentions}")
        await message.add_reaction("✅")
    elif not congrats_sent:
        await channel.send("🥳 Bien joué la TEAM !")
        congrats_sent = True

# Envoyer le message de félicitations le dimanche
async def send_congrats_message():
    channel = bot.get_channel(CHANNEL_ID)
    mentions = " ".join([f"<@{user_id}>" for user_id in users_who_reacted])
    await channel.send(f"🎉 Félicitations à {mentions} pour leur participation !")

# Envoyer le dernier message d'alerte le dimanche
async def send_last_day_message():
    channel = bot.get_channel(CHANNEL_ID)
    mentions = " ".join([f"<@{user_id}>" for user_id in users_to_mention])
    await channel.send(f"📢 Dernier jour pour ajouter vos offres ! \n{mentions}")

# Événement déclenché quand un utilisateur réagit à un message
@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return
    if reaction.message.channel.id == CHANNEL_ID and user.id in users_to_mention:
        users_who_reacted.add(user.id)
        users_to_mention.discard(user.id)
        save_weekly_users()
        print(f"✅ {user.name} ne sera plus mentionné cette semaine.")

bot.run(TOKEN)
