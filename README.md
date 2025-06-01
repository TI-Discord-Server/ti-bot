# TI Discord Bot

## run tibot-v3 developers

This bot can be started using python3 or via a container.

1. Create a .env file and fill it in as usual (see the README for details).
2. Start the bot in your preferred way.

### without docker

1. Run using `python3 main.py`.

## 🚀 Deploying Tibot-v3 with Docker

1. Run the following command in your CLI from the root folder to build the Docker image:

   ```bash
   docker build -t tibot-v3 .
   ```

### running with docker compose

2. Open the file **`docker-compose.yml`**.
3. Ensure your **`.env`** file is in the repository's root folder with the exact name `.env`.
4. Start the services using Docker Compose:

   ```bash
   docker compose up -d
   ```

---

### 🚀 Running Without Docker Compose

If you prefer not to use `docker compose`, follow these steps:

1. Open your terminal or CLI.
2. Run the following command, adjusting the values where necessary:

   ```bash
   docker run      -e BOT_TOKEN="tokenxxx"      -e MONGODB_IP_ADDRESS="127.0.0.1"      -e MONGODB_PASSWORD="xxxxx"      -e WEBHOOK_URL="https://discord.com/api/webhooks/1343185088115904662/YXcrhENRo6d1eQQFL5mCjOpF5Y8A0JS1udqraJB70v33vHAFrJ2Nqade7hagB0Zid6ta"      --link mongo:mongo      tibot-v3
   ```

---

### 🛠️ Notes

- Ensure MongoDB is running before starting the bot.
- The `.env` file should contain all necessary environment variables.
- If you face any networking issues, consider adjusting the `MONGODB_IP_ADDRESS` to match your setup.

## Repo Regels

- Gebruik [Ruff](https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff), een PEP8 compliant linter zodat al je code de style guide volgt en beetje leesbaar is.
- Maak een Discord bot via de [Discord developer portal](https://discord.com/developers/applications) om je code te testen voordat je iets in production gebruikt.
- Gelieve de ./cogs en ./utils folders correct te gebruiken. ./utils is voor code die herbruikt kan/moet worden en back-end logic. ./cogs is voor alle tasks, commands, etc. waar users interactie mee hebben. Kijk gerust naar de voorbeelden in ./cogs/help.py en ./cogs/faq.py.
- Upload emojis die gebruikt worden door de bot naar de Discord developer portal in plaats van server emojis te gebruiken. Zo ontstaan er geen permission issues of missing emojis.

## Slash commands

- Wanneer je de commands niet kan zien, reload Discord applicatie.
- Het duurt soms even voor de (nieuwe) slash commands zichtbaar zijn

## Emojis

- Upload emojis [hier](https://discord.com/developers/applications/1334455177616556154/emojis).
- Maak er zo gebruik van: <:emoji_name:emoji_id>

## Environment Variables (.env)

De bot gebruikt een `.env` bestand voor gevoelige gegevens, zie `.env.example` voor een voorbeeld. De volgende variabelen zijn nodig:

- `BOT_TOKEN`: Je Discord bot token
- `MONGODB_IP_ADDRESS`: Het IP-adres van je MongoDB server
- `MONGODB_PASSWORD`: Het wachtwoord voor MongoDB authenticatie
- `MONGODB_PORT`: De poort van je MongoDB server (standaard waarde = 27017)
- `MONGODB_USERNAME`: De naam van de MongoDB tabel en gebruiker (standaard waarde = bot)
- `WEBHOOK_URL`: Discord webhook URL voor logging (optioneel)

## MongoDB Gebruiker Toevoegen

Als je nog geen bot-gebruiker hebt voor MongoDB, run de volgende twee commandos apart.

```mongo
use bot
```

```mongo
db.createUser({
  user: "bot",
  pwd: "Password123",
  roles: [
    { role: "readWrite", db: "bot" }
  ]
})
```

Gebruik dit wachtwoord als `MONGODB_PASSWORD` in je `.env` bestand.

## TODOS

Nyo:

- mod functies (ban, mute, kick, etc...)
- unban verzoek
- Prune (optioneel)

Quinten:

- Confessions
- Voorbeeld variabelen gebruiken adhv collection

Jaak:

- Verify functie (Office365 auth?)

Kobe:

- ~~Modmail~~ (stickers kunnen niet verstuurd worden.)
- Loggen naar bestand + bestand opslaan in server, bestand moet kunnen opgevraagd worden via commando (/transcript [user_id])

Warre:

- Bekendmaking punten commando (variabel maken)
- Report functie
