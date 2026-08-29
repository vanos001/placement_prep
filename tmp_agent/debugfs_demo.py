# MODEL: a miniature debugfs -- dict-backed in-memory tree, typed node
# factories, file_operations-style dispatch. Kernel habits preserved:
# mode bits gate writes; a 0444 node rejects writes with EACCES.
import errno

class DebugfsError(OSError):
    def __init__(self, no, msg):
        super().__init__(no, msg)

class Node:
    def __init__(self, name, mode):
        self.name, self.mode = name, mode

class Dir(Node):
    def __init__(self, name, mode=0o755):
        super().__init__(name, mode)
        self.children = {}

class U64(Node):
    """debugfs_create_u64(): decimal in/out, wraps as a u64 would."""
    def __init__(self, name, mode, value=0):
        super().__init__(name, mode)
        self.value = value
    def read(self):
        return "%d\n" % self.value
    def write(self, data):
        try:
            v = int(data.strip())
        except ValueError:
            raise DebugfsError(errno.EINVAL, "bad u64 input")
        self.value = v % (1 << 64)

class Bool(Node):
    """debugfs_create_bool(): Y/N out; y|n|1|0 in; junk silently ignored."""
    def __init__(self, name, mode, value=False):
        super().__init__(name, mode)
        self.value = bool(value)
    def read(self):
        return "Y\n" if self.value else "N\n"
    def write(self, data):
        s = data.strip().lower()
        if s in ("y", "1"):
            self.value = True
        elif s in ("n", "0"):
            self.value = False

class Blob(Node):
    """debugfs_create_blob(): created read-only, always."""
    def __init__(self, name, data):
        super().__init__(name, 0o444)
        self.data = data
    def read(self):
        return self.data.decode("ascii")
    def write(self, data):
        raise DebugfsError(errno.EACCES, "write on read-only blob")

class SeqFile(Node):
    """seq_file-backed node: .show emits unbounded text page by page."""
    def __init__(self, name, show):
        super().__init__(name, 0o444)
        self.show = show
    def read(self):
        return "".join(self.show())
    def write(self, data):
        raise DebugfsError(errno.EINVAL, "no .write op registered")

def debugfs_create_dir(name, parent):
    parent.children[name] = Dir(name)
    return parent.children[name]

def debugfs_create(node, parent):
    parent.children[node.name] = node
    return node

def dispatch(node, op, data=None):
    """file_operations dispatch: kernel gates write on mode's w-bits."""
    if op == "read":
        return node.read()
    if not node.mode & 0o222:
        raise DebugfsError(errno.EACCES, "mode 0%o denies write" % node.mode)
    node.write(data)

def dump_tree(dirnode, depth=0):
    out = [] if depth else [dirnode.name]
    for name in sorted(dirnode.children):
        child, pad = dirnode.children[name], "  " * depth
        if isinstance(child, Dir):
            out.append("%s%s/" % (pad, name))
            out.extend(dump_tree(child, depth + 1))
        else:
            desc = type(child).__name__
            if isinstance(child, U64):
                desc += " value=%d" % child.value
            if isinstance(child, Bool):
                desc += " value=%s" % ("Y" if child.value else "N")
            out.append("%s%s  %s 0%03o" % (pad, name, desc, child.mode))
    return out

root = Dir("/sys/kernel/debug")
froboz = debugfs_create_dir("froboz", root)
counter = debugfs_create(U64("counter", 0o644, 42), froboz)
enabled = debugfs_create(Bool("enabled", 0o644, True), froboz)
fwver = debugfs_create(Blob("fw_version", b"Froboz FW 3.11 (built-in)\n"),
                       froboz)
debugfs_create(SeqFile("stats", lambda: [
    "packets=%d\n" % counter.value,
    "enabled=%s\n" % enabled.read().strip()]), froboz)

for line in dump_tree(root):
    print(line)
print("--- interaction transcript ---")
print("$ cat counter      -> %s" % dispatch(counter, "read"), end="")
dispatch(counter, "write", "100")
print("$ echo 100 >counter-> %s" % dispatch(counter, "read"), end="")
print("$ cat stats        -> %s" % dispatch(froboz.children["stats"],
                                            "read"), end="")
dispatch(enabled, "write", "maybe")          # junk: silently ignored
print("$ echo maybe >enabled  value stays %s" % enabled.read().strip())
for node, data in ((fwver, "hack"), (counter, "oops")):
    try:
        dispatch(node, "write", data)
    except DebugfsError as e:
        print("$ echo %s >%-9s -> %s: %s" % (data, node.name,
                                             errno.errorcode[e.errno], e))
