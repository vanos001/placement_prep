# File Processing Problems

## Log Analyzer

### Requirements
- Parse log files in various formats (Apache, Nginx, JSON)
- Extract statistics: request count, error rate, response times
- Filter by time range, status code, path
- Output summary reports

### Implementation (Python)

```python
import re
from collections import Counter, defaultdict
from datetime import datetime

class LogAnalyzer:
    LOG_PATTERN = re.compile(
        r'(?P<ip>\S+) - - \[(?P<time>[^\]]+)\] "(?P<method>\S+) (?P<path>\S+) \S+" (?P<status>\d+) (?P<size>\d+)'
    )
    
    def __init__(self):
        self.entries = []
    
    def parse(self, filepath):
        with open(filepath) as f:
            for line in f:
                match = self.LOG_PATTERN.match(line)
                if match:
                    self.entries.append(match.groupdict())
    
    def top_paths(self, n=10):
        return Counter(e['path'] for e in self.entries).most_common(n)
    
    def error_rate(self):
        errors = sum(1 for e in self.entries if int(e['status']) >= 400)
        return errors / len(self.entries) if self.entries else 0
    
    def status_distribution(self):
        return Counter(e['status'] for e in self.entries)
    
    def requests_per_hour(self):
        hourly = defaultdict(int)
        for e in self.entries:
            dt = datetime.strptime(e['time'], '%d/%b/%Y:%H:%M:%S %z')
            hourly[dt.hour] += 1
        return dict(sorted(hourly.items()))
    
    def slow_requests(self, threshold_ms=1000):
        # If log includes response time
        return [e for e in self.entries 
                if int(e.get('response_time', 0)) > threshold_ms]
```

## Duplicate Detector

### Requirements
- Find duplicate files by content (hash-based)
- Support large files (streaming hash)
- Report duplicate groups
- Option to hardlink duplicates (save space)

### Implementation

```python
import hashlib
import os
from collections import defaultdict

class DuplicateDetector:
    def __init__(self, root_dir):
        self.root = root_dir
        self.size_map = defaultdict(list)  # size → [paths]
        self.hash_map = defaultdict(list)  # hash → [paths]
    
    def scan(self):
        # Phase 1: Group by size (fast filter)
        for dirpath, _, filenames in os.walk(self.root):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    size = os.path.getsize(filepath)
                    self.size_map[size].append(filepath)
                except OSError:
                    pass
        
        # Phase 2: Hash files with same size
        for size, paths in self.size_map.items():
            if len(paths) < 2:
                continue
            for path in paths:
                file_hash = self._hash_file(path)
                self.hash_map[file_hash].append(path)
        
        # Return groups of duplicates
        return {h: paths for h, paths in self.hash_map.items() 
                if len(paths) > 1}
    
    def _hash_file(self, filepath, chunk_size=8192):
        """Stream hash for large files."""
        h = hashlib.sha256()
        with open(filepath, 'rb') as f:
            while chunk := f.read(chunk_size):
                h.update(chunk)
        return h.hexdigest()
    
    def total_wasted_space(self):
        total = 0
        for paths in self.hash_map.values():
            if len(paths) > 1:
                size = os.path.getsize(paths[0])
                total += size * (len(paths) - 1)
        return total
```

## File Search Tool

### Requirements
- Search files by name pattern (glob/regex)
- Search by content (grep-like)
- Filter by size, date, type
- Respect .gitignore
- Parallel search for performance

### Implementation

```python
import os
import fnmatch
import re
from concurrent.futures import ThreadPoolExecutor

class FileSearch:
    def __init__(self, root='.'):
        self.root = root
        self.ignores = self._load_gitignore()
    
    def search(self, name_pattern=None, content_pattern=None,
               min_size=None, max_size=None, extensions=None):
        results = []
        
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = []
            for filepath in self._walk():
                if self._matches_filters(filepath, name_pattern, 
                                        min_size, max_size, extensions):
                    if content_pattern:
                        futures.append(
                            executor.submit(self._search_content, 
                                          filepath, content_pattern))
                    else:
                        results.append(filepath)
            
            for future in futures:
                match = future.result()
                if match:
                    results.append(match)
        
        return results
    
    def _walk(self):
        for dirpath, dirnames, filenames in os.walk(self.root):
            # Filter ignored directories
            dirnames[:] = [d for d in dirnames 
                          if not self._is_ignored(os.path.join(dirpath, d))]
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if not self._is_ignored(filepath):
                    yield filepath
    
    def _search_content(self, filepath, pattern):
        try:
            with open(filepath) as f:
                for i, line in enumerate(f, 1):
                    if re.search(pattern, line):
                        return f"{filepath}:{i}: {line.strip()}"
        except (UnicodeDecodeError, PermissionError):
            pass
        return None
    
    def _matches_filters(self, path, name_pattern, min_size, max_size, exts):
        if name_pattern and not fnmatch.fnmatch(os.path.basename(path), name_pattern):
            return False
        if exts:
            ext = os.path.splitext(path)[1]
            if ext not in exts:
                return False
        if min_size or max_size:
            size = os.path.getsize(path)
            if min_size and size < min_size:
                return False
            if max_size and size > max_size:
                return False
        return True
    
    def _is_ignored(self, path):
        # Simplified gitignore check
        name = os.path.basename(path)
        return name.startswith('.') or name == '__pycache__'
    
    def _load_gitignore(self):
        patterns = []
        gitignore = os.path.join(self.root, '.gitignore')
        if os.path.exists(gitignore):
            with open(gitignore) as f:
                patterns = [line.strip() for line in f 
                           if line.strip() and not line.startswith('#')]
        return patterns
```

## Interview Questions

**Q: How would you find duplicates in a directory with millions of files?**
A: (1) Group by file size first (fast, eliminates most non-duplicates), (2) for same-size files, compute hash (SHA-256) using streaming (8KB chunks), (3) use parallel hashing for speed, (4) report groups with same hash.

**Q: How do you search large log files efficiently?**
A: (1) Use memory-mapped files (mmap) for large files, (2) parallel search with thread pool, (3) use grep/ripgrep for simple patterns, (4) index logs with tools like Elasticsearch for repeated queries, (5) compress and search with zgrep for gzipped logs.

## References

- [Python os module](https://docs.python.org/3/library/os.html)
- [Python hashlib](https://docs.python.org/3/library/hashlib.html)
- [ripgrep — faster grep](https://github.com/BurntSushi/ripgrep)
