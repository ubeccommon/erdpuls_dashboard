#!/usr/bin/env python3
"""
================================================================================
Database Schema Documentation Generator for Erdpuls Collective Threshold Model
================================================================================
Erdpuls Müllrose - Center for Sustainability Literacy

This script creates a comprehensive documentation of your database schema,
serving as the single source of truth for your database structure.

The documentation includes:
- Complete table structures with all columns and their properties
- Relationships between tables (foreign keys)
- Indexes for performance optimization
- Constraints that ensure data integrity
- Triggers and their purposes
- Visual relationship diagrams
- Contribution model documentation (privacy-protected contributions)
- Best practices and usage notes

Philosophy:
    "As we learn to think like a plant, we discover that technology and nature
    exist in symbiosis - distinct identities creating reciprocal support between
    our monitoring systems and the living world they observe."

This project uses the services of Claude and Anthropic PBC to inform our
decisions and recommendations.

================================================================================
The material is available as Open Educational Resource (OER) and is licensed 
under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International 
(CC BY-NC-SA 4.0). For license details visit:
https://creativecommons.org/licenses/by-nc-sa/4.0/deed.de
================================================================================

Author: Farmer
Version: 1.0.0
License: CC BY-NC-SA 4.0
"""

import psycopg2
import json
import os
import sys
import re
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging
import argparse
from pathlib import Path

# Try to import python-dotenv for loading .env files
try:
    from dotenv import load_dotenv
except ImportError:
    print("Warning: python-dotenv not installed. Trying to continue with environment variables.")
    print("To install: pip install python-dotenv --break-system-packages")
    load_dotenv = None

# Set up logging to help track the documentation process
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ================================================================================
# Constants
# ================================================================================

VERSION = "1.0.0"
DEFAULT_SCHEMA = "erdpuls_threshold"
DEFAULT_DATABASE = "ubec_erdpuls"
GENERATOR_NAME = "Erdpuls Collective Threshold Model Schema Documenter"
AUTHOR = "Farmer"
LICENSE = "CC BY-NC-SA 4.0"
LICENSE_URL = "https://creativecommons.org/licenses/by-nc-sa/4.0/deed.de"

# Erdpuls Platform specific tables for enhanced documentation
ERDPULS_CORE_TABLES = {
    'users': 'User accounts with authentication credentials (admin/user roles)',
    'offerings': 'Workshops, courses, events with threshold-based funding model',
    'registrations': 'Participation intentions (separate from contributions for privacy)',
    'contributions': 'ANONYMOUS contributions - no contributor identification stored!',
    'contribution_contacts': 'Separated contact info for operational purposes only',
    'regeneration_fund': 'Community reserve from surplus contributions',
    'token_rates': 'Exchange rates for UBECrc tokens to EUR',
    'hours_rates': 'Valuation rates for different types of contribution hours',
}

# Contribution types in Erdpuls Platform
ERDPULS_CONTRIBUTION_TYPES = {
    'euro': 'Direct monetary contribution in EUR',
    'token': 'UBECrc tokens earned through environmental stewardship (~70 tokens = €1)',
    'hours': 'Pre-arranged work valued by category (garden labor, technical, etc.)',
}

# Default roles in Erdpuls Platform (simplified)
ERDPULS_ROLES = {
    'user': {'level': 10, 'description': 'Can create offerings, participate, contribute'},
    'admin': {'level': 100, 'description': 'Full system access, fund management'},
}

# Hours contribution categories
ERDPULS_HOURS_CATEGORIES = {
    'garden_labor': {'eur_per_hour': 10, 'description': 'Weeding, planting, harvesting, composting'},
    'skilled_labor': {'eur_per_hour': 20, 'description': 'Carpentry, electrical, sensor installation'},
    'knowledge_sharing': {'eur_per_hour': 25, 'description': 'Leading sessions, mentoring, traditional knowledge'},
    'translation': {'eur_per_hour': 20, 'description': 'DE/EN/PL translation, documentation'},
    'technical_support': {'eur_per_hour': 30, 'description': 'Data processing, sensor calibration, web development'},
    'administrative': {'eur_per_hour': 12, 'description': 'Communication, scheduling, outreach'},
}


# ================================================================================
# Environment Configuration
# ================================================================================

def find_and_load_env_file() -> bool:
    """
    Search for and load the .env file from various possible locations.
    
    This function helps locate your project's .env file by checking common
    locations where it might be stored.
    
    Returns:
        bool: True if .env file was found and loaded, False otherwise
    """
    if load_dotenv is None:
        logger.warning("python-dotenv not available, skipping .env file loading")
        return False
        
    current_path = Path.cwd()
    paths_to_check = [
        current_path / '.env',
        current_path.parent / '.env',
        current_path.parent.parent / '.env',
    ]
    
    # Check for Erdpuls project root
    for parent in current_path.parents:
        if parent.name in ('erdpuls-threshold', 'erdpuls_threshold', 'erdpuls'):
            paths_to_check.insert(0, parent / '.env')
            break
    
    # Also check common deployment locations
    paths_to_check.extend([
        Path('/home/kelpit/UBEC_ERDPULS/.env'),
    ])
    
    for env_path in paths_to_check:
        if env_path.exists():
            logger.info(f"Found .env file at: {env_path}")
            load_dotenv(env_path)
            return True
    
    logger.warning("No .env file found in common locations")
    logger.info(f"Searched in: {[str(p) for p in paths_to_check]}")
    return False


def get_database_config() -> Dict[str, Any]:
    """
    Get database configuration from environment variables with multiple fallbacks.
    
    This function understands that different projects might use different
    environment variable names for the same purpose.
    
    Returns:
        Dict[str, Any]: Database configuration parameters
        
    Raises:
        ValueError: If database password is not configured
    """
    env_loaded = find_and_load_env_file()
    
    # Define multiple possible environment variable names
    config_mappings = {
        'host': ['DB_HOST', 'POSTGRES_HOST', 'DATABASE_HOST', 'PGHOST'],
        'port': ['DB_PORT', 'POSTGRES_PORT', 'DATABASE_PORT', 'PGPORT'],
        'database': ['DB_NAME', 'POSTGRES_DB', 'DATABASE_NAME', 'PGDATABASE'],
        'user': ['DB_USER', 'POSTGRES_USER', 'DATABASE_USER', 'PGUSER'],
        'password': ['DB_PASSWORD', 'POSTGRES_PASSWORD', 'DATABASE_PASSWORD', 'PGPASSWORD']
    }
    
    config = {}
    
    for param, possible_vars in config_mappings.items():
        value = None
        for var_name in possible_vars:
            value = os.environ.get(var_name)
            if value:
                break
        if value:
            config[param] = value
    
    # Try to parse DATABASE_URL if individual params not found
    database_url = os.environ.get('DATABASE_URL')
    if database_url and not all(k in config for k in ['host', 'database', 'user', 'password']):
        try:
            # Parse postgresql://user:password@host:port/database
            match = re.match(
                r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)',
                database_url
            )
            if match:
                config.setdefault('user', match.group(1))
                config.setdefault('password', match.group(2))
                config.setdefault('host', match.group(3))
                config.setdefault('port', match.group(4))
                config.setdefault('database', match.group(5))
                logger.info("Parsed database config from DATABASE_URL")
        except Exception as e:
            logger.warning(f"Could not parse DATABASE_URL: {e}")
    
    # Provide defaults for non-critical parameters
    defaults = {
        'host': 'localhost',
        'port': 5432,
        'database': DEFAULT_DATABASE,
        'user': 'ubecpuls'
    }
    
    for param, default_value in defaults.items():
        if param not in config:
            config[param] = default_value
            logger.warning(f"No {param} found, using default: {default_value}")
    
    # Password is critical
    if 'password' not in config:
        logger.error("No database password found in environment variables!")
        logger.info("Please ensure your .env file contains DATABASE_URL or DB_PASSWORD")
        
        db_related_vars = [
            var for var in os.environ.keys()
            if 'DB' in var or 'POSTGRES' in var or 'DATABASE' in var
        ]
        if db_related_vars:
            logger.info(f"Found these database-related vars: {', '.join(db_related_vars)}")
        
        raise ValueError("Database password not configured. Please check your .env file.")
    
    config['port'] = int(config['port'])
    return config


# ================================================================================
# Schema Documenter Class
# ================================================================================

class SchemaDocumenter:
    """
    A comprehensive schema documentation generator for the Erdpuls Collective
    Threshold Model platform.
    
    This class examines every aspect of your database structure and creates
    detailed documentation that serves as the single source of truth.
    
    Attributes:
        connection_params: Database connection parameters
        schema_name: PostgreSQL schema to document (default: erdpuls_threshold)
        conn: Active database connection
        documentation: Collected documentation data
    """
    
    def __init__(self, connection_params: Dict[str, Any], schema_name: str = DEFAULT_SCHEMA):
        """
        Initialize the documenter with database connection parameters.
        
        Args:
            connection_params: Database connection parameters (host, port, database, user, password)
            schema_name: The schema to document (default: 'erdpuls_threshold')
        """
        self.connection_params = connection_params
        self.schema_name = schema_name
        self.conn = None
        self.documentation = {
            'metadata': {},
            'tables': {},
            'relationships': [],
            'indexes': {},
            'triggers': {},
            'functions': {},
            'contribution_model': {},
            'summary': {}
        }
        
    def connect(self) -> None:
        """Establish connection to the database."""
        try:
            self.conn = psycopg2.connect(**self.connection_params)
            self.conn.autocommit = True
            logger.info("Successfully connected to database")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
            
    def disconnect(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
            
    def generate_documentation(self) -> Dict[str, Any]:
        """
        Generate complete schema documentation.
        
        This is the main orchestrator method that calls all specific
        documentation methods in the right order.
        
        Returns:
            Dict containing all documentation
        """
        logger.info(f"Starting schema documentation for '{self.schema_name}'")
        
        steps_completed = []
        
        try:
            logger.info("Step 1: Documenting metadata...")
            self._document_metadata()
            steps_completed.append('metadata')
            
            logger.info("Step 2: Documenting tables...")
            self._document_tables()
            steps_completed.append('tables')
            
            logger.info("Step 3: Documenting relationships...")
            self._document_relationships()
            steps_completed.append('relationships')
            
            logger.info("Step 4: Documenting indexes...")
            self._document_indexes()
            steps_completed.append('indexes')
            
            logger.info("Step 5: Documenting triggers...")
            self._document_triggers()
            steps_completed.append('triggers')
            
            logger.info("Step 6: Documenting functions...")
            self._document_functions()
            steps_completed.append('functions')
            
            logger.info("Step 7: Documenting contribution model...")
            self._document_contribution_model()
            steps_completed.append('contribution_model')
            
            logger.info("Step 8: Generating summary...")
            self._generate_summary()
            steps_completed.append('summary')
            
            logger.info("Schema documentation completed successfully")
            
        except Exception as e:
            logger.error(f"Error during documentation: {e}")
            logger.error(f"Steps completed before error: {', '.join(steps_completed)}")
            raise Exception(
                f"Documentation failed after: {', '.join(steps_completed)}. Error: {str(e)}"
            )
            
        return self.documentation
        
    def _document_metadata(self) -> None:
        """Document metadata about the database and documentation process."""
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT version()")
        pg_version = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT pg_database_size(current_database()) as size_bytes,
                   pg_size_pretty(pg_database_size(current_database())) as size_pretty
        """)
        db_size = cursor.fetchone()
        
        # Check for UUID extension
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM pg_extension WHERE extname = 'uuid-ossp'
            )
        """)
        has_uuid = cursor.fetchone()[0]
        
        # Check for pgcrypto extension
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM pg_extension WHERE extname = 'pgcrypto'
            )
        """)
        has_pgcrypto = cursor.fetchone()[0]
        
        self.documentation['metadata'] = {
            'generated_at': datetime.now().isoformat(),
            'schema_name': self.schema_name,
            'database_version': pg_version,
            'database_size': {
                'bytes': db_size[0],
                'human_readable': db_size[1]
            },
            'extensions': {
                'uuid-ossp': has_uuid,
                'pgcrypto': has_pgcrypto
            },
            'documentation_version': VERSION,
            'generator': GENERATOR_NAME,
            'project': 'Erdpuls Collective Threshold Model',
            'author': AUTHOR,
            'license': LICENSE,
            'license_url': LICENSE_URL
        }
        
        cursor.close()
        logger.info("Metadata documentation completed")
        
    def _document_tables(self) -> None:
        """Document all tables in the schema with complete details."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT 
                t.table_name,
                obj_description(c.oid) as table_comment
            FROM information_schema.tables t
            JOIN pg_class c ON c.relname = t.table_name
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE t.table_schema = %s 
            AND t.table_type = 'BASE TABLE'
            AND n.nspname = %s
            ORDER BY t.table_name
        """, (self.schema_name, self.schema_name))
        
        tables = cursor.fetchall()
        logger.info(f"Found {len(tables)} tables to document")
        
        for table_name, table_comment in tables:
            logger.info(f"Documenting table: {table_name}")
            
            # Get column information
            cursor.execute("""
                SELECT 
                    c.column_name,
                    c.data_type,
                    c.character_maximum_length,
                    c.numeric_precision,
                    c.numeric_scale,
                    c.is_nullable,
                    c.column_default,
                    c.is_identity,
                    c.is_generated,
                    c.generation_expression,
                    pgd.description as column_comment
                FROM information_schema.columns c
                LEFT JOIN pg_catalog.pg_description pgd ON 
                    pgd.objoid = (
                        SELECT oid FROM pg_class 
                        WHERE relname = c.table_name 
                        AND relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = c.table_schema)
                    )
                    AND pgd.objsubid = c.ordinal_position
                WHERE c.table_schema = %s 
                AND c.table_name = %s
                ORDER BY c.ordinal_position
            """, (self.schema_name, table_name))
            
            columns = []
            for col in cursor.fetchall():
                column_info = {
                    'name': col[0],
                    'data_type': self._format_data_type(col[1], col[2], col[3], col[4]),
                    'nullable': col[5] == 'YES',
                    'default': col[6],
                    'is_identity': col[7] == 'YES',
                    'is_generated': col[8] == 'ALWAYS',
                    'generation_expression': col[9],
                    'comment': col[10]
                }
                columns.append(column_info)
            
            # Get constraints
            cursor.execute("""
                SELECT 
                    con.conname as constraint_name,
                    con.contype as constraint_type,
                    pg_get_constraintdef(con.oid) as definition
                FROM pg_constraint con
                JOIN pg_namespace nsp ON nsp.oid = con.connamespace
                WHERE nsp.nspname = %s
                AND con.conrelid = (
                    SELECT oid FROM pg_class 
                    WHERE relname = %s 
                    AND relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = %s)
                )
                ORDER BY con.conname
            """, (self.schema_name, table_name, self.schema_name))
            
            constraints = []
            constraint_type_map = {
                'p': 'PRIMARY KEY',
                'u': 'UNIQUE',
                'c': 'CHECK',
                'f': 'FOREIGN KEY',
                'x': 'EXCLUSION'
            }
            for con in cursor.fetchall():
                constraints.append({
                    'name': con[0],
                    'type': constraint_type_map.get(con[1], con[1]),
                    'definition': con[2]
                })
            
            # Get row count and table size
            try:
                cursor.execute(f"""
                    SELECT 
                        COUNT(*) as row_count,
                        pg_size_pretty(pg_total_relation_size(
                            quote_ident(%s) || '.' || quote_ident(%s)
                        )) as total_size
                    FROM {self.schema_name}.{table_name}
                """, (self.schema_name, table_name))
                stats = cursor.fetchone()
            except Exception as e:
                logger.warning(f"Could not get stats for {table_name}: {e}")
                stats = (0, 'Unknown')
            
            # Add Erdpuls-specific description if known
            erdpuls_description = ERDPULS_CORE_TABLES.get(table_name)
            
            # Determine privacy sensitivity
            is_privacy_sensitive = table_name in ['contributions', 'contribution_contacts']
            
            self.documentation['tables'][table_name] = {
                'comment': table_comment,
                'erdpuls_description': erdpuls_description,
                'columns': columns,
                'constraints': constraints,
                'statistics': {
                    'row_count': stats[0],
                    'total_size': stats[1]
                },
                'is_erdpuls_core': table_name in ERDPULS_CORE_TABLES,
                'is_privacy_sensitive': is_privacy_sensitive
            }
        
        cursor.close()
        logger.info("Table documentation completed")
        
    def _format_data_type(
        self,
        data_type: str,
        char_length: Optional[int],
        numeric_precision: Optional[int],
        numeric_scale: Optional[int]
    ) -> str:
        """Format data type information into a readable string."""
        if data_type == 'character varying' and char_length:
            return f"varchar({char_length})"
        elif data_type == 'numeric' and numeric_precision:
            if numeric_scale:
                return f"numeric({numeric_precision},{numeric_scale})"
            return f"numeric({numeric_precision})"
        elif data_type == 'ARRAY':
            return "array"
        return data_type
            
    def _document_relationships(self) -> None:
        """Document all foreign key relationships between tables."""
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    tc.table_name as from_table,
                    kcu.column_name as from_column,
                    ccu.table_name as to_table,
                    ccu.column_name as to_column,
                    tc.constraint_name,
                    rc.update_rule,
                    rc.delete_rule
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu 
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage ccu 
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
                JOIN information_schema.referential_constraints rc
                    ON rc.constraint_name = tc.constraint_name
                    AND rc.constraint_schema = tc.table_schema
                WHERE tc.table_schema = %s
                AND tc.constraint_type = 'FOREIGN KEY'
                ORDER BY tc.table_name, tc.constraint_name
            """, (self.schema_name,))
            
            relationships = []
            for row in cursor.fetchall():
                if len(row) < 7:
                    continue
                    
                relationships.append({
                    'from_table': row[0],
                    'from_column': row[1],
                    'to_table': row[2],
                    'to_column': row[3],
                    'constraint_name': row[4],
                    'update_rule': row[5],
                    'delete_rule': row[6],
                    'relationship_type': self._infer_relationship_type(row[0], row[1], row[2])
                })
                
            self.documentation['relationships'] = relationships
            logger.info(f"Documented {len(relationships)} relationships")
            
        except Exception as e:
            logger.error(f"Error in relationship documentation: {e}")
            self.documentation['relationships'] = []
            
        finally:
            cursor.close()
        
    def _infer_relationship_type(
        self,
        from_table: str,
        from_column: str,
        to_table: str
    ) -> str:
        """Infer the type of relationship based on table and column names."""
        if from_column.endswith('_id'):
            if from_table.endswith('s') and to_table.endswith('s'):
                return "many-to-one (possible many-to-many via junction)"
            return "many-to-one"
        return "one-to-one"
            
    def _document_indexes(self) -> None:
        """Document all indexes in the schema."""
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    indexname,
                    tablename,
                    indexdef
                FROM pg_indexes
                WHERE schemaname = %s
                ORDER BY tablename, indexname
            """, (self.schema_name,))
            
            indexes_by_table = {}
            
            for row in cursor.fetchall():
                if len(row) < 3:
                    continue
                
                index_name = row[0]
                table_name = row[1]
                index_def = row[2]
                
                is_unique = 'UNIQUE' in index_def.upper()
                is_primary = index_name.endswith('_pkey')
                
                if table_name not in indexes_by_table:
                    indexes_by_table[table_name] = []
                
                indexes_by_table[table_name].append({
                    'name': index_name,
                    'definition': index_def,
                    'is_unique': is_unique,
                    'is_primary': is_primary,
                    'columns': self._extract_index_columns(index_def)
                })
            
            self.documentation['indexes'] = indexes_by_table
            total_indexes = sum(len(idxs) for idxs in indexes_by_table.values())
            logger.info(f"Documented {total_indexes} indexes")
            
        except Exception as e:
            logger.error(f"Error in index documentation: {e}")
            self.documentation['indexes'] = {}
            
        finally:
            cursor.close()
        
    def _extract_index_columns(self, index_def: str) -> List[str]:
        """Extract column names from an index definition."""
        if not index_def:
            return []
            
        try:
            match = re.search(r'\((.*?)\)', index_def)
            if match:
                columns_str = match.group(1)
                columns = []
                for col in columns_str.split(','):
                    col_clean = col.strip().split()[0].strip('"').strip("'")
                    if col_clean:
                        columns.append(col_clean)
                return columns
        except Exception as e:
            logger.warning(f"Error extracting index columns: {e}")
            
        return []
        
    def _document_triggers(self) -> None:
        """Document all triggers in the schema."""
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    trigger_name,
                    event_object_table,
                    event_manipulation,
                    action_timing,
                    action_orientation,
                    action_statement
                FROM information_schema.triggers
                WHERE trigger_schema = %s
                ORDER BY event_object_table, trigger_name
            """, (self.schema_name,))
            
            triggers_by_table = {}
            
            for row in cursor.fetchall():
                if len(row) < 6:
                    continue
                    
                table_name = row[1]
                if table_name not in triggers_by_table:
                    triggers_by_table[table_name] = []
                    
                triggers_by_table[table_name].append({
                    'name': row[0],
                    'event': row[2],
                    'timing': row[3],
                    'orientation': row[4],
                    'function': row[5]
                })
                
            self.documentation['triggers'] = triggers_by_table
            total_triggers = sum(len(trgs) for trgs in triggers_by_table.values())
            logger.info(f"Documented {total_triggers} triggers")
            
        except Exception as e:
            logger.error(f"Error documenting triggers: {e}")
            self.documentation['triggers'] = {}
            
        finally:
            cursor.close()
        
    def _document_functions(self) -> None:
        """Document custom functions and procedures in the schema."""
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    p.proname as function_name,
                    pg_get_function_result(p.oid) as return_type,
                    pg_get_function_arguments(p.oid) as arguments,
                    p.prosrc as source_code,
                    obj_description(p.oid) as comment,
                    l.lanname as language
                FROM pg_proc p
                JOIN pg_namespace n ON n.oid = p.pronamespace
                JOIN pg_language l ON l.oid = p.prolang
                WHERE n.nspname = %s
                AND p.prokind IN ('f', 'p')
                ORDER BY p.proname
            """, (self.schema_name,))
            
            functions = []
            for func in cursor.fetchall():
                functions.append({
                    'name': func[0],
                    'return_type': func[1],
                    'arguments': func[2],
                    'source_code': func[3],
                    'comment': func[4],
                    'language': func[5]
                })
                
            self.documentation['functions'] = functions
            logger.info(f"Documented {len(functions)} functions/procedures")
            
        except Exception as e:
            logger.error(f"Error documenting functions: {e}")
            self.documentation['functions'] = []
            
        finally:
            cursor.close()
            
    def _document_contribution_model(self) -> None:
        """Document the Erdpuls Collective Threshold contribution model."""
        cursor = self.conn.cursor()
        
        contribution_info = {
            'contribution_types': [],
            'hours_rates': [],
            'token_rates': [],
            'privacy_model': {
                'description': 'Community-Anonymous, Operationally-Known',
                'public_visibility': 'Aggregates only (total amount, contributor count)',
                'organizer_visibility': 'Individual contributions + linked contact info',
                'no_public_individual_amounts': True
            }
        }
        
        # Document contribution types
        for type_name, description in ERDPULS_CONTRIBUTION_TYPES.items():
            contribution_info['contribution_types'].append({
                'type': type_name,
                'description': description
            })
        
        try:
            # Document hours rates from database
            cursor.execute(f"""
                SELECT category, eur_per_hour, description
                FROM {self.schema_name}.hours_rates
                ORDER BY category
            """)
            for row in cursor.fetchall():
                contribution_info['hours_rates'].append({
                    'category': row[0],
                    'eur_per_hour': float(row[1]),
                    'description': row[2]
                })
            logger.info(f"Documented {len(contribution_info['hours_rates'])} hours rates")
            
        except Exception as e:
            logger.warning(f"Could not document hours rates from DB: {e}")
            # Use default hours categories
            for category, info in ERDPULS_HOURS_CATEGORIES.items():
                contribution_info['hours_rates'].append({
                    'category': category,
                    'eur_per_hour': info['eur_per_hour'],
                    'description': info['description']
                })
        
        try:
            # Document current token rate
            cursor.execute(f"""
                SELECT tokens_per_eur, effective_from
                FROM {self.schema_name}.token_rates
                WHERE effective_until IS NULL OR effective_until > NOW()
                ORDER BY effective_from DESC
                LIMIT 1
            """)
            row = cursor.fetchone()
            if row:
                contribution_info['token_rates'].append({
                    'tokens_per_eur': float(row[0]),
                    'effective_from': row[1].isoformat() if row[1] else None,
                    'description': f"Approximately {int(row[0])} UBECrc = €1"
                })
            logger.info("Documented token rate")
            
        except Exception as e:
            logger.warning(f"Could not document token rates from DB: {e}")
            # Use default
            contribution_info['token_rates'].append({
                'tokens_per_eur': 70.0,
                'effective_from': None,
                'description': 'Approximately 70 UBECrc = €1'
            })
        
        try:
            # Get Regeneration Fund balance
            cursor.execute(f"""
                SELECT COALESCE(SUM(
                    CASE 
                        WHEN transaction_type = 'surplus_in' THEN amount
                        WHEN transaction_type IN ('shortfall_cover', 'seed_offering') THEN -amount
                        WHEN transaction_type = 'adjustment' THEN amount
                        ELSE 0
                    END
                ), 0) as balance
                FROM {self.schema_name}.regeneration_fund
            """)
            balance = cursor.fetchone()[0]
            contribution_info['regeneration_fund'] = {
                'current_balance': float(balance),
                'purpose': 'Community reserve from surplus contributions'
            }
            logger.info(f"Documented Regeneration Fund balance: €{balance}")
            
        except Exception as e:
            logger.warning(f"Could not document Regeneration Fund: {e}")
        
        self.documentation['contribution_model'] = contribution_info
        cursor.close()

    def _generate_summary(self) -> None:
        """Generate summary statistics and insights."""
        tables = self.documentation['tables']
        relationships = self.documentation['relationships']
        indexes = self.documentation['indexes']
        triggers = self.documentation['triggers']
        functions = self.documentation['functions']
        
        # Count totals
        total_columns = sum(len(t['columns']) for t in tables.values())
        total_indexes = sum(len(idxs) for idxs in indexes.values())
        total_triggers = sum(len(trgs) for trgs in triggers.values())
        
        # Sort tables by row count
        tables_by_rows = sorted(
            [
                {'table': name, 'rows': info['statistics']['row_count']}
                for name, info in tables.items()
            ],
            key=lambda x: x['rows'],
            reverse=True
        )
        
        # Find most referenced tables
        referenced_counts = {}
        for rel in relationships:
            to_table = rel['to_table']
            referenced_counts[to_table] = referenced_counts.get(to_table, 0) + 1
        
        most_referenced = dict(
            sorted(referenced_counts.items(), key=lambda x: x[1], reverse=True)
        )
        
        # Find orphan tables (no relationships)
        all_tables = set(tables.keys())
        tables_with_relationships = set()
        for rel in relationships:
            tables_with_relationships.add(rel['from_table'])
            tables_with_relationships.add(rel['to_table'])
        orphan_tables = list(all_tables - tables_with_relationships)
        
        # Count Erdpuls core tables
        erdpuls_core_count = sum(1 for t in tables.values() if t.get('is_erdpuls_core'))
        
        # Count privacy-sensitive tables
        privacy_sensitive_count = sum(1 for t in tables.values() if t.get('is_privacy_sensitive'))
        
        self.documentation['summary'] = {
            'total_tables': len(tables),
            'total_columns': total_columns,
            'total_relationships': len(relationships),
            'total_indexes': total_indexes,
            'total_triggers': total_triggers,
            'total_functions': len(functions),
            'erdpuls_core_tables': erdpuls_core_count,
            'privacy_sensitive_tables': privacy_sensitive_count,
            'tables_by_rows': tables_by_rows,
            'most_referenced_tables': most_referenced,
            'orphan_tables': orphan_tables,
            'contribution_summary': {
                'contribution_types': len(self.documentation['contribution_model'].get('contribution_types', [])),
                'hours_categories': len(self.documentation['contribution_model'].get('hours_rates', []))
            }
        }
        
        logger.info("Summary generation completed")
        
    def save_documentation(
        self,
        output_format: str = 'markdown',
        output_file: Optional[str] = None
    ) -> None:
        """
        Save the documentation to a file.
        
        Args:
            output_format: Output format ('markdown', 'json', 'html')
            output_file: Output filename (auto-generated if not specified)
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if output_file:
            filename = output_file
        else:
            ext_map = {'markdown': 'md', 'json': 'json', 'html': 'html'}
            ext = ext_map.get(output_format, 'md')
            filename = f"erdpuls_schema_documentation_{timestamp}.{ext}"
        
        if output_format == 'markdown':
            self._save_as_markdown(filename)
        elif output_format == 'json':
            self._save_as_json(filename)
        elif output_format == 'html':
            self._save_as_html(filename)
        else:
            raise ValueError(f"Unsupported format: {output_format}")
            
    def _save_as_markdown(self, filename: str) -> None:
        """Save documentation as Markdown."""
        with open(filename, 'w') as f:
            # Header
            f.write("# 🌱 Erdpuls Collective Threshold Model - Database Schema Documentation\n\n")
            f.write("> **Single Source of Truth** for the Erdpuls Platform database structure\n\n")
            f.write("---\n\n")
            
            # Metadata
            meta = self.documentation['metadata']
            f.write("## Metadata\n\n")
            f.write(f"| Property | Value |\n")
            f.write(f"|----------|-------|\n")
            f.write(f"| Generated | {meta['generated_at']} |\n")
            f.write(f"| Schema | `{meta['schema_name']}` |\n")
            f.write(f"| Database Size | {meta['database_size']['human_readable']} |\n")
            f.write(f"| PostgreSQL | {meta['database_version'][:50]}... |\n")
            f.write(f"| UUID Extension | {'✅ Enabled' if meta['extensions']['uuid-ossp'] else '❌ Not installed'} |\n")
            f.write(f"| Author | {meta['author']} |\n")
            f.write(f"| License | [{meta['license']}]({meta['license_url']}) |\n\n")
            
            # Table of Contents
            f.write("## Table of Contents\n\n")
            f.write("1. [Summary](#summary)\n")
            f.write("2. [Contribution Model](#contribution-model)\n")
            f.write("3. [Tables](#tables)\n")
            f.write("4. [Relationships](#relationships)\n")
            f.write("5. [Indexes](#indexes)\n")
            f.write("6. [Functions](#functions)\n\n")
            
            # Summary
            f.write("## Summary\n\n")
            summary = self.documentation['summary']
            f.write(f"| Metric | Count |\n")
            f.write(f"|--------|-------|\n")
            f.write(f"| Tables | {summary['total_tables']} |\n")
            f.write(f"| Columns | {summary['total_columns']} |\n")
            f.write(f"| Relationships | {summary['total_relationships']} |\n")
            f.write(f"| Indexes | {summary['total_indexes']} |\n")
            f.write(f"| Triggers | {summary['total_triggers']} |\n")
            f.write(f"| Functions | {summary['total_functions']} |\n")
            f.write(f"| Erdpuls Core Tables | {summary['erdpuls_core_tables']} |\n")
            f.write(f"| Privacy-Sensitive Tables | {summary['privacy_sensitive_tables']} |\n\n")
            
            # Contribution Model
            f.write("## Contribution Model\n\n")
            contrib = self.documentation['contribution_model']
            
            f.write("### Privacy Model\n\n")
            f.write("> **Community-Anonymous, Operationally-Known**\n\n")
            f.write("- **Public visibility:** Aggregates only (total amount, contributor count)\n")
            f.write("- **Organizer visibility:** Individual contributions + linked contact info\n")
            f.write("- **No individual amounts displayed publicly**\n\n")
            
            f.write("### Contribution Types\n\n")
            f.write("| Type | Description |\n")
            f.write("|------|-------------|\n")
            for ct in contrib.get('contribution_types', []):
                f.write(f"| `{ct['type']}` | {ct['description']} |\n")
            f.write("\n")
            
            if contrib.get('hours_rates'):
                f.write("### Hours Contribution Rates\n\n")
                f.write("| Category | €/Hour | Description |\n")
                f.write("|----------|--------|-------------|\n")
                for hr in contrib['hours_rates']:
                    f.write(f"| `{hr['category']}` | €{hr['eur_per_hour']} | {hr.get('description', '')} |\n")
                f.write("\n")
            
            if contrib.get('token_rates'):
                f.write("### Token Exchange Rates\n\n")
                for tr in contrib['token_rates']:
                    f.write(f"- **Current rate:** {tr['tokens_per_eur']} UBECrc = €1\n")
                    f.write(f"- {tr['description']}\n\n")
            
            if contrib.get('regeneration_fund'):
                rf = contrib['regeneration_fund']
                f.write("### Regeneration Fund\n\n")
                f.write(f"- **Current Balance:** €{rf['current_balance']:.2f}\n")
                f.write(f"- **Purpose:** {rf['purpose']}\n\n")
            
            # Tables
            f.write("## Tables\n\n")
            for table_name, table_info in self.documentation['tables'].items():
                core_badge = " 🏛️" if table_info.get('is_erdpuls_core') else ""
                privacy_badge = " 🔒" if table_info.get('is_privacy_sensitive') else ""
                f.write(f"### {table_name}{core_badge}{privacy_badge}\n\n")
                
                if table_info.get('erdpuls_description'):
                    f.write(f"> {table_info['erdpuls_description']}\n\n")
                elif table_info.get('comment'):
                    f.write(f"> {table_info['comment']}\n\n")
                
                stats = table_info['statistics']
                f.write(f"**Rows:** {stats['row_count']:,} | **Size:** {stats['total_size']}\n\n")
                
                f.write("| Column | Type | Nullable | Default |\n")
                f.write("|--------|------|----------|--------|\n")
                for col in table_info['columns']:
                    nullable = '✓' if col['nullable'] else '✗'
                    default = col['default'][:30] if col['default'] else '-'
                    f.write(f"| `{col['name']}` | {col['data_type']} | {nullable} | {default} |\n")
                f.write("\n")
                
                if table_info['constraints']:
                    f.write("**Constraints:**\n\n")
                    for con in table_info['constraints']:
                        f.write(f"- `{con['name']}` ({con['type']})\n")
                    f.write("\n")
                
                f.write("---\n\n")
            
            # Relationships
            f.write("## Relationships\n\n")
            if self.documentation['relationships']:
                f.write("| From Table | Column | To Table | Column | On Delete |\n")
                f.write("|------------|--------|----------|--------|----------|\n")
                for rel in self.documentation['relationships']:
                    f.write(
                        f"| `{rel['from_table']}` | {rel['from_column']} | "
                        f"`{rel['to_table']}` | {rel['to_column']} | {rel['delete_rule']} |\n"
                    )
            else:
                f.write("No foreign key relationships defined.\n")
            f.write("\n")
            
            # Indexes
            f.write("## Indexes\n\n")
            for table_name, indexes in self.documentation['indexes'].items():
                f.write(f"### {table_name}\n\n")
                for idx in indexes:
                    icon = "🔑" if idx['is_primary'] else ("🔒" if idx['is_unique'] else "📇")
                    f.write(f"- {icon} `{idx['name']}` on ({', '.join(idx['columns'])})\n")
                f.write("\n")
            
            # Functions
            if self.documentation['functions']:
                f.write("## Functions\n\n")
                for func in self.documentation['functions']:
                    f.write(f"### {func['name']}\n\n")
                    f.write(f"- **Returns:** {func['return_type']}\n")
                    f.write(f"- **Arguments:** {func['arguments'] or 'none'}\n")
                    f.write(f"- **Language:** {func['language']}\n\n")
            
            # Footer
            f.write("---\n\n")
            f.write("*This project uses the services of Claude and Anthropic PBC to inform our ")
            f.write("decisions and recommendations.*\n\n")
            f.write(f"*Generated by {GENERATOR_NAME} v{VERSION}*\n\n")
            f.write("---\n\n")
            f.write(f"© {AUTHOR} | License: {LICENSE} | {LICENSE_URL}\n")
        
        logger.info(f"Documentation saved to {filename}")
        print(f"\n✅ Schema documentation saved to: {filename}")
        
    def _save_as_json(self, filename: str) -> None:
        """Save documentation as JSON."""
        with open(filename, 'w') as f:
            json.dump(self.documentation, f, indent=2, default=str)
        logger.info(f"Documentation saved to {filename}")
        print(f"\n✅ Schema documentation saved to: {filename}")
        
    def _save_as_html(self, filename: str) -> None:
        """Save documentation as HTML with Erdpuls styling."""
        meta = self.documentation['metadata']
        summary = self.documentation['summary']
        
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Erdpuls Collective Threshold Model - Schema Documentation</title>
    <style>
        :root {{
            --erdpuls-primary: #2d5016;
            --erdpuls-secondary: #4a7c23;
            --erdpuls-accent: #7cb342;
            --erdpuls-bg: #f5f7f3;
            --erdpuls-card: #ffffff;
            --erdpuls-text: #333333;
            --erdpuls-muted: #666666;
        }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: var(--erdpuls-bg);
            color: var(--erdpuls-text);
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        h1 {{
            color: var(--erdpuls-primary);
            border-bottom: 3px solid var(--erdpuls-accent);
            padding-bottom: 10px;
        }}
        h2 {{
            color: var(--erdpuls-secondary);
            margin-top: 30px;
        }}
        .card {{
            background: var(--erdpuls-card);
            border-radius: 8px;
            padding: 20px;
            margin: 15px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 15px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 10px;
            text-align: left;
        }}
        th {{
            background: var(--erdpuls-secondary);
            color: white;
        }}
        tr:nth-child(even) {{
            background: #f9f9f9;
        }}
        .badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 0.85em;
        }}
        .badge-core {{
            background: var(--erdpuls-accent);
            color: white;
        }}
        .badge-privacy {{
            background: #ff9800;
            color: white;
        }}
        code {{
            background: #e8e8e8;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }}
        .meta-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }}
        .meta-item {{
            background: var(--erdpuls-bg);
            padding: 15px;
            border-radius: 6px;
            text-align: center;
        }}
        .meta-value {{
            font-size: 1.5em;
            font-weight: bold;
            color: var(--erdpuls-primary);
        }}
        .privacy-notice {{
            background: #fff3cd;
            border-left: 4px solid #ff9800;
            padding: 15px;
            margin: 15px 0;
            border-radius: 0 8px 8px 0;
        }}
        .footer {{
            margin-top: 40px;
            padding: 20px;
            text-align: center;
            color: var(--erdpuls-muted);
            font-size: 0.9em;
        }}
        .license {{
            margin-top: 20px;
            padding: 15px;
            background: var(--erdpuls-card);
            border-radius: 8px;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🌱 Erdpuls Collective Threshold Model - Database Schema</h1>
        
        <div class="card">
            <h2>Overview</h2>
            <div class="meta-grid">
                <div class="meta-item">
                    <div class="meta-value">{summary['total_tables']}</div>
                    <div>Tables</div>
                </div>
                <div class="meta-item">
                    <div class="meta-value">{summary['total_columns']}</div>
                    <div>Columns</div>
                </div>
                <div class="meta-item">
                    <div class="meta-value">{summary['total_relationships']}</div>
                    <div>Relationships</div>
                </div>
                <div class="meta-item">
                    <div class="meta-value">{summary['total_indexes']}</div>
                    <div>Indexes</div>
                </div>
                <div class="meta-item">
                    <div class="meta-value">{summary['erdpuls_core_tables']}</div>
                    <div>Core Tables</div>
                </div>
                <div class="meta-item">
                    <div class="meta-value">{summary['contribution_summary']['contribution_types']}</div>
                    <div>Contribution Types</div>
                </div>
            </div>
        </div>
        
        <div class="privacy-notice">
            <strong>🔒 Privacy Model:</strong> Community-Anonymous, Operationally-Known<br>
            Contributions are privacy-protected. Individual amounts are never displayed publicly.
        </div>
        
        <div class="card">
            <h2>Metadata</h2>
            <table>
                <tr><th>Property</th><th>Value</th></tr>
                <tr><td>Generated</td><td>{meta['generated_at']}</td></tr>
                <tr><td>Schema</td><td><code>{meta['schema_name']}</code></td></tr>
                <tr><td>Database Size</td><td>{meta['database_size']['human_readable']}</td></tr>
                <tr><td>Author</td><td>{meta['author']}</td></tr>
                <tr><td>License</td><td><a href="{meta['license_url']}">{meta['license']}</a></td></tr>
            </table>
        </div>
        
        <div class="footer">
            <p>This project uses the services of Claude and Anthropic PBC.</p>
            <p>Generated by {GENERATOR_NAME} v{VERSION}</p>
            <div class="license">
                © {AUTHOR} | License: <a href="{LICENSE_URL}">{LICENSE}</a>
            </div>
        </div>
    </div>
</body>
</html>"""
        
        with open(filename, 'w') as f:
            f.write(html_content)
        logger.info(f"Documentation saved to {filename}")
        print(f"\n✅ Schema documentation saved to: {filename}")


# ================================================================================
# Main Entry Point
# ================================================================================

def main() -> int:
    """
    Main function that orchestrates the schema documentation process.
    
    Returns:
        int: Exit code (0 for success, 1 for error)
    """
    parser = argparse.ArgumentParser(
        description='Generate comprehensive database schema documentation for Erdpuls Collective Threshold Model',
        epilog='This tool creates a single source of truth for your database structure.'
    )
    
    # Try to get configuration from environment
    try:
        env_config = get_database_config()
    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}")
        print("\nTo fix this, create a .env file with your database credentials:")
        print("  DATABASE_URL=postgresql://user:password@localhost:5432/ubec_erdpuls")
        print("\nOr set individual variables:")
        print("  DB_HOST=localhost")
        print("  DB_PORT=5432")
        print("  DB_NAME=ubec_erdpuls")
        print("  DB_USER=ubecpuls")
        print("  DB_PASSWORD=your_password")
        return 1
    
    # Command line arguments
    parser.add_argument('--host', default=env_config['host'],
                       help='Database host')
    parser.add_argument('--port', type=int, default=env_config['port'],
                       help='Database port')
    parser.add_argument('--database', default=env_config['database'],
                       help='Database name')
    parser.add_argument('--user', default=env_config['user'],
                       help='Database user')
    parser.add_argument('--password', default=env_config.get('password'),
                       help='Database password')
    parser.add_argument('--schema', default=DEFAULT_SCHEMA,
                       help=f'Schema name to document (default: {DEFAULT_SCHEMA})')
    parser.add_argument('--format', choices=['markdown', 'json', 'html'],
                       default='markdown', help='Output format')
    parser.add_argument('--output', help='Output filename')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    conn_params = {
        'host': args.host,
        'port': args.port,
        'database': args.database,
        'user': args.user,
        'password': args.password
    }
    
    print("\n" + "=" * 60)
    print("  Erdpuls Collective Threshold Model - Schema Documentation")
    print("=" * 60)
    print(f"\n🔗 Connecting to database:")
    print(f"   Host: {conn_params['host']}")
    print(f"   Port: {conn_params['port']}")
    print(f"   Database: {conn_params['database']}")
    print(f"   Schema: {args.schema}\n")
    
    documenter = SchemaDocumenter(conn_params, args.schema)
    
    try:
        documenter.connect()
        
        print(f"📚 Generating schema documentation for '{args.schema}'...")
        print("   This will examine every aspect of your database structure.\n")
        
        documenter.generate_documentation()
        documenter.save_documentation(args.format, args.output)
        
        summary = documenter.documentation['summary']
        print(f"\n📊 Documentation Summary:")
        print(f"   - Documented {summary['total_tables']} tables")
        print(f"   - Found {summary['total_relationships']} relationships")
        print(f"   - Cataloged {summary['total_indexes']} indexes")
        print(f"   - Discovered {summary['total_triggers']} triggers")
        print(f"   - Erdpuls Core Tables: {summary['erdpuls_core_tables']}")
        print(f"   - Privacy-Sensitive Tables: {summary['privacy_sensitive_tables']}")
        
        if summary['orphan_tables']:
            print(f"\n⚠️  Found {len(summary['orphan_tables'])} orphan tables")
        
        print("\n✨ Your database schema documentation is ready!")
        print("   This serves as your single source of truth.\n")
        
    except Exception as e:
        logger.error(f"Error generating documentation: {e}")
        print(f"\n❌ Error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1
        
    finally:
        documenter.disconnect()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
