# JVM Class Loaders

## The Big Picture

Class loading is the bridge between `.class` files on disk and live objects inside the running VM. It is responsible for three things: locating the bytes of a class, transforming those bytes into a `Class` object (an internal C++ `InstanceKlass` in HotSpot), and resolving symbolic references lazily enough that it doesn't pay for work it won't need. The whole subsystem is governed by **JLS Chapter 12** (initialization) and **JVMS Chapter 5** (loading, linking, and initialization).

There are exactly two entry points: the *bootstrap* loader (a piece of C++ code, no Java class) and instances of `java.lang.ClassLoader`. Everything you do at the application level funnels through one of these.

```
                     ┌──────────────────────────────────┐
                     │  bootstrap   (native, C++, null)  │  ← loads rt/java.base
                     │   returns null from getParent()   │
                     └────────────┬─────────────────────┘
                                  │
                     ┌────────────▼─────────────────────┐
                     │  platform  (jdk.internal.loader.  │  ← was "ext" pre-9
                     │  ClassLoaders$PlatformClassLoader)│
                     └────────────┬─────────────────────┘
                                  │
                     ┌────────────▼─────────────────────┐
                     │  app       (jdk.internal.loader.  │  ← classpath
                     │  ClassLoaders$AppClassLoader)      │
                     └────────────┬─────────────────────┘
                                  │
                     ┌────────────▼─────────────────────┐
                     │  user-defined URLClassLoader etc. │
                     └──────────────────────────────────┘
```

Three things to commit to memory before any interview:

1. The **bootstrap class loader is not a Java object**. Its `getParent()` is null, and you can spot loaded-by-bootstrap classes because `clazz.getClassLoader() == null`.
2. The **platform class loader** is JDK 9+'s rename of the old *extension* loader. The extension mechanism (`-Djava.ext.dirs`) was removed by JEP 320, and the loader was repurposed for `java.platform.spec` modules.
3. The **app class loader** is the default — it loads from the `-cp` / `--class-path` / module path.

## The Delegation Model

When a `ClassLoader.loadClass(name)` is invoked, the standard `ClassLoader` implementation does **parent-first delegation**:

```java
// Substantially simplified from java.lang.ClassLoader#loadClass
protected Class<?> loadClass(String name, boolean resolve)
        throws ClassNotFoundException {
    synchronized (getClassLoadingLock(name)) {
        // 1. Have we already loaded this class?
        Class<?> c = findLoadedClass(name);
        if (c == null) {
            // 2. Ask the parent first.
            try {
                c = parent.loadClass(name, false);
            } catch (ClassNotFoundException e) {
                // 3. Parent couldn't — try ourselves.
                c = findClass(name);
            }
        }
        if (resolve) resolveClass(c);
        return c;
    }
}
```

The motivation is twofold. First, **safety**: only the bootstrap loader can ever load `java.lang.String`, which prevents a malicious classpath from shadowing the core types. Second, **uniqueness**: if a class has already been defined by a parent loader, child loaders must reuse the parent's `Class` object rather than define their own — the runtime identity `(loader, name)` pair is unique. A type is identified by `(name, definingClassLoader)`, which is why you cannot cast between two `Foo` classes that have identical bytecode but were loaded by different loaders.

The `getClassLoadingLock(name)` call returns a per-class-name lock object; before JDK 7, `loadClass` was `synchronized` on the `ClassLoader` instance, which serialized all loads in a hierarchy and was a real scalability bottleneck.

## The Five Phases

JVMS Chapter 5 splits loading into a pipeline of phases that are not strictly sequential — they can interleave.

```
   load  ─► verify ─► prepare ─► resolve (lazy) ─► initialize
     │       │           │            │              │
     │       │           │            │              ▼
     │       │           │            │      <clinit> runs
     │       │           │            │      static fields assigned
     │       │           ▼            │
     │       │      static fields     │
     │       │      set to default    │
     │       │      values (0/null)   │
     │       ▼                         │
     │      bytecode verifier          │
     │      checks type safety         │
     │      & stack map frames        │
     ▼                                 │
   bytes  →  Class object                │
   read                              (in 1–5 steps)
   from disk
```

1. **Loading**: locate bytes (typically via a `URL` for `URLClassLoader`), pass them to `defineClass`. The bytes are parsed into a `Class` object and stored in the loader's internal table. JVMS §5.3.

2. **Verification**: JVMS §4.10. The verifier walks the bytecode, builds *stack map frames* (`StackMapTable` attribute written into the class file by `javac`), and checks that every instruction has a well-typed operand stack and that local variables are typed correctly. Verification is the security boundary that prevents hand-crafted bytecode from forging pointers — a class that fails verification is rejected with `VerifyError`.

3. **Preparation**: JVMS §5.4.2. Each `static` field is allocated and set to the *default* value (0, `0L`, `null`, `0.0`, `false`). This is distinct from initialization, where the actual assignment runs.

4. **Resolution**: JVMS §5.4.3. Symbolic references in the constant pool (`CONSTANT_Fieldref_info`, `CONSTANT_Methodref_info`, etc.) are lazily resolved to direct references. HotSpot does this on first use; some implementations do it eagerly. Resolution can be triggered by `getstatic`, `putstatic`, `invokestatic`, `invokevirtual`, `invokeinterface`, `new`, `anewarray`, `checkcast`, `instanceof`.

5. **Initialization**: JVMS §5.5. The `<clinit>` method runs. It is the JVM-synthesized method that contains the static field initializers and static blocks of the class in source order. `<clinit>` is synchronized at the JVM level — only one thread runs `<clinit>` for a given class at a time, and other threads block waiting.

There are six triggers for initialization (JLS §12.4.1):

- Creating an instance (`new`)
- Calling a static method
- Assigning / reading a static field (except `final` constants whose value is inlined into callers as `ConstantValue`)
- Reflective use (`Class.forName`)
- Subclass initialization triggers parent initialization
- A class designated as the initial class at startup

## Custom Class Loaders

Custom loaders subclass `ClassLoader` and override `findClass`:

```java
import java.nio.file.*;
import java.io.IOException;

public class DiskClassLoader extends ClassLoader {
    private final Path root;

    public DiskClassLoader(Path root, ClassLoader parent) {
        super(parent);
        this.root = root;
    }

    @Override
    protected Class<?> findClass(String name) throws ClassNotFoundException {
        byte[] bytes;
        try {
            bytes = Files.readAllBytes(
                root.resolve(name.replace('.', '/') + ".class"));
        } catch (IOException e) {
            throw new ClassNotFoundException(name, e);
        }
        // defineClass is the bridge: bytes -> live Class object
        return defineClass(name, bytes, 0, bytes.length);
    }
}
```

The contract is "find the bytes, then call `defineClass`". `defineClass` runs the bytecode verifier, parses the constant pool, allocates the `Class` and links it into the loader's internal `classes` vector. Once a class is defined by a loader, that loader is its *defining loader* for life.

Two useful tricks:

- **Parent-last / child-first loading**: override `loadClass` instead of `findClass`. Be careful: this breaks the class uniqueness invariant for classes that share a name with something the parent can also load. Used by application servers and OSGi to provide isolation.
- **Parallel capable loaders**: mark your class `protected static final ClassLoader.registerAsParallelCapable()` at class init time. Allows fine-grained locking per-class-name instead of per-loader, which is the difference between thread-safe and throughput-killing.

## Class Loader Isolation Patterns

Real systems need *isolation* — two webapps deployed in the same JVM that both want to use different versions of `commons-logging` without colliding. Three patterns dominate:

### 1. Tomcat (per-webapp loader, child-first)

```
   Bootstrap
       │
   Platform
       │
   App (Common loader — shared by all webapps)
       │
   ┌───┴────┐
   │        │
   Webapp1  Webapp2   ← each loads WEB-INF/classes,
                          WEB-INF/lib/*.jar; child-first
```

Tomcat's `WebappClassLoader` deliberately flips the delegation order: it tries `findClass` *before* delegating to the parent. This lets a webapp override JARs shared at the server level, which is the contract users actually expect.

### 2. OSGi (one bundle = one loader, graph of imports)

OSGi turns class loading into a directed graph of bundles, each with its own loader. A bundle's loader answers questions of the form "where do I get class `com.acme.Foo`?" by consulting the *import/export* tables:

```
  Bundle A (exports com.acme.api)              Bundle B (imports com.acme.api)
     │                                            │
     A.ClassLoader ◄──── wire ◄─── B.ClassLoader
                                      │
                                 └─► on a class in com.acme.api:
                                     A's loader handles the load;
                                     B's loader participates only
                                     as initiating loader
```

This gives strong isolation: two bundles can have *different* versions of `com.acme.api.Foo` simultaneously, because the loaders are separate and the wires explicit. The classic gotcha is the `org.osgi.framework.BundleException` when a wire can't be resolved — usually means a transitive `Import-Package` is missing.

### 3. JBoss Modules (Declarative module loaders)

JBoss Modules uses a static module identifier (a `ModuleIdentifier` like `org.jboss.logging`) rather than a parent chain. Each module declares its dependencies; resolution is by *name*, not by parent walking. This avoids the linear "Minecraft launcher dependency hell" that parent-first can fall into.

## The JDK 9+ Module System

JEP 261 (module system at run time) reshapes class loading on the JVM. Every `ClassLoader` is associated with a `Module`; conversely, every `Module` has exactly one loader. The bootstrap loader owns `java.base`, the platform loader owns platform modules (`java.sql`, `java.xml`, etc.), the app loader owns the unnamed module that holds the classpath.

The `ClassLoader` API gained `ClassLoader::getNamedModule`, `Class::getModule`, and the `Layer` API. Class loading now flows through an additional check:

```
   loadClass("com.acme.Foo")
            │
            ▼
   Has the loader been told that its module exports com.acme?  ──► no, fail
            │
            ▼
   proceed to findClass
```

```
$ java --module-path mods -m com.acme.app/com.acme.app.Main
$ java --describe-module com.acme.app  # prints requires / exports / uses
$ jdeps --list-deps myapp.jar
```

The runtime image was reorganized too. Pre-9, you had `rt.jar` and `tools.jar` in `$JAVA_HOME/lib`; post-9 they are replaced by a JEP 220 *runtime image* — a single `lib/modules` file (`jrt:/` filesystem, accessible via `java.nio.file.FileSystems.newFileSystem(URI.create("jrt:/")))` for tooling. The `jimage` tool can list and extract entries:

```
$ jimage list $JAVA_HOME/lib/modules | head -20
$ jimage extract --dir=/tmp/extracted $JAVA_HOME/lib/modules
```

Module-path loading is still a class loader concept underneath — `jdk.internal.loader.ModuleLayerBuilder` creates `ModuleClassLoader` instances per layer.

## Common Pitfalls

- **Leaking loaders**: a `static` field somewhere holding a reference to a `ClassLoader` prevents it (and everything it loaded) from being GC'd. Tomcat famously warned about this; the fix is `Thread.currentThread().setContextClassLoader(...)` hygiene plus not stashing loaders in statics.
- **`Class.forName` and the context class loader**: `Class.forName(name)` uses the *calling* class's loader. `Thread.currentThread().getContextClassLoader()` is the recommended way for framework code that needs to load classes "from the user's perspective" — e.g. `ServiceLoader`.
- **`ServiceLoader` in modules**: post-9, `ServiceLoader.load(Foo.class)` walks `provides`/`uses` declarations in `module-info`, falling back to `META-INF/services/` files only for code in the unnamed module.
- **Reflection vs. classes**: `Class.forName(name, initialize, loader)` lets you skip `<clinit>` — useful when loading a class to inspect it without side effects.

## References

- JVMS Chapter 5 — Loading, Linking, and Initializing: <https://docs.oracle.com/javase/specs/jvms/se22/html/jvms-5.html>
- JVMS §4.10 — Verification of `class` Files: <https://docs.oracle.com/javase/specs/jvms/se22/html/jvms-4.html#jvms-4.10>
- JLS §12.4.1 — When Initialization Occurs: <https://docs.oracle.com/javase/specs/jls/se22/html/jls-12.html#jls-12.4.1>
- OpenJDK `ClassLoader.java` source with its full delegation dance: <https://github.com/openjdk/jdk/blob/master/src/java.base/share/classes/java/lang/ClassLoader.java>
- JEP 261 — Module System at Run-Time: <https://openjdk.org/jeps/261>
- JEP 220 — Modular Run-Time Images: <https://openjdk.org/jeps/220>
- JEP 320 — Remove the JDK and JRE Fab/Ext Mechanisms: <https://openjdk.org/jeps/320>
- JEP 463 — Launch Multi-File Source-Code Programs (uses the app loader context): <https://openjdk.org/jeps/463>
- OSGi Core specification, §3 (Module Lifecycle and Class Loading): <https://docs.osgi.org/specification/osgi.core/8.0.0/framework.module.lifecycle.html>
- OSGi "Class Loading and Visibility" deep dive: <https://blog.osgi.org/2011/10/osgi-and-java-modules-part-2.html>
- Tomcat 10 `WebappClassLoaderBase` documentation: <https://tomcat.apache.org/tomcat-10.1-doc/class-loader-howto.html>
- JBoss Modules user guide: <https://docs.jboss.org/author/display/MODULES/Home>
- Aleksey Shipilev on `ConstantValue` and `<clinit>` semantics: <https://shipilev.net/jvm/anatomy-quarks/>
