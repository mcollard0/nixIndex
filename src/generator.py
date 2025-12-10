#!/usr/bin/env python3
"""
Generator module for nixIndex.
Generate test files from URLs with encoding and target size.
"""

import os;
import tempfile;
import zipfile;
import io;
from pathlib import Path;
from typing import Optional;

try:
    import urllib.request;
    HAS_URLLIB = True;
except ImportError:
    HAS_URLLIB = False;

from decoder import encode, DecoderError;


class GeneratorError( Exception ):
    """Exception raised when generation fails."""
    pass;


class Generator:
    """Generate test files with encoding."""
    
    @staticmethod
    def download_url( url: str ) -> bytes:
        """
        Download file from URL.
        
        Args:
            url: URL to download
            
        Returns:
            Downloaded bytes
        """
        if not HAS_URLLIB:
            raise GeneratorError( "URL download not supported" );
        
        print( f"Downloading: {url}" );
        
        try:
            with urllib.request.urlopen( url ) as response:
                data = response.read();
            
            print( f"Downloaded {len( data )} bytes" );
            return data;
        except Exception as e:
            raise GeneratorError( f"Failed to download {url}: {str( e )}" );
    
    @staticmethod
    def extract_zip( data: bytes ) -> bytes:
        """
        Extract and concatenate all files from ZIP archive.
        
        Args:
            data: ZIP file bytes
            
        Returns:
            Concatenated file contents
        """
        print( f"Extracting ZIP archive..." );
        
        result = io.BytesIO();
        
        try:
            with zipfile.ZipFile( io.BytesIO( data ) ) as zf:
                file_count = 0;
                for name in zf.namelist():
                    file_data = zf.read( name );
                    result.write( file_data );
                    file_count += 1;
                    print( f"  Extracted: {name} ( {len( file_data )} bytes )" );
            
            print( f"Extracted {file_count} files" );
        except Exception as e:
            raise GeneratorError( f"Failed to extract ZIP: {str( e )}" );
        
        return result.getvalue();
    
    @staticmethod
    def generate_file( url: Optional[ str ], encoding: str, 
                       target_size: int = 100 * 1024 * 1024 * 1024,
                       output_path: Optional[ str ] = None ) -> str:
        """
        Generate test file with encoding.
        
        Args:
            url: URL to download (None for random data)
            encoding: Encoding type to apply
            target_size: Target file size in bytes (default 100GB)
            output_path: Optional output path (uses temp file if None)
            
        Returns:
            Path to generated file
        """
        print( f"Generating test file:" );
        print( f"  Target size: {target_size / ( 1024**3 ):.2f} GB" );
        print( f"  Encoding: {encoding}" );
        
        # Get source data
        if url:
            # Download from URL
            source_data = Generator.download_url( url );
            
            # Extract if ZIP
            if url.endswith( '.zip' ):
                source_data = Generator.extract_zip( source_data );
        else:
            # Generate random data (1MB)
            import random;
            print( "Generating random data..." );
            source_data = os.urandom( 1024 * 1024 );
        
        print( f"Source data size: {len( source_data )} bytes" );
        
        # Calculate repetitions needed
        repetitions = max( 1, target_size // len( source_data ) );
        print( f"Repeating data {repetitions} times to reach target size" );
        
        # Create output file
        if not output_path:
            fd, output_path = tempfile.mkstemp( suffix='.bin', prefix='nixindex_' );
            os.close( fd );
        
        print( f"Writing to: {output_path}" );
        
        # Encode and write data
        with open( output_path, 'wb' ) as f:
            for i in range( repetitions ):
                encoded = encode( source_data, encoding );
                f.write( encoded );
                
                if ( i + 1 ) % 100 == 0:
                    written_size = ( i + 1 ) * len( encoded );
                    progress = ( written_size / target_size ) * 100;
                    print( f"  Progress: {progress:.1f}% ( {written_size / ( 1024**3 ):.2f} GB )", end='\r' );
        
        # Get final size
        final_size = os.path.getsize( output_path );
        print( f"\n\nGenerated file: {output_path}" );
        print( f"Final size: {final_size / ( 1024**3 ):.2f} GB" );
        
        return output_path;
