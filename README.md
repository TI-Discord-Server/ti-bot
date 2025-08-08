# TI Discord Bot

## 🔧 Voor Ontwikkelaars: Tibot-v3 Uitvoeren

Deze bot kan worden gestart met Python of via een container (Docker).

### Zonder Docker

1. Maak een `.env` bestand aan en vul dit in zoals gebruikelijk (zie `.env.example` voor een voorbeeld).
2. Start de bot met het volgende commando:
   ```bash
   # Zonder TLS (standaard)
   python3 main.py
   
   # Met TLS ingeschakeld
   python3 main.py --tls
   ```

---

## 🚀 Tibot-v3 Deployen met Docker

### 1. Docker image bouwen

Voer het volgende commando uit in je CLI, vanuit de rootmap:
```bash
# Standaard build (zonder TLS)
docker build -t tibot-v3 .

# Build met TLS ingeschakeld
docker build -t tibot-v3 --build-arg ENABLE_TLS=true .
```

### 2. Docker Compose gebruiken

1. Controleer het bestand `docker-compose.yml`.
2. Maak een bestand genaamd `.env` aan door de inhoud van `examples.env` te kopiëren.

#### Vereiste omgevingsvariabelen (.env)

De bot gebruikt een `.env` bestand voor gevoelige gegevens. Zie `.env.example` als correcte template met onze `docker-compose.yml` configuratie. De volgende variabelen zijn vereist:

- `BOT_TOKEN`: Je Discord bot-token
- `MONGODB_IP_ADDRESS`: Het IP-adres van je MongoDB-server
- `MONGODB_PASSWORD`: Het wachtwoord voor MongoDB-authenticatie
- `MONGODB_PORT`: De poort van je MongoDB-server (standaardwaarde = 27017)
- `MONGODB_USERNAME`: De naam van de MongoDB-gebruiker en database (standaard = bot)
- `WEBHOOK_URL`: Discord webhook URL voor logging (optioneel)
- `SMTP_PASSWORD`: Het wachtwoord voor SMTP-authenticatie (voor e-mailverificatie)
- `SMTP_EMAIL`: Het e-mailadres dat gebruikt wordt voor het versturen van verificatie-e-mails
- `SMTP_SERVER`: De SMTP-server voor het versturen van e-mails (bijv. smtp.gmail.com)
- `ENCRYPTION_KEY`: Een Fernet-encryptiesleutel voor het beveiligen van gevoelige gegevens
- `OLD_CONNECTION_STRING`: MongoDB connection string voor oude database (optioneel, voor migratie van verificatiegegevens)

**Voorbeeld (.env):**
```env
BOT_TOKEN='XXX'
MONGODB_IP_ADDRESS='mongo' # Laat dit ongewijzigd bij gebruik van docker-compose
MONGODB_PASSWORD='yourpassword123!' # Moet overeenkomen met docker-compose.yml
WEBHOOK_URL='https://discord.com/api/webhooks/123456789/abcdef...'
MONGODB_PORT=27017
MONGODB_USERNAME=bot
SMTP_PASSWORD='app_password_for_email' # App-specifiek wachtwoord voor e-mail
SMTP_EMAIL='toegepasteinformaticadiscord@gmail.com'
SMTP_SERVER='smtp.gmail.com'
ENCRYPTION_KEY='generated_fernet_key' # Genereer met het generate_key.py script
OLD_CONNECTION_STRING='mongodb://username:password@host:port/database' # Optioneel: voor migratie
```

### Fernet Encryptiesleutel Genereren

Voor het beveiligen van gevoelige gegevens gebruikt de bot een Fernet-encryptiesleutel. Gebruik het meegeleverde Python script om een veilige sleutel te genereren:

```bash
# Voer het script uit om een sleutel te genereren
python3 generate_key.py
```

Kopieer de gegenereerde sleutel naar je `.env` bestand als `ENCRYPTION_KEY='gegenereerde_sleutel'`.

### Migratie van Oude Verificatiegegevens

De bot ondersteunt migratie van verificatiegegevens uit een oude database. Dit is optioneel en alleen nodig als je gebruikers wilt migreren van een vorige versie van de bot.

**Configuratie:**
- Voeg `OLD_CONNECTION_STRING` toe aan je `.env` bestand met de MongoDB connection string van de oude database
- De connection string moet het formaat hebben: `mongodb://username:password@host:port/database`
- Als deze variabele niet is ingesteld, is de migratiefunctionaliteit uitgeschakeld

**Gebruik:**
- Gebruikers kunnen hun oude verificatie migreren via de verificatie-interface
- Het systeem controleert automatisch op e-mail bounces en blokkeert migratie indien nodig
- Gemigreerde gebruikers worden gemarkeerd in de database om dubbele migratie te voorkomen

### TLS Configuratie

De bot ondersteunt nu een optionele TLS-verbinding voor MongoDB. Standaard is TLS uitgeschakeld voor lokale ontwikkeling, maar het kan worden ingeschakeld met de `--tls` vlag:

```bash
# TLS inschakelen bij het starten van de bot
python3 main.py --tls
```

Bij gebruik van Docker kan TLS worden ingeschakeld op verschillende manieren:

1. Tijdens het bouwen van de image:
   ```bash
   docker build -t tibot-v3 --build-arg ENABLE_TLS=true .
   ```

2. In docker-compose.yml (wijzig de ENABLE_TLS waarde):
   ```yaml
   webapp:
     build:
       context: .
       args:
         ENABLE_TLS: "true"  # Wijzig naar "true" om TLS in te schakelen
   ```
### 3. Services starten met Docker Compose

Start MongoDB:
```bash
docker compose up mongo -d
```

### 4. MongoDB-gebruiker toevoegen

Als je nog geen gebruiker hebt voor de bot:
1. Connecteer met een MongoDB CLI of GUI app met deze connection string:
   ```
   mongodb://root:yourpassword123!@localhost:27017/
   ```
2. Voer deze commando's uit om een nieuwe gebruiker aan te maken:
   ```javascript
   use bot
   
   db.createUser({
     user: "bot",
     pwd: "yourpassword123!",
     roles: [
       { role: "readWrite", db: "bot" }
     ]
   })
   ```
3. Gebruik dit wachtwoord als `MONGODB_PASSWORD` in je `.env` bestand.

### 5. Bot starten

Start de bot container:
```bash
docker compose up webapp -d
```

---

## 🛠️ Notities

- Zorg ervoor dat MongoDB actief is vóór het starten van de bot.
- Het `.env` bestand moet alle vereiste variabelen bevatten.
- Bij netwerkproblemen: controleer of `MONGODB_IP_ADDRESS` juist is ingesteld.
- TLS is standaard uitgeschakeld voor lokale ontwikkeling, maar kan worden ingeschakeld met de `--tls` vlag.

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
