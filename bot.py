import discord
from discord.ext import tasks, commands
from datetime import datetime
import os
from dotenv import load_dotenv
import json
import locale
import sys
import tkinter as tk
from tkinter import messagebox

# Charger les variables d'environnement
load_dotenv()
locale.setlocale(locale.LC_TIME, "fr_FR.UTF-8")

# Créer le dossier "json" s'il n'existe pas
if not os.path.exists("json"):
    os.makedirs("json")

# Créer le fichier "reminders.json" s'il n'existe pas
if not os.path.exists("json/reminders.json"):
    with open("json/reminders.json", "w") as file:
        json.dump([], file, indent=4)

# Créer un fichier .env s'il n'existe pas et demander à l'utilisateur de le remplir
if not os.path.exists(".env"):
    print(
        "⚠️ Dans votre nouveau fichier .env, ajoutez votre token Discord en remplaçant 'your_token_here' par votre token.")
    with open(".env", "w") as file:
        file.write("DISCORD_TOKEN=your_token_here\n")
        fenetre = tk.Tk()
        fenetre.withdraw()
        messagebox.showerror("Erreur",
                             "Votre fichier .env n'existe pas. Un nouveau fichier a été créé. Veuillez le remplir avec votre token Discord.")
        fenetre.destroy()
        sys.exit()

# Récupérer le token depuis le fichier .env
TOKEN = os.getenv("DISCORD_TOKEN")

# Configurer les intentions du bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True
intents.messages = True
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree


@tasks.loop(minutes=1)
async def check_time():
    # Vérifier et envoyer les rappels à l'heure spécifiée
    await check_and_send_reminders()


@bot.event
async def on_ready():
    # Événement déclenché lorsque le bot est prêt
    print(f"✅ Connecté en tant que {bot.user}")
    try:
        await bot.tree.sync()
        print("✅ Commandes slash synchronisées pour TOUS les serveurs !")
        commands = await bot.tree.fetch_commands()
        print("📜 Commandes disponibles :", [cmd.name for cmd in commands])
    except Exception as e:
        print(f"⚠️ Erreur de synchronisation des commandes : {e}")

    # Démarrer les tâches si elles ne sont pas déjà en cours
    if not check_time.is_running():
        check_time.start()

    if not reset_remaining_users.is_running():
        reset_remaining_users.start()


@bot.tree.command(name="addreminder",
                  description="Ajoute un rappel personnalisé. La fréquence peut être 'tous les jours' ou une liste 'lundi, mardi'.")
async def addreminder(interaction: discord.Interaction, nom: str, heure: str, frequence: str, contenu: str):
    """
    Ajoute un rappel personnalisé.
    - nom : Nom unique du rappel
    - heure : Heure au format HH:MM (exemple : 18:30)
    - frequence : Jours spécifiques ('lundi, mardi') ou 'tous les jours'
    - contenu : Contenu du message (utilisez \\n pour les retours à la ligne)
    """
    try:
        # Vérifier le format de l'heure
        datetime.strptime(heure, "%H:%M")

        # Valider les jours spécifiés
        jours_valides = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche", "tous les jours"]
        jours_specifies = [jour.strip().lower() for jour in frequence.split(",")]

        if "tous les jours" in jours_specifies:
            jours_specifies = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]

        if not all(jour in jours_valides for jour in jours_specifies):
            raise ValueError(
                "Fréquence invalide. Utilisez 'tous les jours' ou une liste de jours valides (exemple : 'lundi, mardi').")

        # Charger les rappels existants
        try:
            with open("json/reminders.json", "r") as file:
                reminders = json.load(file)
        except FileNotFoundError:
            reminders = []

        # Vérifier si un rappel avec le même nom existe déjà
        if any(reminder["nom"] == nom for reminder in reminders):
            await interaction.response.send_message(f"⚠️ Un rappel avec le nom `{nom}` existe déjà.", ephemeral=True)
            return

        # Remplacer les séquences \n par de véritables retours à la ligne
        contenu = contenu.replace("\\n", "\n")

        # Ajouter le nouveau rappel
        reminders.append({
            "nom": nom,
            "heure": heure,
            "jours": jours_specifies,
            "contenu": contenu,
        })

        # Sauvegarder les rappels dans le fichier JSON
        with open("json/reminders.json", "w") as file:
            json.dump(reminders, file, indent=4)

        # Créer des fichiers JSON vides pour le rappel
        with open(f"json/{nom}_reminder_users.json", "w") as file:
            json.dump({"users": []}, file, indent=4)

        with open(f"json/{nom}_remaining_users.json", "w") as file:
            json.dump({"users": []}, file, indent=4)

        # Créer un fichier JSON pour stocker un channel_id par défaut
        with open(f"json/{nom}_channel.json", "w") as file:
            json.dump({"channel_id": 0}, file, indent=4)

        await interaction.response.send_message(
            f"✅ Rappel ajouté : {nom} - {contenu} à {heure} pour les jours {', '.join(jours_specifies)}. "
            f"Les fichiers JSON ont été créés, avec un channel par défaut.",
            ephemeral=True
        )
    except ValueError as e:
        await interaction.response.send_message(f"⚠️ {str(e)}", ephemeral=True)


@bot.tree.command(name="delreminder", description="Supprime un rappel existant par son nom")
async def delreminder(interaction: discord.Interaction, nom: str):
    """
    Supprime un rappel existant et ses fichiers associés.
    - nom : Nom unique du rappel
    """
    try:
        with open("json/reminders.json", "r") as file:
            reminders = json.load(file)

        # Filtrer les rappels pour exclure celui avec le nom donné
        updated_reminders = [reminder for reminder in reminders if reminder["nom"] != nom]

        if len(updated_reminders) == len(reminders):
            await interaction.response.send_message(f"⚠️ Aucun rappel trouvé avec le nom `{nom}`.", ephemeral=True)
            return

        with open("json/reminders.json", "w") as file:
            json.dump(updated_reminders, file, indent=4)

        # Supprimer les fichiers JSON associés au rappel
        try:
            os.remove(f"json/{nom}_reminder_users.json")
        except FileNotFoundError:
            pass

        try:
            os.remove(f"json/{nom}_remaining_users.json")
        except FileNotFoundError:
            pass

        try:
            os.remove(f"json/{nom}_channel.json")  # Supprimer le fichier du channel
        except FileNotFoundError:
            pass

        await interaction.response.send_message(f"✅ Rappel `{nom}` et ses fichiers associés supprimés avec succès.",
                                                ephemeral=True)
    except FileNotFoundError:
        await interaction.response.send_message("⚠️ Fichier de rappels introuvable.", ephemeral=True)


@bot.tree.command(name="listreminders", description="Liste tous les noms des rappels existants")
async def listreminders(interaction: discord.Interaction):
    """
    Liste tous les noms des rappels existants.
    """
    try:
        with open("json/reminders.json", "r") as file:
            reminders = json.load(file)

        if not reminders:
            await interaction.response.send_message("📋 Aucun rappel n'est enregistré.", ephemeral=True)
            return

        reminder_names = [reminder["nom"] for reminder in reminders]
        response = "📋 **Liste des rappels :**\n" + "\n".join(f"- {name}" for name in reminder_names)
        await interaction.response.send_message(response, ephemeral=True)
    except FileNotFoundError:
        await interaction.response.send_message("⚠️ Fichier de rappels introuvable.", ephemeral=True)


@bot.tree.command(name="affichecara", description="Affiche les détails d'un rappel spécifique")
async def affichecara(interaction: discord.Interaction, nom: str):
    """
    Affiche les détails d'un rappel spécifique.
    - nom : Nom unique du rappel
    """
    try:
        # Charger les détails du rappel
        with open("json/reminders.json", "r") as file:
            reminders = json.load(file)

        reminder = next((r for r in reminders if r["nom"] == nom), None)

        if not reminder:
            await interaction.response.send_message(f"⚠️ Aucun rappel trouvé avec le nom `{nom}`.", ephemeral=True)
            return

        # Charger le channel associé
        try:
            with open(f"json/{nom}_channel.json", "r") as file:
                channel_data = json.load(file)
                channel_id = channel_data.get("channel_id", None)
                channel = bot.get_channel(channel_id) if channel_id else None
        except FileNotFoundError:
            channel = None

        # Construire la réponse
        channel_name = channel.mention if channel else "Non défini"
        response = (
            f"📋 **Détails du rappel `{nom}`**\n"
            f"- **Heure d'envoi** : {reminder['heure']}\n"
            f"- **Channel** : {channel_name}\n"
            f"- **Fréquence** : {', '.join(reminder['jours'])}"
        )
        await interaction.response.send_message(response, ephemeral=True)

    except FileNotFoundError:
        await interaction.response.send_message("⚠️ Fichier de rappels introuvable.", ephemeral=True)


@bot.tree.command(name="clear", description="Se retirer des mentions de la semaine pour un rappel spécifique")
async def clear(interaction: discord.Interaction, nom: str):
    """
    Se retirer des mentions de la semaine pour un rappel spécifique.
    - nom : Nom unique du rappel
    """
    try:
        # Charger le fichier des utilisateurs restants pour le rappel
        with open(f"json/{nom}_remaining_users.json", "r") as file:
            remaining_users = json.load(file)

        if interaction.user.id in remaining_users["users"]:
            remaining_users["users"].remove(interaction.user.id)

            # Sauvegarder les modifications
            with open(f"json/{nom}_remaining_users.json", "w") as file:
                json.dump(remaining_users, file, indent=4)

            await interaction.response.send_message(
                f"❌ {interaction.user.mention} retiré des mentions pour le rappel `{nom}` cette semaine.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"⚠️ Tu n'es pas dans la liste des mentions pour le rappel `{nom}`.",
                ephemeral=True
            )
    except FileNotFoundError:
        await interaction.response.send_message(
            f"⚠️ Le rappel `{nom}` n'existe pas ou le fichier associé est introuvable.",
            ephemeral=True
        )


# Commande pour définir le channel pour le rappel
@bot.tree.command(name="setchannel", description="Définit le channel pour un rappel spécifique")
async def setchannel(interaction: discord.Interaction, nom: str, channel: discord.TextChannel):
    print(f"✅ {interaction.user} a défini le channel sur {channel} pour le rappel {nom}")
    try:
        with open("json/reminders.json", "r") as file:
            reminders = json.load(file)

        if not any(reminder["nom"] == nom for reminder in reminders):
            await interaction.response.send_message(f"⚠️ Aucun rappel trouvé avec le nom `{nom}`.", ephemeral=True)
            return

        with open(f"json/{nom}_channel.json", "w") as file:
            json.dump({"channel_id": channel.id}, file, indent=4)

        await interaction.response.send_message(f"✅ Channel défini sur {channel.mention} pour le rappel `{nom}` !",
                                                ephemeral=True)
    except FileNotFoundError:
        await interaction.response.send_message("⚠️ Fichier de rappels introuvable.", ephemeral=True)


# Commande pour ajouter un utilisateur à la liste des mentions
@bot.tree.command(name="adduser", description="Ajoute un utilisateur à la liste des mentions pour un rappel spécifique")
async def adduser(interaction: discord.Interaction, nom: str, member: discord.Member):
    print(f"✅ {interaction.user} a ajouté {member} aux mentions pour le rappel {nom}")
    try:
        # Mettre à jour reminder_users
        with open(f"json/{nom}_reminder_users.json", "r") as file:
            reminder_users = json.load(file)

        if member.id not in reminder_users["users"]:
            reminder_users["users"].append(member.id)
            with open(f"json/{nom}_reminder_users.json", "w") as file:
                json.dump(reminder_users, file, indent=4)

        # Mettre à jour remaining_users
        with open(f"json/{nom}_remaining_users.json", "r") as file:
            remaining_users = json.load(file)

        if member.id not in remaining_users["users"]:
            remaining_users["users"].append(member.id)
            with open(f"json/{nom}_remaining_users.json", "w") as file:
                json.dump(remaining_users, file, indent=4)

        await interaction.response.send_message(
            f"✅ {member.mention} ajouté aux mentions pour le rappel `{nom}` dans les deux listes !", ephemeral=True
        )
    except FileNotFoundError:
        await interaction.response.send_message(
            f"⚠️ Le rappel `{nom}` n'existe pas ou les fichiers associés sont introuvables.", ephemeral=True
        )


@bot.tree.command(name="deluser", description="Supprime un utilisateur des mentions pour un rappel spécifique")
async def deluser(interaction: discord.Interaction, nom: str, member: discord.Member):
    print(f"❌ {interaction.user} a retiré {member} des mentions pour le rappel {nom}")
    try:
        # Supprimer de reminder_users
        with open(f"json/{nom}_reminder_users.json", "r") as file:
            reminder_users = json.load(file)

        if member.id in reminder_users["users"]:
            reminder_users["users"].remove(member.id)
            with open(f"json/{nom}_reminder_users.json", "w") as file:
                json.dump(reminder_users, file, indent=4)
            print(f"❌ {member.mention} retiré de `reminder_users` pour `{nom}`.")

        # Supprimer de remaining_users
        with open(f"json/{nom}_remaining_users.json", "r") as file:
            remaining_users = json.load(file)

        if member.id in remaining_users["users"]:
            remaining_users["users"].remove(member.id)
            with open(f"json/{nom}_remaining_users.json", "w") as file:
                json.dump(remaining_users, file, indent=4)
            print(f"❌ {member.mention} retiré de `remaining_users` pour `{nom}`.")

        await interaction.response.send_message(
            f"❌ {member.mention} retiré des deux listes pour le rappel `{nom}` !", ephemeral=True
        )
    except FileNotFoundError:
        await interaction.response.send_message(
            f"⚠️ Le rappel `{nom}` n'existe pas ou les fichiers associés sont introuvables.", ephemeral=True
        )


# Commande pour retirer un utilisateur des remaining_users pour un rappel spécifique
@bot.tree.command(name="addreactuser",
                  description="Retire un utilisateur des remaining_users pour un rappel spécifique")
async def addreactuser(interaction: discord.Interaction, nom: str, member: discord.Member):
    """
    Retire un utilisateur des remaining_users pour un rappel spécifique.
    - nom : Nom unique du rappel
    - member : Utilisateur Discord à retirer
    """
    try:
        with open(f"json/{nom}_remaining_users.json", "r") as file:
            remaining_users = json.load(file)

        if member.id in remaining_users["users"]:
            remaining_users["users"].remove(member.id)
            with open(f"json/{nom}_remaining_users.json", "w") as file:
                json.dump(remaining_users, file, indent=4)

            await interaction.response.send_message(
                f"✅ {member.mention} sera mentionné par le rappel `{nom}`.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"⚠️ {member.mention} n'est pas dans la liste des mentions pour le rappel `{nom}`.", ephemeral=True
            )
    except FileNotFoundError:
        await interaction.response.send_message(
            f"⚠️ Le rappel `{nom}` n'existe pas ou le fichier associé est introuvable.", ephemeral=True
        )


# Commande pour ajouter un utilisateur dans remaining_users pour un rappel spécifique
@bot.tree.command(name="delreactuser",
                  description="Ajoute un utilisateur dans remaining_users pour un rappel spécifique")
async def delreactuser(interaction: discord.Interaction, nom: str, member: discord.Member):
    """
    Ajoute un utilisateur dans remaining_users pour un rappel spécifique.
    - nom : Nom unique du rappel
    - member : Utilisateur Discord à ajouter
    """
    try:
        with open(f"json/{nom}_remaining_users.json", "r") as file:
            remaining_users = json.load(file)

        if member.id not in remaining_users["users"]:
            remaining_users["users"].append(member.id)
            with open(f"json/{nom}_remaining_users.json", "w") as file:
                json.dump(remaining_users, file, indent=4)

            await interaction.response.send_message(
                f"❌ {member.mention} ne sera plus mentionné par le rappel `{nom}`.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"⚠️ {member.mention} est déjà dans la liste des mentions pour le rappel `{nom}`.", ephemeral=True
            )
    except FileNotFoundError:
        await interaction.response.send_message(
            f"⚠️ Le rappel `{nom}` n'existe pas ou le fichier associé est introuvable.", ephemeral=True
        )


# Commande pour lister les utilisateurs mentionnés pour un rappel spécifique
@bot.tree.command(name="listuser", description="Liste les utilisateurs mentionnés pour un rappel spécifique")
async def listuser(interaction: discord.Interaction, nom: str):
    """
    Liste les utilisateurs mentionnés pour un rappel spécifique.
    """
    try:
        with open(f"json/{nom}_reminder_users.json", "r") as file:
            reminder_users = json.load(file)

        mentions = "\n".join([f"<@{user_id}>" for user_id in reminder_users["users"]])
        await interaction.response.send_message(f"📜 Liste des mentions pour `{nom}` :\n{mentions}", ephemeral=True)
    except FileNotFoundError:
        await interaction.response.send_message(
            f"⚠️ Le rappel `{nom}` n'existe pas ou le fichier associé est introuvable.", ephemeral=True
        )


# Commande pour lister les utilisateurs mentionnés cette semaine pour un rappel spécifique
@bot.tree.command(name="listweekuser",
                  description="Liste les utilisateurs mentionnés cette semaine pour un rappel spécifique")
async def listweekuser(interaction: discord.Interaction, nom: str):
    """
    Liste les utilisateurs présents dans remaining_users pour un rappel spécifique.
    """
    try:
        with open(f"json/{nom}_remaining_users.json", "r") as file:
            remaining_users = json.load(file)

        mentions = "\n".join([f"<@{user_id}>" for user_id in remaining_users["users"]])
        await interaction.response.send_message(f"📜 Utilisateurs à mentionner pour `{nom}` cette semaine :\n{mentions}",
                                                ephemeral=True)
    except FileNotFoundError:
        await interaction.response.send_message(
            f"⚠️ Le rappel `{nom}` n'existe pas ou le fichier `remaining_users` est introuvable.", ephemeral=True
        )


# Commande pour lister les utilisateurs ayant ajouté une réaction / utilisé la commande /clear
@bot.tree.command(name="listreactuser",
                  description="Liste les utilisateurs dans reminder_users mais pas dans remaining_users")
async def listreactuser(interaction: discord.Interaction, nom: str):
    """
    Liste les utilisateurs présents dans reminder_users mais pas dans remaining_users pour un rappel spécifique.
    """
    try:
        with open(f"json/{nom}_reminder_users.json", "r") as reminder_file:
            reminder_users = json.load(reminder_file)

        with open(f"json/{nom}_remaining_users.json", "r") as remaining_file:
            remaining_users = json.load(remaining_file)

        # Trouver les utilisateurs dans reminder_users mais pas dans remaining_users
        diff_users = set(reminder_users["users"]) - set(remaining_users["users"])
        mentions = "\n".join([f"<@{user_id}>" for user_id in diff_users])

        await interaction.response.send_message(
            f"📜 Utilisateurs dans `reminder_users` mais pas dans `remaining_users` pour `{nom}` :\n{mentions}",
            ephemeral=True
        )
    except FileNotFoundError:
        await interaction.response.send_message(
            f"⚠️ Le rappel `{nom}` n'existe pas ou les fichiers associés sont introuvables.", ephemeral=True
        )


# Événement déclenché quand un utilisateur réagit à un message
@bot.event
async def on_raw_reaction_add(payload):
    print(f"🚀 Réaction captée ! Utilisateur: {payload.user_id} - Emoji: {payload.emoji}")
    if payload.user_id == bot.user.id:
        print("🤖 Réaction ignorée (bot)")
        return

    try:
        with open("json/reminders.json", "r") as file:
            reminders = json.load(file)

        for reminder in reminders:
            nom = reminder["nom"]
            try:
                with open(f"json/{nom}_remaining_users.json", "r") as file:
                    remaining_users = json.load(file)

                if payload.user_id in remaining_users["users"]:
                    if payload.emoji.name == "✅":
                        remaining_users["users"].remove(payload.user_id)
                        with open(f"json/{nom}_remaining_users.json", "w") as file:
                            json.dump(remaining_users, file, indent=4)
                        print(f"✅ {payload.user_id} ne sera plus mentionné pour `{nom}` cette semaine.")
            except FileNotFoundError:
                continue
    except FileNotFoundError:
        print("⚠️ Fichier de rappels introuvable.")


# Commande pour afficher le message d'un rappel spécifique
@bot.tree.command(name="affichemessage", description="Affiche le message d'un rappel spécifique")
async def affichemessage(interaction: discord.Interaction, nom: str):
    """
    Affiche le message d'un rappel spécifique dans le channel où la commande est exécutée.
    - nom : Nom unique du rappel
    """
    try:
        # Charger les rappels depuis le fichier JSON
        with open("json/reminders.json", "r") as file:
            reminders = json.load(file)

        # Trouver le rappel correspondant
        reminder = next((r for r in reminders if r["nom"] == nom), None)

        if not reminder:
            await interaction.response.send_message(f"⚠️ Aucun rappel trouvé avec le nom `{nom}`.", ephemeral=True)
            return

        # Charger les utilisateurs à mentionner pour ce rappel
        try:
            with open(f"json/{nom}_reminder_users.json", "r") as user_file:
                reminder_users = json.load(user_file)
                mentions = " ".join([f"<@{user_id}>" for user_id in reminder_users["users"]])
        except FileNotFoundError:
            mentions = "Aucun utilisateur à mentionner."

        # Charger les utilisateurs restants à mentionner
        try:
            with open(f"json/{nom}_remaining_users.json", "r") as remaining_file:
                remaining_users = json.load(remaining_file)
                remaining_mentions = " ".join([f"<@{user_id}>" for user_id in remaining_users["users"]])
        except FileNotFoundError:
            remaining_mentions = "Aucun utilisateur restant à mentionner."

        # Créer le message au format texte
        message = f"{reminder['contenu']}\n{remaining_mentions}\n"

        # Envoyer le message dans le channel où la commande est exécutée
        await interaction.response.send_message(message, ephemeral=True)

    except FileNotFoundError:
        await interaction.response.send_message("⚠️ Fichier de rappels introuvable.", ephemeral=True)


# Tâche pour vérifier et envoyer les rappels à l'heure spécifiée
@tasks.loop(minutes=1)
async def check_and_send_reminders():
    try:
        with open("json/reminders.json", "r") as file:
            reminders = json.load(file)

        current_time = datetime.now().strftime("%H:%M")
        current_day = datetime.now().strftime("%A").lower()  # Obtenir le jour actuel en minuscule

        for reminder in reminders:
            if current_day in reminder["jours"] and reminder["heure"] == current_time:
                # Charger les utilisateurs à mentionner pour ce rappel
                try:
                    with open(f"json/{reminder['nom']}_reminder_users.json", "r") as user_file:
                        reminder_users = json.load(user_file)
                        mentions = " ".join([f"<@{user_id}>" for user_id in reminder_users["users"]])
                except FileNotFoundError:
                    mentions = "Aucun utilisateur à mentionner."

                # Charger les utilisateurs restants à mentionner
                try:
                    with open(f"json/{reminder['nom']}_remaining_users.json", "r") as remaining_file:
                        remaining_users = json.load(remaining_file)
                        remaining_mentions = " ".join([f"<@{user_id}>" for user_id in remaining_users["users"]])
                except FileNotFoundError:
                    remaining_mentions = "Aucun utilisateur restant à mentionner."

                # Créer le message au format texte
                message = f"{reminder['contenu']}\n{remaining_mentions}\n"

                # Envoyer le message dans le channel spécifié
                try:
                    with open(f"json/{reminder['nom']}_channel.json", "r") as channel_file:
                        channel_data = json.load(channel_file)
                        channel_id = channel_data.get("channel_id", 0)

                    if channel_id != 0:
                        channel = bot.get_channel(channel_id)
                        if channel:
                            await channel.send(content=message)
                        else:
                            print(f"⚠️ Channel introuvable pour le rappel `{reminder['nom']}`.")
                    else:
                        print(f"⚠️ Aucun channel défini pour le rappel `{reminder['nom']}`.")
                except FileNotFoundError:
                    print(f"⚠️ Fichier de channel introuvable pour le rappel `{reminder['nom']}`.")
    except FileNotFoundError:
        print("⚠️ Fichier de rappels introuvable.")


# Tâche pour réinitialiser les utilisateurs restants chaque lundi à 00:00
@tasks.loop(minutes=1)
async def reset_remaining_users():
    """
    Réinitialise la liste des remaining_users chaque lundi à 00:00 en copiant tous les utilisateurs de reminder_users.
    """
    now = datetime.now()
    if now.strftime("%A").lower() == "lundi" and now.strftime("%H:%M") == "00:00":
        try:
            with open("json/reminders.json", "r") as file:
                reminders = json.load(file)

            for reminder in reminders:
                nom = reminder["nom"]
                try:
                    # Charger reminder_users
                    with open(f"json/{nom}_reminder_users.json", "r") as reminder_file:
                        reminder_users = json.load(reminder_file)

                    # Réinitialiser remaining_users
                    with open(f"json/{nom}_remaining_users.json", "w") as remaining_file:
                        json.dump({"users": reminder_users["users"]}, remaining_file, indent=4)

                    print(f"✅ Liste des remaining_users réinitialisée pour le rappel `{nom}`.")
                except FileNotFoundError:
                    print(f"⚠️ Fichier reminder_users introuvable pour le rappel `{nom}`.")
        except FileNotFoundError:
            print("⚠️ Fichier de rappels introuvable.")


bot.run(TOKEN)
