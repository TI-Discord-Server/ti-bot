# TI Discord Bot
Run using `python3 main.py`.

## Repo Regels
- Gebruik [Ruff](https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff), een PEP8 compliant linter zodat al je code de style guide volgt en beetje leesbaar is.
- Maak een Discord bot via de [Discord developer portal](https://discord.com/developers/applications) om je code te testen voordat je iets in production gebruikt.
- Gelieve de ./cogs en ./utils folders correct te gebruiken. ./utils is voor code die herbruikt kan/moet worden en back-end logic. ./cogs is voor alle tasks, commands, etc. waar users interactie mee hebben. Kijk gerust naar de voorbeelden in ./cogs/help.py en ./cogs/faq.py.
- Upload emojis die gebruikt worden door de bot naar de Discord developer portal in plaats van server emojis te gebruiken. Zo ontstaan er geen permission issues of missing emojis.