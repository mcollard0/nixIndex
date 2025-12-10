#!/usr/bin/env python3
"""
Database module for nixIndex.
SQLite schema with optimized indexes for fast token-based search.
"""

import sqlite3;
import time;
from typing import List, Tuple, Optional;
from pathlib import Path;


class Database:
    """Manage SQLite database for token storage and retrieval."""
    
    def __init__( self, db_path: str = "nixindex.db" ):
        """Initialize database connection."""
        self.db_path = db_path;
        self.conn = None;
        self.cursor = None;
    
    def connect( self ):
        """Connect to database and create schema if needed."""
        self.conn = sqlite3.connect( self.db_path );
        self.cursor = self.conn.cursor();
        self._create_schema();
    
    def close( self ):
        """Close database connection."""
        if self.conn:
            self.conn.close();
    
    def _create_schema( self ):
        """Create database schema with optimized indexes."""
        # Enable WAL mode for better concurrent access
        self.cursor.execute( "PRAGMA journal_mode=WAL" );
        
        # Encoding table
        self.cursor.execute( """
            CREATE TABLE IF NOT EXISTS encoding (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type VARCHAR( 50 ) NOT NULL
            )
        """ );
        
        # File table
        self.cursor.execute( """
            CREATE TABLE IF NOT EXISTS file (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename VARCHAR( 512 ) NOT NULL,
                encoding_id INTEGER,
                FOREIGN KEY ( encoding_id ) REFERENCES encoding( id )
            )
        """ );
        
        # Record table
        self.cursor.execute( """
            CREATE TABLE IF NOT EXISTS record (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_pos INTEGER NOT NULL,
                end_pos INTEGER NOT NULL
            )
        """ );
        
        # Token table
        self.cursor.execute( """
            CREATE TABLE IF NOT EXISTS token (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                value VARCHAR( 255 ) NOT NULL UNIQUE,
                count INTEGER DEFAULT 1
            )
        """ );
        
        # Token occurrence table
        self.cursor.execute( """
            CREATE TABLE IF NOT EXISTS token_occurrence (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_id INTEGER NOT NULL,
                record_id INTEGER NOT NULL,
                FOREIGN KEY ( token_id ) REFERENCES token( id ),
                FOREIGN KEY ( record_id ) REFERENCES record( id )
            )
        """ );
        
        # Create indexes for fast lookups
        self.cursor.execute( """
            CREATE INDEX IF NOT EXISTS idx_token_value ON token( value )
        """ );
        
        self.cursor.execute( """
            CREATE INDEX IF NOT EXISTS idx_token_occurrence_token_id 
            ON token_occurrence( token_id )
        """ );
        
        self.cursor.execute( """
            CREATE INDEX IF NOT EXISTS idx_token_occurrence_record_id 
            ON token_occurrence( record_id )
        """ );
        
        self.conn.commit();
    
    def truncate_tables( self ):
        """Truncate all tables for fresh import."""
        tables = [ 'token_occurrence', 'token', 'record', 'file', 'encoding' ];
        for table in tables:
            self.cursor.execute( f"DELETE FROM {table}" );
        self.conn.commit();
    
    def insert_encoding( self, encoding_type: str ) -> int:
        """Insert encoding type and return its ID."""
        self.cursor.execute( 
            "INSERT INTO encoding ( type ) VALUES ( ? )", 
            ( encoding_type, ) 
        );
        self.conn.commit();
        return self.cursor.lastrowid;
    
    def insert_file( self, filename: str, encoding_id: int ) -> int:
        """Insert file and return its ID."""
        self.cursor.execute( 
            "INSERT INTO file ( filename, encoding_id ) VALUES ( ?, ? )", 
            ( filename, encoding_id ) 
        );
        self.conn.commit();
        return self.cursor.lastrowid;
    
    def insert_record( self, start_pos: int, end_pos: int ) -> int:
        """Insert record and return its ID."""
        self.cursor.execute( 
            "INSERT INTO record ( start_pos, end_pos ) VALUES ( ?, ? )", 
            ( start_pos, end_pos ) 
        );
        return self.cursor.lastrowid;
    
    def insert_token( self, value: str ) -> int:
        """
        Insert token or update count if exists.
        Returns token ID.
        """
        # Try to get existing token
        self.cursor.execute( 
            "SELECT id, count FROM token WHERE value = ?", 
            ( value, ) 
        );
        result = self.cursor.fetchone();
        
        if result:
            token_id, count = result;
            self.cursor.execute( 
                "UPDATE token SET count = ? WHERE id = ?", 
                ( count + 1, token_id ) 
            );
            return token_id;
        else:
            self.cursor.execute( 
                "INSERT INTO token ( value, count ) VALUES ( ?, 1 )", 
                ( value, ) 
            );
            return self.cursor.lastrowid;
    
    def insert_token_occurrence( self, token_id: int, record_id: int ):
        """Insert token occurrence."""
        self.cursor.execute( 
            "INSERT INTO token_occurrence ( token_id, record_id ) VALUES ( ?, ? )", 
            ( token_id, record_id ) 
        );
    
    def commit( self ):
        """Commit current transaction."""
        self.conn.commit();
    
    def search_token( self, term: str ) -> List[ Tuple[ int, int, int ] ]:
        """
        Search for token and return list of ( record_id, start_pos, end_pos ).
        """
        self.cursor.execute( """
            SELECT DISTINCT r.id, r.start_pos, r.end_pos
            FROM token t
            JOIN token_occurrence tok_occ ON t.id = tok_occ.token_id
            JOIN record r ON tok_occ.record_id = r.id
            WHERE t.value = ?
            ORDER BY r.start_pos
        """, ( term, ) );
        
        return self.cursor.fetchall();
    
    def get_file_info( self ) -> Optional[ Tuple[ str, str ] ]:
        """Get filename and encoding type."""
        self.cursor.execute( """
            SELECT f.filename, e.type
            FROM file f
            JOIN encoding e ON f.encoding_id = e.id
            LIMIT 1
        """ );
        return self.cursor.fetchone();
    
    def apply_acuity_filter( self, min_count: int ) -> Tuple[ int, float ]:
        """
        Remove tokens with count less than min_count.
        Returns ( deleted_count, duration_seconds ).
        """
        start_time = time.time();
        
        # Get token IDs to delete
        self.cursor.execute( 
            "SELECT id FROM token WHERE count < ?", 
            ( min_count, ) 
        );
        token_ids = [ row[ 0 ] for row in self.cursor.fetchall() ];
        
        if not token_ids:
            return ( 0, time.time() - start_time );
        
        deleted_count = len( token_ids );
        
        # Delete in batches to avoid SQL variable limit (max 999)
        batch_size = 900;
        for i in range( 0, len( token_ids ), batch_size ):
            batch = token_ids[ i:i+batch_size ];
            placeholders = ','.join( [ '?' ] * len( batch ) );
            
            # Delete token occurrences for this batch
            self.cursor.execute( 
                f"DELETE FROM token_occurrence WHERE token_id IN ( {placeholders} )", 
                batch 
            );
            
            # Delete tokens for this batch
            self.cursor.execute( 
                f"DELETE FROM token WHERE id IN ( {placeholders} )", 
                batch 
            );
        
        # Commit before VACUUM (VACUUM can't run in transaction)
        self.conn.commit();
        
        # Rebuild tables and reindex
        self.cursor.execute( "VACUUM" );
        self.cursor.execute( "REINDEX" );
        
        duration = time.time() - start_time;
        return ( deleted_count, duration );
    
    def get_stats( self ) -> dict:
        """Get database statistics."""
        stats = {};
        
        self.cursor.execute( "SELECT COUNT(*) FROM token" );
        stats[ 'tokens' ] = self.cursor.fetchone()[ 0 ];
        
        self.cursor.execute( "SELECT COUNT(*) FROM record" );
        stats[ 'records' ] = self.cursor.fetchone()[ 0 ];
        
        self.cursor.execute( "SELECT COUNT(*) FROM token_occurrence" );
        stats[ 'occurrences' ] = self.cursor.fetchone()[ 0 ];
        
        return stats;
