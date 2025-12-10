#!/usr/bin/env python3
"""
nixIndex - Fast Binary File Query System

Efficiently query large binary files through indexed token search.
"""

import sys;
import os;
import argparse;
from pathlib import Path;

# Add src directory to path
sys.path.insert( 0, os.path.join( os.path.dirname( __file__ ), 'src' ) );

from database import Database;
from parser import Parser;
from search import Searcher;
from generator import Generator;


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='nixIndex - Fast Binary File Query System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Import and parse an encoded file
  ./nixindex.py --import --file data.bin --encoding base64
  
  # Search for a term
  ./nixindex.py --search --term restaurant
  
  # Generate test file from URL
  ./nixindex.py --generate --url https://example.com/data.zip --encoding gzip
  
  # Parse with custom separator and chunk size
  ./nixindex.py --import --file data.txt --separator "\\n\\n" --chunk 1MB
  
  # Apply acuity filter after import
  ./nixindex.py --import --file data.bin --acuity 10
        """
    );
    
    # Operation mode
    mode_group = parser.add_mutually_exclusive_group( required=True );
    mode_group.add_argument( '--import', dest='do_import', action='store_true',
                            help='Import and parse file into database' );
    mode_group.add_argument( '--search', dest='do_search', action='store_true',
                            help='Search for term in database' );
    mode_group.add_argument( '--generate', dest='do_generate', action='store_true',
                            help='Generate test file with encoding' );
    
    # Input options
    input_group = parser.add_mutually_exclusive_group();
    input_group.add_argument( '--file', type=str,
                             help='Input file path' );
    input_group.add_argument( '--stdin', action='store_true',
                             help='Read from stdin' );
    
    # Encoding options
    parser.add_argument( '--encoding', '--decode', type=str, default='none',
                        help='Encoding type: none, base64, ascii85, hex, brotli, gzip, zip, tar, rot13, caesar, etc. (default: none)' );
    
    # Parser options
    parser.add_argument( '--separator', type=str, default=r'\n',
                        help='Record separator (character or regex) (default: \\n)' );
    parser.add_argument( '--chunk', type=str, default='64',
                        help='Chunk size with optional unit (64, 1KB, 10MB, 2GB) (default: 64KB)' );
    parser.add_argument( '--acuity', type=int, default=5,
                        help='Minimum token occurrence count (default: 5)' );
    
    # Search options
    parser.add_argument( '--term', type=str,
                        help='Search term (required for --search)' );
    
    # Generator options
    parser.add_argument( '--url', type=str,
                        help='URL to download for --generate' );
    parser.add_argument( '--target-size', type=str, default='100GB',
                        help='Target file size for --generate (default: 100GB)' );
    parser.add_argument( '--output', type=str,
                        help='Output file path for --generate' );
    
    # Database options
    parser.add_argument( '--db', type=str, default='nixindex.db',
                        help='Database file path (default: nixindex.db)' );
    
    args = parser.parse_args();
    
    try:
        if args.do_import:
            do_import( args );
        elif args.do_search:
            do_search( args );
        elif args.do_generate:
            do_generate( args );
    except KeyboardInterrupt:
        print( "\n\nOperation cancelled by user" );
        sys.exit( 1 );
    except Exception as e:
        print( f"\nError: {e}", file=sys.stderr );
        sys.exit( 1 );


def do_import( args ):
    """Handle import operation."""
    if not args.file and not args.stdin:
        print( "Error: --file or --stdin required for --import", file=sys.stderr );
        sys.exit( 1 );
    
    # Parse chunk size
    chunk_size = Parser.parse_chunk_size( args.chunk );
    
    # Initialize database
    db = Database( args.db );
    db.connect();
    
    # Truncate tables
    print( "Truncating database tables..." );
    db.truncate_tables();
    
    # Initialize parser
    parser = Parser( 
        db=db,
        encoding=args.encoding,
        separator=args.separator,
        chunk_size=chunk_size
    );
    
    # Parse file
    filepath = args.file if args.file else '<stdin>';
    parser.parse_file( filepath, use_stdin=args.stdin );
    
    # Apply acuity filter if specified
    if args.acuity > 0:
        print( f"\nApplying acuity filter (min count: {args.acuity})..." );
        deleted, duration = db.apply_acuity_filter( args.acuity );
        print( f"Removed {deleted} low-frequency tokens in {duration:.2f}s" );
        
        # Show updated stats
        stats = db.get_stats();
        print( f"\nFinal statistics:" );
        print( f"  Records: {stats[ 'records' ]}" );
        print( f"  Unique tokens: {stats[ 'tokens' ]}" );
        print( f"  Token occurrences: {stats[ 'occurrences' ]}" );
    
    db.close();
    print( "\nImport complete!" );


def do_search( args ):
    """Handle search operation."""
    if not args.term:
        print( "Error: --term required for --search", file=sys.stderr );
        sys.exit( 1 );
    
    # Initialize database
    db = Database( args.db );
    db.connect();
    
    # Check if database has data
    stats = db.get_stats();
    if stats[ 'tokens' ] == 0:
        print( "Error: Database is empty. Run --import first.", file=sys.stderr );
        sys.exit( 1 );
    
    # Initialize searcher
    searcher = Searcher( db );
    
    # Perform search
    results = searcher.search( args.term, filepath=args.file );
    
    # Display results
    searcher.display_results( results );
    
    db.close();


def do_generate( args ):
    """Handle generate operation."""
    if not args.encoding or args.encoding == 'none':
        print( "Error: --encoding required for --generate", file=sys.stderr );
        sys.exit( 1 );
    
    # Parse target size
    target_size = Parser.parse_chunk_size( args.target_size );
    
    # Generate file
    output_path = Generator.generate_file(
        url=args.url,
        encoding=args.encoding,
        target_size=target_size,
        output_path=args.output
    );
    
    print( f"\nGeneration complete: {output_path}" );


if __name__ == '__main__':
    main();
