# Building Parsers

## Overview

Parsing is a fundamental skill — you'll build parsers for config files, data formats, log files, and DSLs. This section covers building parsers from scratch.

## 1. JSON Parser

### Understanding JSON Grammar

```
JSON = object | array | string | number | boolean | null
object = '{' (string ':' value (',' string ':' value)*)? '}'
array  = '[' (value (',' value)*)? ']'
string = '"' characters '"'
number = integer ('.' digits)? (('e'|'E') ('+'|'-')? digits)?
boolean = 'true' | 'false'
null = 'null'
```

### Recursive Descent Parser (Python)

```python
import json
from typing import Any


class JSONParser:
    """Parse JSON string into Python objects."""
    
    def __init__(self, text: str):
        self.text = text
        self.pos = 0
    
    def peek(self) -> str:
        if self.pos >= len(self.text):
            return ''
        return self.text[self.pos]
    
    def advance(self) -> str:
        ch = self.text[self.pos]
        self.pos += 1
        return ch
    
    def expect(self, ch: str):
        if self.advance() != ch:
            raise SyntaxError(
                f"Expected '{ch}' at position {self.pos}")
    
    def skip_whitespace(self):
        while self.pos < len(self.text) and self.text[self.pos] in ' \t\n\r':
            self.pos += 1
    
    def parse(self) -> Any:
        self.skip_whitespace()
        result = self.parse_value()
        self.skip_whitespace()
        if self.pos < len(self.text):
            raise SyntaxError(
                f"Unexpected character at position {self.pos}")
        return result
    
    def parse_value(self) -> Any:
        self.skip_whitespace()
        ch = self.peek()
        
        if ch == '{':
            return self.parse_object()
        elif ch == '[':
            return self.parse_array()
        elif ch == '"':
            return self.parse_string()
        elif ch == '-' or ch.isdigit():
            return self.parse_number()
        elif ch == 't' or ch == 'f':
            return self.parse_boolean()
        elif ch == 'n':
            return self.parse_null()
        else:
            raise SyntaxError(
                f"Unexpected character '{ch}' at position {self.pos}")
    
    def parse_object(self) -> dict:
        obj = {}
        self.expect('{')
        self.skip_whitespace()
        
        if self.peek() == '}':
            self.advance()
            return obj
        
        while True:
            self.skip_whitespace()
            key = self.parse_string()
            self.skip_whitespace()
            self.expect(':')
            self.skip_whitespace()
            value = self.parse_value()
            obj[key] = value
            
            self.skip_whitespace()
            if self.peek() == ',':
                self.advance()
            elif self.peek() == '}':
                self.advance()
                return obj
            else:
                raise SyntaxError(
                    f"Expected ',' or '}}' at position {self.pos}")
    
    def parse_array(self) -> list:
        arr = []
        self.expect('[')
        self.skip_whitespace()
        
        if self.peek() == ']':
            self.advance()
            return arr
        
        while True:
            self.skip_whitespace()
            arr.append(self.parse_value())
            self.skip_whitespace()
            
            if self.peek() == ',':
                self.advance()
            elif self.peek() == ']':
                self.advance()
                return arr
            else:
                raise SyntaxError(
                    f"Expected ',' or ']' at position {self.pos}")
    
    def parse_string(self) -> str:
        self.expect('"')
        result = []
        
        while self.pos < len(self.text):
            ch = self.advance()
            if ch == '"':
                return ''.join(result)
            elif ch == '\\':
                escaped = self.advance()
                escape_map = {
                    '"': '"', '\\': '\\', '/': '/',
                    'b': '\b', 'f': '\f', 'n': '\n',
                    'r': '\r', 't': '\t'
                }
                if escaped in escape_map:
                    result.append(escape_map[escaped])
                elif escaped == 'u':
                    hex_str = self.text[self.pos:self.pos+4]
                    self.pos += 4
                    result.append(chr(int(hex_str, 16)))
                else:
                    raise SyntaxError(f"Invalid escape: \\{escaped}")
            else:
                result.append(ch)
        
        raise SyntaxError("Unterminated string")
    
    def parse_number(self) -> float:
        start = self.pos
        
        if self.peek() == '-':
            self.advance()
        
        while self.pos < len(self.text) and self.text[self.pos].isdigit():
            self.advance()
        
        if self.pos < len(self.text) and self.text[self.pos] == '.':
            self.advance()
            while (self.pos < len(self.text) and 
                   self.text[self.pos].isdigit()):
                self.advance()
        
        if self.pos < len(self.text) and self.text[self.pos] in 'eE':
            self.advance()
            if self.pos < len(self.text) and self.text[self_pos] in '+-':
                self.advance()
            while (self.pos < len(self.text) and 
                   self.text[self.pos].isdigit()):
                self.advance()
        
        num_str = self.text[start:self.pos]
        return float(num_str) if '.' in num_str or 'e' in num_str.lower() else int(num_str)
    
    def parse_boolean(self) -> bool:
        if self.text[self.pos:self.pos+4] == 'true':
            self.pos += 4
            return True
        elif self.text[self.pos:self.pos+5] == 'false':
            self.pos += 5
            return False
        raise SyntaxError(f"Expected boolean at position {self.pos}")
    
    def parse_null(self) -> None:
        if self.text[self.pos:self.pos+4] == 'null':
            self.pos += 4
            return None
        raise SyntaxError(f"Expected null at position {self.pos}")


# Usage
def main():
    parser = JSONParser('{"name": "Alice", "age": 30, "scores": [95, 87, 92]}')
    result = parser.parse()
    print(result)
    # {'name': 'Alice', 'age': 30, 'scores': [95, 87, 92]}
    
    # Test edge cases
    test_cases = [
        '{}',
        '[]',
        '{"a": null, "b": true, "c": false}',
        '{"nested": {"key": "value"}}',
        '[1, 2, [3, 4]]',
        '"hello \\"world\\""',
    ]
    for tc in test_cases:
        parsed = JSONParser(tc).parse()
        print(f"  {tc} → {parsed}")

if __name__ == "__main__":
    main()
```

## 2. CSV Parser

```python
import io
from typing import List, Iterator


class CSVParser:
    """Parse CSV with proper quote handling."""
    
    def __init__(self, delimiter: str = ',', quotechar: str = '"'):
        self.delimiter = delimiter
        self.quotechar = quotechar
    
    def parse_line(self, line: str) -> List[str]:
        """Parse a single CSV line."""
        fields = []
        field = []
        in_quotes = False
        i = 0
        
        while i < len(line):
            ch = line[i]
            
            if in_quotes:
                if ch == self.quotechar:
                    # Check for escaped quote
                    if (i + 1 < len(line) and 
                            line[i + 1] == self.quotechar):
                        field.append(self.quotechar)
                        i += 2
                    else:
                        in_quotes = False
                        i += 1
                else:
                    field.append(ch)
                    i += 1
            else:
                if ch == self.quotechar:
                    in_quotes = True
                    i += 1
                elif ch == self.delimiter:
                    fields.append(''.join(field))
                    field = []
                    i += 1
                else:
                    field.append(ch)
                    i += 1
        
        fields.append(''.join(field))
        return fields
    
    def parse(self, text: str) -> List[List[str]]:
        """Parse entire CSV text."""
        lines = []
        current_line = []
        in_quotes = False
        
        for line in text.split('\n'):
            if in_quotes:
                current_line.append(line)
                # Count quotes to check if we're still in quotes
                quote_count = line.count(self.quotechar)
                if quote_count % 2 == 1:  # Odd = closing quote
                    in_quotes = False
                    lines.append('\n'.join(current_line))
                    current_line = []
            else:
                # Check if line starts a quoted field
                quote_count = line.count(self.quotechar)
                if quote_count % 2 == 1:  # Odd = unclosed quote
                    in_quotes = True
                    current_line = [line]
                else:
                    lines.append(line)
        
        return [self.parse_line(line) for line in lines if line.strip()]
    
    def parse_to_dicts(self, text: str) -> List[dict]:
        """Parse CSV with header row into list of dicts."""
        rows = self.parse(text)
        if not rows:
            return []
        headers = rows[0]
        return [
            dict(zip(headers, row))
            for row in rows[1:]
        ]
    
    def parse_iter(self, file_obj) -> Iterator[List[str]]:
        """Stream parse — memory efficient for large files."""
        for line in file_obj:
            line = line.rstrip('\n')
            if line.strip():
                yield self.parse_line(line)


# Usage
csv_text = """name,age,city
Alice,30,"New York"
Bob,25,"San Francisco, CA"
Charlie,35,"Los Angeles"

parser = CSVParser()
rows = parser.parse_to_dicts(csv_text)
for row in rows:
    print(row)
```

## 3. URL Parser

```python
from dataclasses import dataclass
from typing import Dict, Optional
from urllib.parse import unquote


@dataclass
class ParsedURL:
    scheme: str
    host: str
    port: Optional[int]
    path: str
    query_params: Dict[str, str]
    fragment: str
    username: Optional[str]
    password: Optional[str]
    
    def to_string(self) -> str:
        url = f"{self.scheme}://"
        if self.username:
            url += self.username
            if self.password:
                url += f":{self.password}"
            url += "@"
        url += self.host
        if self.port:
            url += f":{self.port}"
        url += self.path
        if self.query_params:
            params = "&".join(
                f"{k}={v}" for k, v in self.query_params.items())
            url += f"?{params}"
        if self.fragment:
            url += f"#{self.fragment}"
        return url


class URLParser:
    """Parse URL into components."""
    
    def parse(self, url: str) -> ParsedURL:
        # Fragment
        fragment = ""
        if '#' in url:
            url, fragment = url.split('#', 1)
        
        # Query string
        query_params = {}
        if '?' in url:
            url, query = url.split('?', 1)
            query_params = self._parse_query(query)
        
        # Scheme
        scheme = ""
        if '://' in url:
            scheme, url = url.split('://', 1)
        
        # User info
        username = password = None
        if '@' in url:
            userinfo, url = url.rsplit('@', 1)
            if ':' in userinfo:
                username, password = userinfo.split(':', 1)
            else:
                username = userinfo
        
        # Host and port
        host = url
        port = None
        if '/' in url:
            host, path = url.split('/', 1)
            path = '/' + path
        else:
            path = '/'
        
        if ':' in host:
            host, port_str = host.rsplit(':', 1)
            port = int(port_str)
        
        return ParsedURL(
            scheme=scheme,
            host=host,
            port=port,
            path=path,
            query_params=query_params,
            fragment=fragment,
            username=username,
            password=password
        )
    
    def _parse_query(self, query: str) -> Dict[str, str]:
        params = {}
        if not query:
            return params
        for pair in query.split('&'):
            if '=' in pair:
                key, value = pair.split('=', 1)
                params[unquote(key)] = unquote(value)
            else:
                params[unquote(pair)] = ""
        return params


# Usage
parser = URLParser()
url = parser.parse("https://user:pass@example.com:8080/path?key=val&foo=bar#section")
print(f"Scheme: {url.scheme}")      # https
print(f"Host: {url.host}")          # example.com
print(f"Port: {url.port}")          # 8080
print(f"Path: {url.path}")          # /path
print(f"Params: {url.query_params}") # {'key': 'val', 'foo': 'bar'}
print(f"Fragment: {url.fragment}")   # section
```

## 4. Expression Evaluator

```python
from typing import Union


class ExpressionEvaluator:
    """Evaluate mathematical expressions with operator precedence.
    
    Supports: +, -, *, /, ^, (), unary minus
    Grammar:
      expr   → term (('+' | '-') term)*
      term   → factor (('*' | '/') factor)*
      factor → base ('^' factor)?
      base   → NUMBER | '(' expr ')' | ('-' | '+') base
    """
    
    def __init__(self, expression: str):
        self.expr = expression.replace(' ', '')
        self.pos = 0
    
    def evaluate(self) -> float:
        result = self.parse_expr()
        if self.pos < len(self.expr):
            raise ValueError(
                f"Unexpected character at position {self.pos}")
        return result
    
    def peek(self) -> str:
        if self.pos >= len(self.expr):
            return ''
        return self.expr[self.pos]
    
    def advance(self) -> str:
        ch = self.expr[self.pos]
        self.pos += 1
        return ch
    
    def parse_expr(self) -> float:
        """expr → term (('+' | '-') term)*"""
        result = self.parse_term()
        
        while self.peek() in '+-':
            op = self.advance()
            right = self.parse_term()
            if op == '+':
                result += right
            else:
                result -= right
        
        return result
    
    def parse_term(self) -> float:
        """term → factor (('*' | '/') factor)*"""
        result = self.parse_factor()
        
        while self.peek() in '*/':
            op = self.advance()
            right = self.parse_factor()
            if op == '*':
                result *= right
            else:
                if right == 0:
                    raise ValueError("Division by zero")
                result /= right
        
        return result
    
    def parse_factor(self) -> float:
        """factor → base ('^' factor)?"""
        result = self.parse_base()
        
        if self.peek() == '^':
            self.advance()
            exponent = self.parse_factor()  # Right-associative
            result = result ** exponent
        
        return result
    
    def parse_base(self) -> float:
        """base → NUMBER | '(' expr ')' | unary op"""
        # Unary minus/plus
        if self.peek() == '-':
            self.advance()
            return -self.parse_base()
        elif self.peek() == '+':
            self.advance()
            return self.parse_base()
        
        # Parenthesized expression
        if self.peek() == '(':
            self.advance()
            result = self.parse_expr()
            if self.peek() != ')':
                raise ValueError("Missing closing parenthesis")
            self.advance()
            return result
        
        # Number
        return self.parse_number()
    
    def parse_number(self) -> float:
        start = self.pos
        
        while self.pos < len(self.expr) and (
                self.expr[self.pos].isdigit() or 
                self.expr[self.pos] == '.'):
            self.advance()
        
        if self.pos == start:
            raise ValueError(
                f"Expected number at position {self.pos}")
        
        return float(self.expr[start:self.pos])


# Usage
tests = [
    ("2 + 3", 5),
    ("2 * 3 + 4", 10),
    ("2 + 3 * 4", 14),
    ("(2 + 3) * 4", 20),
    ("2 ^ 3", 8),
    ("2 ^ 3 ^ 2", 512),  # Right-associative: 2^(3^2) = 2^9
    ("-5 + 3", -2),
    ("10 / 3", 10/3),
    ("2 * (3 + 4) - 5", 9),
]

print("=== Expression Evaluator ===\n")
for expr, expected in tests:
    result = ExpressionEvaluator(expr).evaluate()
    status = "✅" if abs(result - expected) < 0.0001 else "❌"
    print(f"  {status} {expr} = {result} (expected {expected})")
```

## Common Parsing Techniques

| Technique | Use Case | Example |
|-----------|----------|---------|
| Recursive Descent | Grammar-based parsing | JSON, expressions |
| State Machine | Line-by-line parsing | CSV, TSV |
| Regex | Simple pattern matching | Log lines |
| Shunting Yard | Expression parsing | Math expressions |
| Stream Processing | Large files | Log analysis |

## Interview Tips

1. **Start with the grammar** — write it down before coding
2. **Handle errors gracefully** — give meaningful error messages with position
3. **Test edge cases** — empty input, nested structures, escape characters
4. **Consider streaming** — for large inputs, parse lazily
