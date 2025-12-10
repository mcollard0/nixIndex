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
        
        # Use streaming decompression for large files to avoid OOM
        import gzip;
        import io;
        
        # Determine if we can stream (only gzip supported for streaming)
        can_stream = ( encoding == 'gzip' or encoding == 'gz' );
        
        if can_stream:
            # Stream decompress and extract only needed records
            matching_records = self._stream_extract_records( filepath, results );
        else:
            # Fall back to full decode for other encodings
            matching_records = self._full_extract_records( filepath, encoding, results );
        
        elapsed = time.time() - start_time;
        print( f"\nSearch completed in {elapsed:.3f}s" );
        
        return matching_records;
    
    def _stream_extract_records( self, filepath: str, results: List[ Tuple[ int, int, int ] ] ) -> List[ str ]:
        """Extract records using streaming decompression (for gzip)."""
        import gzip;
        import os;
        
        matching_records = [];
        
        # Check file size - if very large (>10GB compressed), use system gzip
        file_size = os.path.getsize( filepath );
        if file_size > 10 * 1024 * 1024 * 1024:  # > 10GB
            print( f"  Large file detected ({file_size / (1024**3):.1f} GB), using system gzip..." );
            return self._system_gzip_extract( filepath, results );
        
        # Sort results by start position for efficient streaming
        sorted_results = sorted( results, key=lambda x: x[ 1 ] );
        
        # Open gzip file for streaming
        with gzip.open( filepath, 'rt', encoding='utf-8', errors='ignore' ) as f:
            current_pos = 0;
            buffer = "";
            result_idx = 0;
            
            # Read in chunks
            chunk_size = 10 * 1024 * 1024;  # 10MB chunks
            
            while result_idx < len( sorted_results ):
                record_id, start_pos, end_pos = sorted_results[ result_idx ];
                
                # Read until we have the record
                while current_pos + len( buffer ) <= end_pos:
                    chunk = f.read( chunk_size );
                    if not chunk:
                        break;
                    buffer += chunk;
                
                # Extract record from buffer
                buffer_start = start_pos - current_pos;
                buffer_end = end_pos - current_pos;
                
                if buffer_start >= 0 and buffer_end <= len( buffer ):
                    record_text = buffer[ buffer_start:buffer_end ];
                    matching_records.append( record_text );
                    result_idx += 1;
                else:
                    # Record not in current buffer, need to read more
                    chunk = f.read( chunk_size );
                    if not chunk:
                        break;  # EOF reached
                    buffer += chunk;
                
                # Trim buffer to save memory (keep last 1MB)
                if len( buffer ) > chunk_size * 2:
                    trim_pos = len( buffer ) - 1024 * 1024;
                    buffer = buffer[ trim_pos: ];
                    current_pos += trim_pos;
        
        return matching_records;
    
    def _full_extract_records( self, filepath: str, encoding: str, results: List[ Tuple[ int, int, int ] ] ) -> List[ str ]:
        """Extract records using full file decode (for non-gzip encodings)."""
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
        matching_records = [];
        for record_id, start_pos, end_pos in results:
            record_text = text[ start_pos:end_pos ];
            matching_records.append( record_text );
        
        return matching_records;
    
    def _system_gzip_extract( self, filepath: str, results: List[ Tuple[ int, int, int ] ] ) -> List[ str ]:
        """Extract records using system gzip command (for very large files)."""
        import subprocess;
        import platform;
        import tempfile;
        import os;
        
        matching_records = [];
        
        # Determine gzip command based on OS
        system = platform.system();
        if system == 'Windows':
            # Try common Windows gzip locations
            gzip_cmd = None;
            for cmd in [ 'gzip', 'C:\\Program Files\\Git\\usr\\bin\\gzip.exe', 'C:\\msys64\\usr\\bin\\gzip.exe' ]:
                try:
                    subprocess.run( [ cmd, '--version' ], capture_output=True, check=True );
                    gzip_cmd = cmd;
                    break;
                except ( subprocess.CalledProcessError, FileNotFoundError ):
                    continue;
            
            if not gzip_cmd:
                # Fall back to Python gzip
                print( "  System gzip not found on Windows, using Python gzip..." );
                return self._stream_extract_records_simple( filepath, results );
        else:
            # Linux/Mac - gzip should be available
            gzip_cmd = 'gzip';
        
        # Extract records using system gzip with byte range extraction
        # This uses a temporary fifo/pipe approach for streaming
        sorted_results = sorted( results, key=lambda x: x[ 1 ] );
        
        # Use subprocess to stream decompress and extract byte ranges
        try:
            # Create temporary file for extracted content if needed
            # For very large files, we extract only the regions we need
            
            # Process results in batches to avoid too many subprocesses
            batch_size = 100;
            for batch_start in range( 0, len( sorted_results ), batch_size ):
                batch_end = min( batch_start + batch_size, len( sorted_results ) );
                batch = sorted_results[ batch_start:batch_end ];
                
                if not batch:
                    continue;
                
                # Find min and max positions for this batch
                min_pos = batch[ 0 ][ 1 ];
                max_pos = batch[ -1 ][ 2 ];
                
                # Stream decompress and extract region
                # Use gzip -cd to decompress to stdout
                proc = subprocess.Popen(
                    [ gzip_cmd, '-cd', filepath ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL
                );
                
                # Read and extract records from stream
                current_pos = 0;
                buffer = b'';
                chunk_size = 10 * 1024 * 1024;  # 10MB
                
                for record_id, start_pos, end_pos in batch:
                    # Skip ahead if needed
                    while current_pos < start_pos:
                        skip_amount = min( chunk_size, start_pos - current_pos );
                        skipped = proc.stdout.read( skip_amount );
                        if not skipped:
                            break;
                        current_pos += len( skipped );
                    
                    # Read the record
                    record_size = end_pos - start_pos;
                    record_data = proc.stdout.read( record_size );
                    current_pos += len( record_data );
                    
                    if record_data:
                        try:
                            record_text = record_data.decode( 'utf-8', errors='ignore' );
                            matching_records.append( record_text );
                        except Exception:
                            pass;
                
                proc.stdout.close();
                proc.wait();
        
        except Exception as e:
            print( f"  System gzip failed ({str( e )}), falling back to Python gzip..." );
            return self._stream_extract_records_simple( filepath, results );
        
        return matching_records;
    
    def _stream_extract_records_simple( self, filepath: str, results: List[ Tuple[ int, int, int ] ] ) -> List[ str ]:
        """Simplified streaming extraction without system gzip."""
        import gzip;
        
        matching_records = [];
        sorted_results = sorted( results, key=lambda x: x[ 1 ] );
        
        with gzip.open( filepath, 'rt', encoding='utf-8', errors='ignore' ) as f:
            current_pos = 0;
            chunk_size = 1024 * 1024;  # 1MB chunks to reduce memory
            
            for record_id, start_pos, end_pos in sorted_results:
                # Skip to start position
                while current_pos < start_pos:
                    skip_amount = min( chunk_size, start_pos - current_pos );
                    f.read( skip_amount );
                    current_pos += skip_amount;
                
                # Read record
                record_size = end_pos - start_pos;
                record_text = f.read( record_size );
                current_pos += len( record_text );
                
                if record_text:
                    matching_records.append( record_text );
        
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
