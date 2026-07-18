# Yeslek Mail

Yeslek Mail est une plateforme autonome d’e-mails transactionnels construite avec :

- Python et Flask ;
- Jinja2 ;
- PostgreSQL ;
- Redis ;
- Celery ;
- Docker ;
- Mailpit en développement ;
- Postfix pour la production ;
- Google Cloud Run ;
- Cloud Run Worker Pools ;
- Cloud SQL ;
- Secret Manager.

## Fonctionnalités actuelles

- inscription ;
- connexion et déconnexion ;
- mots de passe hashés avec Argon2 ;
- sessions stockées dans Redis ;
- protection CSRF ;
- rate limiting ;
- création automatique d’une organisation ;
- création automatique du premier projet ;
- tableau de bord ;
- statistiques d’e-mails ;
- file d’attente Celery ;
- migrations PostgreSQL ;
- pages d’erreurs ;
- traductions françaises et anglaises.

## Architecture

```text
yeslek-mail/
├── app.py
├── config.py
├── extensions.py
├── celery_app.py
├── celery_entry.py
│
├── routes/
├── models/
├── repositories/
├── services/
├── workers/
├── forms/
│
├── templates/
├── static/
├── l10n/
├── migrations/
│
├── requirements.txt
├── Dockerfile
├── docker-compose.local.yml
├── cloudbuild.yaml
├── .env.example
├── .gitignore
└── .dockerignore
```

# Développement local

## 1. Créer le fichier `.env`

Sous PowerShell :

```powershell
Copy-Item .env.example .env
```

Sous Linux ou macOS :

```bash
cp .env.example .env
```

Ne publie jamais le fichier `.env`.

## 2. Variables minimales

Le fichier `.env` doit contenir au minimum :

```env
# ---------------------------
# Application
# ---------------------------

APP_NAME=Yeslek Mail
APP_ENV=development

SECRET_KEY=replace-with-a-long-random-secret
API_KEY_PEPPER=replace-with-another-long-random-secret

PUBLIC_BASE_URL=http://localhost:5000


# ---------------------------
# PostgreSQL
# ---------------------------

DATABASE_URL=postgresql+psycopg://yeslek:yeslek_local_password@localhost:5432/yeslek_mail


# ---------------------------
# Redis
# ---------------------------

REDIS_URL=redis://localhost:6379/0
SESSION_REDIS_URL=redis://localhost:6379/1
CELERY_BROKER_URL=redis://localhost:6379/2
CELERY_RESULT_BACKEND=redis://localhost:6379/3


# ---------------------------
# SMTP local
# ---------------------------

SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_USE_TLS=false
SMTP_USE_SSL=false

MAIL_DEFAULT_SENDER_EMAIL=notifications@yeslek.local
MAIL_DEFAULT_SENDER_NAME=Yeslek Mail
MAIL_MESSAGE_ID_DOMAIN=yeslek.local


# ---------------------------
# Plan
# ---------------------------

DEFAULT_MONTHLY_EMAIL_LIMIT=300
```

Les valeurs réseau sont automatiquement remplacées par Docker Compose lorsque l’application fonctionne dans les conteneurs.

## 3. Construire et démarrer

```powershell
docker compose -f docker-compose.local.yml up -d --build
```

## 4. Vérifier les services

```powershell
docker compose -f docker-compose.local.yml ps
```

## 5. Consulter les journaux

```powershell
docker compose -f docker-compose.local.yml logs -f web worker
```

# Base de données

## Première initialisation seulement

Exécute cette commande uniquement si le dossier `migrations/` n’existe pas encore :

```powershell
docker compose -f docker-compose.local.yml exec web `
    flask --app app db init
```

Sous Linux ou macOS :

```bash
docker compose -f docker-compose.local.yml exec web \
    flask --app app db init
```

## Créer une migration

```powershell
docker compose -f docker-compose.local.yml exec web `
    flask --app app db migrate `
    -m "Initial schema"
```

## Appliquer les migrations

```powershell
docker compose -f docker-compose.local.yml exec web `
    flask --app app db upgrade
```

Une autre possibilité consiste à utiliser le service dédié :

```powershell
docker compose -f docker-compose.local.yml `
    --profile tools `
    run --rm migrate
```

## Annuler la dernière migration

```powershell
docker compose -f docker-compose.local.yml exec web `
    flask --app app db downgrade
```

# Adresses locales

Application :

```text
http://localhost:5000
```

Inscription :

```text
http://localhost:5000/auth/register
```

Connexion :

```text
http://localhost:5000/auth/login
```

Tableau de bord :

```text
http://localhost:5000/dashboard/
```

Mailpit :

```text
http://localhost:8025
```

Vérification de santé :

```text
http://localhost:5000/health
```

# Commandes Docker utiles

## Arrêter les services

```powershell
docker compose -f docker-compose.local.yml down
```

## Arrêter et supprimer les données locales

Attention : cette commande supprime PostgreSQL, Redis et les e-mails Mailpit locaux.

```powershell
docker compose -f docker-compose.local.yml down -v
```

## Reconstruire l’application

```powershell
docker compose -f docker-compose.local.yml up -d --build
```

## Ouvrir un shell dans le conteneur web

```powershell
docker compose -f docker-compose.local.yml exec web sh
```

## Ouvrir PostgreSQL

```powershell
docker compose -f docker-compose.local.yml exec postgres `
    psql -U yeslek -d yeslek_mail
```

## Vérifier Redis

```powershell
docker compose -f docker-compose.local.yml exec redis `
    redis-cli ping
```

# Sécurité

## Mots de passe

Les mots de passe sont hashés avec Argon2.

Ils ne doivent jamais être :

- enregistrés en clair ;
- ajoutés aux journaux ;
- envoyés dans les événements analytiques ;
- inclus dans une URL.

## Clés API

Les clés API doivent :

- être générées avec un générateur cryptographique ;
- être affichées une seule fois ;
- être enregistrées uniquement sous forme hashée ;
- posséder un préfixe visible ;
- pouvoir être révoquées ;
- être associées à un projet.

## Secrets

Ne place jamais ces valeurs dans Git :

- `SECRET_KEY` ;
- `API_KEY_PEPPER` ;
- mot de passe PostgreSQL ;
- URL Redis contenant un mot de passe ;
- identifiants SMTP ;
- clés DKIM ;
- comptes de service Google Cloud.

# API d’envoi

Exemple de requête :

```bash
curl -X POST "http://localhost:5000/api/v1/emails/send" \
    -H "Authorization: Bearer yeslek_live_VOTRE_CLE" \
    -H "Content-Type: application/json" \
    -H "Idempotency-Key: commande-2026-001" \
    -d '{
        "to": {
            "email": "client@example.com",
            "name": "Client"
        },
        "subject": "Bienvenue chez Yeslek",
        "text": "Votre compte est prêt.",
        "html": "<h1>Votre compte est prêt</h1>"
    }'
```

Le header `Idempotency-Key` empêche la création de plusieurs e-mails pour la même opération.

# Déploiement Google Cloud

Le fichier `cloudbuild.yaml` exécute :

```text
Build Docker
    ↓
Push Artifact Registry
    ↓
Création ou mise à jour du job de migration
    ↓
Exécution des migrations
    ↓
Déploiement du service Flask
    ↓
Déploiement du worker Celery
```

## Ressources nécessaires

Avant le premier déploiement, crée :

- un dépôt Artifact Registry ;
- un service Cloud SQL PostgreSQL ;
- une instance Redis ou Memorystore ;
- un connecteur VPC ;
- un compte de service d’exécution ;
- les secrets Secret Manager ;
- un déclencheur Cloud Build lié à GitHub.

## APIs Google Cloud

Exemple :

```bash
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    secretmanager.googleapis.com \
    sqladmin.googleapis.com \
    redis.googleapis.com \
    vpcaccess.googleapis.com
```

## Artifact Registry

```bash
gcloud artifacts repositories create yeslek \
    --repository-format=docker \
    --location=europe-west1 \
    --description="Images Docker Yeslek"
```

## Compte de service

```bash
gcloud iam service-accounts create yeslek-runtime \
    --display-name="Yeslek Runtime"
```

Adresse obtenue :

```text
yeslek-runtime@PROJECT_ID.iam.gserviceaccount.com
```

## Secrets requis

Le fichier `cloudbuild.yaml` attend les secrets suivants :

```text
yeslek-secret-key
yeslek-api-key-pepper
yeslek-database-url
yeslek-redis-url
yeslek-session-redis-url
yeslek-celery-broker-url
yeslek-celery-result-backend
```

Exemple de création :

```bash
printf "%s" "VALEUR_SECRETE" |
gcloud secrets create yeslek-secret-key \
    --data-file=-
```

Pour ajouter une nouvelle version :

```bash
printf "%s" "NOUVELLE_VALEUR" |
gcloud secrets versions add yeslek-secret-key \
    --data-file=-
```

## Accès aux secrets

```bash
gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="serviceAccount:yeslek-runtime@PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

## Variables Cloud Build

Adapte les substitutions du fichier `cloudbuild.yaml` :

```yaml
_REGION: europe-west1
_REPOSITORY: yeslek
_SERVICE_NAME: yeslek-mail

_MIGRATION_JOB: yeslek-mail-migrate
_WORKER_POOL: yeslek-mail-worker
_WORKER_INSTANCES: "1"

_RUNTIME_SERVICE_ACCOUNT:
  yeslek-runtime@PROJECT_ID.iam.gserviceaccount.com

_VPC_CONNECTOR: yeslek-serverless-vpc

_PUBLIC_BASE_URL: https://mail.yeslek.com

_SMTP_HOST: 10.10.0.10
_SMTP_PORT: "587"
_SMTP_USE_TLS: "true"

_MAIL_DEFAULT_SENDER_EMAIL: notifications@yeslek.com
_MAIL_DEFAULT_SENDER_NAME: Yeslek Mail
_MAIL_MESSAGE_ID_DOMAIN: yeslek.com
```

## Soumettre manuellement un build

```bash
gcloud builds submit \
    --config cloudbuild.yaml
```

# GitHub

## Initialiser Git

```powershell
git init
git add .
git commit -m "Initial Yeslek Mail platform"
```

## Ajouter le dépôt distant

```powershell
git remote add origin `
    https://github.com/VOTRE_COMPTE/yeslek-mail.git
```

## Publier

```powershell
git branch -M main
git push -u origin main
```

Vérifie avant chaque publication que ces fichiers ne sont pas suivis :

```text
.env
*.pem
*.key
credentials.json
service-account.json
```

Commande de vérification :

```powershell
git status
git ls-files
```

# Production SMTP

Mailpit sert uniquement au développement.

La production utilisera :

```text
Application Flask
    ↓
Redis et Celery
    ↓
Postfix privé
    ↓
OpenDKIM
    ↓
Serveurs MX destinataires
```

La production nécessitera également :

- une adresse IP publique fixe ;
- un reverse DNS PTR ;
- SPF ;
- DKIM ;
- DMARC ;
- TLS ;
- un domaine de rebond ;
- la gestion des hard bounces ;
- la gestion des plaintes ;
- une liste de suppression ;
- une limitation de la cadence d’envoi ;
- un suivi de la réputation.

# Licence

Projet privé Yeslek.

Toute copie ou distribution nécessite l’autorisation du propriétaire.