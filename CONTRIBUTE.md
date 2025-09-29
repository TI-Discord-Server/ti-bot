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