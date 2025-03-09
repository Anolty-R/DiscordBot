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
        return set()  # Retourne un set vide si le fichier n'existe pas ou est corrompu


intents = discord.Intents.default()
intents.members = True  # ✅ Active l'intent pour récupérer les membres
intents.reactions = True  # ✅ Nécessaire pour suivre les réactions
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree  # Accès aux commandes slash

CHANNEL_ID = 0  # ID du channel pour les rappels
MENTIONED_USERS = load_users()  # Liste des utilisateurs à mentionner
users_to_mention = set(MENTIONED_USERS)
users_who_reacted = set()
congrats_sent = False  # ✅ Ajout de cette variable pour éviter les doublons

def save_users():
    with open("users.json", "w") as file:
        json.dump(list(MENTIONED_USERS), file, indent=4)  # Convertit en liste avant d'enregistrer


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

    check_time.start()  # ✅ Démarrer la tâche dans on_ready()

# Commande pour afficher le message journalier
@bot.tree.command(name="dailymessage", description="Renvoi (en message éphémère) l'exemple du message journalier")
async def dailymassage(interaction: discord.Interaction):
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
    global CHANNEL_ID
    CHANNEL_ID = channel.id
    await interaction.response.send_message(f"✅ Channel défini sur {channel.mention} !", ephemeral=True)

# Commande pour ajouter un utilisateur
@bot.tree.command(name="adduser", description="Ajoute un utilisateur à la liste des mentions")
async def adduser(interaction: discord.Interaction, member: discord.Member):
    if member.id not in MENTIONED_USERS:
        MENTIONED_USERS.add(member.id)
        users_to_mention.add(member.id)
        save_users()  # ✅ Sauvegarde dans le JSON
        await interaction.response.send_message(f"✅ {member.mention} ajouté à la liste des mentions !", ephemeral=True)
    else:
        await interaction.response.send_message(f"⚠️ {member.mention} est déjà dans la liste !", ephemeral=True)

# Commande pour lister les utilisateurs
@bot.tree.command(name="listuser", description="Donne la liste des personnes à mentionner")
async def listuser(interaction: discord.Interaction):
    if MENTIONED_USERS:
        mentions = "\n".join([f"<@{user_id}>" for user_id in MENTIONED_USERS])
        await interaction.response.send_message(f"📜 Liste des mentions :\n{mentions}", ephemeral=True)
    else:
        await interaction.response.send_message("⚠️ Aucun utilisateur à mentionner !", ephemeral=True)

# Commande pour supprimer un utilisateur
@bot.tree.command(name="deluser", description="Supprime un utilisateur de la liste des mentions")
async def deluser(interaction: discord.Interaction, member: discord.Member):
    if member.id in MENTIONED_USERS:
        MENTIONED_USERS.remove(member.id)
        users_to_mention.discard(member.id)
        save_users()  # ✅ Sauvegarde dans le JSON
        await interaction.response.send_message(f"✅ {member.mention} retiré de la liste des mentions !", ephemeral=True)
    else:
        await interaction.response.send_message(f"⚠️ {member.mention} n'est pas dans la liste !", ephemeral=True)

# Vérifie l'heure et envoie un message quotidien à 18h00
@tasks.loop(minutes=1)
async def check_time():
    now = datetime.now()
    if now.hour == 18 and now.minute == 0:
        await send_daily_message()
    if now.weekday() == 6 and now.hour == 18 and now.minute == 0:  # Dimanche 18h00
        await send_last_day_message()
    if now.weekday() == 6 and now.hour == 20 and now.minute == 0:  # Dimanche 20h00
        await send_congrats_message()
    if now.weekday() == 0 and now.hour == 0 and now.minute == 0:  # Lundi minuit
        reset_mentions()

# Réinitialisation de la liste des mentions chaque semaine
def reset_mentions():
    global users_to_mention, users_who_reacted, congrats_sent
    users_to_mention = set(MENTIONED_USERS)
    users_who_reacted.clear()
    congrats_sent = False  # ✅ Réinitialise le message de félicitations chaque semaine
    print("🔄 Mentions et félicitations réinitialisées !")

# Envoi du message quotidien
async def send_daily_message():
    global congrats_sent

    channel = bot.get_channel(CHANNEL_ID)

    if users_to_mention:
        mentions = " ".join([f"<@{user_id}>" for user_id in users_to_mention])
        message = await channel.send(f"📢 Rappel quotidien ! 📢\n Vous devez ajouter vos offres d'emplois sur iziA !! \n{mentions}")
        await message.add_reaction("✅")
    else:
        if not congrats_sent:  # ✅ Vérifie si le message a déjà été envoyé cette semaine
            await channel.send("🥳 Bien joué la TEAM ! 🥳\n Vous avez tous ajouté vos offres d'emplois sur iziA !!")
            congrats_sent = True  # ✅ Empêche l'envoi du message plusieurs fois

# Envoi du message de félicitations le dimanche
async def send_congrats_message():
    channel = bot.get_channel(CHANNEL_ID)
    mentions = " ".join([f"<@{user_id}>" for user_id in users_who_reacted])
    message = await channel.send(f"🎉 Félicitations à {mentions} pour avoir ajouté leurs offres d'emplois sur iziA cette semaine ! 🎉")
    await message.add_reaction("👏")

# Envoi du message pour le dernier jour de la semaine
async def send_last_day_message():
    channel = bot.get_channel(CHANNEL_ID)
    mentions = " ".join([f"<@{user_id}>" for user_id in users_to_mention])
    message = await channel.send(f"📢 Dernier jour pour ajouter vos offres d'emplois sur iziA !! \n{mentions}")
    await message.add_reaction("✅")

# Suivi des réactions pour retirer les utilisateurs mentionnés
@bot.event
async def on_reaction_add(reaction, user):
    global users_to_mention, users_who_reacted
    if user.bot:
        return
    if reaction.message.channel.id == CHANNEL_ID and user.id in users_to_mention:
        users_who_reacted.add(user.id)
        users_to_mention.discard(user.id)
        print(f"✅ {user.name} a réagi, il ne sera plus mentionné cette semaine.")

# Lancement du bot
bot.run(TOKEN)
