# TI Discord Bot
Run using `python3 main.py`.

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
Als je nog geen bot-gebruiker hebt voor MongoDB:

```mongo
use bot
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
- Modmail
- Loggen naar bestand + bestand opslaan in server, bestand moet kunnen opgevraagd worden via commando

Warre:
- Bekendmaking punten commando (variabel maken)
- Report functie