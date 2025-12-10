#!/usr/bin/env python3
"""
Test suite for nixIndex.
Tests with Yelp dataset and verifies 2-second search target.
"""

import sys;
import os;
import time;
import tempfile;
import random;
import subprocess;

# Add src to path
sys.path.insert( 0, os.path.join( os.path.dirname( __file__ ), '..', 'src' ) );

from database import Database;
from decoder import Decoder, encode;
from parser import Parser;
from search import Searcher;
from generator import Generator;


def test_decoder():
    """Test various encoding/decoding operations."""
    print( "\n=== Testing Decoder ===" );
    
    test_data = b"Hello, World! This is a test message with numbers 12345 and symbols @#$%";
    decoder = Decoder();
    
    encodings = [ 
        'base64', 'ascii85', 'hex', 'gzip', 'bz2', 'zlib', 
        'rot13', 'rot7', 'caesar:3', 'caesar:-5'
    ];
    
    for encoding in encodings:
        try:
            # Encode
            encoded = encode( test_data, encoding );
            
            # Decode
            decoded = decoder.decode( encoded, encoding );
            
            # Verify
            if decoded == test_data:
                print( f"  ✓ {encoding}: PASS" );
            else:
                print( f"  ✗ {encoding}: FAIL (data mismatch)" );
        except Exception as e:
            print( f"  ✗ {encoding}: FAIL ({str( e )})" );
    
    print( "Decoder tests complete\n" );


def test_chunk_size_parser():
    """Test chunk size parsing."""
    print( "=== Testing Chunk Size Parser ===" );
    
    test_cases = [
        ( "64", 64 * 1024 ),
        ( "1KB", 1024 ),
        ( "10MB", 10 * 1024 * 1024 ),
        ( "2GB", 2 * 1024 * 1024 * 1024 ),
    ];
    
    for size_str, expected in test_cases:
        result = Parser.parse_chunk_size( size_str );
        if result == expected:
            print( f"  ✓ {size_str} = {expected}: PASS" );
        else:
            print( f"  ✗ {size_str}: FAIL (got {result}, expected {expected})" );
    
    print( "Chunk size parser tests complete\n" );


def test_database():
    """Test database operations."""
    print( "=== Testing Database ===" );
    
    # Create temp database
    fd, db_path = tempfile.mkstemp( suffix='.db' );
    os.close( fd );
    
    try:
        db = Database( db_path );
        db.connect();
        
        # Insert test data
        encoding_id = db.insert_encoding( 'base64' );
        file_id = db.insert_file( 'test.txt', encoding_id );
        
        # Insert records and tokens
        record_id = db.insert_record( 0, 100 );
        token_id = db.insert_token( 'hello' );
        db.insert_token_occurrence( token_id, record_id );
        
        db.commit();
        
        # Search
        results = db.search_token( 'hello' );
        
        if len( results ) == 1:
            print( "  ✓ Token search: PASS" );
        else:
            print( f"  ✗ Token search: FAIL (got {len( results )} results)" );
        
        # Stats
        stats = db.get_stats();
        if stats[ 'tokens' ] == 1 and stats[ 'records' ] == 1:
            print( "  ✓ Statistics: PASS" );
        else:
            print( f"  ✗ Statistics: FAIL ({stats})" );
        
        db.close();
        print( "Database tests complete\n" );
    finally:
        os.unlink( db_path );


def test_full_workflow():
    """Test complete import and search workflow."""
    print( "=== Testing Full Workflow ===" );
    
    # Create test data file
    test_text = """{"business_id":"abc123","name":"Great Restaurant","city":"Phoenix","stars":4.5}
{"business_id":"def456","name":"Amazing Cafe","city":"Portland","stars":4.0}
{"business_id":"ghi789","name":"Superb Bistro","city":"Seattle","stars":5.0}
{"business_id":"jkl012","name":"Wonderful Diner","city":"Austin","stars":3.5}
{"business_id":"mno345","name":"Excellent Eatery","city":"Denver","stars":4.8}""";
    
    # Create temp files
    fd_data, data_path = tempfile.mkstemp( suffix='.json' );
    os.write( fd_data, test_text.encode( 'utf-8' ) );
    os.close( fd_data );
    
    fd_db, db_path = tempfile.mkstemp( suffix='.db' );
    os.close( fd_db );
    
    try:
        # Import data
        db = Database( db_path );
        db.connect();
        db.truncate_tables();
        
        parser = Parser( db, encoding='none', separator='\n', chunk_size=65536 );
        parser.parse_file( data_path );
        
        stats = db.get_stats();
        print( f"  Records: {stats[ 'records' ]}" );
        print( f"  Unique tokens: {stats[ 'tokens' ]}" );
        
        # Search for a term
        searcher = Searcher( db );
        
        start_time = time.time();
        results = searcher.search( 'restaurant', filepath=data_path );
        elapsed = time.time() - start_time;
        
        print( f"  Search time: {elapsed:.3f}s" );
        
        if len( results ) == 1:
            print( "  ✓ Search results: PASS" );
        else:
            print( f"  ✗ Search results: FAIL (got {len( results )} results, expected 1)" );
        
        if elapsed < 2.0:
            print( "  ✓ Performance target: PASS (< 2s)" );
        else:
            print( f"  ✗ Performance target: FAIL ({elapsed:.3f}s >= 2s)" );
        
        db.close();
        print( "Full workflow tests complete\n" );
    finally:
        os.unlink( data_path );
        os.unlink( db_path );


def test_yelp_dataset():
    """Test with real Yelp dataset if available."""
    print( "=== Testing with Yelp Dataset ===" );
    
    yelp_url = "https://business.yelp.com/external-assets/files/Yelp-JSON.zip";
    
    print( "Attempting to download Yelp dataset..." );
    print( "(This may take a few minutes)" );
    
    try:
        # Download and extract
        zip_data = Generator.download_url( yelp_url );
        json_data = Generator.extract_zip( zip_data );
        
        print( f"Dataset size: {len( json_data ) / ( 1024**2 ):.2f} MB" );
        
        # Choose random encoding for test
        encodings = [ 'base64', 'gzip', 'hex' ];
        test_encoding = random.choice( encodings );
        print( f"Test encoding: {test_encoding}" );
        
        # Encode data
        encoded_data = encode( json_data, test_encoding );
        
        # Save to temp file
        fd_data, data_path = tempfile.mkstemp( suffix='.bin' );
        os.write( fd_data, encoded_data );
        os.close( fd_data );
        
        fd_db, db_path = tempfile.mkstemp( suffix='.db' );
        os.close( fd_db );
        
        try:
            # Import
            print( "Importing dataset..." );
            import_start = time.time();
            
            db = Database( db_path );
            db.connect();
            db.truncate_tables();
            
            parser = Parser( db, encoding=test_encoding, separator='\n', chunk_size=1024*1024 );
            parser.parse_file( data_path );
            
            import_time = time.time() - import_start;
            print( f"Import time: {import_time:.2f}s" );
            
            stats = db.get_stats();
            print( f"Records: {stats[ 'records' ]}" );
            print( f"Unique tokens: {stats[ 'tokens' ]}" );
            print( f"Token occurrences: {stats[ 'occurrences' ]}" );
            
            # Pick a random token for search
            db.cursor.execute( "SELECT value FROM token ORDER BY RANDOM() LIMIT 1" );
            random_token = db.cursor.fetchone()[ 0 ];
            print( f"\nSearching for random token: {random_token}" );
            
            # Search
            searcher = Searcher( db );
            
            start_time = time.time();
            results = searcher.search( random_token, filepath=data_path );
            elapsed = time.time() - start_time;
            
            print( f"Found {len( results )} results in {elapsed:.3f}s" );
            
            if elapsed < 2.0:
                print( "  ✓ Performance target: PASS (< 2s)" );
            else:
                print( f"  ✗ Performance target: FAIL ({elapsed:.3f}s >= 2s)" );
            
            # Display sample result
            if results:
                print( f"\nSample result:" );
                print( results[ 0 ][ :200 ] + "..." if len( results[ 0 ] ) > 200 else results[ 0 ] );
            
            db.close();
            print( "\nYelp dataset tests complete\n" );
        finally:
            os.unlink( data_path );
            os.unlink( db_path );
    
    except Exception as e:
        print( f"Yelp dataset test skipped: {str( e )}" );
        print( "(This is optional - core functionality still tested)\n" );


def run_all_tests():
    """Run all tests."""
    print( "\n" + "=" * 60 );
    print( "nixIndex Test Suite" );
    print( "=" * 60 );
    
    test_decoder();
    test_chunk_size_parser();
    test_database();
    test_full_workflow();
    test_yelp_dataset();
    
    print( "=" * 60 );
    print( "All tests complete!" );
    print( "=" * 60 );


if __name__ == '__main__':
    run_all_tests();
