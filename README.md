# 🤖 DiscordBot

Un bot Discord personnel pour des rappels quotidiens. 📅

## ✨ Pourquoi ce bot ?

J'ai créé ce bot parce que j'avais du mal avec les applications de rappel classiques. Souvent, je voyais la notification, mais je me disais "je le ferai plus tard", et je finissais par oublier. ❌ Je voulais aussi créer un rappel commun à plusieurs personnes. 👏

💡 **Mais avec Discord, c'est différent !**  Lorsque je reçois une notification, j'ai le réflexe de cliquer dessus immédiatement. L'idée m'est donc venue de créer un bot qui m'enverrait des rappels directement sur Discord. **Résultat : je suis devenu plus productif !** ✅

📌 Vous pouvez utiliser les commandes pour créer vos propres rappels personnalisés !

💭 Votre seule limite est votre imagination 💫.

---

## 🔧 Commandes disponibles

Voici les commandes que vous pouvez utiliser avec le bot :

*Dans les commandes disponibles, `reminder` est le nom (unique) du rappel.

• **`/clear reminder`** : Retire l’exécuteur de la commande de la liste des personnes à notifier dans la semaine pour ledit rappel. ❌

• **`/setchannel reminder channel`** : Définit le salon où le rappel sera envoyé. 📢

• **`/listuser reminder`** : Affiche la liste des utilisateurs qui souhaitent être mentionnés pour ledit rappel. 👥

• **`/adduser reminder @utilisateur`** : Ajoute un utilisateur à la liste des personnes mentionnées pour le rappel mentionné. ➕

• **`/delluser reminder @utilisateur`** : Supprime un utilisateur de la liste des personnes mentionnées pour le rappel mentionné. ❌

• **`/listweekuser reminder`** : Liste les utilisateurs à mentionner cette semaine pour le rappel spécifié. 📜

• **`/listreactuser reminder`** : Liste les utilisateurs qui ont réagi à un des messages du bot ou qui ont utilisé la commande `/clear` pour le rappel spécifié. 📜

• **`/addreactuser reminder @utilisateur`** : Ajoute un utilisateur à la liste des personnes ayant réagi ou utilisé la commande `/clear` pour ledit rappel. ➕

• **`/delreactuser reminder @utilisateur`** : Supprime un utilisateur de la liste des personnes ayant réagi ou utilisé la commande `/clear` pour ledit rappel. ❌

---

## 🛠️ Installation

1️⃣ **Clonez ce dépôt** :

```bash
git clone https://github.com/Anolty-R/DiscordBot.git
```

2️⃣ **Accédez au dossier du projet** :

```bash
cd DiscordBot
```

3️⃣ **Installez les dépendances requises** :

```bash
pip install -r requirements.txt
```

4️⃣ **Configurez votre bot** en ajoutant votre token Discord dans le fichier de configuration. 🛠️
5️⃣ **Lancez le bot** :

```bash
python bot.py
```

