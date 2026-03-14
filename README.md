# 🤖 Free-Work Job Bot

Bot d'automatisation de candidatures sur [Free-Work.com](https://www.free-work.com) avec personnalisation IA des messages via OpenAI.

## ✨ Fonctionnalités

- **Candidature automatique** — Recherche et postule aux offres correspondant à vos mots-clés
- **Messages personnalisés par IA** — Chaque candidature est adaptée à l'offre grâce à GPT-4o-mini et votre CV
- **Filtrage intelligent** — Exclut automatiquement les offres contenant des mots-clés non pertinents
- **Détection de doublons** — Ignore les offres auxquelles vous avez déjà postulé
- **Anti-détection** — User-Agent personnalisé et mesures anti-bot
- **Docker ready** — Image Docker avec Chromium pour exécution headless

## 🚀 Installation

### Prérequis
- Python 3.9+
- Google Chrome (pour exécution locale)
- Docker (optionnel, pour exécution conteneurisée)

### Setup local

```bash
# Cloner le repo
git clone https://github.com/imadmallahi/free-work.git
cd free-work

# Créer l'environnement virtuel
python3 -m venv .venv
source .venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt

# Configurer les variables d'environnement
cp .env.example .env
# Éditer .env avec vos identifiants
```

### Setup Docker

```bash
docker build -t freework-bot .
```

## ⚙️ Configuration

Éditez le fichier `.env` :

| Variable | Description |
|---|---|
| `FREEWORK_EMAIL` | Votre email Free-Work |
| `FREEWORK_PASSWORD` | Votre mot de passe Free-Work |
| `FREEWORK_TEMPLATE` | Template de base pour les candidatures |
| `OPENAI_API_KEY` | Clé API OpenAI (pour personnalisation IA) |

Personnalisez `cv.txt` avec votre propre CV pour que l'IA génère des messages basés sur votre profil.

## 🏃 Utilisation

### Local (avec navigateur visible)
```bash
python freework.py
```

### Docker (headless)
```bash
docker run -e HEADLESS=true \
  -v $(pwd)/.env:/app/.env \
  -v $(pwd)/logs:/app/logs \
  freework-bot
```

## 📁 Structure

```
free-work/
├── freework.py        # Script principal
├── cv.txt             # Votre CV (utilisé par l'IA)
├── requirements.txt   # Dépendances Python
├── Dockerfile         # Image Docker avec Chromium
├── .env               # Variables sensibles (non versionné)
├── .env.example       # Template de configuration
└── logs/              # Logs d'exécution
```

## 🔒 Sécurité

- Les identifiants et clés API sont stockés dans `.env` (exclu du repo via `.gitignore`)
- Aucune donnée sensible n'est versionnée
- Le mode `DRY_RUN = True` permet de tester sans postuler réellement

## 📝 Licence

Usage personnel uniquement.
