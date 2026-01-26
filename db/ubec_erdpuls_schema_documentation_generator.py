#!/usr/bin/env python3
"""
================================================================================
Database Schema Documentation Generator for UBEC IOT Platform
================================================================================
UBEC DAO Protocol - GNU General Public License v3.0

This script creates a comprehensive documentation of your database schema,
serving as the single source of truth for your database structure.

The documentation includes:
- Complete table structures with all columns and their properties
- Relationships between tables (foreign keys)
- Indexes for performance optimization
- Constraints that ensure data integrity
- Triggers and their purposes
- Visual relationship diagrams
- RBAC (Role-Based Access Control) documentation
- Best practices and usage notes

Philosophy:
    "As we learn to think like a plant, we discover that technology and nature
    are not opposites but complementary expressions of the same creative forces
    that shape our world."

This project uses the services of Claude and Anthropic PBC to inform our
decisions and recommendations. This project was made possible with the
assistance of Claude and Anthropic PBC.

Author: UBEC DAO Protocol
Version: 1.0.0
License: GPL-3.0
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
    print("To install: pip install python-dotenv")
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
DEFAULT_SCHEMA = "ubec_hub"
DEFAULT_DATABASE = "ubec_iot"
GENERATOR_NAME = "UBEC IOT Platform Schema Documenter"

# UBEC Platform specific tables for enhanced documentation
UBEC_CORE_TABLES = {
    'users': 'User accounts with authentication credentials',
    'user_sessions': 'JWT session tracking for token management',
    'roles': 'Role definitions for RBAC (member, contributor, project_manager, admin)',
    'user_roles': 'User-role assignments (many-to-many junction)',
    'permissions': 'Fine-grained permission definitions (resource:action pattern)',
    'role_permissions': 'Role-permission mappings',
    'endpoint_permissions': 'Database-driven API endpoint access control',
    'project_access': 'Project-level access control configuration',
    'project_endpoint_permissions': 'Per-project endpoint permission overrides',
}

# Default roles in UBEC Platform
UBEC_ROLES = {
    'member': {'level': 10, 'description': 'Basic authenticated user, read access'},
    'contributor': {'level': 20, 'description': 'Can submit observations, participate'},
    'project_manager': {'level': 50, 'description': 'Can manage project data, edit milestones'},
    'admin': {'level': 100, 'description': 'Full system access'},
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
    
    # Check for UBEC_IOT project root
    for parent in current_path.parents:
        if parent.name in ('UBEC_IOT', 'ubec_platform', 'ubec-iot'):
            paths_to_check.insert(0, parent / '.env')
            break
    
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
        'user': 'ubec'
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
    A comprehensive schema documentation generator for the UBEC IOT Platform.
    
    This class examines every aspect of your database structure and creates
    detailed documentation that serves as the single source of truth.
    
    Attributes:
        connection_params: Database connection parameters
        schema_name: PostgreSQL schema to document (default: ubec_hub)
        conn: Active database connection
        documentation: Collected documentation data
    """
    
    def __init__(self, connection_params: Dict[str, Any], schema_name: str = DEFAULT_SCHEMA):
        """
        Initialize the documenter with database connection parameters.
        
        Args:
            connection_params: Database connection parameters (host, port, database, user, password)
            schema_name: The schema to document (default: 'ubec_hub')
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
            'rbac': {},
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
            
            logger.info("Step 7: Documenting RBAC structure...")
            self._document_rbac()
            steps_completed.append('rbac')
            
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
        
        # Check for TimescaleDB extension
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'
            )
        """)
        has_timescale = cursor.fetchone()[0]
        
        self.documentation['metadata'] = {
            'generated_at': datetime.now().isoformat(),
            'schema_name': self.schema_name,
            'database_version': pg_version,
            'database_size': {
                'bytes': db_size[0],
                'human_readable': db_size[1]
            },
            'extensions': {
                'timescaledb': has_timescale
            },
            'documentation_version': VERSION,
            'generator': GENERATOR_NAME,
            'project': 'UBEC IOT Platform',
            'license': 'GPL-3.0'
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
            
            # Add UBEC-specific description if known
            ubec_description = UBEC_CORE_TABLES.get(table_name)
            
            self.documentation['tables'][table_name] = {
                'comment': table_comment,
                'ubec_description': ubec_description,
                'columns': columns,
                'constraints': constraints,
                'statistics': {
                    'row_count': stats[0],
                    'total_size': stats[1]
                },
                'is_ubec_core': table_name in UBEC_CORE_TABLES
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
            
    def _document_rbac(self) -> None:
        """Document RBAC (Role-Based Access Control) structure specific to UBEC."""
        cursor = self.conn.cursor()
        
        rbac_info = {
            'roles': [],
            'permissions': [],
            'role_permissions': [],
            'endpoint_permissions': []
        }
        
        try:
            # Document roles
            cursor.execute(f"""
                SELECT name, display_name, description, level, is_system
                FROM {self.schema_name}.roles
                ORDER BY level
            """)
            for row in cursor.fetchall():
                rbac_info['roles'].append({
                    'name': row[0],
                    'display_name': row[1],
                    'description': row[2],
                    'level': row[3],
                    'is_system': row[4]
                })
            logger.info(f"Documented {len(rbac_info['roles'])} roles")
            
        except Exception as e:
            logger.warning(f"Could not document roles table: {e}")
            # Use default UBEC roles
            for name, info in UBEC_ROLES.items():
                rbac_info['roles'].append({
                    'name': name,
                    'level': info['level'],
                    'description': info['description'],
                    'is_system': True
                })
        
        try:
            # Document permissions
            cursor.execute(f"""
                SELECT name, display_name, description, category, is_system
                FROM {self.schema_name}.permissions
                ORDER BY category, name
            """)
            for row in cursor.fetchall():
                rbac_info['permissions'].append({
                    'name': row[0],
                    'display_name': row[1],
                    'description': row[2],
                    'category': row[3],
                    'is_system': row[4]
                })
            logger.info(f"Documented {len(rbac_info['permissions'])} permissions")
            
        except Exception as e:
            logger.warning(f"Could not document permissions table: {e}")
        
        try:
            # Document role-permission mappings
            cursor.execute(f"""
                SELECT r.name as role_name, p.name as permission_name
                FROM {self.schema_name}.role_permissions rp
                JOIN {self.schema_name}.roles r ON r.id = rp.role_id
                JOIN {self.schema_name}.permissions p ON p.id = rp.permission_id
                ORDER BY r.name, p.name
            """)
            for row in cursor.fetchall():
                rbac_info['role_permissions'].append({
                    'role': row[0],
                    'permission': row[1]
                })
            logger.info(f"Documented {len(rbac_info['role_permissions'])} role-permission mappings")
            
        except Exception as e:
            logger.warning(f"Could not document role_permissions: {e}")
        
        try:
            # Document endpoint permissions
            cursor.execute(f"""
                SELECT path_pattern, method, name, category, is_public, allowed_roles
                FROM {self.schema_name}.endpoint_permissions
                WHERE is_enabled = true
                ORDER BY category, path_pattern
            """)
            for row in cursor.fetchall():
                rbac_info['endpoint_permissions'].append({
                    'path_pattern': row[0],
                    'method': row[1],
                    'name': row[2],
                    'category': row[3],
                    'is_public': row[4],
                    'allowed_roles': row[5] or []
                })
            logger.info(f"Documented {len(rbac_info['endpoint_permissions'])} endpoint permissions")
            
        except Exception as e:
            logger.warning(f"Could not document endpoint_permissions: {e}")
        
        self.documentation['rbac'] = rbac_info
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
        
        # Count UBEC core tables
        ubec_core_count = sum(1 for t in tables.values() if t.get('is_ubec_core'))
        
        self.documentation['summary'] = {
            'total_tables': len(tables),
            'total_columns': total_columns,
            'total_relationships': len(relationships),
            'total_indexes': total_indexes,
            'total_triggers': total_triggers,
            'total_functions': len(functions),
            'ubec_core_tables': ubec_core_count,
            'tables_by_rows': tables_by_rows,
            'most_referenced_tables': most_referenced,
            'orphan_tables': orphan_tables,
            'rbac_summary': {
                'roles': len(self.documentation['rbac'].get('roles', [])),
                'permissions': len(self.documentation['rbac'].get('permissions', [])),
                'endpoint_rules': len(self.documentation['rbac'].get('endpoint_permissions', []))
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
            filename = f"ubec_iot_schema_documentation_{timestamp}.{ext}"
        
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
            f.write("# UBEC IOT Platform - Database Schema Documentation\n\n")
            f.write("> **Single Source of Truth** for the UBEC Platform database structure\n\n")
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
            f.write(f"| TimescaleDB | {'✅ Enabled' if meta['extensions']['timescaledb'] else '❌ Not installed'} |\n")
            f.write(f"| License | {meta['license']} |\n\n")
            
            # Table of Contents
            f.write("## Table of Contents\n\n")
            f.write("1. [Summary](#summary)\n")
            f.write("2. [RBAC Structure](#rbac-structure)\n")
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
            f.write(f"| UBEC Core Tables | {summary['ubec_core_tables']} |\n\n")
            
            # RBAC Structure
            f.write("## RBAC Structure\n\n")
            rbac = self.documentation['rbac']
            
            f.write("### Roles\n\n")
            f.write("| Role | Level | Description |\n")
            f.write("|------|-------|-------------|\n")
            for role in rbac.get('roles', []):
                f.write(f"| `{role['name']}` | {role.get('level', 'N/A')} | {role.get('description', '')} |\n")
            f.write("\n")
            
            if rbac.get('permissions'):
                f.write("### Permissions\n\n")
                f.write("| Permission | Category | Description |\n")
                f.write("|------------|----------|-------------|\n")
                for perm in rbac['permissions'][:20]:  # Limit to first 20
                    f.write(f"| `{perm['name']}` | {perm.get('category', '')} | {perm.get('description', '')[:50] or ''} |\n")
                if len(rbac['permissions']) > 20:
                    f.write(f"\n*...and {len(rbac['permissions']) - 20} more permissions*\n")
                f.write("\n")
            
            if rbac.get('endpoint_permissions'):
                f.write("### Endpoint Permissions\n\n")
                f.write("| Path Pattern | Method | Public | Allowed Roles |\n")
                f.write("|--------------|--------|--------|---------------|\n")
                for ep in rbac['endpoint_permissions'][:15]:
                    roles = ', '.join(ep.get('allowed_roles', [])) or '-'
                    public = '✅' if ep.get('is_public') else '🔒'
                    f.write(f"| `{ep['path_pattern']}` | {ep['method']} | {public} | {roles} |\n")
                if len(rbac['endpoint_permissions']) > 15:
                    f.write(f"\n*...and {len(rbac['endpoint_permissions']) - 15} more endpoint rules*\n")
                f.write("\n")
            
            # Tables
            f.write("## Tables\n\n")
            for table_name, table_info in self.documentation['tables'].items():
                core_badge = " 🏛️" if table_info.get('is_ubec_core') else ""
                f.write(f"### {table_name}{core_badge}\n\n")
                
                if table_info.get('ubec_description'):
                    f.write(f"> {table_info['ubec_description']}\n\n")
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
            f.write("decisions and recommendations. This project was made possible with the ")
            f.write("assistance of Claude and Anthropic PBC.*\n\n")
            f.write(f"*Generated by {GENERATOR_NAME} v{VERSION}*\n")
        
        logger.info(f"Documentation saved to {filename}")
        print(f"\n✅ Schema documentation saved to: {filename}")
        
    def _save_as_json(self, filename: str) -> None:
        """Save documentation as JSON."""
        with open(filename, 'w') as f:
            json.dump(self.documentation, f, indent=2, default=str)
        logger.info(f"Documentation saved to {filename}")
        print(f"\n✅ Schema documentation saved to: {filename}")
        
    def _save_as_html(self, filename: str) -> None:
        """Save documentation as HTML with UBEC styling."""
        meta = self.documentation['metadata']
        summary = self.documentation['summary']
        
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>UBEC IOT Platform - Schema Documentation</title>
    <style>
        :root {{
            --ubec-primary: #2d5016;
            --ubec-secondary: #4a7c23;
            --ubec-accent: #7cb342;
            --ubec-bg: #f5f7f3;
            --ubec-card: #ffffff;
            --ubec-text: #333333;
            --ubec-muted: #666666;
        }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: var(--ubec-bg);
            color: var(--ubec-text);
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        h1 {{
            color: var(--ubec-primary);
            border-bottom: 3px solid var(--ubec-accent);
            padding-bottom: 10px;
        }}
        h2 {{
            color: var(--ubec-secondary);
            margin-top: 30px;
        }}
        .card {{
            background: var(--ubec-card);
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
            background: var(--ubec-secondary);
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
            background: var(--ubec-accent);
            color: white;
        }}
        .badge-public {{
            background: #4caf50;
            color: white;
        }}
        .badge-private {{
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
            background: var(--ubec-bg);
            padding: 15px;
            border-radius: 6px;
            text-align: center;
        }}
        .meta-value {{
            font-size: 1.5em;
            font-weight: bold;
            color: var(--ubec-primary);
        }}
        .footer {{
            margin-top: 40px;
            padding: 20px;
            text-align: center;
            color: var(--ubec-muted);
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🌱 UBEC IOT Platform - Database Schema</h1>
        
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
                    <div class="meta-value">{summary['rbac_summary']['roles']}</div>
                    <div>Roles</div>
                </div>
                <div class="meta-item">
                    <div class="meta-value">{summary['rbac_summary']['permissions']}</div>
                    <div>Permissions</div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>Metadata</h2>
            <table>
                <tr><th>Property</th><th>Value</th></tr>
                <tr><td>Generated</td><td>{meta['generated_at']}</td></tr>
                <tr><td>Schema</td><td><code>{meta['schema_name']}</code></td></tr>
                <tr><td>Database Size</td><td>{meta['database_size']['human_readable']}</td></tr>
                <tr><td>License</td><td>{meta['license']}</td></tr>
            </table>
        </div>
        
        <div class="footer">
            <p>This project uses the services of Claude and Anthropic PBC.</p>
            <p>Generated by {GENERATOR_NAME} v{VERSION}</p>
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
        description='Generate comprehensive database schema documentation for UBEC IOT Platform',
        epilog='This tool creates a single source of truth for your database structure.'
    )
    
    # Try to get configuration from environment
    try:
        env_config = get_database_config()
    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}")
        print("\nTo fix this, create a .env file with your database credentials:")
        print("  DATABASE_URL=postgresql://ubec:password@localhost:5432/ubec_platform")
        print("\nOr set individual variables:")
        print("  DB_HOST=localhost")
        print("  DB_PORT=5432")
        print("  DB_NAME=ubec_platform")
        print("  DB_USER=ubec")
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
    print("  UBEC IOT Platform - Schema Documentation Generator")
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
        print(f"   - RBAC: {summary['rbac_summary']['roles']} roles, "
              f"{summary['rbac_summary']['permissions']} permissions")
        
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
