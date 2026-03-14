# Utiliser une image Python officielle plus stable
FROM python:3.9-slim-bookworm

# Éviter la mise en cache de pip
ENV PIP_NO_CACHE_DIR=1
ENV PYTHONUNBUFFERED=1

# Installer les dépendances système minimales et Chromium
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    chromium \
    chromium-driver \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers du projet
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY freework.py .
COPY cv.txt .

# Créer le dossier de logs
RUN mkdir -p logs

# Configuration pour Selenium pour utiliser Chromium installé par apt
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_BIN=/usr/bin/chromedriver

# Commande par défaut pour lancer le script
CMD ["python", "freework.py"]
