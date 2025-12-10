# nixIndex - Fast Binary File Query System

Efficiently query large encoded binary files without storing decoded versions. Achieve sub-2-second searches on 100GB files.

## Quick Start

### Installation

No installation needed! Just Python 3.7+:

```bash
# Optional: Install brotli support
pip install brotli
```

### Basic Usage

1. **Import a file**:
```bash
./nixindex.py --import --file mydata.bin --encoding base64
```

2. **Search for a term**:
```bash
./nixindex.py --search --term restaurant
```

That's it!

## Features

- ✨ **Fast searches**: < 2 seconds regardless of source file size
- 🔐 **Multiple encodings**: base64, gzip, hex, brotli, ROT13, and more
- 💾 **Space efficient**: Database typically 5% of decoded file size
- 🚀 **No external dependencies**: All decoding done inline
- 📊 **Acuity filtering**: Remove low-frequency tokens for better performance
- 🔍 **Position-based extraction**: Direct record access via stored positions

## Supported Encodings

- **Compression**: gzip, bz2, zlib, brotli, zip, tar
- **Encoding**: base64, ascii85, hex
- **Ciphers**: ROT-N (e.g., ROT13), Caesar cipher
- **Legacy**: uuencode, xxencode
- **Raw**: none (for pre-decoded data)

## Command Reference

### Import Command

```bash
./nixindex.py --import --file <path> [options]
```

**Options**:
- `--encoding <type>`: Encoding to decode (default: none)
- `--separator <sep>`: Record separator (default: \n)
- `--chunk <size>`: Chunk size (e.g., 64, 1KB, 10MB)
- `--acuity <n>`: Minimum token count (default: 5)
- `--db <path>`: Database file (default: nixindex.db)

**Examples**:
```bash
# Import base64-encoded file
./nixindex.py --import --file data.b64 --encoding base64

# Import with custom separator
./nixindex.py --import --file data.txt --separator '\n\n'

# Import with acuity filter
./nixindex.py --import --file data.json --acuity 10

# Import from stdin
cat data.gz | ./nixindex.py --import --stdin --encoding gzip
```

### Search Command

```bash
./nixindex.py --search --term <word>
```

**Options**:
- `--term <word>`: Word to search for (required)
- `--file <path>`: Source file (if different from import)
- `--db <path>`: Database file (default: nixindex.db)

**Examples**:
```bash
# Basic search
./nixindex.py --search --term restaurant

# Search with custom database
./nixindex.py --search --term cafe --db mydata.db
```

### Generate Command

```bash
./nixindex.py --generate --encoding <type> [options]
```

**Options**:
- `--encoding <type>`: Encoding to apply (required)
- `--url <url>`: URL to download (optional)
- `--target-size <size>`: Target file size (default: 100GB)
- `--output <path>`: Output file path (default: temp file)

**Examples**:
```bash
# Generate from Yelp dataset
./nixindex.py --generate \
  --url https://business.yelp.com/external-assets/files/Yelp-JSON.zip \
  --encoding base64 \
  --target-size 10GB \
  --output testdata.bin

# Generate random data
./nixindex.py --generate --encoding gzip --target-size 1GB
```

## How It Works

1. **Import Phase**:
   - Read file in chunks
   - Decode using specified encoding
   - Split into records by separator
   - Extract tokens (alphanumeric words)
   - Store in indexed SQLite database

2. **Search Phase**:
   - Look up token in database (fast B-tree index)
   - Get record positions
   - Read and decode source file
   - Extract matching records
   - Display results

3. **Why It's Fast**:
   - Token lookup: O(log n) via indexes
   - No full file scan needed
   - Only matching records processed
   - Efficient position-based extraction

## Performance

### Expected Timings

| File Size | Import Time | Search Time | Database Size |
|-----------|-------------|-------------|---------------|
| 1 GB      | 1-3 min     | < 0.5s      | 50-150 MB     |
| 10 GB     | 5-15 min    | < 1s        | 500 MB-1.5 GB |
| 100 GB    | 30-60 min   | < 2s        | 2-5 GB        |

*Times vary based on encoding type and CPU speed*

### Optimization Tips

1. **Use acuity filtering**: Remove rare tokens for smaller database
2. **Choose efficient encoding**: gzip > base64 > hex for size
3. **Increase chunk size**: Larger chunks = fewer I/O operations
4. **Use appropriate separator**: Match your data structure

## Examples

### Example 1: JSON Log Files

```bash
# Import JSON logs with newline separation
./nixindex.py --import --file logs.json --separator '\n'

# Search for error events
./nixindex.py --search --term error

# Search for specific service
./nixindex.py --search --term authentication
```

### Example 2: Encoded Archives

```bash
# Import gzipped data
./nixindex.py --import --file archive.gz --encoding gzip

# Search for terms
./nixindex.py --search --term database
```

### Example 3: Base64 Email Data

```bash
# Import base64-encoded emails
./nixindex.py --import --file emails.b64 --encoding base64 --separator '-----'

# Search for sender
./nixindex.py --search --term john
```

## Testing

Run the comprehensive test suite:

```bash
./tests/test_nixindex.py
```

Tests include:
- All encoding formats
- Database operations
- Full import/search workflow
- Yelp dataset download and test
- Performance verification (< 2s target)

## Troubleshooting

### "No results found"

- Check token spelling (case-insensitive)
- Verify data was imported correctly
- Check if acuity filter removed term (reduce `--acuity`)

### "Database is empty"

- Run `--import` before `--search`
- Check database file path matches

### Slow imports

- Increase `--chunk` size (e.g., `--chunk 10MB`)
- Use faster encoding (avoid hex for large files)
- Reduce `--acuity` to filter fewer tokens

### Out of memory

- Reduce chunk size
- Process files in smaller batches
- Increase system swap space

## File Locations

```
nixIndex/
├── nixindex.py          # Main program
├── nixindex.db          # Database (created after import)
├── src/                 # Source modules
├── tests/               # Test suite
├── logs/                # Log files
└── backup/              # Code backups
```

## Advanced Usage

### Custom Database Location

```bash
# Use custom database
./nixindex.py --import --file data.bin --db /path/to/my.db
./nixindex.py --search --term word --db /path/to/my.db
```

### Pipeline Processing

```bash
# Decode and import in pipeline
cat encoded.b64 | base64 -d | ./nixindex.py --import --stdin
```

### Multiple Databases

```bash
# Keep separate databases for different datasets
./nixindex.py --import --file dataset1.bin --db data1.db
./nixindex.py --import --file dataset2.bin --db data2.db

./nixindex.py --search --term foo --db data1.db
./nixindex.py --search --term bar --db data2.db
```

## Requirements

- Python 3.7 or higher
- Standard library modules only
- Optional: `brotli` for Brotli compression

## License

Built for the nixCraft Challenge.

## Documentation

- `README.md` - This file (user guide)
- `WARP.md` - Technical architecture and implementation
- `ARCHITECTURE.md` - Original specification

## Support

For technical details, see `WARP.md`  
For architecture, see `ARCHITECTURE.md`
