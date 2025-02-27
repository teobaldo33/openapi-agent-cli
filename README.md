# OpenAPI Agent

Un agent d'IA interactif qui utilise Claude d'Anthropic pour communiquer avec des API via leurs spécifications OpenAPI.

## Caractéristiques

- Générer des outils Claude-compatibles à partir de spécifications OpenAPI
- Discuter avec Claude pour interagir avec des API
- Interface en ligne de commande interactive
- Support pour l'authentification API
- Journalisation détaillée

## Installation

1. Clonez le dépôt:

```bash
git clone https://github.com/username/anthropic-tool-tuto.git
cd anthropic-tool-tuto
```

2. Installez les dépendances:

```bash
pip install -r requirements.txt
```

3. Pour une installation en mode développement de la bibliothèque `openapi-agent-tools`:

```bash
pip install -e .
```

4. Créez un fichier `.env` avec votre clé API Anthropic:

```
ANTHROPIC_API_KEY=votre_clé_api_claude
TARGET_API_KEY=votre_clé_api_cible
```

## Utilisation

### Mode interactif

```bash
python cli.py --interactive --openapi-url https://api.example.com/openapi.json
```

### Exécution de requête unique

```bash
python cli.py --query "Obtenir la liste des utilisateurs" --openapi-url https://api.example.com/openapi.json
```

### Avec authentification

```bash
python cli.py --interactive --openapi-url https://api.example.com/openapi.json --target-api-key votre_clé_api --auth-scheme Bearer
```

## Bibliothèque `openapi-agent-tools`

Ce projet inclut une bibliothèque autonome pour générer et valider des outils Claude-compatibles:

```bash
# Installer la bibliothèque
pip install .

# Utiliser la CLI de la bibliothèque
openapi-agent-tools generate --url http://localhost:9999/doc --output tools.json

# Valider des outils existants
openapi-agent-tools validate tools.json --output fixed_tools.json
```

## License

MIT
