# Contract Testing

## Overview

Contract testing is a technique for managing the integration boundary between two services that communicate over a network. Instead of running both services end-to-end (expensive, brittle, slow), each side is tested in isolation against a small machine-checkable description of the expected interaction called a **contract**. The consumer writes the contract from its own perspective — "here is the request I send and the response I require" — and the provider verifies that its implementation honors that contract. If both sides agree on the contract and both pass their tests, integration can be assumed to work without an end-to-end run. This inversion — consumer first, provider verifies — is called **consumer-driven contract testing** (CDC), and it is the central idea of the technique.

Martin Fowler's 2006 article *Consumer-Driven Contracts* reframed the conversation around the integration test pyramid. End-to-end integration tests, he argued, are the most expensive tests you can write: they require both services up, network, databases, real auth, and they break for any one of a dozen reasons unrelated to whether the contract is honored. CDC replaces them with two cheap, fast, isolated tests that share a contract artifact. In a microservices deployment where a single service may have thirty consumers, this difference compounds: end-to-end tests of every consumer–provider pair become combinatorially infeasible, while contract tests remain linear in the number of pairs.

The dominant framework is **Pact**, originally written in Ruby by Pete Bangham (Realestate.com.au, 2013) and now ported to JVM, JS, .NET, Go, Python, Rust, Swift, PHP, and Kotlin. **PactFlow** (Smartbear) is the commercial hosted broker with SSO, role-based access, and verification webhooks. The protocol — consumer writes pact, pact is published to a broker, broker notifies the provider, provider runs `pact verify` against its own implementation — is the same across implementations.

## Consumer-Driven Contracts: The Idea

A contract has three parts:

1. **Request** — what the consumer will send (method, path, headers, body).
2. **Expected response** — what the consumer requires back. Crucially, the consumer specifies only the *fields it uses* — not the entire response. The contract is a *subset specification*, intentionally under-specified, so the provider can add fields without breaking consumers.
3. **Matchers** — instead of literal expected values, the consumer specifies matchers (`matching(type)`, `like(42)`, `each-like({id: 1})`) that assert "the response must contain a field of this type at this path" without pinning a specific value. This is the *postel's law* principle: "be liberal in what you accept from others, conservative in what you send."

```
        Consumer                                    Provider
     +------------+                              +-------------+
     |  unit test |                              |  API impl   |
     |  writes a  |                              |             |
     |  pact file |                              |             |
     +-----+------+                              +------+------+
           |                                            |
           |  publish pact to broker                   |
           v                                            |
     +------------+                              +-----v------+
     |   Broker   | ----- can-i-deploy? ----->  |  verify    |
     |  (pactflow  | <---- verify result ------|  against   |
     |   or self- |                            |  provider  |
     |   hosted)   |                            |  impl      |
     +------------+                            +------------+
```

The flow runs twice in CI:

- **Consumer pipeline:** generate pact → publish to broker → ask broker "can I deploy?" (broker checks whether all consumers' pacts are currently verified by the provider) → deploy if yes.
- **Provider pipeline:** broker notifies provider on pact publish → provider pulls pact → runs `pact verify` against its own implementation → publishes verification result back to broker.

If both sides are green, the contract is honored and `can-i-deploy` returns true. If the consumer adds a new requirement, the provider's pipeline breaks before deployment — exactly the early-failure signal end-to-end tests give you, at a fraction of the cost.

## The Pact Framework

A consumer-side test in Pact-JVM looks like this. The consumer configures a mock provider on a random port, sets up expectations on the mock, makes its real production HTTP call against the mock, asserts on the response, and Pact captures the interaction into a JSON file.

```java
// build.gradle: testImplementation 'au.com.dius.pact.consumer:junit5:4.6.4'
import au.com.dius.pact.consumer.dsl.PactDslJsonBody;
import au.com.dius.pact.consumer.dsl.PactDslWithProvider;
import au.com.dius.pact.consumer.junit5.PactConsumerTestExt;
import au.com.dius.pact.consumer.junit5.PactTest;
import au.com.dius.pact.core.model.RequestResponsePact;
import au.com.dius.pact.core.model.annotations.Pact;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;

@ExtendWith(PactConsumerTestExt.class)
class UserClientContractTest {

    @Pact(consumer = "userClient")
    RequestResponsePact getUser(PactDslWithProvider builder) {
        return builder
            .given("user 42 exists")
            .uponReceiving("a request for user 42")
              .path("/users/42")
              .method("GET")
              .header("Accept", "application/json")
            .willRespondWith()
              .status(200)
              .body(new PactDslJsonBody()
                  .integerType("id", 42)            // must be an int, value 42
                  .stringType("name")               // must be a string, any value
                  .booleanType("active"))          // must be a bool
            .toPact();
    }

    @Test
    @PactTestFor(pactMethod = "getUser")
    void testGetUser(MockServer mockServer) {
        // Point the real client at the mock server
        var client = new UserClient(mockServer.getUrl());
        var user = client.getUser(42);
        assertEquals(42, user.id());
        assertNotNull(user.name());
    }
}
```

Pact generates `pacts/userClient-userService.json`, a JSON document containing the interaction, the matchers, and the provider state ("user 42 exists"). On the provider side, the JUnit runner reads the pact, starts the real provider (typically via Spring Boot's `@SpringBootTest` or via [Testcontainers](./testcontainers.md)), replays each request, and compares the response with the matchers:

```java
// build.gradle: testImplementation 'au.com.dius.pact.provider:junit5:4.6.4'
@ExtendWith(PactVerificationSpringProvider.class)
@PactVerification(value = "userClient")
@SpringBootTest(webEnvironment = RANDOM_PORT)
class UserServiceProviderPactTest {

    @TestTemplate
    @ExtendWith(PactVerificationInvocationContextProvider.class)
    void verifyPact(PactVerificationContext context) {
        context.verifyInteraction();
    }

    @State("user 42 exists")        // provider state setup method
    void createUser42() {
        repo.save(new User(42L, "Alice", true));
    }
}
```

The `@State` method is the provider's hook to set up the preconditions named in the pact. Pact calls it before replaying the request. This is the only place real state setup happens — there is no end-to-end network call.

## The Broker: Sharing Pacts Between Pipelines

Pact files must travel from the consumer's CI to the provider's CI. The **Pact Broker** is the artifact store and event hub. Self-hosted via Docker (`pactfoundation/pact-broker`) or via hosted PactFlow, the broker:

- Stores pacts, one per consumer+version+branch tag.
- Stores verification results, so a consumer can ask `can-i-deploy?` before deploying.
- Publishes webhooks: when a new pact arrives, the broker pings the provider's CI to run verification.
- Provides a matrix UI showing every consumer–provider pair and its verification status.
- Supports cross-version compatibility checks (the `pact broker can-i-deploy` command): before deploying consumer v2, ask the broker whether v2's pacts are verified against the version of the provider currently in production.

```bash
# consumer pipeline
pact-broker publish ./pacts \
  --consumer-version $GIT_SHA \
  --tag $BRANCH \
  --broker-base-url $BROKER_URL

# "Can I deploy consumer@sha to prod?"
pact-broker can-i-deploy \
  --pacticipant userClient \
  --version $GIT_SHA \
  --to-environment production \
  --broker-base-url $BROKER_URL

# provider pipeline (triggered by webhook)
pact-broker verify \
  --pacticipant=userService \
  --pacticipant-version=$GIT_SHA \
  --broker-base-url $BROKER_URL
```

The `can-i-deploy` gate is the broker's killer feature. It encodes a policy question — "is it safe to deploy this version of this service?" — into a single boolean the CI pipeline can gate on. The answer depends on whether every pact authored by the consumer is currently verified by the version of each provider that's deployed in the target environment. The broker tracks this matrix across time, so a previously-green verification stays green even as the contract evolves — until the consumer publishes a new pact, at which point a fresh verification is required.

## Comparison to Integration Testing

End-to-end integration tests bring both services up, drive a real HTTP call from one to the other, and assert on the combined behavior. They catch integration bugs but at a steep and growing cost as the system scales. CDC replaces them with two isolated tests, one per side.

| Dimension | End-to-End Integration | Contract Testing |
|-----------|------------------------|-------------------|
| **What is tested** | Both services up, real network call, real DB | Each side in isolation against a JSON contract |
| **Speed** | 5–30 seconds per test | <100 ms per interaction |
| **Stability** | Breaks when DB, network, auth, or either service changes | Breaks only when contract is violated |
| **Blast radius** | One pair per test, but \\(O(N^2)\\) tests for \\(N\\) services | Linear in pairs, runs in CI of each side independently |
| **Coverage** | Catches integration bugs the contract misses (timing, TLS, headers added by middleware) | Catches contract violations only |
| **Cost of false positive** | High (whole pipeline blocked on a real environment issue) | Low (violation points to a specific field in a specific contract) |
| **What it does NOT catch** | (when tests are written per side) | Latency, partial-failure, real-network edge cases |

A common pattern is to keep a thin end-to-end smoke test (5–10 tests) for the very top of the pyramid and replace the bulk of integration tests with contract tests. The end-to-end tests catch what contracts can't (a misconfigured load balancer adding the wrong `Host` header, a TLS version mismatch); the contract tests catch what end-to-end can't scale to (every pair, every branch, on every commit).

## The CDC Pattern in Microservices

CDC shines in microservices for two reasons: dependency direction and ownership boundaries.

**Dependency direction.** In a tightly coupled deployment, consumers tell providers what they need — but only informally, via Slack, RFC, or a wiki page that drifts. In CDC the consumer writes a contract that *is* the requirement; the provider's CI fails on contract violation. This is "consumer-driven" in the literal sense: the consumer drives the contract, the provider conforms. The provider is free to add fields, change implementations, refactor endpoints — but it cannot remove a field any consumer requires, nor change a type, without breaking a contract somewhere.

**Ownership boundaries.** In a large organization (say, 200 services), no single team can own all the integration tests. CDC distributes ownership cleanly: the consumer team owns the consumer test and the pact; the provider team owns the verification job. Each team's CI is green or red on its own contract; cross-team coordination happens via the broker, not via meetings.

```
Without CDC:                            With CDC:
+--------+   E2E test    +--------+     +--------+  contract  +--------+
|  C1    |--------------|  P     |     |  C1    |  published  |  P     |
+--------+              +--------+     +--------+             +--------+
+--------+   E2E test    +--------+     +--------+  contract  +--------+
|  C2    |--------------|  P     |     |  C2    |  published  |  P     |
+--------+              +--------+     +--------+             +--------+
+--------+   E2E test    +--------+     +--------+  contract  +--------+
|  C3    |--------------|  P     |     |  C3    |  published  |  P     |
+--------+              +--------+     +--------+             +--------+

Need: P up, DB up, network up.          Need: only your own service up.
N consumers x 1 provider = N tests.     Provider CI verifies N pacts.
```

When a consumer changes its requirement, the new pact is published. The provider's verification job runs against the new pact. If verification fails, the provider team is notified; if it succeeds, the broker records the new verification and the consumer can deploy. The whole flow runs in CI on every commit and resolves in minutes, not the hours an end-to-end suite takes.

## Pitfalls and Best Practices

- **Don't pin the entire response.** Use matchers (`stringType`, `eachLike`, `regex`) instead of literals wherever possible. A pact that pins the exact value of every field breaks on every non-breaking change to the provider.
- **Use provider states meaningfully.** "User 42 exists" is a real precondition, not a comment. Implement it as a real DB setup (use [Testcontainers](./testcontainers.md) or in-memory stores) so the verification is meaningful.
- **Don't put business logic in the pact.** The pact is an interface description; if your consumer test asserts that the returned total equals `subtotal + tax`, you have crossed into the provider's business logic. Move that assertion to the provider's own unit tests.
- **Version your pacts with branch tags.** Publish pacts with `--tag=$BRANCH` and use `can-i-deploy --to-environment`. Without tags, the broker can't distinguish a feature-branch pact from a main-branch pact.
- **Run provider verification on every PR, not just nightly.** The whole value of CDC is early failure. Nightly runs reintroduce the integration-test latency the technique was designed to avoid.
- **Beware WIP pacts.** Pending pacts from unmerged consumer branches can pile up in the broker. Use `--include-pending-status` and the broker's webhook-based cleanup to keep the matrix manageable.
- **Don't replace all integration tests.** Smoke-level end-to-end tests catch what contracts can't (load balancer headers, TLS, real-network latency). Keep a small set; let contract tests do the heavy lifting.

## Interview Questions

**Q1: What is consumer-driven contract testing, and what problem does it solve?**
A: A technique where the consumer of a service writes a contract (request + expected response with matchers) and the provider verifies its implementation honors it. It replaces end-to-end integration tests, which require both services up, with two isolated tests against a shared JSON artifact. It solves the combinatorial explosion of pairwise integration tests in microservices — \\(O(N^2)\\) end-to-end pairs become \\(O(N)\\) contract tests per service.

**Q2: Describe the Pact flow end to end.**
A: Consumer unit test sets up expectations on a Pact mock server, calls the real production client against the mock, asserts on the response. Pact captures the interaction into a JSON file. The consumer pipeline publishes the pact to the broker with a version and branch tag. The broker fires a webhook to the provider's CI. The provider CI pulls the pact, starts the real provider, sets up the named provider states, replays each request, and matches the response. Verification result is published back to the broker. The consumer pipeline asks `can-i-deploy?` — the broker answers based on whether the consumer's pacts are verified against the production version of the provider.

**Q3: Why are matchers (like, each-like, term) preferred over literal values in a pact?**
A: Literals pin the contract to a specific value. If the provider returns a different (but valid) value, the verification fails — a false positive that breaks the consumer's CI for no real reason. Matchers assert "the response must contain a field of this type at this path" without pinning the value, allowing the provider to evolve its data while honoring the structural contract. This corresponds to Postel's law: be conservative in what you send, liberal in what you accept.

**Q4: What does the broker's `can-i-deploy` check do?**
A: Given a pacticipant (consumer or provider) name, a version, and a target environment, it returns true only if every pact authored by (or consumed by) that version is currently verified by the version of the counterparty deployed in the target environment. It's the gate that makes CDC safe: a consumer cannot deploy a new requirement before the provider has verified it, and a provider cannot deploy a breaking change before all its consumers' pacts pass against the new version.

**Q5: How does contract testing compare to integration testing? When would you choose one over the other?**
A: Contract tests run each side in isolation against a JSON contract; integration tests bring both sides up and drive real network calls. Contract tests are fast, stable, and scale linearly with consumer count; integration tests are slow, brittle, and scale combinatorially. Integration tests catch what contracts miss (real network, TLS, middleware headers, latency). The standard pattern: keep a thin end-to-end smoke suite (5–10 tests) and replace the bulk of pairwise integration tests with contract tests.

**Q6: How would you introduce contract testing to a team running 50 microservices with no existing integration tests?**
A: Start with the highest-churn pair (the consumer that changes most often and breaks most often). Implement a single pact, set up the broker, wire both CI pipelines. Demonstrate the time savings vs an end-to-end test for the same pair. Expand pair by pair. Don't try to retrofit every pair at once; the value compounds as the matrix grows.

## References

- [Pact documentation](https://docs.pact.io/) — canonical reference for the framework and the protocol across language implementations
- [Martin Fowler — Consumer-Driven Contracts](https://martinfowler.com/articles/consumerDrivenContracts.html) — the 2006 article that framed the technique
- [PactFlow documentation](https://docs.pactflow.io/) — the commercial broker; many docs apply equally to the self-hosted broker
- [Pact specification (V3)](https://github.com/pact-foundation/pact-specification) — the JSON schema and versioning rules every Pact implementation follows
- [Pact Broker docs](https://docs.pact.io/pact_broker) — self-hosted broker and `can-i-deploy` semantics
- [Pact JVM](https://github.com/pact-foundation/pact-jvm) — the JVM implementation used by Spring Boot and Quarkus
- See also: [Integration Testing](./integration-testing.md), [Testcontainers](./testcontainers.md), [Mocking](./mocking.md), [Test Strategy](./test-strategy.md)
