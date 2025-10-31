# Déploiement PostgreSQL pour DispyCluster

Guide pour migrer de SQLite (développement) vers PostgreSQL (production).

## Vue d'ensemble

DispyCluster utilise une abstraction de base de données (`web/core/database.py`) qui permet de basculer entre SQLite et PostgreSQL sans changer le code métier.

## Architecture

```
┌─────────────────────┐
│   Application       │
│   (web/app.py)      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  DatabaseManager    │
│  (abstraction)      │
└──────────┬──────────┘
           │
    ┌──────┴──────┐
    │             │
    ▼             ▼
┌─────────┐  ┌──────────┐
│ SQLite  │  │PostgreSQL│
│ (local) │  │  (prod)  │
└─────────┘  └──────────┘
```

## Prérequis

### PostgreSQL

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib

# Créer la base de données
sudo -u postgres createdb dispycluster
sudo -u postgres createuser dispycluster_user

# Définir le mot de passe
sudo -u postgres psql
ALTER USER dispycluster_user WITH PASSWORD 'votre_mot_de_passe';
GRANT ALL PRIVILEGES ON DATABASE dispycluster TO dispycluster_user;
\q
```

### Dépendances Python

```bash
pip install psycopg2-binary
# ou
pip install asyncpg  # Pour support asynchrone
```

## Configuration

### Variables d'environnement

Créer un fichier `.env` ou définir les variables :

```bash
# Type de base de données
DATABASE_TYPE=postgresql

# Connexion PostgreSQL
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=dispycluster
DATABASE_USER=dispycluster_user
DATABASE_PASSWORD=votre_mot_de_passe

# Ou connection string complète
DATABASE_URL=postgresql://dispycluster_user:password@localhost:5432/dispycluster
```

### Configuration dans le code

Modifier `web/core/database.py` pour utiliser PostgreSQL :

```python
from web.core.database import DatabaseManager

# Avec variables d'environnement
import os
db_manager = DatabaseManager(
    db_type="postgresql",
    connection_string=os.getenv("DATABASE_URL")
)

# Ou avec paramètres individuels
db_manager = DatabaseManager(
    db_type="postgresql",
    host=os.getenv("DATABASE_HOST", "localhost"),
    port=int(os.getenv("DATABASE_PORT", 5432)),
    database=os.getenv("DATABASE_NAME", "dispycluster"),
    user=os.getenv("DATABASE_USER"),
    password=os.getenv("DATABASE_PASSWORD")
)
```

## Migration depuis SQLite

### 1. Exporter les données SQLite

```python
import sqlite3
import json

# Connexion SQLite
conn_sqlite = sqlite3.connect("web/data/cluster.db")
cursor_sqlite = conn_sqlite.cursor()

# Exporter les jobs
cursor_sqlite.execute("SELECT * FROM scraper_jobs")
jobs = cursor_sqlite.fetchall()

# Exporter les résultats
cursor_sqlite.execute("SELECT * FROM scraper_results")
results = cursor_sqlite.fetchall()

# Sauvegarder en JSON
with open("migration_data.json", "w") as f:
    json.dump({
        "jobs": [dict(row) for row in jobs],
        "results": [dict(row) for row in results]
    }, f, default=str)

conn_sqlite.close()
```

### 2. Créer le schéma PostgreSQL

Le schéma est créé automatiquement par `DatabaseManager`, mais on peut aussi le créer manuellement :

```sql
-- Connexion à PostgreSQL
psql -U dispycluster_user -d dispycluster

-- Tables des jobs scrapers
CREATE TABLE IF NOT EXISTS scraper_jobs (
    id TEXT PRIMARY KEY,
    job_id TEXT UNIQUE NOT NULL,
    url TEXT NOT NULL,
    max_pages INTEGER DEFAULT 10,
    status TEXT NOT NULL DEFAULT 'pending',
    assigned_node TEXT,
    progress REAL DEFAULT 0,
    result TEXT,
    error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Table des résultats de scraping
CREATE TABLE IF NOT EXISTS scraper_results (
    id SERIAL PRIMARY KEY,
    job_id TEXT NOT NULL,
    url TEXT NOT NULL,
    crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    emails TEXT,
    phones TEXT,
    links_count INTEGER DEFAULT 0,
    error TEXT,
    FOREIGN KEY (job_id) REFERENCES scraper_jobs(job_id)
);

-- Index
CREATE INDEX IF NOT EXISTS idx_job_id ON scraper_jobs(job_id);
CREATE INDEX IF NOT EXISTS idx_status ON scraper_jobs(status);
CREATE INDEX IF NOT EXISTS idx_scraper_results_job ON scraper_results(job_id);
```

### 3. Importer les données

```python
import psycopg2
import json

# Connexion PostgreSQL
conn_pg = psycopg2.connect(
    host="localhost",
    port=5432,
    database="dispycluster",
    user="dispycluster_user",
    password="votre_mot_de_passe"
)
cursor_pg = conn_pg.cursor()

# Charger les données
with open("migration_data.json", "r") as f:
    data = json.load(f)

# Importer les jobs
for job in data["jobs"]:
    cursor_pg.execute("""
        INSERT INTO scraper_jobs 
        (id, job_id, url, max_pages, status, assigned_node, progress, result, error, created_at, started_at, completed_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (job_id) DO NOTHING
    """, (
        job["id"], job["job_id"], job["url"], job["max_pages"],
        job["status"], job.get("assigned_node"), job.get("progress"),
        job.get("result"), job.get("error"),
        job.get("created_at"), job.get("started_at"), job.get("completed_at")
    ))

# Importer les résultats
for result in data["results"]:
    cursor_pg.execute("""
        INSERT INTO scraper_results 
        (job_id, url, crawled_at, emails, phones, links_count, error)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        result["job_id"], result["url"], result.get("crawled_at"),
        result.get("emails"), result.get("phones"),
        result.get("links_count", 0), result.get("error")
    ))

conn_pg.commit()
conn_pg.close()
```

## Configuration de production

### Sécurité

```bash
# Limiter les connexions
# Dans postgresql.conf
max_connections = 100

# Authentification
# Dans pg_hba.conf
host    dispycluster    dispycluster_user    127.0.0.1/32    md5
```

### Performance

```sql
-- Optimisations PostgreSQL
ALTER TABLE scraper_jobs SET (fillfactor = 90);
ALTER TABLE scraper_results SET (fillfactor = 90);

-- Vacuum automatique
ALTER TABLE scraper_jobs SET (autovacuum_vacuum_scale_factor = 0.05);
ALTER TABLE scraper_results SET (autovacuum_vacuum_scale_factor = 0.05);
```

### Backups

```bash
# Backup quotidien avec cron
0 2 * * * pg_dump -U dispycluster_user dispycluster > /backups/dispycluster_$(date +\%Y\%m\%d).sql

# Ou avec pg_basebackup pour backup continu
pg_basebackup -D /backups/pg_base -Ft -z -P
```

## Utilisation dans l'application

Le `DatabaseManager` détecte automatiquement le type de base de données :

```python
# Dans web/services/scraper_service.py
from web.core.database import DatabaseManager
import os

# Configuration automatique depuis les variables d'env
db_type = os.getenv("DATABASE_TYPE", "sqlite")
if db_type == "postgresql":
    database = DatabaseManager(
        db_type="postgresql",
        connection_string=os.getenv("DATABASE_URL")
    )
else:
    database = DatabaseManager(
        db_type="sqlite",
        db_path="web/data/cluster.db"
    )
```

## Vérification

```bash
# Tester la connexion
psql -U dispycluster_user -d dispycluster -c "SELECT COUNT(*) FROM scraper_jobs;"

# Vérifier les performances
psql -U dispycluster_user -d dispycluster -c "EXPLAIN ANALYZE SELECT * FROM scraper_jobs WHERE status = 'completed';"
```

## Dépannage

### Connexion refusée

```bash
# Vérifier que PostgreSQL écoute
sudo netstat -tlnp | grep 5432

# Vérifier pg_hba.conf
sudo cat /etc/postgresql/*/main/pg_hba.conf
```

### Permissions insuffisantes

```sql
GRANT ALL PRIVILEGES ON DATABASE dispycluster TO dispycluster_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO dispycluster_user;
```

### Performance lente

```sql
-- Analyser les tables
ANALYZE scraper_jobs;
ANALYZE scraper_results;

-- Vérifier les index
\d+ scraper_jobs
```

## Notes

- SQLite reste utilisé par défaut pour le développement
- PostgreSQL est recommandé pour la production
- L'abstraction DatabaseManager permet de basculer sans changement de code
- Les migrations de données doivent être faites manuellement

