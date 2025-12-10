#!/usr/bin/env python3
"""
Search module for nixIndex.
Fast token-based record retrieval with decoded output.
"""

import time;
from typing import List, Tuple;
from pathlib import Path;

from decoder import Decoder;
from database import Database;


class SearchError( Exception ):
    """Exception raised when search fails."""
    pass;


class Searcher:
    """Fast token-based search."""
    
    def __init__( self, db: Database ):
        """Initialize searcher."""
        self.db = db;
        self.decoder = Decoder();
    
    def search( self, term: str, filepath: str = None ) -> List[ str ]:
        """
        Search for term and return matching records.
        
        Args:
            term: Search term (single token)
            filepath: Optional path to source file for reading records
            
        Returns:
            List of matching record texts
        """
        start_time = time.time();
        
        # Search database for token
        print( f"Searching for: {term}" );
        results = self.db.search_token( term.lower() );
        
        if not results:
            elapsed = time.time() - start_time;
            print( f"\nNo results found ( {elapsed:.3f}s )" );
            return [];
        
        print( f"Found {len( results )} matching records" );
        
        # Get file info to know encoding
        file_info = self.db.get_file_info();
        if not file_info:
            raise SearchError( "No file information in database" );
        
        stored_filename, encoding = file_info;
        
        # Use provided filepath or stored one
        if not filepath:
            filepath = stored_filename;
        
        # Read file
        with open( filepath, 'rb' ) as f:
            encoded_data = f.read();
        
        # Decode if necessary
        if encoding != 'none':
            decoded_data = self.decoder.decode( encoded_data, encoding );
        else:
            decoded_data = encoded_data;
        
        # Convert to text
        try:
            text = decoded_data.decode( 'utf-8', errors='ignore' );
        except Exception:
            text = decoded_data.decode( 'latin-1', errors='ignore' );
        
        # Extract matching records
        text_bytes = text.encode( 'utf-8', errors='ignore' );
        matching_records = [];
        
        for record_id, start_pos, end_pos in results:
            # Extract record from decoded data
            record_text = text[ start_pos:end_pos ];
            matching_records.append( record_text );
        
        elapsed = time.time() - start_time;
        print( f"\nSearch completed in {elapsed:.3f}s" );
        
        return matching_records;
    
    def display_results( self, records: List[ str ], max_display: int = 10 ):
        """
        Display search results.
        
        Args:
            records: List of matching records
            max_display: Maximum number of records to display
        """
        if not records:
            return;
        
        print( f"\n{'=' * 60}" );
        print( f"Displaying {min( len( records ), max_display )} of {len( records )} results:" );
        print( f"{'=' * 60}\n" );
        
        for i, record in enumerate( records[ :max_display ] ):
            print( f"--- Record {i + 1} ---" );
            # Truncate long records
            if len( record ) > 500:
                print( record[ :500 ] + "..." );
            else:
                print( record );
            print();
        
        if len( records ) > max_display:
            print( f"... and {len( records ) - max_display} more results" );
