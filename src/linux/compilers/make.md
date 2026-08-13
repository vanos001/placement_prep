# Make — Build Automation

## Introduction

Make is the classic Unix build automation tool. It reads a `Makefile` that describes
how to build target files from source files, using rules that specify dependencies
and commands. Make only rebuilds what's necessary by comparing file timestamps,
making it efficient for large projects.

Despite being over 45 years old, Make remains widely used. GNU Make (the most
common implementation on Linux) has evolved with features like pattern rules,
automatic variables, conditional directives, and parallel execution. Many other
build systems (CMake, Autotools) generate Makefiles as their output.

## How Make Works

### Timestamp-Based Dependency Checking

```
Make checks: Is the target older than any prerequisite?
  If yes → run the command to rebuild the target
  If no  → skip (already up to date)

  main.o: main.c utils.h       ← main.o depends on main.c and utils.h
      gcc -c main.c -o main.o   ← command to rebuild main.o

  If main.c or utils.h is newer than main.o → rebuild
  If main.o is newer than both → skip
```

```
┌──────────────┐
│  Makefile     │
│  (rules)      │
└──────┬───────┘
       │
       ▼
┌──────────────┐     ┌──────────────┐
│   Make       │────►│  Dependency  │
│   (reads)    │     │  Graph       │
└──────┬───────┘     └──────┬───────┘
       │                    │
       │  timestamp check   │
       ▼                    ▼
┌──────────────┐     ┌──────────────┐
│  Execute     │     │  Skip        │
│  commands    │     │  (up to date)│
└──────────────┘     └──────────────┘
```

## Makefile Basics

### Simplest Makefile

```makefile
# Makefile for a simple C project
CC = gcc
CFLAGS = -Wall -Wextra -O2

myprogram: main.o utils.o
	$(CC) $(CFLAGS) -o myprogram main.o utils.o

main.o: main.c utils.h
	$(CC) $(CFLAGS) -c main.c

utils.o: utils.c utils.h
	$(CC) $(CFLAGS) -c utils.c

clean:
	rm -f myprogram *.o
```

### Rules

A rule has three parts:

```makefile
target: prerequisites
	command
```

- **target**: The file to create (or a phony name like `clean`)
- **prerequisites**: Files that must exist/up-to-date before the command runs
- **command**: Shell command to create the target (MUST be indented with a TAB)

### Variables

```makefile
# Simple assignment
CC = gcc

# Recursive expansion (expanded when used)
CC = gcc
CFLAGS = -Wall -O2
CMD = $(CC) $(CFLAGS)      # Expanded each time CMD is used

# Simple expansion (expanded when defined)
CC := gcc
CFLAGS := -Wall -O2
CMD := $(CC) $(CFLAGS)     # Expanded now, CMD is a fixed string

# Conditional assignment (only if not already defined)
CC ?= gcc

# Append
CFLAGS += -g

# Automatic variables
# $@ — target name
# $< — first prerequisite
# $^ — all prerequisites
# $? — prerequisites newer than target
# $* — stem (matched by pattern rule %)
```

### Pattern Rules

```makefile
# Pattern rule: compile any .c to .o
%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

# Pattern rule with multiple prerequisites
%.o: %.c %.h
	$(CC) $(CFLAGS) -c $< -o $@

# Static pattern rule (applies only to specific targets)
$(objects): %.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@
```

### Phony Targets

```makefile
# Phony targets don't represent actual files
.PHONY: all clean install test

all: myprogram

clean:
	rm -f myprogram *.o

install: myprogram
	install -m 755 myprogram /usr/local/bin/

test: myprogram
	./myprogram --test
```

## Intermediate Makefile Example

```makefile
# Makefile for a multi-file C project
# ─────────────────────────────────────

# Compiler and flags
CC      := gcc
CFLAGS  := -Wall -Wextra -Werror -O2 -g
LDFLAGS := -lm -lpthread

# Directories
SRCDIR := src
OBJDIR := build
BINDIR := bin

# Sources and objects
SRCS := $(wildcard $(SRCDIR)/*.c)
OBJS := $(patsubst $(SRCDIR)/%.c,$(OBJDIR)/%.o,$(SRCS))
DEPS := $(OBJS:.o=.d)

# Target
TARGET := $(BINDIR)/myprogram

# Default target
all: $(TARGET)

# Link
$(TARGET): $(OBJS) | $(BINDIR)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

# Compile (with dependency generation)
$(OBJDIR)/%.o: $(SRCDIR)/%.c | $(OBJDIR)
	$(CC) $(CFLAGS) -MMD -MP -c $< -o $@

# Create directories
$(OBJDIR):
	mkdir -p $(OBJDIR)

$(BINDIR):
	mkdir -p $(BINDIR)

# Include auto-generated dependencies
-include $(DEPS)

# Phony targets
.PHONY: all clean install test

clean:
	rm -rf $(OBJDIR) $(BINDIR)

install: $(TARGET)
	install -m 755 $(TARGET) /usr/local/bin/

test: $(TARGET)
	./$(TARGET) --test

# Print variables (for debugging)
print-%:
	@echo $* = $($*)
```

### Dependency Generation

```bash
# Auto-generate dependencies
gcc -MMD -MP -c main.c
# Creates main.d:
# main.o: main.c utils.h config.h
# utils.h:
# config.h:

# In Makefile:
-include $(DEPS)
```

## Advanced Features

### Functions

```makefile
# String substitution
SRCS := main.c utils.c parser.c
OBJS := $(SRCS:.c=.o)              # main.o utils.o parser.o

# Pattern substitution
OBJS := $(patsubst %.c,%.o,$(SRCS))

# Wildcard
SRCS := $(wildcard src/*.c)

# Filter
C_SRCS := $(filter %.c,$(SRCS))
NON_C  := $(filter-out %.c,$(SRCS))

# Sort (remove duplicates, sort)
DIRS := $(sort $(dir $(SRCS)))

# For each
DIRS := src lib test
INCLUDES := $(foreach dir,$(DIRS),-I$(dir))

# If/else
BUILD_TYPE ?= debug
ifeq ($(BUILD_TYPE),release)
  CFLAGS := -O2 -DNDEBUG
else
  CFLAGS := -O0 -g
endif

# Call (user-defined functions)
capitalize = $(shell echo $(1) | tr 'a-z' 'A-Z')
RESULT := $(call capitalize,hello)

# Shell
GIT_HASH := $(shell git rev-parse --short HEAD)
FILES    := $(shell find . -name '*.c')
```

### Conditional Directives

```makefile
# ifeq / ifneq
DEBUG ?= 1
ifeq ($(DEBUG),1)
  CFLAGS += -g -O0
else
  CFLAGS += -O2 -DNDEBUG
endif

# ifdef / ifndef
ifdef VERBOSE
  Q :=
else
  Q := @
endif

all:
	$(Q)gcc -o myprogram main.c
```

### Target-Specific Variables

```makefile
# Apply CFLAGS only to specific targets
CFLAGS += -Wall

debug: CFLAGS += -g -O0
debug: myprogram

release: CFLAGS += -O2 -DNDEBUG
release: myprogram

myprogram: main.o utils.o
	$(CC) $(CFLAGS) -o $@ $^
```

### Secondary Expansion

```makefile
# .SECONDEXPANSION allows using automatic variables in prerequisites
.PHONY: all

objects := main.o utils.o parser.o

all: $$(objects)    # Note: double $$

%.o: %.c
	$(CC) -c $< -o $@

# With .SECONDEXPANSION:
.SECONDEXPANSION:
all: $$(objects)
```

### Canned Recipes

```makefile
# Define reusable recipe
define compile_c
$(CC) $(CFLAGS) -c $(1) -o $(2)
endef

# Use it
main.o: main.c
	$(call compile_c,$<,$@)
```

## Parallel Make

```bash
# Run with parallel jobs
make -j$(nproc)               # Use all CPU cores
make -j8                      # Use 8 jobs

# Parallel with load limit
make -j8 -l 4.0              # Max 8 jobs, max load avg 4.0

# Keep going on errors
make -j8 -k                  # Continue building other targets on error

# Dry run
make -n                      # Show commands without executing
make --dry-run

# Debug make
make -d                      # Full debug output
make --debug=b              # Basic debug
```

### Safe Parallel Builds

For parallel builds to work correctly, all dependencies must be properly declared:

```makefile
# BAD: missing dependency (race condition in parallel build)
parser.o: parser.c
	$(CC) -c parser.c -o parser.o

# GOOD: all dependencies declared
parser.o: parser.c parser.h tokens.h
	$(CC) -c parser.c -o parser.o

# Use order-only prerequisites (don't trigger rebuild)
$(OBJDIR)/%.o: $(SRCDIR)/%.c | $(OBJDIR)
	$(CC) -c $< -o $@
```

## Autotools Relationship

The GNU Build System (Autotools) generates Makefiles from higher-level descriptions:

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ configure.ac │──►│  configure   │──►│  Makefile     │
│ Makefile.am  │   │  (generated) │   │  (generated) │
└──────────────┘   └──────────────┘   └──────────────┘
```

### Autotools Basics

```bash
# Project structure
myproject/
├── configure.ac        # Autoconf input
├── Makefile.am         # Automake input
├── src/
│   ├── Makefile.am
│   └── main.c
└── m4/                 # Autoconf macros

# Generate build system
autoreconf -i           # Creates configure script

# Standard build process
./configure             # Detect system features, generate Makefiles
make                    # Build
make install            # Install
make dist               # Create distribution tarball
```

### configure.ac

```m4
# configure.ac
AC_PREREQ([2.69])
AC_INIT([myproject], [1.0], [bug@example.com])
AM_INIT_AUTOMAKE([foreign -Wall -Werror])
AC_PROG_CC
AC_PROG_RANLIB
AC_CHECK_LIB([m], [sin], [], [AC_MSG_ERROR([libm required])])
AC_CHECK_HEADERS([stdio.h stdlib.h])
AC_CONFIG_FILES([Makefile src/Makefile])
AC_OUTPUT
```

### Makefile.am

```makefile
# Top-level Makefile.am
SUBDIRS = src
EXTRA_DIST = README.md LICENSE

# src/Makefile.am
bin_PROGRAMS = myprogram
myprogram_SOURCES = main.c utils.c utils.h
myprogram_CFLAGS = -Wall -Wextra -O2
myprogram_LDADD = -lm -lpthread
```

### Autotools Workflow

```bash
# Developer: generate build system
autoreconf -i

# User: build from tarball
tar xzf myproject-1.0.tar.gz
cd myproject-1.0
./configure --prefix=/usr/local
make -j$(nproc)
sudo make install

# Common configure options
./configure --help
./configure --prefix=/usr/local
./configure --enable-debug
./configure --with-openssl=/usr/local/ssl
./configure CC=clang CFLAGS="-O2 -march=native"
```

## Recursive Make

Traditional approach where each subdirectory has its own Makefile:

```makefile
# Top-level Makefile
SUBDIRS = src lib test

all: $(SUBDIRS)

$(SUBDIRS):
	$(MAKE) -C $@

clean:
	for dir in $(SUBDIRS); do $(MAKE) -C $$dir clean; done

.PHONY: all clean $(SUBDIRS)
```

### Non-Recursive Make (Recommended)

Use `include` instead of recursive make for better dependency tracking:

```makefile
# Makefile (non-recursive)
SRCDIR := src
LIBDIR := lib
OBJDIR := build

include $(SRCDIR)/Makefile.mk
include $(LIBDIR)/Makefile.mk

# All objects from all subdirectories
ALL_OBJS := $(SRC_OBJS) $(LIB_OBJS)

all: $(OBJDIR)/myprogram

$(OBJDIR)/myprogram: $(ALL_OBJS)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)
```

```makefile
# src/Makefile.mk
SRC_SRCS := $(SRCDIR)/main.c $(SRCDIR)/utils.c
SRC_OBJS := $(patsubst $(SRCDIR)/%.c,$(OBJDIR)/src/%.o,$(SRC_SRCS))
```

## Makefile Best Practices

```makefile
# 1. Use := for simple expansion (more predictable)
CC := gcc

# 2. Use ?= for overridable defaults
CFLAGS ?= -O2

# 3. Always declare .PHONY targets
.PHONY: all clean install test

# 4. Use automatic variables
%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

# 5. Use -MMD for automatic dependency tracking
%.o: %.c
	$(CC) $(CFLAGS) -MMD -MP -c $< -o $@
-include $(DEPS)

# 6. Use | for order-only prerequisites
$(OBJDIR)/%.o: $(SRCDIR)/%.c | $(OBJDIR)
	$(CC) -c $< -o $@

# 7. Use $(MAKE) instead of make (for recursive invocations)
$(SUBDIRS):
	$(MAKE) -C $@

# 8. Support DESTDIR for packaging
install: $(TARGET)
	install -m 755 $(TARGET) $(DESTDIR)$(PREFIX)/bin/

# 9. Print useful info in silent mode
all:
	@echo "  CC    $@"
	@$(CC) $(CFLAGS) -c $< -o $@

# 10. Use variables for tools (enable cross-compilation)
CC ?= gcc
AR ?= ar
STRIP ?= strip
```

## Debugging Makefiles

```bash
# Print a variable
make print-CFLAGS

# With the rule:
print-%:
	@echo $* = $($*)

# Show what make would do
make -n                    # Dry run
make --just-print

# Debug make's decision process
make -d                    # Full debug
make --debug=b            # Basic debug

# Show implicit rules
make -p                    # Print database

# Show why a target is rebuilt
make -q                    # Question mode (exit status tells you)

# Check if a target is up to date
make -q target && echo "up to date" || echo "needs rebuild"
```

## Common Makefile Patterns

### Building a Library

```makefile
LIB := libfoo.a
SRCS := $(wildcard src/*.c)
OBJS := $(SRCS:.c=.o)

$(LIB): $(OBJS)
	$(AR) rcs $@ $^

%.o: %.c
	$(CC) $(CFLAGS) -fPIC -c $< -o $@
```

### Multi-Configuration Builds

```makefile
# Build multiple configurations
.PHONY: debug release

debug:
	$(MAKE) BUILD_TYPE=debug OBJDIR=build/debug

release:
	$(MAKE) BUILD_TYPE=release OBJDIR=build/release

ifeq ($(BUILD_TYPE),debug)
  CFLAGS += -g -O0 -DDEBUG
else
  CFLAGS += -O2 -DNDEBUG
endif
```

### Header Dependencies

```makefile
# Auto-generate header dependencies
DEPFLAGS = -MMD -MP -MF $(OBJDIR)/$*.d

%.o: %.c | $(OBJDIR)
	$(CC) $(CFLAGS) $(DEPFLAGS) -c $< -o $@

-include $(wildcard $(OBJDIR)/*.d)
```

## References

- [The Linux Kernel Documentation](https://docs.kernel.org/)
- [LWN.net - Linux and free software news](https://lwn.net/)
- [GNU Project Documentation](https://www.gnu.org/doc/doc.html)
- [GNU Manuals](https://www.gnu.org/manual/manual.html)
- [Free Software Directory](https://directory.fsf.org/wiki/Main_Page)
- [Planet GNU](https://planet.gnu.org/)
- [Free Software Books](https://www.gnu.org/doc/other-free-books.html)

- [GNU Make Manual](https://www.gnu.org/software/make/manual/)
- [Makefile Tutorial](https://makefiletutorial.com/)
- [Recursive Make Considered Harmful (PDF)](http://aegis.sourceforge.net/auug97.pdf)
- [Autotools Tutorial](https://www.lrde.epita.fr/~adl/autotools.html)

## Related Topics

- [CMake](./cmake.md) — Modern build system generator
- [GCC](./gcc.md) — The compiler that Make drives
- [Linker](./linker.md) — How object files are linked
