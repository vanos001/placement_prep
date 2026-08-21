# Testcontainers

## Overview

Testcontainers is an open-source library (Java/JVM, .NET, Go, Python, Rust, Node.js, Haskell) that spins up real third-party services — PostgreSQL, MySQL, Kafka, Redis, Elasticsearch, Localstack, anything that runs in Docker — as Docker containers, scoped to the lifetime of a single test or test class. It is the modern answer to the question that has haunted integration testing for two decades: how do you test against a real database, a real message broker, a real S3, without either sharing a flaky central QA database or hand-rolling per-developer Docker setup. The library manages the Docker lifecycle (pull, start, wait for healthy, expose a mapped port, run the test, stop and remove), the test framework integrates the lifecycle via annotations (JUnit, pytest, Go testing), and every test gets a clean, isolated, real instance. The project, started by Richard North in 2017, is now part of the CNCF sandbox; https://www.testcontainers.org.

The case for Testcontainers is the failure mode of the alternatives. **In-memory databases** (H2, HSQLDB, SQLite) lie: their SQL dialect, type system, transaction semantics, and concurrency behavior differ from the production database. Tests pass against H2 and fail against Postgres in production. **Shared test databases** are slower, mutate state, and require team coordination. **Mocked repositories** don't test SQL, don't catch `n+1` query bugs, don't surface transaction-isolation anomalies. Testcontainers gives you a real PostgreSQL 16, a real Kafka 3.7, a real Redis 7, on every test run, with the cost of a few seconds per container startup — and with reuse mode, even that cost is amortized.

## The Container Lifecycle

A Testcontainers-managed container follows a strict lifecycle synchronized to the test's lifetime:

```
  test class @Container                   JUnit lifecycle
       |                                        |
       v                                        v
+----------------+    setup  +--------------------+
| start container| <------- | @BeforeAll         |
| (pull image if  |          |  (or @BeforeEach   |
|  not cached)    |          |   for per-test)    |
+--------+--------+          +---------+----------+
         |
         v
+----------------+    wait   +--------------------+
| wait for healthy| <------ | WaitStrategy        |
| (port listening,|          | .forListeningPort  |
|  log line, HTTP)|          | .forLogMessage      |
|                 |          | .forHttp(...)        |
+--------+--------+          +---------+----------+
         |
         v
+----------------+  expose  +--------------------+
| mapped host port| <------ | Container         |
| 127.0.0.1:33107 |          | .getHost()        |
+--------+--------+          | .getFirstMappedPort()|
         |                  +---------+----------+
         v
+----------------+  test    +--------------------+
| run @Test       | <------ | your test code     |
| against the     |          | talks to the      |
| container's port|          | container via     |
+--------+--------+          | JDBC/HTTP/etc.    |
         |                  +---------+----------+
         v
+----------------+ teardown +--------------------+
| stop + remove  | <------- | @AfterAll           |
| (or persist if  |          | (or @AfterEach)    |
| reuse=true)    |          |                    |
+----------------+          +--------------------+
```

The cycle is the same regardless of container type. What varies is the `WaitStrategy` — a Postgres container is ready when the log line `database system is ready to accept connections` appears; a Kafka container is ready when the broker's `/` endpoint returns 200; an Elasticsearch container is ready when the cluster status is yellow. Testcontainers ships with `Wait.forLogMessage`, `Wait.forListeningPort`, `Wait.forHttp`, and a few more; you can write your own.

The minimum Java example, using the JUnit 5 integration:

```java
import org.junit.jupiter.api.Test;
import org.testcontainers.containers.PostgreSQLContainer;

class PlainPostgresTest {

    static PostgreSQLContainer<?> postgres =
        new PostgreSQLContainer<>("postgres:16-alpine")
            .withDatabaseName("testdb")
            .withUsername("test")
            .withPassword("test");

    static {
        postgres.start();   // container starts once, JVM-shutdown hook stops it
    }

    @Test
    void canQueryVersion() throws Exception {
        try (var c = java.sql.DriverManager.getConnection(
                postgres.getJdbcUrl(),
                postgres.getUsername(),
                postgres.getPassword())) {
            var rs = c.createStatement().executeQuery("SELECT version()");
            rs.next();
            System.out.println(rs.getString(1));  // PostgreSQL 16.x ...
        }
    }
}
```

Note the JDBC URL `getJdbcUrl()` returns: it is `jdbc:postgresql://localhost:33107/testdb` (or similar), where `33107` is a randomly allocated host port mapped to the container's `5432`. Testcontainers uses the Docker API to discover this port at runtime; you should never hard-code it.

## The @Testcontainers Annotation (JUnit 5)

The JUnit 5 integration uses JUnit's extension model. The `@Testcontainers` annotation on the test class registers a `TestcontainersExtension` that scans for fields annotated `@Container` and manages their lifecycle. Static fields are started once for the whole class (`@BeforeAll`); instance fields are started per test (`@BeforeEach`).

```java
import org.junit.jupiter.api.Test;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.containers.PostgreSQLContainer;

@Testcontainers
class LifecycleTest {

    @Container                       // static field  -> class-level lifecycle
    static PostgreSQLContainer<?> pg =
        new PostgreSQLContainer<>("postgres:16-alpine");

    @Container                       // instance field -> per-test lifecycle
    GenericContainer<?> redis =
        new GenericContainer<>("redis:7-alpine").withExposedPorts(6379);

    @Test
    void test1() {
        // pg is up; redis for this test only
    }

    @Test
    void test2() {
        // pg is still up; a *new* redis is up
    }
}
```

`@Container` is the JUnit 5 mechanism. The Testcontainers extension calls `start()` on the container before the test (or before the class, for static fields) and `stop()` after. For shared, cross-class lifecycle, use a `SingletonContainer` base class:

```java
public abstract class SharedPostgres {
    static final PostgreSQLContainer<?> PG =
        new PostgreSQLContainer<>("postgres:16-alpine");
    static { PG.start(); }
    // PG is reused by every subclass in the JVM; never stopped until JVM exits
}
```

The Spring Boot integration (3.1+) takes the annotation approach one step further. `@ServiceConnection` on a `@Container` field tells Spring Boot to wire that container as the named service connection — properties like `spring.datasource.url` are auto-populated at runtime; no YAML, no `@DynamicPropertySource`. This is the recommended modern pattern.

```java
@SpringBootTest
@Testcontainers
class SpringBootWithContainersTest {

    @Container
    @ServiceConnection                       // Spring auto-wires DataSource
    static PostgreSQLContainer<?> pg =
        new PostgreSQLContainer<>("postgres:16-alpine");

    @Autowired
    CustomerRepository repository;

    @Test
    void repositoryPersistsAndQueries() {
        repository.save(new Customer("Alice"));
        assertEquals(1, repository.count());
    }
}
```

## Container Types

Testcontainers ships with two layers: the **typed modules** (PostgreSQLContainer, MySQLContainer, KafkaContainer, ElasticsearchContainer, LocalstackContainer, GenericRedis, etc.) that know about each image's startup behavior and configuration; and **GenericContainer**, the escape hatch for any Docker image.

| Container Type | Image | What You Get | Notes |
|-----------------|-------|--------------|------|
| `PostgreSQLContainer` | `postgres:N` | JDBC URL, username, password, database | Type-coerced; ready when log says "ready to accept connections" |
| `MySQLContainer` | `mysql:N` | Same shape as PostgreSQL | Newer versions need `withUrlParam("useSSL", "false")` |
| `MariaDBContainer` | `mariadb:N` | Same shape as MySQL | — |
| `OracleContainer` | `gvenzl/oracle-xe:N` | Same shape | Faster image available; default XEPDB1 |
| `MSSQLServerContainer` | `mcr.microsoft.com/mssql/server` | JDBC URL | License-acceptance env var |
| `KafkaContainer` | `confluentinc/cp-kafka` | Bootstrap servers | Includes Zookeeper or uses KRaft mode |
| `GenericContainer` | any | Host + port + start/stop | Use `withExposedPorts`, `withEnv`, `withCommand` |
| `DockerComposeContainer` | `docker-compose.yml` | All services in the compose file | Compose V1 via `LOCAL_GIT_HASH=...`; or Compose V2 |

`GenericContainer` is the escape hatch. Any Docker image becomes a test fixture:

```java
GenericContainer<?> nginx =
    new GenericContainer<>("nginx:alpine")
        .withExposedPorts(80)
        .waitingFor(Wait.forHttp("/").forStatusCode(200));

@Test
void nginxServesIndex() throws Exception {
    String url = "http://" + nginx.getHost() + ":" + nginx.getFirstMappedPort();
    int code = HttpClient.newHttpClient()
        .send(HttpRequest.newBuilder(URI.create(url)).build(),
              HttpResponse.BodyHandlers.ofString()).statusCode();
    assertEquals(200, code);
}
```

`DockerComposeContainer` runs a compose file:

```java
DockerComposeContainer<?> env =
    new DockerComposeContainer<>(new File("docker-compose.yml"))
        .withExposedService("db", 5432)
        .withExposedService("redis", 6379)
        .withPull(false);
env.start();
String dbHost = env.getServiceHost("db", 5432);
Integer dbPort = env.getServicePort("db", 5432);
```

Compose mode is useful for end-to-end testing of multi-service topologies, but the typing is weaker (no JDBC URL helpers, no `withDatabaseName`), and startup is slower. Prefer the typed module where one exists.

## Reuse Mode

Each container startup is a fresh Docker pull (or layer cache hit) plus a container boot — 1–5 seconds for Postgres, 5–15 seconds for Kafka, longer for Elasticsearch. For a 200-test suite this adds minutes to every CI run, and worse, minutes to every local `mvn test`. Reuse mode mitigates this by keeping a container running between test runs — the container is started once and **not** stopped at the end of the test class, surviving across the JVM. Subsequent test runs discover the existing container and reuse it.

```java
PostgreSQLContainer<?> pg =
    new PostgreSQLContainer<>("postgres:16-alpine")
        .withReuse(true);                       // opt in per container
```

```
Run 1 (mvn test):
  + docker pull postgres:16-alpine      (one-time)
  + docker run -d postgres:16-alpine... (mapped port 33107)
  + run tests
  + JVM exits; container stays (because reuse=true)
Run 2 (mvn test):
  + discover existing container (matched by reuse ID)
  + reuse mapped port 33107
  + run tests
  + container stays
```

Reuse is **off by default** and must be enabled both per-container (`withReuse(true)`) and globally (`~/.testcontainers.properties` containing `testcontainers.reuse.enable=true`). The opt-in is two-level because reusing a Postgres container across test runs means leftover data — your tests must be idempotent, must drop and recreate schema per run, must not assume a clean DB.

Reuse trades isolation for speed. It is the right choice for local development (where the dev wants speed) but the wrong choice for CI (where a stale container can mask a real bug). Teams typically enable reuse only on developer machines.

## The JDBC URL Magic

A second, older integration mode is the "JDBC URL magic." Instead of explicitly starting a `PostgreSQLContainer` and wiring its URL into your JDBC connection, you put a magic marker in the JDBC URL itself: `jdbc:tc:postgresql:16-alpine:///testdb`. Testcontainers' JDBC driver intercepts the `tc:` scheme, starts a container, swaps the URL for the real one (`jdbc:postgresql://localhost:33107/testdb`), and hands the real URL to the underlying driver. Your test code is unchanged.

```java
// application-test.yml
spring:
  datasource:
    url: jdbc:tc:postgresql:16-alpine:///testdb
    driver-class-name: org.testcontainers.jdbc.ContainerDatabaseDriver
```

```java
@Test
void queryWorks() throws Exception {
    // DriverManager.getConnection("jdbc:tc:postgresql:16-alpine:///testdb")
    // automatically starts a Postgres container and returns a real Connection
    // pointing at it.
}
```

The `tc:` prefix is the magic. The URL is `jdbc:tc:<image>:<tag>:///<databasename>?<options>`. The driver accepts extra options: `?TC_MYTESTVAR=value` sets env vars on the container; `?TC_TMPFS=/var/lib/postgresql/data:rw` mounts tmpfs.

| URL Form | Effect |
|----------|--------|
| `jdbc:tc:postgresql:16-alpine:///testdb` | Start Postgres 16 alpine, database `testdb` |
| `jdbc:tc:mysql:8:///db?TC_MYTESTVAR=foo` | Start MySQL 8, database `db`, env var `MYTESTVAR=foo` in container |
| `jdbc:tc:postgresql:16-alpine:///db?TC_TMPFS=/var/lib/postgresql/data:rw` | Start Postgres with tmpfs-backed data (faster, ephemeral) |

JDBC URL magic is convenient but has limits: it works only for database-style containers (the ones for which a `jdbc:` driver exists), it doesn't expose container ports for non-JDBC uses, and it can't be combined with reuse mode (the driver doesn't have a stable container reference to mark reusable). The `@Container` + `@ServiceConnection` pattern in Spring Boot 3.1+ is the modern, more flexible replacement; JDBC URL magic remains useful for quick one-liners and legacy configs.

## Comparison to H2 / In-Memory Databases

The temptation with in-memory databases is that they're fast (sub-second startup), need no Docker, and "just work" for 95% of tests. The cost is the 5% that quietly fail in production.

| Dimension | H2 (in-memory) | Testcontainers (real Postgres) |
|------------|----------------|--------------------------------|
| **Startup time** | <100 ms | 1–3 s (or 0 s with reuse) |
| **SQL dialect** | H2's, often slightly different | Real Postgres SQL |
| **Type system** | H2 type coercion (subtle bugs) | Real Postgres types (`numeric`, `timestamptz`, `jsonb`) |
| **Concurrency** | Single-connection by default | Real MVCC, real locking |
| **Index behavior** | Different query plans | Same query planner, same plans |
| **JSON / `jsonb` / `tsrange`** | None or partial | First-class |
| **Stored procedures, triggers** | Limited | Full PL/pgSQL |
| **CI cost** | None (no Docker) | Docker daemon required |
| **Setup per test** | Trivial (drop + recreate) | Trivial (drop + recreate) |
| **Risk of false positives** | Low (permissive) | Matches production |
| **Risk of false negatives** | High (passes locally, fails in prod) | Low |

The canonical failure pattern is: tests pass against H2 because H2 accepts a SQL syntax that Postgres rejects; or H2's NULL ordering differs; or H2 doesn't enforce a foreign key the way Postgres does; or the production app relies on `jsonb` and H2 doesn't have it. None of these is caught by H2; all are caught by Testcontainers with a real Postgres image. The 1–3-second startup cost is paid per test class (with `@BeforeAll`) or amortized to zero (with reuse) and is dramatically cheaper than the debugging time when a test passes locally and fails in production.

The defensive recommendation is **both**: use H2 for the bulk of fast unit tests of repository logic; use Testcontainers with real Postgres for the slower suite that catches dialect, type, and concurrency bugs. The two suites run in different phases of CI — H2 in every PR's fast test job, Testcontainers in the integration job that gates merges to main.

## Pitfalls and Best Practices

- **Don't use a fixed tag in the JDBC URL without an explicit registry.** `jdbc:tc:postgresql:///db` pulls `latest`, which can drift. Pin to a specific version (`postgresql:16-alpine`), and pin the same version in production.
- **Use `@BeforeAll` for static containers when possible.** One container per test class is much cheaper than one container per test, and most tests don't need a clean database — they need a clean schema, which you can drop and recreate.
- **Always use a `WaitStrategy`.** The default is `forListeningPort`, which is insufficient for databases that accept connections before being ready. Postgres needs `forLogMessage(".*database system is ready to accept connections.*", 1)`; Kafka needs `forHttp("/")`; Elasticsearch needs a cluster-status check.
- **Set resource limits.** A test container can eat memory; CI machines with 50 parallel jobs and unlimited containers will OOM. Use `.withCreateContainerCmdModifier(c -> c.getHostConfig().withMemory(512 * 1024 * 1024L))` or compose-level limits.
- **Beware Docker-in-Docker in CI.** Most CI providers (GitHub Actions, GitLab CI, CircleCI) support Docker natively. Some (Jenkins on Kubernetes without DinD) don't — install a DinD sidecar or use `KubernetesRunner`.
- **Reset state, don't restart containers.** Drop and recreate the schema in `@BeforeEach` (Flyway/Liquibase); don't stop and start the container per test.
- **Enable reuse only locally.** `~/.testcontainers.properties` with `testcontainers.reuse.enable=true` is a per-developer setting; do not commit it. CI should run with reuse off so containers are fresh.
- **Use `@ServiceConnection` over `@DynamicPropertySource`.** The Spring Boot 3.1+ pattern is shorter, type-safe, and handles multiple containers cleanly. `@DynamicPropertySource` works but is verbose and error-prone.
- **Don't test third-party images.** Don't write a test that asserts "Redis 7 increments keys correctly" — trust the image. Test *your* code against the image.
- **Watch Ryuk.** Testcontainers runs a reaper container (`ryuk`) that cleans up leftover containers when the JVM exits uncleanly. If you see "ryuk failed to start" warnings, your Docker socket permissions are wrong (common on Linux without rootless Docker).

## Interview Questions

**Q1: What is Testcontainers and what problem does it solve?**
A: A library that spins up real third-party services (Postgres, Kafka, Redis, etc.) as Docker containers scoped to the lifetime of a test. It solves the brittleness of in-memory databases (whose behavior differs from production), the slowness and state-mutation problems of shared QA databases, and the manual-setup cost of per-developer Docker. Each test gets an isolated, real instance with a mapped host port; the library handles start, wait-for-healthy, and stop.

**Q2: Describe the container lifecycle under the JUnit 5 integration.**
A: The `@Testcontainers` extension scans for `@Container` fields. Static fields are started in `@BeforeAll` and stopped in `@AfterAll` (class-level lifecycle, shared across all tests in the class). Instance fields are started per test (`@BeforeEach`/`@AfterEach`). The container's `WaitStrategy` blocks until the service is ready (log line, HTTP, port). The test code reads the host and mapped port via `getHost()` and `getFirstMappedPort()` and connects as if to any external service.

**Q3: What does the `jdbc:tc:` URL do, and when would you use it?**
A: `jdbc:tc:postgresql:16-alpine:///testdb` is a magic URL handled by Testcontainers' JDBC driver. The driver intercepts the `tc:` scheme, starts a Postgres 16 container, swaps the URL for the real one (`jdbc:postgresql://localhost:<mapped>/testdb`), and hands it to the underlying driver. Useful for quick configs and legacy apps; less flexible than `@Container` + `@ServiceConnection` because it only works for JDBC-style containers and can't combine with reuse.

**Q4: What is Testcontainers reuse mode and what are its trade-offs?**
A: An opt-in (per-container `withReuse(true)` plus global `testcontainers.reuse.enable=true`) that keeps a container running between test runs — the container is started once, JVM exits, container stays, next test run discovers and reuses it. Trade-off: dramatically faster local dev (seconds → milliseconds) but breaks isolation (leftover data). Use locally, not in CI; tests must be idempotent and reset schema per run.

**Q5: Why prefer Testcontainers over H2 for integration tests?**
A: H2 lies. Its SQL dialect, type system, NULL semantics, concurrency, and JSON support all differ from Postgres/MySQL. Tests pass against H2 and fail in production. Testcontainers gives you real Postgres with a few seconds of startup, amortized to zero with reuse. The 5% of tests that fail in production because of dialect differences is dramatically more expensive than the seconds saved by H2. The defensive pattern is both: H2 for fast unit-level repository tests, Testcontainers for the integration suite that catches dialect, type, and concurrency bugs.

**Q6: How does Spring Boot 3.1's `@ServiceConnection` simplify Testcontainers?**
A: Annotating a `@Container` field with `@ServiceConnection` tells Spring Boot to wire that container as the named service connection — `spring.datasource.url`, `spring.data.redis.host`, etc. are auto-populated at runtime based on the container type. No YAML, no `@DynamicPropertySource`. The container's image tag determines the connection; Spring handles the rest.

## References

- [Testcontainers documentation](https://www.testcontainers.org/) — the canonical reference; quickstarts and module list
- [Testcontainers GitHub](https://github.com/testcontainers) — the org with repos for the Java, Go, .NET, Node.js, Python, Rust ports
- [Spring Boot Testcontainers documentation](https://docs.spring.io/spring-boot/docs/current/reference/html/features.html#features.testing.testcontainers) — the `@ServiceConnection` integration introduced in 3.1
- [Testcontainers JDBC URL reference](https://java.testcontainers.org/modules/databases/jdbc/) — the `jdbc:tc:` scheme, options, and limitations
- [Testcontainers reuse mode](https://java.testcontainers.org/features/reuse/) — `withReuse(true)`, `testcontainers.reuse.enable`, and the safety considerations
- [Testcontainers modules list](https://java.testcontainers.org/modules/) — the catalogue of typed container modules (Postgres, MySQL, Kafka, Elasticsearch, Localstack, etc.)
- [Testcontainers for Go](https://golang.testcontainers.org/) and [Testcontainers for Python](https://testcontainers-python.readthedocs.io/) — non-JVM ports
- See also: [Integration Testing](./integration-testing.md), [Contract Testing](./contract-testing.md), [Mocking](./mocking.md), [Test Strategy](./test-strategy.md)
