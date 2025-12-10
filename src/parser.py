#!/usr/bin/env python3
"""
Parser module for nixIndex.
Chunk-based file parsing with configurable separator and tokenization.
"""

import re;
import sys;
from typing import Iterator, List, Optional;
from pathlib import Path;

from decoder import Decoder, DecoderError;
from database import Database;


class ParserError( Exception ):
    """Exception raised when parsing fails."""
    pass;


class Parser:
    """Parse files in chunks and extract tokens."""
    
    def __init__( self, db: Database, encoding: str = 'none', 
                  separator: str = '\n', chunk_size: int = 65536 ):
        """
        Initialize parser.
        
        Args:
            db: Database instance
            encoding: Encoding type for decoding
            separator: Record separator (character or regex)
            chunk_size: Chunk size in bytes
        """
        self.db = db;
        self.encoding = encoding;
        self.separator = separator;
        self.chunk_size = chunk_size;
        self.decoder = Decoder();
        
        # Compile regex for tokenization (split on non-alphanumeric)
        self.token_pattern = re.compile( r'[^a-zA-Z0-9]+' );
    
    @staticmethod
    def parse_chunk_size( size_str: str ) -> int:
        """
        Parse chunk size string with units.
        
        Args:
            size_str: Size string like "64", "1KB", "10MB", "2GB"
            
        Returns:
            Size in bytes
        """
        size_str = size_str.strip().upper();
        
        if size_str == 'NONE':
            return 65536;  # Default
        
        # Extract number and unit
        match = re.match( r'^(\d+)\s*([KMGT]?B?)?$', size_str );
        if not match:
            raise ValueError( f"Invalid chunk size format: {size_str}" );
        
        number = int( match.group( 1 ) );
        unit = match.group( 2 ) or '';
        
        # Convert to bytes
        multipliers = {
            '': 1024,  # Default to KB
            'K': 1024,
            'KB': 1024,
            'M': 1024 * 1024,
            'MB': 1024 * 1024,
            'G': 1024 * 1024 * 1024,
            'GB': 1024 * 1024 * 1024,
        };
        
        if unit not in multipliers:
            raise ValueError( f"Invalid unit: {unit}" );
        
        return number * multipliers[ unit ];
    
    def parse_file( self, filepath: str, use_stdin: bool = False ) -> None:
        """
        Parse file and populate database.
        
        Args:
            filepath: Path to file to parse
            use_stdin: If True, read from stdin instead
        """
        print( f"Parsing file: {filepath}" );
        print( f"Encoding: {self.encoding}" );
        print( f"Chunk size: {self.chunk_size} bytes" );
        print( f"Separator: {repr( self.separator )}" );
        
        # Insert encoding and file info
        encoding_id = self.db.insert_encoding( self.encoding );
        file_id = self.db.insert_file( filepath, encoding_id );
        
        # Read and decode file in chunks
        if use_stdin:
            decoded_data = self._read_and_decode_stdin();
        else:
            decoded_data = self._read_and_decode_file( filepath );
        
        # Parse records and tokenize
        self._parse_records( decoded_data );
        
        self.db.commit();
        
        stats = self.db.get_stats();
        print( f"\nParsing complete:" );
        print( f"  Records: {stats[ 'records' ]}" );
        print( f"  Unique tokens: {stats[ 'tokens' ]}" );
        print( f"  Token occurrences: {stats[ 'occurrences' ]}" );
    
    def _read_and_decode_file( self, filepath: str ) -> bytes:
        """Read and decode entire file."""
        print( f"Reading file..." );
        
        with open( filepath, 'rb' ) as f:
            encoded_data = f.read();
        
        print( f"File size: {len( encoded_data )} bytes" );
        
        if self.encoding != 'none':
            print( f"Decoding..." );
            decoded_data = self.decoder.decode( encoded_data, self.encoding );
            print( f"Decoded size: {len( decoded_data )} bytes" );
        else:
            decoded_data = encoded_data;
        
        return decoded_data;
    
    def _read_and_decode_stdin( self ) -> bytes:
        """Read and decode from stdin."""
        print( f"Reading from stdin..." );
        
        encoded_data = sys.stdin.buffer.read();
        
        print( f"Input size: {len( encoded_data )} bytes" );
        
        if self.encoding != 'none':
            print( f"Decoding..." );
            decoded_data = self.decoder.decode( encoded_data, self.encoding );
            print( f"Decoded size: {len( decoded_data )} bytes" );
        else:
            decoded_data = encoded_data;
        
        return decoded_data;
    
    def _parse_records( self, data: bytes ):
        """Parse records from decoded data."""
        print( f"Extracting records and tokens..." );
        
        # Convert to string for splitting
        try:
            text = data.decode( 'utf-8', errors='ignore' );
        except Exception:
            text = data.decode( 'latin-1', errors='ignore' );
        
        # Split by separator
        if self.separator == r'\n':
            records = text.split( '\n' );
        elif self.separator == r'\t':
            records = text.split( '\t' );
        else:
            # Try as regex first, fall back to literal
            try:
                records = re.split( self.separator, text );
            except re.error:
                records = text.split( self.separator );
        
        # Process each record
        pos = 0;
        batch_size = 1000;
        record_count = 0;
        
        for i, record_text in enumerate( records ):
            if not record_text.strip():
                pos += len( record_text.encode( 'utf-8', errors='ignore' ) ) + 1;
                continue;
            
            # Calculate positions
            record_bytes = record_text.encode( 'utf-8', errors='ignore' );
            start_pos = pos;
            end_pos = pos + len( record_bytes );
            pos = end_pos + 1;  # +1 for separator
            
            # Insert record
            record_id = self.db.insert_record( start_pos, end_pos );
            
            # Tokenize record
            tokens = self._tokenize( record_text );
            
            # Insert tokens and occurrences
            for token in tokens:
                if token:  # Skip empty tokens
                    token_id = self.db.insert_token( token.lower() );
                    self.db.insert_token_occurrence( token_id, record_id );
            
            record_count += 1;
            
            # Commit in batches for performance
            if record_count % batch_size == 0:
                self.db.commit();
                print( f"  Processed {record_count} records...", end='\r' );
        
        print( f"  Processed {record_count} records...done" );
    
    def _tokenize( self, text: str ) -> List[ str ]:
        """
        Tokenize text by splitting on non-alphanumeric characters.
        
        Args:
            text: Text to tokenize
            
        Returns:
            List of tokens
        """
        # Split on non-alphanumeric
        tokens = self.token_pattern.split( text );
        
        # Filter out empty strings and return
        return [ t for t in tokens if t ];
