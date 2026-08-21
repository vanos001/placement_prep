# Spring Boot Internals

## Overview

**Spring Boot** is a convention-over-configuration layer on top of the Spring Framework that ships sensible defaults, an embedded HTTP server, and a runtime auto-configuration engine. The first 1.0 release shipped in April 2014 with the explicit goal of killing the ceremony around Spring: XML wiring, manual `web.xml` servlets, manual JAR dependency management. The mechanism is what matters here — Spring Boot does not throw away the Spring container, it programs it: it scans your classpath, decides what beans to instantiate, and wires them up before your `main()` returns. The auto-configuration engine (roughly 150 conditional `@Configuration` classes in `spring-boot-autoconfigure`) is the single most studied piece of Spring source.

The interesting internals are six things:

- The **`@SpringBootApplication`** composite annotation (a one-line replacement for `@Configuration` + `@EnableAutoConfiguration` + `@ComponentScan`).
- The **auto-configuration loading** mechanism, which changed between Spring Boot 2.x (`META-INF/spring.factories`) and 2.7+ (`META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`).
- The **Spring bean lifecycle** as the container drives it: instantiate → populate properties → aware callbacks → BeanPostProcessor before → `@PostConstruct` → `InitializingBean.afterPropertiesSet` → custom init → BeanPostProcessor after → destruction.
- The **`@Conditional*`** family, which decides which auto-configuration actually contributes beans at runtime.
- The **Actuator** endpoints: `/health`, `/info`, `/metrics` — production-grade introspection shipped with the framework.
- **Devtools** — the hot-reload workflow that turns restarts from multi-second container cold boots into sub-second JVM warm restarts.

This page closes with the runtime-vs-build-time contrast that defines Spring Boot's competition: Quarkus and Micronaut move most of this work to compile time.

> Related: [Java Overview](./README.md), [JVM Internals](./jvm.md), [JVM Classloader](./jvm-classloader.md), [Reactive Programming](./reactive-programming.md), [Quarkus and Micronaut](./quarkus-micronaut.md), [Java Concurrency Deep Dive](./java-concurrent-deep.md)

## The @SpringBootApplication Composite

```java
@SpringBootApplication  // <- this is three annotations
public class Application {
    public static void main(String[] args) {
        SpringApplication.run(Application.class, args);
    }
}
```

`@SpringBootApplication` is `@SpringBootConfiguration` (a synonym for `@Configuration`), `@EnableAutoConfiguration`, and `@ComponentScan` in a single meta-annotation. The interesting one is `@EnableAutoConfiguration`, which is itself meta-annotated with `@Import(AutoConfigurationImportSelector.class)`. That import selector is where the classpath-driven wiring happens.

## Auto-Configuration Loading

`AutoConfigurationImportSelector.selectImports()` is the heart of auto-configuration. The modern flow:

1. Load candidate auto-configuration class names from `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports` files on the classpath. Each entry is a fully-qualified `@Configuration` class.
2. Remove duplicates, apply `@AutoConfigureOrder`, `@AutoConfigureBefore`, `@AutoConfigureAfter` ordering hints.
3. Filter through `AutoConfigurationExcludeFilter` (driven by `spring.autoconfigure.exclude` properties) and through `@Conditional` annotations evaluated by `ConditionEvaluator`.
4. Return the surviving class names to Spring, which then registers them as `@Configuration` beans — and the regular `@Bean` factory methods inside them kick in.

```
spring-boot-autoconfigure-3.x.jar
  └── META-INF
       └── spring
            └── org.springframework.boot.autoconfigure.AutoConfiguration.imports
                  ↓ (one FQCN per line, e.g.)
                  org.springframework.boot.autoconfigure.web.servlet.WebMvcAutoConfiguration
                  org.springframework.boot.autoconfigure.jdbc.DataSourceAutoConfiguration
                  org.springframework.boot.autoconfigure.flyway.FlywayAutoConfiguration
                  ... ~150 entries ...
```

Before 2.7, the same content lived in `META-INF/spring.factories` under the key `org.springframework.boot.autoconfigure.EnableAutoConfiguration`. The split was deliberate: `spring.factories` had grown to carry many unrelated keys (auto-configuration, test listeners, failure analyzers); a dedicated file lets the framework skip loading every auto-config class when running in a context that only needs test listeners, and lets it read the file in O(n) instead of parsing a properties file. The old file is still supported for backwards compatibility in 3.x but emits deprecation warnings.

A minimal custom auto-configuration, complete:

```java
@AutoConfiguration
@ConditionalOnClass(PasswordEncoder.class)
@ConditionalOnProperty(prefix = "app.security", name = "enabled", havingValue = "true")
public class SecurityAutoConfiguration {

    @Bean
    @ConditionalOnMissingBean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }
}
```

Plus `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports` containing the FQCN. The class loads only if `PasswordEncoder` is on the classpath and `app.security.enabled=true`. If the user has declared their own `PasswordEncoder` bean anywhere, `@ConditionalOnMissingBean` short-circuits ours.

## @ComponentScan

`@ComponentScan` is not Spring Boot specific — it lives in `spring-context` — but Boot turns it on by default. The default scan root is the package of the class annotated with `@SpringBootApplication`, recursed downward. `@Component`, `@Service`, `@Repository`, `@Controller`, `@RestController`, `@Configuration`, `@ControllerAdvice` and JSR-330 `@Named` are detected.

Two subtleties interviewers love to probe:

- **Type filtering happens through `AnnotationTypeFilter`s** registered on `ClassPathBeanDefinitionScanner`. A custom `@ComponentScan(includeFilters = @Filter(type = CUSTOM, classes = MyTypeFilter.class))` lets you load classes that aren't annotated at all.
- **`BeanNameGenerator` defaults to `AnnotationBeanNameGenerator`**, which lower-cases the simple class name. Two classes named `FooController` in different packages will collide — the second registration silently overwrites the first. This is a frequent source of confusing `NoSuchBeanDefinitionException` in modular codebases.

## Bean Lifecycle

The full lifecycle from the container's perspective:

```
                       ┌───────────────────────────────────┐
                       │  BeanDefinition (factory state)    │
                       │  - class name                     │
                       │  - constructor args               │
                       │  - property values                │
                       │  - init / destroy methods         │
                       │  - scope (singleton/prototype/...) │
                       └─────────────┬─────────────────────┘
                                     │ instantiate
                                     ▼
                       ┌───────────────────────────────────┐
                       │  1. INSTANTIATE                    │
                       │  constructor or factory method     │
                       │  (this is where @Autowired on      │
                       │   constructor args is resolved;    │
                       │   circular deps throw unless       │
                       │   one side uses setter injection) │
                       └─────────────┬─────────────────────┘
                                     │ populate
                                     ▼
                       ┌───────────────────────────────────┐
                       │  2. POPULATE PROPERTIES            │
                       │  - @Autowired fields / setters    │
                       │  - @Value placeholders resolved    │
                       │  - @Resource, JSR-330 @Inject     │
                       │  - EnvironmentAware resolution    │
                       └─────────────┬─────────────────────┘
                                     │ aware
                                     ▼
                       ┌───────────────────────────────────┐
                       │  3. AWARE CALLBACKS                │
                       │  BeanNameAware                    │
                       │  BeanClassLoaderAware             │
                       │  BeanFactoryAware                 │
                       │  EnvironmentAware                 │
                       │  ResourceLoaderAware              │
                       │  ApplicationEventPublisherAware   │
                       │  MessageSourceAware               │
                       │  ApplicationContextAware          │
                       └─────────────┬─────────────────────┘
                                     │ bpp before
                                     ▼
                       ┌───────────────────────────────────┐
                       │  4. BeanPostProcessor              │
                       │     .postProcessBeforeInitialization│
                       │  (this is where @PostConstruct      │
                       │   is invoked by CommonAnnotationBPP)│
                       └─────────────┬─────────────────────┘
                                     │ init
                                     ▼
                       ┌───────────────────────────────────┐
                       │  5. INITIALIZE                     │
                       │  - @PostConstruct (already done)    │
                       │  - InitializingBean                │
                       │    .afterPropertiesSet()           │
                       │  - @Bean(initMethod = "init")      │
                       └─────────────┬─────────────────────┘
                                     │ bpp after
                                     ▼
                       ┌───────────────────────────────────┐
                       │  6. BeanPostProcessor              │
                       │     .postProcessAfterInitialization│
                       │  (this is where AOP proxies are     │
                       │   wrapped — e.g. @Transactional)   │
                       └─────────────┬─────────────────────┘
                                     │ ready
                                     ▼
                       ┌───────────────────────────────────┐
                       │  7. IN USE                         │
                       │  singleton lives for context life  │
                       │  (prototypes are handed back to     │
                       │   caller, not tracked for destroy) │
                       └─────────────┬─────────────────────┘
                                     │ context.close()
                                     ▼
                       ┌───────────────────────────────────┐
                       │  8. DESTROY                        │
                       │  - @PreDestroy                     │
                       │  - DisposableBean.destroy()        │
                       │  - @Bean(destroyMethod = "close")   │
                       └───────────────────────────────────┘
```

The observable consequence: `@PostConstruct` fires before `afterPropertiesSet` and before `initMethod`; `@PreDestroy` fires before `DisposableBean.destroy()`. AOP proxies (transactional, async, security, scopes) are applied between init and ready — which means a self-invocation inside a `@Transactional` method bypasses the proxy and the transaction is silently not started. This is the single most common Spring bug.

`BeanPostProcessor` is also the integration point for many Spring Boot features: `ConfigurationPropertiesBindingPostProcessor` binds `@ConfigurationProperties` objects; `AsyncAnnotationBeanPostProcessor` wraps `@Async` methods; `ScheduledAnnotationBeanPostProcessor` registers `@Scheduled` methods with the `TaskScheduler`.

## The @Conditional Family

| Annotation | What it checks | Typical use |
|------------|----------------|-------------|
| `@ConditionalOnClass` | Is a named class on the classpath? | Skip datasource config when no JDBC driver |
| `@ConditionalOnMissingClass` | Is a named class absent? | Provide a fallback when an optional lib isn't present |
| `@ConditionalOnBean` | Does the context contain a bean of type X? | Wire secondary beans only when their primary exists |
| `@ConditionalOnMissingBean` | Does the context lack a bean of type X? | Allow user overrides of defaults |
| `@ConditionalOnProperty` | Does a property match a value? | `spring.datasource.hikari.enabled=false` disables |
| `@ConditionalOnResource` | Is a classpath resource present? | Skip Flyway when no migrations folder |
| `@ConditionalOnWebApplication` | Is this a servlet or reactive web context? | Skip MVC config when running as batch CLI |
| `@ConditionalOnNotWebApplication` | The inverse | Disable web server when running as `CommandLineRunner` only |
| `@ConditionalOnExpression` | SpEL expression truthy | Compose multi-condition checks |
| `@ConditionalOnJava` | Java version range | Drop newer APIs on old JDKs |

`@ConditionalOnMissingBean` deserves special attention. It is the mechanism by which Spring Boot "opinions" can be overridden: the auto-configuration class `DataSourceAutoConfiguration` declares a `@Bean @ConditionalOnMissingBean DataSource dataSource(...)`, so the moment you define your own `@Bean DataSource customDs()` in any `@Configuration`, the framework steps back. The contract is that user beans win over defaults.

There is a subtle ordering hazard: `@ConditionalOnMissingBean` only inspects the beans that the container has already processed at the time the conditional is evaluated. If your configuration is ordered after the auto-configuration, your bean is registered later and the conditional evaluates true (nothing yet exists) — but Spring Boot handles this by deferring evaluation until the relevant phase, and `@AutoConfigureBefore` / `@AutoConfigureAfter` let authors enforce ordering. Forgetting this is a frequent cause of phantom "two `DataSource`s" errors.

## Actuator

`spring-boot-starter-actuator` adds an HTTP (or JMX) management interface backed by `Endpoints`. Each endpoint is a Spring bean implementing `Endpoint<T>` or, more commonly today, `@Endpoint` / `@ReadOperation` / `@WriteOperation` annotated. The defaults:

| Path | Endpoint | Description |
|------|----------|-------------|
| `/actuator/health` | `HealthEndpoint` | Aggregated health: DB, disk, ping, liveness, readiness. Returns `{"status": "UP"}` or `{"status": "DOWN", "details": {...}}` |
| `/actuator/info` | `InfoEndpoint` | Static build info from `META-INF/build-info.properties` or `info.*` properties |
| `/actuator/metrics` | `MetricsEndpoint` | Micrometer registry browse; `/actuator/metrics/jvm.memory.used?tag=area:heap` |
| `/actuator/loggers` | `LoggersEndpoint` | Browse and change logging levels at runtime |
| `/actuator/env` | `EnvironmentEndpoint` | Read Spring `Environment` sources |
| `/actuator/beans` | `BeansEndpoint` | List every bean with its scope, type, dependencies |
| `/actuator/configprops` | `ConfigurationPropertiesEndpoint` | All `@ConfigurationProperties` bindings |
| `/actuator/threaddump` | `ThreadDumpEndpoint` | Live thread dump (JSON or text) |
| `/actuator/heapdump` | `HeapDumpWebEndpoint` | Returns a HotSpot `.hprof` on the wire |
| `/actuator/prometheus` | `PrometheusScrapeEndpoint` | Prometheus exposition format |

Health is extensible with `HealthIndicator` beans:

```java
@Component
public class DownstreamHealthIndicator implements HealthIndicator {
    private final HttpClient http;
    public DownstreamHealthIndicator(HttpClient http) { this.http = http; }
    @Override
    public Health health() {
        try {
            int code = http.ping();
            return code == 200 ? Health.up().build()
                                : Health.down().withDetail("status", code).build();
        } catch (Exception e) {
            return Health.down(e).build();
        }
    }
}
```

Kubernetes liveness/readiness is built on this: `management.endpoint.health.probes.enabled=true` exposes `/actuator/health/liveness` and `/actuator/health/readiness` and Spring Boot wires them to the application lifecycle so a crashed event loop reports DOWN before the liveness probe picks it up. Metrics flow through Micrometer, so the same code publishes to Prometheus, Datadog, New Relic, CloudWatch, or any of ~15 backends.

## Devtools

`spring-boot-devtools` is the development-time hot-reload workflow. It is not a Java agent and not a hot-swap engine — it does a smarter version of "restart the JVM".

The mechanism:

1. Devtools registers a `LiveReload` server on port 35729 and a `/actuator/restart` endpoint.
2. When a classpath change is detected (filesystem watcher), devtools triggers a `SpringApplication` restart.
3. Restart is fast (~1 s on a small app) because devtools loads the user's `@ComponentScan` classes in a **throwaway classloader** that is disposed on restart. The framework classes (`spring-boot-autoconfigure`, the Tomcat embed, JDBC pools, etc.) are loaded once by the parent classloader and never reloaded — only the user code is.
4. Trigger conditions: compile → new `.class` file appears on disk → watcher fires. In IntelliJ, `Build → Build Project` (or the auto-build-on-save setting) is the trigger; in Eclipse, the auto-compile setting. VS Code with `java.autobuild.enabled=true` works the same way.

What is NOT reloaded: parent classloader resources, anything annotated `@Reloadable` is honored (rare), static resources handled by `ResourceHttpRequestHandler` when `spring.web.resources.cache.period=0` (the dev default). The JVM hot-swap (method body change only) is layered underneath for class bodies that haven't been recompiled; for method signature changes the devtools restart is required.

Devtools is excluded from fat JARs in production by default — `spring-boot-maven-plugin` omits it from repackaged JARs unless `excludeDevtools=false` is set, which you should not set in production.

## Runtime vs Build-Time: Spring Boot vs Quarkus vs Micronaut

The central architectural contrast:

| Concern | Spring Boot | Quarkus | Micronaut |
|---------|-------------|---------|-----------|
| When DI graph is built | Runtime (bean factory) | Build time (Substrate + Quarkus extensions) | Compile time (annotation processor) |
| Reflection | Heavy (DI, serialization, config binding) | None at runtime by default; precomputed at build | None — constructor injection, no reflection |
| Startup (small service) | ~3 s | ~30 ms (native) / ~1 s (JVM) | ~100 ms (native) / ~1 s (JVM) |
| Memory at rest | ~250 MB RSS | ~25 MB native | ~50 MB native |
| Hot reload | Devtools classloader swap (~1 s) | Quarkus DevUI continuous testing (~200 ms) | Micronaut Incremental |
| GraalVM native | Supported via Spring Native (maturing in 3.x, `native-build-plugin`) | First-class since 1.0 | First-class since 1.0 |

The takeaway: Spring Boot's runtime DI graph is the source of its developer ergonomics (you can override a bean and immediately see it everywhere via context refresh), but it is the same runtime DI graph that costs the first 2-3 seconds of startup. Quarkus and Micronaut trade that off: they pre-compute everything at build time, so runtime work is "wire up the 30 beans from a generated table" — fast, but you cannot change the bean graph at runtime. For a serverless Lambda that starts 10×/minute, the cost dominates; for a monolith that runs for 30 days, nobody cares. See [Quarkus and Micronaut](./quarkus-micronaut.md) for the deep dive on the build-time side.

## Interview Questions

**Q: How does `@SpringBootApplication` work?**
It is a composite meta-annotation combining `@SpringBootConfiguration` (= `@Configuration`), `@EnableAutoConfiguration` (which imports `AutoConfigurationImportSelector`), and `@ComponentScan` with default base package = the annotated class's package. Equivalent to the three written separately.

**Q: What is the difference between `spring.factories` and `AutoConfiguration.imports`?**
Both carry auto-configuration class names. `spring.factories` is a flat properties file with many unrelated keys (autoconfig, failure analyzers, test listeners, etc.) and is loaded eagerly. `AutoConfiguration.imports` (since 2.7) is a plain text file with one FQCN per line, dedicated to auto-configuration only; it loads lazily and is faster to scan. The old file is supported but deprecated in 3.x.

**Q: What is `@ConditionalOnMissingBean` and why is it important?**
A `@Conditional` that means "register this bean only if no bean of the same type is already in the context". It is the cornerstone of Spring Boot's "opinionated defaults that you can override" design: declare your own `DataSource` and the framework's `DataSourceAutoConfiguration` quietly steps back. The ordering hazard: the conditional only sees beans already processed when it evaluates, so `@AutoConfigureBefore` / `@AutoConfigureAfter` is sometimes needed.

**Q: What are the bean lifecycle phases in order?**
Instantiate → Populate properties → Aware callbacks (`BeanNameAware` ... `ApplicationContextAware`) → `BeanPostProcessor.postProcessBeforeInitialization` (this is where `@PostConstruct` is invoked by `CommonAnnotationBeanPostProcessor`) → `InitializingBean.afterPropertiesSet()` and custom `initMethod` → `BeanPostProcessor.postProcessAfterInitialization` (AOP proxy wrapping) → ready → ... → `@PreDestroy` → `DisposableBean.destroy()` → custom `destroyMethod`.

**Q: Why does self-invocation of a `@Transactional` method not start a transaction?**
Because the transactional behavior is implemented by a JDK dynamic proxy or CGLIB subclass wrapped in step 6 (`BeanPostProcessor.postProcessAfterInitialization`). A call `this.otherMethod()` from inside the bean bypasses the proxy entirely and goes straight to the original method. Fix: split into two beans, or self-inject the proxy (`@Autowired private Foo self; self.otherMethod();`), or use AspectJ load-time weaving which is byte-code-level.

**Q: What does the Actuator health endpoint aggregate?**
All `HealthIndicator` beans in the context. Each contributes a status (`UP`, `DOWN`, `OUT_OF_SERVICE`, `UNKNOWN`) and optional details. The aggregator reduces per `HealthStatusAggregator` (default: `SimpleHttpCodeStatusMapper` — any `DOWN` ⇒ overall `DOWN`, returns 503). Liveness and readiness groups are separate sub-paths since Boot 2.3+.

**Q: How does Spring Boot Devtools restart differ from JVM hot-swap?**
Hot-swap (JVM agent) replaces method bodies in place; it cannot add methods or fields. Devtools restarts the whole user application context in a throwaway classloader; the parent classloader holding framework classes stays loaded, so the cost is "reload user beans" rather than "cold start JVM". Typical restart is ~1 s versus 5-15 s for a full JVM cold start.

## Cross-References

- [Java Overview](./README.md)
- [JVM Internals](./jvm.md) — classloading model that Devtools relies on
- [JVM Classloader](./jvm-classloader.md) — parent-child loader scheme leveraged by Devtools
- [Reactive Programming](./reactive-programming.md) — WebFlux, the reactive sibling of Spring MVC
- [Quarkus and Micronaut](./quarkus-micronaut.md) — the build-time competitors
- [Java Concurrency Deep Dive](./java-concurrent-deep.md) — `@Async` and `@Scheduled` thread pools

## References

- Spring Boot Reference Documentation — https://docs.spring.io/spring-boot/index.html
- Spring Boot — Auto-configuration — https://docs.spring.io/spring-boot/docs/current/reference/html/using.html#using.auto-configuration
- Spring Framework — `BeanPostProcessor` Javadoc — https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/beans/factory/config/BeanPostProcessor.html
- Spring Framework — IoC container lifecycle — https://docs.spring.io/spring-framework/reference/core/beans/dependencies/factory-collaborators.html
- Baeldung — Spring Boot Auto-Configuration — https://www.baeldung.com/spring-boot-custom-starter
- Baeldung — Spring Bean Lifecycle — https://www.baeldung.com/spring-bean-lifecycle
- Spring Initializr — https://start.spring.io/
- Spring Boot Actuator Endpoints — https://docs.spring.io/spring-boot/docs/current/actuator/html/
- Spring Boot Devtools — https://docs.spring.io/spring-boot/docs/current/reference/html/using.html#using.devtools
