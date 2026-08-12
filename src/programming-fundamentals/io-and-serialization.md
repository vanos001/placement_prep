# I/O and Serialization

> Programs that can't communicate with the outside world aren't very useful. I/O is how software meets reality.

## 1. File Handling

### Opening and Closing Files

```python
# Python: context manager (recommended)
with open("data.txt", "r") as f:
    content = f.read()

# Manual (not recommended — easy to forget close)
f = open("data.txt", "r")
try:
    content = f.read()
finally:
    f.close()
```

```java
// Java: try-with-resources
try (BufferedReader reader = new BufferedReader(new FileReader("data.txt"))) {
    String line;
    while ((line = reader.readLine()) != null) {
        System.out.println(line);
    }
}
```

```javascript
// Node.js: async file reading
const fs = require('fs').promises;

async function readFile() {
    const content = await fs.readFile('data.txt', 'utf-8');
    console.log(content);
}

// Synchronous (blocks event loop — avoid in production)
const content = fs.readFileSync('data.txt', 'utf-8');
```

```c
// C: FILE* with fopen/fclose
FILE *f = fopen("data.txt", "r");
if (f == NULL) {
    perror("Error opening file");
    return 1;
}
char buffer[1024];
while (fgets(buffer, sizeof(buffer), f)) {
    printf("%s", buffer);
}
fclose(f);
```

```rust
// Rust: Result-based error handling
use std::fs;

fn read_file(path: &str) -> Result<String, std::io::Error> {
    fs::read_to_string(path)
}

// With more control
use std::fs::File;
use std::io::{self, BufRead, BufReader};

fn read_lines(path: &str) -> io::Result<Vec<String>> {
    let file = File::open(path)?;
    let reader = BufReader::new(file);
    reader.lines().collect()
}
```

### File Open Modes

| Mode | C | Python | Description |
|------|---|--------|-------------|
| Read | `"r"` | `"r"` | Read only, file must exist |
| Write | `"w"` | `"w"` | Write only, creates/truncates |
| Append | `"a"` | `"a"` | Write only, appends to end |
| Read+Write | `"r+"` | `"r+"` | Both, file must exist |
| Write+Read | `"w+"` | `"w+"` | Both, creates/truncates |
| Binary | `"rb"`, `"wb"` | `"rb"`, `"wb"` | Binary mode |

### Reading Patterns

```python
# Read entire file
content = open("file.txt").read()

# Read line by line (memory efficient)
with open("file.txt") as f:
    for line in f:
        process(line.strip())

# Read all lines into list
lines = open("file.txt").readlines()

# Read with encoding
with open("file.txt", encoding="utf-8") as f:
    content = f.read()
```

## 2. Streams

A **stream** is a sequence of data elements made available over time.

### Input/Output Streams

```java
// Java: InputStream/OutputStream hierarchy
// Byte streams
FileInputStream fis = new FileInputStream("data.bin");
FileOutputStream fos = new FileOutputStream("output.bin");

// Character streams (handle encoding)
FileReader fr = new FileReader("data.txt");
FileWriter fw = new FileWriter("output.txt");

// Buffered streams (performance)
BufferedReader br = new BufferedReader(new FileReader("data.txt"));
BufferedWriter bw = new BufferedWriter(new FileWriter("output.txt"));
```

```python
# Python: io module
import io

# In-memory text stream
text_stream = io.StringIO()
text_stream.write("Hello")
text_stream.write(" World")
text_stream.seek(0)
content = text_stream.read()  # "Hello World"

# In-memory binary stream
binary_stream = io.BytesIO()
binary_stream.write(b"\x00\x01\x02")
```

### Stream Operations

| Operation | Description | Example |
|-----------|-------------|---------|
| Read | Get data from stream | `stream.read()` |
| Write | Send data to stream | `stream.write(data)` |
| Seek | Move to position | `stream.seek(0)` |
| Flush | Force write to destination | `stream.flush()` |
| Close | Release resources | `stream.close()` |

## 3. Buffers

A **buffer** is a temporary memory area that accumulates data before processing.

### Why Buffers?

```
Without buffering: 1000 system calls for 1000 characters
With buffering:    1 system call for 1000 characters

Buffer: [h][e][l][l][o][ ][w][o][r][l][d]
         ↑ flush when full or explicitly called
```

```python
# Python: buffered I/O is default
# Force flush
print("data", flush=True)

# Unbuffered
import sys
sys.stdout.write("data\n")
sys.stdout.flush()

# Custom buffer
with open("file.txt", "w", buffering=8192) as f:
    f.write("data")  # buffered until 8KB or close
```

```java
// Java: BufferedReader/Writer
BufferedReader reader = new BufferedReader(
    new FileReader("data.txt"),
    16384  // 16KB buffer
);
```

## 4. Unicode, UTF-8, and ASCII

### Character Encoding Basics

```
ASCII (7-bit):
├── 128 characters (0-127)
├── English letters, digits, punctuation
└── A=65, a=97, 0=48

Extended ASCII (8-bit):
├── 256 characters (0-255)
├── Western European characters
└── Not enough for global scripts

Unicode:
├── 149,186+ characters
├── Covers all writing systems
└── Code points: U+0000 to U+10FFFF

UTF-8 (Unicode Transformation Format, 8-bit):
├── Variable-length encoding (1-4 bytes per character)
├── Backward compatible with ASCII
├── Most common encoding on the web (~98%)
└── Self-synchronizing
```

### UTF-8 Encoding

```
Code Point Range    | Bytes | Bit Pattern
U+0000   - U+007F   | 1     | 0xxxxxxx
U+0080   - U+07FF   | 2     | 110xxxxx 10xxxxxx
U+0800   - U+FFFF   | 3     | 1110xxxx 10xxxxxx 10xxxxxx
U+10000  - U+10FFFF | 4     | 11110xxx 10xxxxxx 10xxxxxx 10xxxxxx

Example: 'A' = U+0041 = 01000001 (1 byte)
Example: '€' = U+20AC = 11100010 10000010 10101100 (3 bytes)
Example: '😀' = U+1F600 = 11110000 10011111 10011000 10000000 (4 bytes)
```

### Common Encoding Pitfalls

```python
# Python 3: strings are Unicode, bytes are bytes
s = "Hello, 世界"
b = s.encode("utf-8")   # bytes
s2 = b.decode("utf-8")  # back to string

# Mojibake: wrong encoding
b = "café".encode("utf-8")
b.decode("latin-1")  # "cafÃ©" — wrong!

# BOM (Byte Order Mark)
with open("file.txt", encoding="utf-8-sig") as f:  # handles BOM
    content = f.read()
```

```javascript
// JavaScript: strings are UTF-16
const s = "Hello, 世界";
const encoder = new TextEncoder();       // UTF-8
const bytes = encoder.encode(s);
const decoder = new TextDecoder("utf-8");
const text = decoder.decode(bytes);
```

### Encoding Comparison

| Encoding | Size | Coverage | ASCII Compatible | Use Case |
|----------|------|----------|-----------------|----------|
| ASCII | 1 byte | English only | ✅ | Legacy systems |
| Latin-1 | 1 byte | Western European | ✅ | Legacy European |
| UTF-8 | 1-4 bytes | All Unicode | ✅ | Web, files, default |
| UTF-16 | 2-4 bytes | All Unicode | ❌ | Java, Windows, JS |
| UTF-32 | 4 bytes | All Unicode | ❌ | Rarely used |

## 5. Serialization and Deserialization

**Serialization**: converting objects to a storable/transmittable format.
**Deserialization**: converting back to objects.

### JSON

```python
import json

# Serialize
data = {"name": "Alice", "age": 30, "scores": [95, 87, 92]}
json_str = json.dumps(data, indent=2)
# {
#   "name": "Alice",
#   "age": 30,
#   "scores": [95, 87, 92]
# }

# Deserialize
obj = json.loads(json_str)
print(obj["name"])  # "Alice"

# File I/O
with open("data.json", "w") as f:
    json.dump(data, f, indent=2)

with open("data.json") as f:
    data = json.load(f)
```

```javascript
// JavaScript: built-in JSON support
const data = { name: "Alice", age: 30 };

// Serialize
const jsonStr = JSON.stringify(data, null, 2);

// Deserialize
const obj = JSON.parse(jsonStr);
```

```java
// Java: Jackson library
ObjectMapper mapper = new ObjectMapper();

// Serialize
String json = mapper.writeValueAsString(data);

// Deserialize
MyClass obj = mapper.readValue(json, MyClass.class);
```

### JSON vs XML

| Aspect | JSON | XML |
|--------|------|-----|
| Verbosity | Less verbose | More verbose (`<tag>`) |
| Readability | Human-readable | Human-readable |
| Data types | String, number, boolean, null, array, object | All text (needs schema) |
| Comments | ❌ No | ✅ `<!-- comment -->` |
| Namespaces | ❌ No | ✅ Yes |
| Schema | JSON Schema | XSD, DTD |
| Parsing speed | Faster | Slower |
| Use case | APIs, config | SOAP, legacy systems, documents |

### XML Example

```xml
<?xml version="1.0" encoding="UTF-8"?>
<person>
    <name>Alice</name>
    <age>30</age>
    <scores>
        <score>95</score>
        <score>87</score>
    </scores>
</person>
```

```python
import xml.etree.ElementTree as ET

tree = ET.parse("data.xml")
root = tree.getroot()
name = root.find("name").text  # "Alice"
```

### Protocol Buffers (Binary)

```protobuf
// person.proto
syntax = "proto3";

message Person {
    string name = 1;
    int32 age = 2;
    repeated int32 scores = 3;
}
```

```python
# Python
from person_pb2 import Person

person = Person(name="Alice", age=30, scores=[95, 87])
serialized = person.SerializeToString()  # binary, compact
```

### Serialization Format Comparison

| Format | Type | Size | Speed | Human Readable | Schema |
|--------|------|------|-------|----------------|--------|
| JSON | Text | Medium | Fast | ✅ | Optional |
| XML | Text | Large | Slow | ✅ | XSD/DTD |
| YAML | Text | Medium | Slow | ✅ | Optional |
| Protobuf | Binary | Small | Very fast | ❌ | Required |
| MessagePack | Binary | Small | Very fast | ❌ | Optional |
| CBOR | Binary | Small | Very fast | ❌ | Optional |

## 6. Command-Line Arguments

```python
# Python: sys.argv
import sys
print(sys.argv[0])  # script name
print(sys.argv[1:]) # arguments

# Better: argparse
import argparse
parser = argparse.ArgumentParser(description="Process data")
parser.add_argument("input", help="Input file")
parser.add_argument("-o", "--output", default="out.txt", help="Output file")
parser.add_argument("-v", "--verbose", action="store_true")
args = parser.parse_args()
```

```javascript
// Node.js
// process.argv[0] = node
// process.argv[1] = script.js
// process.argv[2:] = arguments
const args = process.argv.slice(2);

// Better: use a library like 'yargs' or 'commander'
```

```go
// Go
import "os"

func main() {
    args := os.Args[1:]  // skip program name
    // or use "flag" package
}
```

```java
// Java
public static void main(String[] args) {
    for (String arg : args) {
        System.out.println(arg);
    }
}
```

## 7. Environment Variables

```python
import os

# Read
db_host = os.environ.get("DB_HOST", "localhost")  # with default
api_key = os.environ["API_KEY"]  # raises KeyError if missing

# Set (only for current process and children)
os.environ["MY_VAR"] = "value"

# List all
for key, value in os.environ.items():
    print(f"{key}={value}")
```

```javascript
// Node.js
const dbHost = process.env.DB_HOST || "localhost";
const apiKey = process.env.API_KEY;
```

```bash
# Shell
echo $HOME
export MY_VAR="value"
env | grep MY_VAR
```

### Common Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `PATH` | Executable search paths | `/usr/bin:/usr/local/bin` |
| `HOME` | User home directory | `/home/alice` |
| `USER` | Current username | `alice` |
| `LANG` | Locale | `en_US.UTF-8` |
| `SHELL` | Default shell | `/bin/bash` |
| `TERM` | Terminal type | `xterm-256color` |
| `PWD` | Current directory | `/home/alice/project` |

## Interview Questions

1. **What's the difference between text and binary I/O?**
   Text: character-based, involves encoding/decoding, line ending translation. Binary: byte-based, no translation, exact representation of data.

2. **Why use buffered I/O?**
   Reduces system calls. Without buffering, each read/write is a kernel transition. Buffers accumulate data and transfer in bulk, dramatically improving performance.

3. **Explain UTF-8. Why is it dominant?**
   Variable-length Unicode encoding (1-4 bytes). Dominant because: ASCII compatible, space-efficient for English, self-synchronizing, byte-order independent.

4. **What's the difference between JSON and XML?**
   JSON: lighter, faster, no comments, data-oriented. XML: more verbose, has namespaces/comments, document-oriented, better for complex schemas.

5. **What is serialization? Name some formats.**
   Converting objects to storable/transmittable formats. JSON (text, APIs), XML (text, documents), Protobuf (binary, efficient), YAML (text, config), MessagePack (binary, compact).

6. **How do you handle file encoding issues?**
   Always specify encoding explicitly. Handle BOM. Use UTF-8 as default. Detect encoding with libraries when reading unknown files. Handle decode errors gracefully.

7. **What are environment variables used for?**
   Configuration that varies by environment (dev/staging/prod), secrets (API keys, passwords), system information (PATH, HOME). Follow 12-factor app principles.

8. **Explain the RAII pattern for file handling.**
   Tie file lifetime to a scope. In Python: `with open(...)`. In C++: RAII wrappers. In Rust: `File` implements `Drop`. Ensures files are closed even when exceptions occur.
