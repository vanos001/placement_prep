# Java Ecosystem and Tooling

## Overview

Java's ecosystem is among the largest in software: a mature build-tool landscape (**Maven**/**Gradle**), the industry-standard **Spring Boot** framework, **Hibernate** for ORM, **JUnit 5** for testing, and a new generation of cloud-native frameworks (**Quarkus**, **Micronaut**) built for GraalVM native images and Kubernetes. See [Java Overview](./README.md) and [JVM Internals](./jvm.md) for the language and runtime.

## Build Tools: Maven vs Gradle

| | **Maven** | **Gradle** |
|---|---|---|
| Style | XML (`pom.xml`), declarative, convention-over-configuration | Groovy/Kotlin DSL, programmable, task-based |
| Build speed | Slower (fixed lifecycle) | Faster (incremental, build cache, daemon) |
| Learning curve | Gentle, rigid | Steeper, flexible |
| Ecosystem | Huge (everything publishes POMs) | Huge (Maven-compatible) |
| Android | No | **Yes (default)** |
| When | Standard enterprise projects | Multi-module builds needing speed/flexibility |

Maven's **convention** (`src/main/java`, standard lifecycle) makes it the predictable default; Gradle's **flexibility and speed** win for large/complex builds.

```xml
<!-- pom.xml (Maven) -->
<dependencies>
  <dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>
  </dependency>
</dependencies>
```

```kotlin
// build.gradle.kts (Gradle)
plugins { java; id("org.springframework.boot") version "3.4.0" }
dependencies { implementation("org.springframework.boot:spring-boot-starter-web") }
```

## Web Frameworks (2026 landscape)

| Framework | Style | JVM startup | Native startup | Best fit |
|---|---|---|---|---|
| **Spring Boot 3.x/4** | Imperative + reactive (WebFlux) | ~1.9 s | ~100 ms | Enterprise, ecosystem depth, team familiarity |
| **Quarkus** | Imperative + reactive (Vert.x) | ~1.15 s | ~12–50 ms | Kubernetes-native, serverless, fast cold starts |
| **Micronaut** | Compile-time DI, reactive | ~0.65 s | ~25–50 ms | Serverless/Lambda, edge, low-memory |
| **Vert.x** | Reactive event-loop | ~0.3 s | ~20–50 ms | High-throughput event-driven services |
| **Helidon** | MicroProfile | ~0.7 s | ~30–70 ms | Jakarta EE / MicroProfile alignment |

### Spring Boot (the default)

"Convention over configuration" — auto-configuration, embedded server, starter dependencies, Actuator for ops, Spring Data for persistence, Spring Security for auth. The largest ecosystem by far; **62% of enterprise Java microservices** (2026 survey). See [Spring Boot](../../frameworks/spring-boot/README.md).

### Quarkus vs Micronaut (cloud-native challengers)

- **Quarkus** (Red Hat): **build-time** processing (native by design), first-class Kubernetes, Dev Services, Vert.x-reactive core. Cold starts ~12–50 ms natively — designed for scale-to-zero serverless.
- **Micronaut**: **compile-time dependency injection** (no reflection — none of Spring's runtime reflection), smallest footprint, excellent GraalVM native reliability; popular for Lambda and resource-constrained environments.

**Choose**: Spring Boot for enterprise breadth/familiarity; Quarkus for Kubernetes/serverless speed; Micronaut for the leanest native profile.

## Persistence: Hibernate and JPA

- **JPA** (Jakarta Persistence) is the standard ORM spec; **Hibernate** is the dominant implementation.
- **Spring Data JPA** adds repositories: `findByX`, `@Query`, pagination — CRUD without boilerplate.
- Watch for the classic **N+1 query problem**: use `@EntityGraph`, `JOIN FETCH`, or `@BatchSize` (see [the N+1 discussion in Django](../../frameworks/django/README.md) for the same problem in another stack).

```java
@Entity
@Table(name = "users")
public class User {
    @Id @GeneratedValue private Long id;
    private String name;
    // ...
}

public interface UserRepository extends JpaRepository<User, Long> {
    List<User> findByName(String name);
}
```

## Testing: JUnit 5 + Mockito

**JUnit 5** (Jupiter) is the standard: `@Test`, `@BeforeEach`, parameterized tests, extensions. **Mockito** mocks dependencies; **AssertJ** gives fluent assertions; **Testcontainers** spins up real Postgres/Redis in Docker for integration tests.

```java
@SpringBootTest
class UserServiceTest {
    @Autowired UserService service;
    @MockBean UserRepository repo;   // Mockito mock

    @Test
    void findsByName() {
        when(repo.findByName("Ada")).thenReturn(List.of(new User(1L, "Ada")));
        assertThat(service.findByName("Ada")).hasSize(1);
    }
}
```

## Networking and Performance Libraries

| Library | Role |
|---|---|
| **Netty** | High-performance async networking framework (the engine under many servers: gRPC-Java, Cassandra, Elasticsearch, Vert.x) |
| **Project Reactor / RxJava** | Reactive streams (WebFlux uses Reactor) |
| **Virtual threads** (Java 21+) | Lightweight threads that make blocking code scale — "closes the gap" for high-concurrency JVM services |
| **GraalVM native image** | AOT-compiled native binaries (~10× faster startup, lower memory) |

## Interview Questions

### Q: Maven vs Gradle — which and why?

Maven is XML-declarative with a rigid convention lifecycle — predictable and ubiquitous. Gradle is a programmable build (Groovy/Kotlin DSL) with incremental builds, a daemon, and build cache — faster for large/multi-module projects and required for Android. Choose Maven for standard enterprise projects and convention; Gradle when build speed/flexibility matter.

### Q: Spring Boot vs Quarkus vs Micronaut?

Spring Boot: largest ecosystem, best for enterprise teams with Spring expertise. Quarkus: build-time processing, native-by-design, ~12–50 ms cold starts — for Kubernetes/serverless. Micronaut: compile-time DI (no reflection), smallest footprint — for Lambda/edge. All support GraalVM native; the trade-off is ecosystem depth (Spring) vs startup/memory (Quarkus/Micronaut).

### Q: What is the N+1 query problem in Hibernate?

Loading N parent entities then accessing a lazy relation per entity issues N+1 queries. Fixes: `JOIN FETCH`/`@EntityGraph` to eager-fetch in one query, `@BatchSize` to batch lazy loads, or `@NamedEntityGraph`. Same problem exists in every ORM (see the Django page for a parallel).

### Q: How do virtual threads change Java concurrency?

Virtual threads (Java 21+) are lightweight threads managed by the JVM rather than the OS — you can launch millions, and blocking I/O on one no longer consumes an OS thread. This lets classic blocking code (servlets, JDBC) scale to high concurrency without rewriting reactive, so "platform threads + virtual threads" closes much of the gap with reactive frameworks.

### Q: What is Netty and where does it appear?

Netty is an asynchronous event-driven networking framework providing NIO-based servers/clients with high performance and low memory. It's the engine beneath gRPC-Java, Cassandra, Elasticsearch, and Vert.x — so "what powers this server's I/O?" often traces back to Netty.

## References

- Maven — https://maven.apache.org/
- Gradle — https://gradle.org/
- Spring Boot — https://spring.io/projects/spring-boot
- Quarkus — https://quarkus.io/
- Micronaut — https://micronaut.io/
- Hibernate ORM — https://hibernate.org/
- JUnit 5 — https://junit.org/junit5/
- Netty — https://netty.io/

## Related Topics

- [Java Overview](./README.md) — the language
- [JVM Internals](./jvm.md) — class loading, GC, JIT
- [Java Garbage Collection](./gc.md) — the runtime memory model
- [Spring Boot](../../frameworks/spring-boot/README.md) — the framework deep dive
- [Backend Engineering](../../backend/README.md) — services built on this stack
