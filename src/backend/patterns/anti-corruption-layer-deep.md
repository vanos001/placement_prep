# Anti-Corruption Layer Deep Dive

An Anti-Corruption Layer, or ACL, is a translator that sits between your bounded context and another system whose model you do not control. The ACL exposes the foreign system through an interface that speaks **your** domain language and hides the foreign model entirely. Its purpose is to prevent the foreign model — which may be ugly, inconsistent, or governed by external priorities — from **corrupting** your domain model. The pattern originates from Eric Evans's *Domain-Driven Design* (2003), where it is presented as a strategic pattern for context mapping.

## The problem it solves

You have a clean `Order`, `Customer`, and `Invoice` model. Then you integrate with a 1990s-era SOAP service called `CustomerMaster` that represents a customer as `CUST_REC` with fields like `CUST_CD`, `ORG_DTL_NEST`, `LGL_ADDR_3`, and an array of `PHONE_TUPLE` whose first element is the home phone and second is the work phone. If your domain code directly calls this service, you will start finding `CUST_CD` references in your business logic within a week. After a year, your "clean" domain model is gone: it speaks the foreign system's vocabulary.

This is **model corruption**. It is not hypothetical — it is what happens to every team that integrates with a system they don't control. The ACL is the structural answer.

## The adapter pattern applied to integration

Mechanically, an ACL is the **GoF Adapter pattern applied at the architectural level**. The Adapter pattern (Gang of Four, 1994) converts the interface of a class into another interface clients expect. The ACL does the same thing for an entire bounded context.

```
                       your bounded context
                  ┌─────────────────────────────┐
                  │   OrderService              │
                  │     │ uses                   │
                  │     ▼                        │
                  │   CustomerRepository         │
                  │     │ implements             │
                  │     ▼                        │
                  │  ★ ACL interface (port) ★   │
                  └─────────┬────────────────────┘
                            │
                   ┌────────▼─────────┐
                   │   ACL adapter     │
                   │  (translator)     │
                   └────────┬──────────┘
                            │
                  ┌─────────▼─────────┐
                  │  External System   │
                  │   (SOAP/REST/DB)   │
                  │  CUST_REC model    │
                  └────────────────────┘
```

Inside your domain, you ask `customerRepository.findById(id)` and get back a `Customer`. The ACL adapter translates that call into a SOAP request, gets a `CUST_REC` back, and translates the response into a `Customer`. The domain never sees the SOAP envelope, never sees `CUST_CD`, never sees `PHONE_TUPLE`. If the external API is replaced, you rewrite the ACL adapter — nothing else changes.

## The three-piece structure

A well-built ACL has three parts:

1. **A facade** — a coarse-grained interface in **your** domain's language. It offers operations like `findActiveCustomer(id)`, not `getCustRecByCd(code, includePhones=true)`.
2. **An adapter** — the implementation that talks to the external system. It handles the protocol (HTTP, SOAP, JDBC, gRPC), authentication, retries.
3. **A translator** — pure functions that map between the external DTO and your domain object. No I/O, no side effects; easy to unit test.

```java
// The ACL interface (port) — in domain language.
public interface CustomerRepository {
    Customer findById(CustomerId id);
    Customer save(Customer customer);
}

// The external DTO we never expose to the domain.
public record CustRecDto(
    String custCd,
    String legalName,
    List<PhoneTuple> phones,
    AddressNested address
) {}

// The translator — pure mapping functions.
public class CustomerTranslator {
    public Customer toDomain(CustRecDto dto) {
        return new Customer(
            new CustomerId(dto.custCd()),
            new PersonName(dto.legalName()),
            pickPrimaryPhone(dto.phones()),     // domain rule: first home phone
            toAddress(dto.address())
        );
    }
    public CustRecDto toDto(Customer c) { /* inverse */ }
}

// The adapter — owns the external protocol.
public final class CustomerMasterAclAdapter implements CustomerRepository {
    private final CustomerMasterClient soapClient;
    private final CustomerTranslator translator;
    private final Retry retry;

    @Override
    public Customer findById(CustomerId id) {
        return retry.call(() -> {
            var dto = soapClient.getCustRecByCd(id.value());
            return translator.toDomain(dto);
        });
    }
    // ...
}
```

The purity of the translator is the whole point. The translator is the place where the **foreign model becomes your model**; if there is a rule like "the external system stores phone numbers as strings starting with country code, but we store them as `PhoneNumber` objects with separate country code", the translator is where that rule lives. It has no I/O so it can be tested exhaustively with example DTOs.

## ACL in DDD: context mapping

In DDD strategic design, the ACL is one of the patterns used in **context mapping** — the diagram of bounded contexts and their relationships. The classic cases where an ACL appears:

- **Conformist** (no ACL): you accept the other context's model as-is. Used only when the other context's model is genuinely good and you have no leverage.
- **Customer / Supplier** (no ACL): two teams in a Dev/Dev relationship; the upstream ("supplier") team adjusts the model to the downstream ("customer") team's needs.
- **ACL**: you don't trust or can't influence the upstream model, so you put a translator in between. This is the standard pattern for integrating with third-party SaaS, with legacy systems, with a database your team doesn't own.

Evans specifically calls out that the ACL is **not** about technical integration — it is about **protecting the integrity of your model**. You can use a perfect HTTP/2 client library and still have model corruption if the response DTOs leak into your domain. The ACL is the discipline that prevents that leak.

A context map showing the ACL in use:

```
   ┌──────────────────┐                  ┌──────────────────┐
   │  Order context   │                  │ Customer context │
   │  (your team)     │  ←── ACL ──→     │   (legacy/main)   │
   │  Order           │                  │   CUST_REC        │
   │  Customer(ref)   │                  │   PHONE_TUPLE     │
   │  CustomerId      │                  │   LGL_ADDR_NEST  │
   └──────────────────┘                  └──────────────────┘
            │
            │   The Order context only knows CustomerId;
            │   it asks CustomerRepository (the ACL port)
            │   and gets a Customer (domain shape) back.
            │   The legacy shapes are never imported.
            ▼
   no imports of com.legacy.custrec.* anywhere in your domain package
```

## Comparison to API gateway

An API gateway is often confused with an ACL because both sit between clients and backends. They are different patterns.

| Aspect | API Gateway | Anti-Corruption Layer |
|---|---|---|
| Purpose | Routing, auth, rate limit, TLS, cross-cutting infra | Domain model translation |
| Lives where | At the edge of your system | At the boundary of a bounded context |
| Knows about domain? | Usually no (operates on URLs/headers) | Yes (speaks the bounded context's language) |
| Who owns it? | Platform / infra team | Domain team |
| Coupling direction | Backend-agnostic | Strongly coupled to one domain |
| Failure mode | Requests can't reach backend | Domain can't reason about external state |

A common architecture has both: an API gateway at the edge (handles TLS, rate limit, JWT validation) and an ACL between the gateway-facing controller and the legacy backend that owns the data. They compose; they don't replace.

```
   request → API Gateway → Web Controller → CustomerRepository (ACL port)
                                                │
                                                ▼
                                    CustomerMasterAclAdapter
                                                │
                                                ▼
                                         Legacy mainframe
```

## Production examples

### Legacy integration

You are building a new order service. The customer data lives in a 30-year-old mainframe. The order service exposes `POST /orders` with a clean `Customer` reference (id only). Internally, the order service's `CustomerMasterAclAdapter` translates `Customer` lookups to mainframe RPCs, parses the fixed-width response, and returns a `Customer`. The order service's domain code never references the mainframe's field offsets.

When the mainframe is eventually retired and replaced with a new customer service, the **only** code that changes is the adapter implementation — the translator (if schemas are similar) and all domain code stay the same. This is the cheapest possible cost-of-change profile.

### External API wrapping

Your e-commerce backend talks to Stripe, Twilio, and SendGrid. Each has its own model: Stripe uses `customer.currency`, `customer.sources`, `customer.default_source`; your domain uses `Account`, `PaymentMethod`, `PreferredPayment`. An ACL per provider translates between the two. If you switch from Stripe to Adyen, you swap the adapter; the domain is untouched.

```python
class PaymentMethodAcl(Protocol):
    def list_for(self, account_id: str) -> list[PaymentMethod]: ...

class StripePaymentMethodAcl:
    def __init__(self, stripe: StripeClient):
        self._stripe = stripe

    def list_for(self, account_id: str) -> list[PaymentMethod]:
        raw = self._stripe.customers.list_sources(
            account_id, object='card', limit=100)
        default_src = self._stripe.retrieve_customer(account_id).get(
            'default_source')
        return [self._to_domain(c, default_src) for c in raw]

    def _to_domain(self, c: dict, default_id: str | None) -> PaymentMethod:
        return PaymentMethod(
            id=c['id'],
            kind=PaymentKind.CARD,
            last4=c['last4'],
            is_default=(c['id'] == default_id),
        )
```

The translator `_to_domain` is the place where Stripe-specific knowledge ends and your domain begins. Test it with example JSON fixtures; never let a `stripe` import reach your domain package.

## Anti-patterns

- **Leaky ACL**: the adapter returns the raw DTO to the domain. The whole point is to not do this. A tell-tale sign: import statements for `stripe`, `suds` (SOAP), or `psycopg2` in your domain package.
- **ACL as a proxy with no translation**: the adapter just forwards calls and returns the raw response. This is a proxy, not an ACL. It's fine if the foreign model already speaks your language, but it is not an ACL.
- **ACL with business logic**: the adapter starts to make decisions ("if balance > X, route to risk service"). The ACL is a translator, not a router. If you need routing, that's a separate concern.
- **One ACL per endpoint**: an ACL should be coarse-grained and stable; if every external endpoint has its own adapter, you've created a leaky abstraction.
- **ACL shared across bounded contexts**: the ACL is tied to one bounded context's language. Sharing it across contexts re-introduces the corruption problem (now two contexts must agree on what "Customer" means through the ACL).

## Implementation notes

- **Where does the ACL live?** In a package or module that depends on both the external system's SDK and your domain. It is **not** in the domain package — the domain must compile without the external SDK.
- **How do you test it?** Test the translator with example DTOs as pure unit tests. Test the adapter with a fake/mock external client for behavior. Run a small contract test against the real external system in CI to catch drift.
- **Versioning**: the external system changes its schema. The ACL's translator must support the versions your system was built against and the current one. The ACL is the right place to do **version adaptation** (e.g., "if the response has `customer.currency`, use it; else default to `USD`").
- **Performance**: the ACL adds a translation step per call. In hot paths, this matters. The translator must be allocation-conscious (no reflection, no JSON re-serialization in the inner loop).
- **Caching**: the ACL is a natural place to cache external responses because it already encapsulates the call shape. Cache the domain object, not the DTO — that way cache invalidation stays in domain terms.

## When to use an ACL, and when not to

Use an ACL when:

- You are integrating with a system whose model you don't control and don't want to adopt.
- The external model is unstable, ugly, or being deprecated.
- You want your domain code to be portable across providers (e.g., Stripe/Adyen swap).
- You are migrating off a legacy system and want the new system to be insulated from the old shape.

Don't use an ACL when:

- The external model is genuinely good and stable (use Conformist instead).
- The translation is trivial and the upstream team is in a Customer/Supplier relationship with you.
- The integration is one-shot (just a tool, not an ongoing system).

## Cross-references

- [Microservices](./microservices.md) — bounded contexts in DDD
- [Strangler Fig](./strangler-fig.md) — the facade in a strangler migration is often an ACL
- [BFF Pattern](./bff-pattern.md) — a BFF is conceptually an ACL between the frontend's needs and the backend's APIs
- [Service Mesh](../containers/service-mesh.md) — out-of-process version of cross-cutting translation
- [CQRS](./cqrs.md) — separating read and write models is a sibling strategic pattern

## References

- [Microsoft Azure Architecture Center — Anti-Corruption Layer pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/anti-corruption-layer) — the cloud-pattern write-up with code
- [Eric Evans, "Domain-Driven Design: Tackling Complexity in the Heart of Software" (Addison-Wesley, 2003)](https://www.informit.com/store/domain-driven-design-tackling-complexity-in-the-heart-of-software-9780321125217) — original DDD source, Chapter 14 "Maintaining Model Integrity"
- [Vaughn Vernon, "Implementing Domain-Driven Design" (Addison-Wesley, 2013)](https://www.informit.com/store/implementing-domain-driven-design-9780321834577) — Chapter 2 (Context Maps) and Chapter 4 (Integration) give a worked ACL example
- [Martin Fowler — BoundedContext (bliki)](https://martinfowler.com/bliki/BoundedContext.html) — adjacent concept, by the co-author of *Bounded Contexts* in the DDD space
- [DDD Community — Vernon on ACL (2011)](https://www.dddcommunity.com/library/vernon_2011/vernon_2011_2/) — early Vernon article on context mapping with the ACL
- [Martin Fowler — Patterns of Enterprise Application Architecture (catalog)](https://martinfowler.com/eaaCatalog/) — the upstream architectural pattern catalog where the Adapter / Gateway / Mapper siblings live
