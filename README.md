# TI Discord Bot

## 🔧 Voor Ontwikkelaars: Tibot-v3 Uitvoeren

Deze bot kan worden gestart met Python of via een container (Docker).

### Zonder Docker

1. Maak een `.env` bestand aan en vul dit in zoals gebruikelijk (zie `.env.example` voor een voorbeeld).
2. Start de bot met het volgende commando:
   ```bash
   python3 main.py
   ```

---

## 🚀 Tibot-v3 Deployen met Docker

### 1. Docker image bouwen

Voer het volgende commando uit in je CLI, vanuit de rootmap:
```bash
docker build -t tibot-v3 .
```

### 2. Docker Compose gebruiken

1. Controleer het bestand `docker-compose.yml`.
2.1 Maak een bestand genaamd `.env` aan door de inhoud van `examples.env` te kopiëren.

#### Vereiste omgevingsvariabelen (.env)

De bot gebruikt een `.env` bestand voor gevoelige gegevens. Zie `.env.example` als correcte template met onze `docker-compose.yml` configuratie. De volgende variabelen zijn vereist:

- `BOT_TOKEN`: Je Discord bot-token
- `MONGODB_IP_ADDRESS`: Het IP-adres van je MongoDB-server
- `MONGODB_PASSWORD`: Het wachtwoord voor MongoDB-authenticatie
- `MONGODB_PORT`: De poort van je MongoDB-server (standaardwaarde = 27017)
- `MONGODB_USERNAME`: De naam van de MongoDB-gebruiker en database (standaard = bot)
- `WEBHOOK_URL`: Discord webhook URL voor logging (optioneel)

**Voorbeeld (.env):**
```env
BOT_TOKEN='XXX'
MONGODB_IP_ADDRESS='mongo' # Laat dit ongewijzigd bij gebruik van docker-compose
MONGODB_PASSWORD='yourpassword123!' # Moet overeenkomen met docker-compose.yml
WEBHOOK_URL='<https://discord.com/api/webhooks/123456789/abcdef...>'
MONGODB_PORT=27017
MONGODB_USERNAME=bot
```
2.2 Pas in main.py de connection string aan. Verwijder de TLs optie
specifiek verwijder je dit **&tls=true&tlsInsecure=true**
Resultaat:
```py
        # Connect to te MongoDB database with the async version of pymongo. Change IP address if needed.
        motor = AsyncIOMotorClient(
            f"mongodb://{MONGODB_USERNAME}:{MONGODB_PASSWORD}@{MONGODB_IP_ADDRESS}:{MONGODB_PORT}/{MONGODB_USERNAME}?authMechanism=SCRAM-SHA-256",
            connect=True,
        )
```
### 3. Services starten met Docker Compose

Start MongoDB:
```bash
docker compose up mongo -d
```

### 4. MongoDB-gebruiker toevoegen

Als je nog geen gebruiker hebt voor de bot, voer dan deze commando’s afzonderlijk uit:

```mongo
use bot
```

```mongo
db.createUser({
  user: "bot",
  pwd: "yourpassword123!",
  roles: [
    { role: "readWrite", db: "bot" }
  ]
})
```

Gebruik dit wachtwoord als `MONGODB_PASSWORD` in je `.env` bestand.

Start daarna de webapp:
```bash
docker compose up webapp -d
```

---

## 🛠️ Notities

- Zorg ervoor dat MongoDB actief is vóór het starten van de bot.
- Het `.env` bestand moet alle vereiste variabelen bevatten.
- Bij netwerkproblemen: controleer of `MONGODB_IP_ADDRESS` juist is ingesteld.

---

## 📚 Repository Regels

- Gebruik [Ruff](https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff), een PEP8-conforme linter, om je code leesbaar en gestandaardiseerd te houden.
- Maak een Discord bot aan via de [Discord Developer Portal](https://discord.com/developers/applications) om te testen.
- Gebruik `./cogs` voor interactiecommando’s en `./utils` voor herbruikbare backend-logica.
- Upload emoji’s naar de Discord Developer Portal om permissieproblemen te vermijden.

---

## ⚡ Slash Commands

- Zie je slash-commands niet? Herstart de Discord-applicatie.
- Soms duurt het even voordat nieuwe slash-commands zichtbaar zijn.

---

## 😊 Emoji’s

- Upload emoji’s [hier](https://discord.com/developers/applications/1334455177616556154/emojis).
- Gebruik ze als volgt: `<:emoji_naam:emoji_id>`

---

## ✅ TODO's

**Nyo:**
- Mod functies (ban, mute, kick, etc…)
- Unban-verzoek
- Prune (optioneel)

**Quinten:**
- Confessions
- Voorbeeldvariabelen gebruiken adhv collection

**Jaak:**
- Verify functie (Office365-authenticatie?)

**Kobe:**
- ~~Modmail~~ (stickers kunnen niet verstuurd worden)
- Loggen naar bestand + bestand opslaan op server. Bestand moet opvraagbaar zijn via commando: `/transcript [user_id]`

**Warre:**
- Punten bekendmaken (variabel maken)
- Report functie
