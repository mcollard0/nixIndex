#!/usr/bin/env python3
"""
Test nixIndex with 100GB file.
Creates a 100GB file by repeating base data, gzips it, then tests search performance.
"""

import sys;
import os;
import time;
import gzip;

# Add src to path
sys.path.insert( 0, os.path.join( os.path.dirname( __file__ ), '..', 'src' ) );

from database import Database;
from parser import Parser;
from search import Searcher;


def create_100gb_test_file():
    """Create 100GB test file by repeating base data."""
    print( "\n=== Creating 100GB Test File ===" );
    
    # Base data - Yelp-like JSON records
    base_data = """{{"business_id":"abc123","name":"Great Restaurant","city":"Phoenix","stars":4.5,"review":"Excellent food and service"}}
{{"business_id":"def456","name":"Amazing Cafe","city":"Portland","stars":4.0,"review":"Good coffee and atmosphere"}}
{{"business_id":"ghi789","name":"Superb Bistro","city":"Seattle","stars":5.0,"review":"Outstanding quality"}}
{{"business_id":"jkl012","name":"Wonderful Diner","city":"Austin","stars":3.5,"review":"Decent place for breakfast"}}
{{"business_id":"mno345","name":"Excellent Eatery","city":"Denver","stars":4.8,"review":"Highly recommended"}}
{{"business_id":"pqr678","name":"Fantastic Grill","city":"Chicago","stars":4.2,"review":"Great steaks"}}
{{"business_id":"stu901","name":"Marvelous Kitchen","city":"Boston","stars":4.7,"review":"Creative menu"}}
{{"business_id":"vwx234","name":"Splendid Pub","city":"Miami","stars":3.8,"review":"Fun atmosphere"}}
{{"business_id":"yza567","name":"Delightful Tavern","city":"Dallas","stars":4.3,"review":"Nice selection"}}
{{"business_id":"bcd890","name":"Remarkable Lounge","city":"Atlanta","stars":4.6,"review":"Cozy ambiance"}}
""";
    
    base_size = len( base_data.encode( 'utf-8' ) );
    target_size = 100 * 1024 * 1024 * 1024;  # 100GB
    repetitions = target_size // base_size + 1;
    
    print( f"Base data size: {base_size} bytes" );
    print( f"Target size: {target_size / (1024**3):.2f} GB" );
    print( f"Repetitions needed: {repetitions:,}" );
    
    # Output paths
    raw_path = '/Media/4/nixindex_test_100gb.txt';
    gz_path = '/Media/4/nixindex_test_100gb.txt.gz';
    
    print( f"\nCreating raw file: {raw_path}" );
    print( "This will take several minutes..." );
    
    start_time = time.time();
    
    # Write raw file
    with open( raw_path, 'w' ) as f:
        for i in range( repetitions ):
            f.write( base_data );
            if i % 100000 == 0 and i > 0:
                elapsed = time.time() - start_time;
                percent = ( i / repetitions ) * 100;
                print( f"  Progress: {percent:.1f}% ({elapsed:.1f}s elapsed)" );
    
    raw_time = time.time() - start_time;
    raw_size = os.path.getsize( raw_path );
    
    print( f"\nRaw file created: {raw_size / (1024**3):.2f} GB in {raw_time:.1f}s" );
    
    # Compress with gzip
    print( f"\nCompressing to: {gz_path}" );
    print( "This will take several minutes..." );
    
    gz_start = time.time();
    
    with open( raw_path, 'rb' ) as f_in:
        with gzip.open( gz_path, 'wb' ) as f_out:
            chunk_size = 10 * 1024 * 1024;  # 10MB chunks
            chunks_written = 0;
            
            while True:
                chunk = f_in.read( chunk_size );
                if not chunk:
                    break;
                f_out.write( chunk );
                chunks_written += 1;
                
                if chunks_written % 100 == 0:
                    elapsed = time.time() - gz_start;
                    print( f"  Compressed {chunks_written * chunk_size / (1024**3):.2f} GB ({elapsed:.1f}s elapsed)" );
    
    gz_time = time.time() - gz_start;
    gz_size = os.path.getsize( gz_path );
    compression_ratio = raw_size / gz_size;
    
    print( f"\nCompression complete:" );
    print( f"  Raw size: {raw_size / (1024**3):.2f} GB" );
    print( f"  Compressed size: {gz_size / (1024**3):.2f} GB" );
    print( f"  Compression ratio: {compression_ratio:.2f}x" );
    print( f"  Time: {gz_time:.1f}s" );
    
    # Remove raw file to save space
    print( f"\nRemoving raw file to save space..." );
    os.remove( raw_path );
    
    return gz_path;


def test_100gb_search( gz_path ):
    """Test search on 100GB gzipped file."""
    print( "\n=== Testing 100GB Search ===" );
    
    db_path = '/Media/4/nixindex_test_100gb.db';
    
    # Remove old database if exists
    if os.path.exists( db_path ):
        os.remove( db_path );
    
    # Import data
    print( f"\nImporting {gz_path}..." );
    print( "This will take some time..." );
    
    import_start = time.time();
    
    db = Database( db_path );
    db.connect();
    db.truncate_tables();
    
    parser = Parser( db, encoding='gzip', separator='\\n', chunk_size=10*1024*1024 );
    parser.parse_file( gz_path );
    
    import_time = time.time() - import_start;
    
    stats = db.get_stats();
    print( f"\nImport complete in {import_time:.1f}s" );
    print( f"  Records: {stats[ 'records' ]:,}" );
    print( f"  Unique tokens: {stats[ 'tokens' ]:,}" );
    print( f"  Token occurrences: {stats[ 'occurrences' ]:,}" );
    
    # Test searches for various terms
    test_terms = [ 'restaurant', 'phoenix', 'excellent', 'stars', 'abc123' ];
    
    searcher = Searcher( db );
    
    print( f"\n=== Search Performance Tests ===" );
    
    for term in test_terms:
        print( f"\nSearching for: '{term}'" );
        
        start_time = time.time();
        results = searcher.search( term, filepath=gz_path );
        elapsed = time.time() - start_time;
        
        print( f"  Found {len( results ):,} results in {elapsed:.3f}s" );
        
        if elapsed < 2.0:
            print( f"  ✓ PASS (< 2s target)" );
        else:
            print( f"  ✗ FAIL ({elapsed:.3f}s >= 2s target)" );
    
    db.close();
    print( "\n100GB search tests complete!" );


def run_100gb_test():
    """Run the complete 100GB test."""
    print( "\n" + "=" * 60 );
    print( "nixIndex 100GB Test" );
    print( "=" * 60 );
    
    gz_path = '/Media/4/nixindex_test_100gb.txt.gz';
    
    # Check if test file already exists
    if os.path.exists( gz_path ):
        print( f"\nTest file already exists: {gz_path}" );
        size = os.path.getsize( gz_path );
        print( f"Size: {size / (1024**3):.2f} GB" );
        
        response = input( "\nUse existing file? (y/n): " );
        if response.lower() != 'y':
            gz_path = create_100gb_test_file();
    else:
        gz_path = create_100gb_test_file();
    
    # Run search tests
    test_100gb_search( gz_path );
    
    print( "\n" + "=" * 60 );
    print( "Test complete!" );
    print( "=" * 60 );


if __name__ == '__main__':
    run_100gb_test();
