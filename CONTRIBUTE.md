# Contributieregels voor de Discord Bot

Bedankt dat je wilt bijdragen aan dit project!  
Volg onderstaande regels om de kwaliteit en stabiliteit van de bot te waarborgen.

---

## Werken met branches

- Er **mag nooit rechtstreeks op de `main` branch gepusht worden**.  
- Alle nieuwe features, fixes of verbeteringen gebeuren via de `staging` (ook wel `dev`) branch.  
- De `main` branch is **altijd stabiel** en wordt enkel aangepast na voldoende testing op `staging`.

---

## Workflow voor contributors

1. **Fork & clone** dit project.  
2. Maak een nieuwe branch vanuit `staging`.  
   - Naamgevingsconventie: `feature/<naam>` of `fix/<naam>`.  
   - Voorbeeld: `feature/role-selector` of `fix/logging-error`.
3. Voer je aanpassingen door en **commit duidelijk en beknopt**.  
   - Schrijf commits in de vorm: `type(scope): beschrijving`.  
   - Voorbeeld: `fix(confessions): verbeter null check bij post_approved`.
4. **Test altijd lokaal** of via de staging omgeving voor je code doorstuurt.  

---

## Pull Requests

- Dien een **Pull Request (PR)** in richting de `staging` branch.  
- Zorg dat je PR beschrijving bevat:
  - Wat er is veranderd  
  - Waarom de verandering nodig is  
  - Eventuele referenties naar issues of tickets
- PR's worden nagekeken door een maintainer voor ze gemerged worden.  
- Enkel maintainers mogen uiteindelijk mergen naar `main`, **na testing**.

---

## Testing en Codekwaliteit

- Voeg indien mogelijk **unit tests** toe voor nieuwe functies.  
- Zorg dat de code **linting en formatting checks** doorstaat.  
- Vermijd duplicatie en hou de code **consistent met bestaande conventies**.  

---

## Code formatting en pre-commit hooks

Om de code consistent en foutloos te houden, maken we gebruik van **pre-commit hooks**.  
Deze voeren automatisch checks en formatting uit bij elke commit.

### Installatie

1. Installeer de dependencies via pip:  
   ```bash
   pip install -r requirements.txt 
   ```

2. Activeer pre-commit hooks in de repository:  
   ```bash
   pre-commit install  
   ```

3. Vanaf nu worden bij elke commit automatisch de checks uitgevoerd.

### Tools die gebruikt worden

- **Ruff** → snelle linter die je code controleert op fouten en style issues.  
- **Black** → automatische code formatter die zorgt voor consistente stijl.  
- **Pre-commit** → zorgt dat bovenstaande tools draaien bij elke commit.

### Handmatig uitvoeren

Soms wil je de checks zelf handmatig draaien:  

- **Linting checken met Ruff**  
  ```bash
  ruff check .  
  ```

- **Code automatisch formatteren met Black**  
  ```bash
  black .  
  ```

- **Alle pre-commit hooks draaien op heel de repo**  
  ```bash 
  pre-commit run --all-files  
  ```

---

Met deze setup zorgen we ervoor dat alle code in dit project **consistent, netjes en betrouwbaar** blijft.
