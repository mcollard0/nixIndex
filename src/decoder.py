#!/usr/bin/env python3
"""
Decoder module for nixIndex.
Supports multiple encoding formats inline without external programs.
"""

import base64;
import binascii;
import gzip;
import bz2;
import zlib;
import io;
import zipfile;
import tarfile;
from typing import Optional;

try:
    import brotli;
    HAS_BROTLI = True;
except ImportError:
    HAS_BROTLI = False;


class DecoderError( Exception ):
    """Exception raised when decoding fails."""
    pass;


class Decoder:
    """Handle multiple encoding/compression formats."""
    
    @staticmethod
    def decode( data: bytes, encoding: str ) -> bytes:
        """
        Decode data using specified encoding.
        
        Args:
            data: Raw bytes to decode
            encoding: Encoding type (none, base64, ascii85, hex, brotli, gzip, zip, tar, rot13, caesar)
            
        Returns:
            Decoded bytes
            
        Raises:
            DecoderError: If decoding fails
        """
        encoding = encoding.lower();
        
        try:
            if encoding == 'none':
                return data;
            elif encoding == 'base64':
                return base64.b64decode( data );
            elif encoding == 'ascii85' or encoding == 'a85':
                return base64.a85decode( data );
            elif encoding in [ 'hex', 'hexadecimal', 'base16' ]:
                return bytes.fromhex( data.decode( 'ascii' ) );
            elif encoding == 'brotli':
                if not HAS_BROTLI:
                    raise DecoderError( "Brotli support not available. Install: pip install brotli" );
                return brotli.decompress( data );
            elif encoding == 'gzip' or encoding == 'gz':
                return gzip.decompress( data );
            elif encoding == 'bz2' or encoding == 'bzip2':
                return bz2.decompress( data );
            elif encoding == 'zlib':
                return zlib.decompress( data );
            elif encoding == 'zip':
                return Decoder._decode_zip( data );
            elif encoding == 'tar':
                return Decoder._decode_tar( data );
            elif encoding.startswith( 'rot' ):
                return Decoder._decode_rot( data, encoding );
            elif encoding.startswith( 'caesar' ):
                return Decoder._decode_caesar( data, encoding );
            elif encoding == 'uuencode' or encoding == 'uu':
                return Decoder._decode_uuencode( data );
            elif encoding == 'xxencode' or encoding == 'xx':
                return Decoder._decode_xxencode( data );
            else:
                raise DecoderError( f"Unknown encoding: {encoding}" );
        except Exception as e:
            raise DecoderError( f"Failed to decode using {encoding}: {str( e )}" );
    
    @staticmethod
    def _decode_zip( data: bytes ) -> bytes:
        """Decode ZIP archive - extract and concatenate all files."""
        result = io.BytesIO();
        with zipfile.ZipFile( io.BytesIO( data ) ) as zf:
            for name in zf.namelist():
                result.write( zf.read( name ) );
        return result.getvalue();
    
    @staticmethod
    def _decode_tar( data: bytes ) -> bytes:
        """Decode TAR archive - extract and concatenate all files."""
        result = io.BytesIO();
        with tarfile.open( fileobj=io.BytesIO( data ) ) as tf:
            for member in tf.getmembers():
                if member.isfile():
                    f = tf.extractfile( member );
                    if f:
                        result.write( f.read() );
        return result.getvalue();
    
    @staticmethod
    def _decode_rot( data: bytes, encoding: str ) -> bytes:
        """Decode ROT cipher (default ROT13)."""
        # Parse rotation amount from encoding like "rot13" or "rot7"
        try:
            if encoding == 'rot':
                shift = 13;
            else:
                shift = int( encoding[ 3: ] );
        except ( ValueError, IndexError ):
            shift = 13;
        
        result = bytearray();
        for byte in data:
            if 65 <= byte <= 90:  # A-Z
                result.append( ( ( byte - 65 + shift ) % 26 ) + 65 );
            elif 97 <= byte <= 122:  # a-z
                result.append( ( ( byte - 97 + shift ) % 26 ) + 97 );
            else:
                result.append( byte );
        return bytes( result );
    
    @staticmethod
    def _decode_caesar( data: bytes, encoding: str ) -> bytes:
        """Decode Caesar cipher. Format: caesar:N where N is shift (negative shifts left)."""
        # Parse shift from encoding like "caesar:3" or "caesar:-3"
        try:
            if ':' in encoding:
                shift_str = encoding.split( ':', 1 )[ 1 ];
                shift = int( shift_str );
            else:
                shift = 3;  # Default shift
        except ( ValueError, IndexError ):
            shift = 3;
        
        # Caesar cipher is just ROT with custom shift
        result = bytearray();
        for byte in data:
            if 65 <= byte <= 90:  # A-Z
                result.append( ( ( byte - 65 - shift ) % 26 ) + 65 );
            elif 97 <= byte <= 122:  # a-z
                result.append( ( ( byte - 97 - shift ) % 26 ) + 97 );
            else:
                result.append( byte );
        return bytes( result );
    
    @staticmethod
    def _decode_uuencode( data: bytes ) -> bytes:
        """Decode uuencoded data."""
        # Simple uudecode implementation
        lines = data.decode( 'ascii', errors='ignore' ).split( '\n' );
        result = io.BytesIO();
        
        for line in lines:
            if not line or line.startswith( 'begin' ) or line.startswith( 'end' ):
                continue;
            if len( line ) < 1:
                continue;
                
            # First character indicates line length
            try:
                n = ord( line[ 0 ] ) - 32;
                if n < 0 or n > 45:
                    continue;
                    
                line_data = line[ 1: ];
                decoded = bytearray();
                
                for i in range( 0, len( line_data ), 4 ):
                    chunk = line_data[ i:i+4 ];
                    if len( chunk ) < 4:
                        break;
                    
                    c1 = ord( chunk[ 0 ] ) - 32;
                    c2 = ord( chunk[ 1 ] ) - 32;
                    c3 = ord( chunk[ 2 ] ) - 32;
                    c4 = ord( chunk[ 3 ] ) - 32;
                    
                    decoded.append( ( ( c1 << 2 ) | ( c2 >> 4 ) ) & 0xFF );
                    decoded.append( ( ( c2 << 4 ) | ( c3 >> 2 ) ) & 0xFF );
                    decoded.append( ( ( c3 << 6 ) | c4 ) & 0xFF );
                
                result.write( bytes( decoded[ :n ] ) );
            except ( ValueError, IndexError ):
                continue;
        
        return result.getvalue();
    
    @staticmethod
    def _decode_xxencode( data: bytes ) -> bytes:
        """Decode xxencoded data."""
        # xxencode is similar to uuencode but uses different character set
        XX_CHARS = "+-0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";
        
        lines = data.decode( 'ascii', errors='ignore' ).split( '\n' );
        result = io.BytesIO();
        
        for line in lines:
            if not line or line.startswith( 'begin' ) or line.startswith( 'end' ):
                continue;
            if len( line ) < 1:
                continue;
            
            try:
                n = XX_CHARS.index( line[ 0 ] );
                line_data = line[ 1: ];
                decoded = bytearray();
                
                for i in range( 0, len( line_data ), 4 ):
                    chunk = line_data[ i:i+4 ];
                    if len( chunk ) < 4:
                        break;
                    
                    c1 = XX_CHARS.index( chunk[ 0 ] );
                    c2 = XX_CHARS.index( chunk[ 1 ] );
                    c3 = XX_CHARS.index( chunk[ 2 ] );
                    c4 = XX_CHARS.index( chunk[ 3 ] );
                    
                    decoded.append( ( ( c1 << 2 ) | ( c2 >> 4 ) ) & 0xFF );
                    decoded.append( ( ( c2 << 4 ) | ( c3 >> 2 ) ) & 0xFF );
                    decoded.append( ( ( c3 << 6 ) | c4 ) & 0xFF );
                
                result.write( bytes( decoded[ :n ] ) );
            except ( ValueError, IndexError ):
                continue;
        
        return result.getvalue();


def encode( data: bytes, encoding: str ) -> bytes:
    """
    Encode data using specified encoding.
    
    Args:
        data: Raw bytes to encode
        encoding: Encoding type
        
    Returns:
        Encoded bytes
    """
    encoding = encoding.lower();
    
    try:
        if encoding == 'none':
            return data;
        elif encoding == 'base64':
            return base64.b64encode( data );
        elif encoding == 'ascii85' or encoding == 'a85':
            return base64.a85encode( data );
        elif encoding in [ 'hex', 'hexadecimal', 'base16' ]:
            return data.hex().encode( 'ascii' );
        elif encoding == 'brotli':
            if not HAS_BROTLI:
                raise DecoderError( "Brotli support not available" );
            return brotli.compress( data );
        elif encoding == 'gzip' or encoding == 'gz':
            return gzip.compress( data );
        elif encoding == 'bz2' or encoding == 'bzip2':
            return bz2.compress( data );
        elif encoding == 'zlib':
            return zlib.compress( data );
        elif encoding.startswith( 'rot' ):
            return Decoder._decode_rot( data, encoding );  # ROT is symmetric
        elif encoding.startswith( 'caesar' ):
            # Invert the shift for encoding
            if ':' in encoding:
                parts = encoding.split( ':', 1 );
                shift = int( parts[ 1 ] );
                inverted = f"caesar:{-shift}";
            else:
                inverted = "caesar:-3";
            return Decoder._decode_caesar( data, inverted );
        else:
            raise DecoderError( f"Encoding not supported: {encoding}" );
    except Exception as e:
        raise DecoderError( f"Failed to encode using {encoding}: {str( e )}" );
