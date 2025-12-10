nixCraft Challenge
Source: https://www.facebook.com/nixcraft/posts/pfbid0J2wSoeKEGioJN2AkwTqGx9bKwpFtA3VuMbCf6afJyBCMGV16auB1pFhKSTJJgshTl?comment_id=25872536895664358

Customer complaint: 

I have a 100GB binary file. Produced daily. I can’t grep it. But I can decode it.

However, I can’t store the decoded version either. It’s too big.

How do I efficiently query it?

Decoding piped to grep takes 2 minutes.

I want 2 seconds.
Below the post:
textnixCraft
MON AT 2:10 PM
Any humans up for the task? 🤯

Stack:
Architected by a human on earth.
AI can be used only in programming assistance.
Python/Regex/SQLite. Regex chosen over PDTypeAdapter as in my tests it is faster for count and search.

Stretch goal: web search interface.

Humor: The irony of asking AI how to do one-hot and getting shot [down]. 

Requirements:

2 second search after parse. Data cannot be grep, must be parsed. Data is encoded, but we don't know the format, we choose several common formats for this type of work which should be compatible with expected inputs. Can be augmented after MVP demo when customer shares further detail. Customer is unavailable for clarification for a time long enough to complete work. (Holiday?)

INPUT: Default --import/--input if --file or --stdin specified. --search if not which expects --term "word_to_query". Allow for binary pipe in --stdin, which is parsed as if it were a read file. This should allow us to use RSA, GPG, ChaCha20, Brotli, Base64, Ascii85, Hexadecimal/Hex/Base16, uuencode, xxencode, et al. 

Parse --file using record --seperator (character(s) {1..n} or regex/TA mask, which will be compiled by program where possible. Validate input and warn with detail where possible.) after decoding using --decode {none (for piped in previously decoded data as explained above: INPUT), zip, gzip, tar, rot[{1..9999; default: 13}], ceasar(cipher)[:][{1..24}*-1]; so 3 would be -3 (left)}  in repeatable regions, tokenizing each word. Words can be separated by punctuation, which is defined as any non-alphanumeric characters [AZaz09]

Parsing should be done in chunks where possible, configurable with --chunk 64 (default to KB if no unit, case insensitive parse K/KB, M/MB, G/GB. Reject others with error (except none, which defautls to kb.)  

Data stored in SQLite as: (tables truncated upon each run of import.)
encoding (varchar type) (where in the list of the above --decode)
file (varchar filename) 
token (id, value, count) (update with count=count+1 upon insert) unique index:value, unique index id (autoincrement number)
token_occurence (id, token_id, record) index:token_id, record, unique index id (autoincrement number)
record (id, start_pos, end_pos)

When running the parser should read --chunk units, and split on --seperator. 
Each record should have the start and end then be inserted into record table.1
Each record should then be split into tokens on non-alphanumeric (regex/pydantic typeadapter) 
For each token, insert the value (example: budget)

--search : query database for token table id by value, query distinct record from token_occurence where token_id = token.id, select start_pos and end_pos. Show full record, detecting if the data stored encoded via file.encoded. 

--generate : requires 1:(--file or --stdin) and --encoding. Data is calculated for length. Goal length of 100GB, so if smaller, repeat the file until the length is 100GB (using division and a loop.) File may be a URL, have a simple download routine for http[s]; Support encoding and unzip in code then encoding. 

All code for parse must be inline, no firing external programs to decode each segment, which would violate the 2sec time constraint (which only applies to search).


Optimizations:
At end of parse, --acuity {1..999} default:5, delete rows from token/token_occurence and update count which are less than --acuity value. Then rebuild tables and reindex. Time and report this duration.

Tests:
Do --generate using https://business.yelp.com/external-assets/files/Yelp-JSON.zip (Code should UNZIP IT to temp folder, preferably in code not launching unzip). --encoding {choose one from supported at random} Then run it through a segmented encoding from argument. Use a temp file in a OS-safe way.
Then parse file using --file --import {tmpFile} --encoding {type}
Then do a test search using any word in the parsed data. Can select word from database token, and then run program with this word and verify it returns text from the source file. 

Review plan and recommend suggestions.
