"""Abstraction de base de données pour SQLite (local) et PostgreSQL (prod).

Permet de basculer facilement entre les deux sans changer le code métier.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime
import sqlite3
from pathlib import Path
import json
from web.config.logging_config import get_logger

logger = get_logger(__name__)


class DatabaseAdapter(ABC):
    """Interface abstraite pour les adaptateurs de base de données."""
    
    @abstractmethod
    def execute(self, query: str, params: Optional[tuple] = None) -> Any:
        """Exécute une requête SQL.
        
        Args:
            query: Requête SQL
            params: Paramètres (optionnel)
            
        Returns:
            Résultat de la requête
        """
        pass
    
    @abstractmethod
    def fetch_one(self, query: str, params: Optional[tuple] = None) -> Optional[Dict[str, Any]]:
        """Récupère une seule ligne.
        
        Args:
            query: Requête SQL
            params: Paramètres (optionnel)
            
        Returns:
            Dictionnaire avec les colonnes ou None
        """
        pass
    
    @abstractmethod
    def fetch_all(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Récupère plusieurs lignes.
        
        Args:
            query: Requête SQL
            params: Paramètres (optionnel)
            
        Returns:
            Liste de dictionnaires
        """
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Ferme la connexion."""
        pass


class SQLiteAdapter(DatabaseAdapter):
    """Adaptateur SQLite pour le développement local."""
    
    def __init__(self, db_path: str):
        """Initialise l'adaptateur SQLite.
        
        Args:
            db_path: Chemin vers le fichier SQLite
        """
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()
    
    def _init_schema(self) -> None:
        """Initialise le schéma de base de données."""
        cursor = self.conn.cursor()
        
        # Table des jobs scrapers
        cursor.execute("""
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
            )
        """)
        
        # Table des résultats de scraping
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scraper_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                url TEXT NOT NULL,
                crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                emails TEXT,
                phones TEXT,
                links_count INTEGER DEFAULT 0,
                error TEXT,
                FOREIGN KEY (job_id) REFERENCES scraper_jobs(job_id)
            )
        """)
        
        # Index pour les recherches
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_job_id ON scraper_jobs(job_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_status ON scraper_jobs(status)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_scraper_results_job ON scraper_results(job_id)
        """)
        
        self.conn.commit()
    
    def execute(self, query: str, params: Optional[tuple] = None) -> Any:
        """Exécute une requête SQL."""
        cursor = self.conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        self.conn.commit()
        return cursor.rowcount
    
    def fetch_one(self, query: str, params: Optional[tuple] = None) -> Optional[Dict[str, Any]]:
        """Récupère une seule ligne."""
        cursor = self.conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    
    def fetch_all(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Récupère plusieurs lignes."""
        cursor = self.conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def close(self) -> None:
        """Ferme la connexion."""
        if self.conn:
            self.conn.close()


class PostgreSQLAdapter(DatabaseAdapter):
    """Adaptateur PostgreSQL pour la production.
    
    À implémenter quand on basculera en prod.
    """
    
    def __init__(self, connection_string: str):
        """Initialise l'adaptateur PostgreSQL.
        
        Args:
            connection_string: String de connexion PostgreSQL
        """
        # TODO: Implémenter avec psycopg2 ou asyncpg
        raise NotImplementedError("PostgreSQL adapter pas encore implémenté")
    
    def execute(self, query: str, params: Optional[tuple] = None) -> Any:
        raise NotImplementedError
    
    def fetch_one(self, query: str, params: Optional[tuple] = None) -> Optional[Dict[str, Any]]:
        raise NotImplementedError
    
    def fetch_all(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        raise NotImplementedError
    
    def close(self) -> None:
        raise NotImplementedError


class DatabaseManager:
    """Gestionnaire de base de données avec support multi-adaptateurs."""
    
    def __init__(self, db_type: str = "sqlite", **kwargs):
        """Initialise le gestionnaire.
        
        Args:
            db_type: Type de DB ('sqlite' ou 'postgresql')
            **kwargs: Arguments spécifiques à chaque type
                - Pour SQLite: db_path
                - Pour PostgreSQL: connection_string, host, port, database, user, password
        """
        self.db_type = db_type
        
        if db_type == "sqlite":
            db_path = kwargs.get("db_path", "web/data/cluster.db")
            self.adapter = SQLiteAdapter(db_path)
        elif db_type == "postgresql":
            # TODO: Implémenter quand on passera en prod
            connection_string = kwargs.get("connection_string")
            self.adapter = PostgreSQLAdapter(connection_string)
        else:
            raise ValueError(f"Type de base de données non supporté: {db_type}")
    
    def execute(self, query: str, params: Optional[tuple] = None) -> Any:
        """Exécute une requête."""
        return self.adapter.execute(query, params)
    
    def fetch_one(self, query: str, params: Optional[tuple] = None) -> Optional[Dict[str, Any]]:
        """Récupère une ligne."""
        return self.adapter.fetch_one(query, params)
    
    def fetch_all(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Récupère plusieurs lignes."""
        return self.adapter.fetch_all(query, params)
    
    def close(self) -> None:
        """Ferme la connexion."""
        self.adapter.close()

