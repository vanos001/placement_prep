# CLI Tools

## Building Command-Line Applications

### Argument Parsing

#### Python (argparse)

```python
import argparse

parser = argparse.ArgumentParser(description='Process log files')
parser.add_argument('input', help='Input log file')
parser.add_argument('-o', '--output', default='report.txt',
                    help='Output file (default: report.txt)')
parser.add_argument('-v', '--verbose', action='store_true',
                    help='Verbose output')
parser.add_argument('--format', choices=['text', 'json', 'csv'],
                    default='text', help='Output format')
parser.add_argument('-n', '--lines', type=int, default=100,
                    help='Number of lines to process')

args = parser.parse_args()

if args.verbose:
    print(f"Processing {args.input}...")
```

#### Go (cobra)

```go
package cmd

import (
    "fmt"
    "github.com/spf13/cobra"
)

var rootCmd = &cobra.Command{
    Use:   "logproc",
    Short: "Process log files",
    Long:  "A CLI tool for analyzing and processing log files",
    Run: func(cmd *cobra.Command, args []string) {
        verbose, _ := cmd.Flags().GetBool("verbose")
        format, _ := cmd.Flags().GetString("format")
        fmt.Printf("Processing with verbose=%v, format=%s\n", verbose, format)
    },
}

func init() {
    rootCmd.Flags().BoolP("verbose", "v", false, "Verbose output")
    rootCmd.Flags().StringP("format", "f", "text", "Output format (text|json|csv)")
    rootCmd.Flags().IntP("lines", "n", 100, "Number of lines to process")
}
```

### Interactive Prompts

```python
# Using click for interactive CLI
import click

@click.command()
@click.option('--name', prompt='Your name', help='Name to greet')
@click.option('--count', default=1, type=int, help='Number of greetings')
@click.confirmation_option(prompt='Are you sure?')
def greet(name, count):
    for _ in range(count):
        click.echo(f'Hello, {name}!')

# Select from options
@click.command()
@click.option('--format', type=click.Choice(['json', 'csv', 'text']))
def convert(format):
    click.echo(f'Converting to {format}')
```

### Output Formatting

```python
# Table output
from tabulate import tabulate

data = [
    ["alice", 100, "active"],
    ["bob", 200, "inactive"],
    ["charlie", 150, "active"],
]

headers = ["Name", "Requests", "Status"]
print(tabulate(data, headers=headers, tablefmt="grid"))

# +---------+-----------+----------+
# | Name    | Requests  | Status   |
# +=========+===========+==========+
# | alice   | 100       | active   |
# +---------+-----------+----------+

# JSON output
import json
print(json.dumps(data, indent=2))

# Progress bars
from tqdm import tqdm
for item in tqdm(range(100), desc="Processing"):
    process(item)
```

### Color Output

```python
# Using click
click.secho("Success!", fg="green")
click.secho("Warning!", fg="yellow")
click.secho("Error!", fg="red", bold=True)

# Using rich
from rich.console import Console
console = Console()
console.print("[bold green]Success![/bold green]")
console.print("[red]Error:[/red] File not found")
```

### Subcommands

```python
# Using click groups
@click.group()
def cli():
    """Log processing tool."""
    pass

@cli.command()
@click.argument('file')
def analyze(file):
    """Analyze a log file."""
    click.echo(f'Analyzing {file}')

@cli.command()
@click.argument('file')
@click.option('--pattern', required=True)
def search(file, pattern):
    """Search log file for pattern."""
    click.echo(f'Searching {file} for {pattern}')

@cli.command()
@click.argument('files', nargs=-1)
def merge(files):
    """Merge multiple log files."""
    click.echo(f'Merging {len(files)} files')

cli.add_command(analyze)
cli.add_command(search)
cli.add_command(merge)
```

### Error Handling

```python
import sys
import click

def main():
    try:
        result = process_file(args.input)
    except FileNotFoundError:
        click.secho(f"Error: File '{args.input}' not found", fg="red")
        sys.exit(1)
    except PermissionError:
        click.secho(f"Error: Permission denied", fg="red")
        sys.exit(1)
    except Exception as e:
        click.secho(f"Error: {e}", fg="red")
        sys.exit(1)
```

### Configuration Files

```python
import toml
import os

def load_config():
    config_paths = [
        './config.toml',
        '~/.myapp/config.toml',
        '/etc/myapp/config.toml',
    ]
    
    for path in config_paths:
        expanded = os.path.expanduser(path)
        if os.path.exists(expanded):
            return toml.load(expanded)
    
    return {}  # defaults
```

## Interview Questions

**Q: How would you design a CLI tool that handles both interactive and piped input?**
A: Check `sys.stdin.isatty()` — if False, read from stdin (piped). If True, use interactive prompts. Use argparse for flags, support `--no-interactive` for scripts. Handle SIGPIPE gracefully.

**Q: How do you test CLI tools?**
A: (1) Unit test the logic functions separately, (2) use subprocess to test the CLI interface, (3) use click.testing.CliRunner for click-based CLIs, (4) test exit codes, (5) test error messages, (6) test piped input.

## References

- [Python argparse](https://docs.python.org/3/library/argparse.html)
- [Click Documentation](https://click.palletsprojects.com/)
- [Cobra for Go](https://cobra.dev/)
- [Rich Python Library](https://rich.readthedocs.io/)
