# OpenAPI Specification (formerly Swagger)

The OpenAPI Specification (OAS) is a standardized, language-agnostic description format for RESTful APIs. It defines a JSON or YAML document that fully describes an API's endpoints, request/response schemas, authentication, and metadata in a machine-readable form. A correct OpenAPI document is a contract: a client can be generated from it, a server stub can be scaffolded from it, an interactive docs page can render it, and a mock server can simulate it — all from one source of truth.

OpenAPI began life as "Swagger", a tool internally developed at Wordnik around 2011 and open-sourced in 2011. In 2015, SmartBear (which had acquired the Swagger tooling) donated the specification to the Linux Foundation, where it became the OpenAPI Initiative. Swagger 2.0 was renamed OpenAPI 2.0 with minor edits, OpenAPI 3.0 was a major rewrite (2017), and OpenAPI 3.1 (2021) aligned the schema dialect with JSON Schema 2020-12. This lineage matters: tools labelled "Swagger" (Swagger UI, Swagger Editor, Swagger Codegen) still consume OpenAPI documents today.

## Top-Level Structure

An OpenAPI 3.1 document has these top-level fields, in any order:

```
openapi: 3.1.0           # required — version
info: { ... }            # required — metadata
servers: [ ... ]         # optional — base URLs (default: ["/"])
paths: { ... }           # required* — operations on URLs
webhooks: { ... }        # optional — incoming webhook definitions
components: { ... }       # optional — reusable objects
security: [ ... ]        # optional — global security requirements
tags: [ ... ]            # optional — tag metadata for grouping
externalDocs: { ... }    # optional — link to external docs
```

A document must contain either `paths` or `components` (or both). A document with neither is invalid. Every field except `openapi` and `info` is technically optional, but a useful spec will define `paths`, `components`, and at least one `servers` entry.

### The `info` object

```yaml
info:
  title: Acme Payments API
  summary: Accepts card payments and exposes reconciliation data.
  description: |
    The Payments API exposes endpoints for tokenizing cards,
    capturing authorized charges, and retrieving settlement reports.
    All monetary amounts use ISO 4217 currency codes.
  termsOfService: https://acme.example.com/tos
  contact:
    name: Acme API Support
    email: api@acme.example.com
    url: https://acme.example.com/support
  license:
    name: Apache 2.0
    url: https://www.apache.org/licenses/LICENSE-2.0.html
  version: 2.4.1
```

`version` is mandatory and follows the API's own versioning scheme (not the OpenAPI version). Tools use it to pick between revisions of the same API. `summary` is new in 3.1; `description` is multi-line CommonMark.

### Servers

```yaml
servers:
  - url: https://api.acme.example.com/v2
    description: Production
  - url: https://api-staging.acme.example.com/v2
    description: Staging
  - url: https://{user}.acme-test.example.com/v2
    description: Per-tenant sandbox
    variables:
      user:
        default: demo
        description: Tenant slug from onboarding email
        enum: [demo, acme, contoso]
```

`{user}` is a template variable. Clients resolve the variable before constructing a request. The `servers` array is processed in order; tooling like Swagger UI lists each entry as a dropdown.

## Paths and Operations

`paths` is a map of URL paths to Path Item Objects. Paths are case-sensitive and templated with `{name}` placeholders. Each Path Item holds one operation per HTTP method:

```yaml
paths:
  /payments/{paymentId}:
    parameters:
      - $ref: '#/components/parameters/PathPaymentId'
    get:
      operationId: getPayment
      summary: Retrieve a single payment
      tags: [Payments]
      parameters:
        - $ref: '#/components/parameters/IfNoneMatchHeader'
      responses:
        '200':
          description: The payment resource
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Payment'
        '304':
          $ref: '#/components/responses/NotModified'
        '404':
          $ref: '#/components/responses/NotFound'
    patch:
      operationId: updatePayment
      requestBody:
        $ref: '#/components/requestBodies/PaymentUpdate'
      responses:
        '200':
          description: Updated payment
          content:
            application/json:
              schema: { $ref: '#/components/schemas/Payment' }
```

Path-level `parameters` apply to all operations under that path. Operation-level `parameters` are additive. Allowed methods: `get`, `post`, `put`, `patch`, `delete`, `head`, `options`, `trace`. `operationId` is the canonical name code generators use for the client method.

## Parameters

Four `in` locations cover everything outside the request body:

| `in` value | Where it lives | Templating |
|------------|----------------|------------|
| `path` | URL path segment `/users/{id}` | Must declare every `{x}` |
| `query` | URL query string `?status=active` | None |
| `header` | Request header `X-Trace-Id` | None |
| `cookie` | Cookie header `Cookie: session=...` | None |

```yaml
components:
  parameters:
    PathPaymentId:
      name: paymentId
      in: path
      required: true
      schema:
        type: string
        format: uuid
      description: UUID of the payment to operate on.
    PageSize:
      name: page_size
      in: query
      required: false
      schema:
        type: integer
        minimum: 1
        maximum: 200
        default: 25
    IfNoneMatchHeader:
      name: If-None-Match
      in: header
      required: false
      schema: { type: string }
      description: ETag returned by a previous GET.
    SessionCookie:
      name: session
      in: cookie
      required: true
      schema: { type: string }
```

`required: true` is mandatory for path parameters (the URL template must be filled). For query/header/cookie it defaults to `false`.

`explode: true` on array or object query parameters serializes them as separate key=value pairs: `?tag=a&tag=b`. Without `explode`, arrays are joined with commas (`?tag=a,b`). The exact serialization is governed by `style` (matrix, label, form, simple, spaceDelimited, pipeDelimited, deepObject).

## Request Body

```yaml
components:
  requestBodies:
    PaymentUpdate:
      description: Fields to modify on the payment.
      required: true
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/PaymentUpdate'
        application/merge-patch+json:
          schema:
            $ref: '#/components/schemas/PaymentUpdate'
```

`content` is a map keyed by media type. A single endpoint can accept multiple content types with different schemas — useful for `application/json` vs `application/merge-patch+json`, where the latter follows RFC 7396 semantics for null-as-delete.

## Responses

```yaml
responses:
  '200':
    description: OK
    content:
      application/json:
        schema: { $ref: '#/components/schemas/Payment' }
        examples:
          success:
            value: { id: 'f1c0', amount: 1999, currency: 'USD' }
    headers:
      ETag:
        description: Strong validator for caching.
        schema: { type: string }
        example: '"33a8645b"'
  default:
    description: Unexpected error
    content:
      application/problem+json:
        schema: { $ref: '#/components/schemas/ProblemDetails' }
```

Status codes are strings (`'200'`, `'404'`, `'2XX'` ranges are allowed). `default` matches any uncaptured code. `application/problem+json` follows RFC 9457 (Problem Details for HTTP APIs), the de facto standard for HTTP error bodies.

## Schemas — OpenAPI 3.1 = JSON Schema 2020-12

In OpenAPI 3.0 the schema dialect was a *subset* of JSON Schema, with bespoke differences (no `unevaluatedProperties`, no `$defs`, `nullable` instead of `type: [.., "null"]`). In OpenAPI 3.1 the schema dialect is **JSON Schema 2020-12** with one extra keyword (`discriminator`) and one removed (`exclusiveMinimum`/`exclusiveMaximum` are now numbers, not booleans). You can use `$id`, `$ref`, `$defs`, `if`/`then`/`else`, `allOf`, `anyOf`, `oneOf`, `prefixItems`, `unevaluatedProperties`, `contentEncoding`, `contentMediaType`, and the full set of 2020-12 keywords.

```yaml
components:
  schemas:
    Money:
      type: object
      required: [amount, currency]
      properties:
        amount:
          type: integer
          description: Minor units of the currency (e.g., cents).
          minimum: 0
          maximum: 9999999999
        currency:
          type: string
          pattern: '^[A-Z]{3}$'
          description: ISO 4217 currency code.
          examples: [USD, EUR]

    Payment:
      type: object
      required: [id, amount, status, created_at]
      properties:
        id:
          type: string
          format: uuid
        amount: { $ref: '#/components/schemas/Money' }
        status:
          $ref: '#/components/schemas/PaymentStatus'
        created_at:
          type: string
          format: date-time
          description: RFC 3339 timestamp.

    PaymentStatus:
      type: string
      enum: [pending, authorized, captured, voided, refunded]

    PaymentUpdate:
      type: object
      $ref: 'https://example.com/schemas/payment-base.json'
      unevaluatedProperties: false
      properties:
        status:
          $ref: '#/components/schemas/PaymentStatus'
```

External `$ref` URIs are resolved against the document's base URL or the `base` field of `info`. In 3.1, `$ref` siblings are merged (standard JSON Schema behavior) — unlike 3.0, where `$ref` siblings were ignored.

## Security Schemes

Authentication is declarative. Five types are supported:

| Type | Wire mechanism |
|------|---------------|
| `apiKey` | A static key in `header`, `query`, or `cookie` |
| `http` | HTTP `Authorization` header — `scheme: basic`, `bearer`, `digest`, etc. |
| `oauth2` | OAuth 2.0 flows (authorizationCode, implicit, password, clientCredentials) |
| `openIdConnect` | OIDC — discovery URL of the issuer |
| `mutualTLS` | Client cert presented during TLS handshake (3.1) |

```yaml
components:
  securitySchemes:
    ApiKey:
      type: apiKey
      in: header
      name: X-Api-Key
    BearerJwt:
      type: http
      scheme: bearer
      bearerFormat: JWT
    OAuth2:
      type: oauth2
      flows:
        authorizationCode:
          authorizationUrl: https://auth.acme.example.com/authorize
          tokenUrl: https://auth.acme.example.com/oauth/token
          refreshUrl: https://auth.acme.example.com/oauth/refresh
          scopes:
            payments:read: Read payments
            payments:write: Modify payments
            payments:refund: Issue refunds

security:
  - BearerJwt: []
  - OAuth2: [payments:read, payments:write]
```

`security` at top level is the default. Each entry is an OR alternative; within an entry the schemes are AND'd. Operations can override with their own `security` block. An empty list `[]` means the operation is public (no auth).

## `$ref` and Component Reuse

OpenAPI reuses definitions through `$ref`. Inside `components`:

- `schemas` — JSON Schema definitions
- `parameters` — reusable parameters
- `requestBodies` — reusable bodies
- `responses` — reusable response shapes
- `headers` — reusable header schemas
- `securitySchemes` — auth schemes
- `examples` — named examples
- `links` — link objects (runtime references between operations)
- `callbacks` — async webhook callbacks

By convention `components` keys are PascalCase; the `parameters` map has `PathPaymentId` rather than `pathPaymentId`. References look like `$ref: '#/components/schemas/Payment'`. Resolving this against the document root yields the schema. Documents must avoid cycles — many tools refuse to follow circular `$ref`s.

## Documentation: Swagger UI and Redoc

**Swagger UI** is the reference web UI. Given a URL to an OpenAPI document, it renders an interactive page where users fill in parameters, click "Execute", and fire real requests. Swagger UI is bundled in many frameworks (Springfox, Swashbuckle, FastAPI) and is the de facto default.

**Redoc** is the read-only counterpart — a single-page React app optimized for print-style documentation. It does not let users execute requests, but it produces cleaner long-form docs that read well for partner-facing APIs. Both accept the same OpenAPI document; choosing one is a presentation choice, not a spec choice.

A common pattern: serve Swagger UI at `/internal/api-docs` (for engineers) and Redoc at `/api/docs` (for external consumers), both pointing at the same `openapi.json`.

## Code Generation

The **openapi-generator** project (a fork of Swagger Codegen maintained by the OpenAPI Tools group) generates client SDKs, server stubs, and documentation from OpenAPI documents. It supports ~50 generator targets including Java, Go, Python, TypeScript, Rust, C#, Kotlin, Swift, and many more.

```bash
# Install
npm install -g @openapitools/openapi-generator-cli

# Generate a TypeScript fetch client
openapi-generator-cli generate \
  -i ./openapi.yaml \
  -g typescript-fetch \
  -o ./generated/ts-client \
  --additional-properties=supportsES6=true,typescriptThreePlus=true

# Generate a Go server stub
openapi-generator-cli generate \
  -i ./openapi.yaml \
  -g go-server \
  -o ./generated/go-server \
  --additional-properties=packageName=paymentsapi
```

Quality of generated code varies dramatically between generators and languages. The `typescript-fetch` generator produces idiomatic code; the `go` client generator has historically been criticized for awkward naming. Many teams treat the generator output as a starting point and own a fork. For server stubs, the convention is to generate interfaces and have hand-written implementations satisfy them, so regeneration does not clobber business logic.

For Java, the **Springdoc** project integrates OpenAPI 3 into Spring Boot — it scans controllers at runtime and produces a live `openapi.json` from annotations, eliminating the code-gen step.

## Validation

Two validators are commonly used:

- **Spectral** (Stoplight) — rules engine that checks style and conventions on top of spec validity.
- **openapi-validator** (IBM) — Microsoft's C#-based validator for schema conformance.

```bash
# Validate structural correctness
npx @redocly/cli@latest lint openapi.yaml

# Custom ruleset
npx spectral lint openapi.yaml --ruleset .spectral.yaml
```

A typical ruleset enforces: every operation has an `operationId`; every response has a `description`; 4xx responses follow `application/problem+json`; no `example: null` (use `examples`); `tags` are bounded by a pre-approved list.

## Common Mistakes

- **Defining `body` as a `query` parameter** — bodies go in `requestBody`, not parameters.
- **Forgetting to mark `required: true` on path params** — the spec requires it.
- **Using OpenAPI 3.0 `nullable: true`** in a 3.1 document — replaced by `type: [string, "null"]` per JSON Schema.
- **Siblings of `$ref` in 3.0** — these are silently ignored; in 3.1 they merge. Mixing is a source of bugs.
- **Putting examples outside `examples`** — the singular `example` keyword works, but `examples` is preferred for multiple cases.
- **Generating clients without version-pinning** — a regenerated client with breaking changes will silently break consumers; pin by git tag or commit hash.

## Interview Questions

1. **What is the difference between Swagger and OpenAPI?**
   Swagger is the original tooling (UI, Editor, Codegen); OpenAPI is the specification. Swagger 2.0 → OpenAPI 2.0 was a rename with minor edits; OpenAPI 3.0 and 3.1 are real spec evolutions.

2. **What changed in OpenAPI 3.1?**
   The schema dialect became JSON Schema 2020-12, allowing `oneOf`-without-`discriminator`, `$defs`, `prefixItems`, `contentEncoding`. Webhooks were promoted to a top-level field. `exclusiveMinimum` is now a number, not a boolean.

3. **When do you need `application/merge-patch+json` vs `application/json`?**
   RFC 7396 merge-patch treats `null` as a delete operation; `application/json` patch cannot distinguish "set to null" from "do not change".

4. **How does `$ref` work in components?**
   `$ref: '#/components/schemas/X'` resolves against the document root. In 3.1, sibling keys to `$ref` merge with the referenced object (standard JSON Schema); in 3.0, siblings are ignored.

5. **How do you express that an operation requires OAuth2 with a specific scope?**
   Use a top-level `security` for defaults, and override at the operation level with the scopes array: `security: [{ OAuth2: [payments:write] }]`.

## References

- OpenAPI Initiative — OpenAPI Specification 3.1: https://spec.openapis.org/oas/v3.1.0
- OpenAPI Initiative — OpenAPI Specification 3.0: https://spec.openapis.org/oas/v3.0.3
- Swagger UI documentation: https://swagger.io/tools/swagger-ui/
- Redoc documentation: https://redocly.com/redoc/
- openapi-generator docs: https://openapi-generator.tech/
- JSON Schema 2020-12 specification: https://json-schema.org/draft/2020-12/json-schema-core.html
- RFC 9457 — Problem Details for HTTP APIs: https://www.rfc-editor.org/rfc/rfc9457
- RFC 7396 — JSON Merge Patch: https://www.rfc-editor.org/rfc/rfc7396
- RFC 3986 — URI Generic Syntax (path templating): https://www.rfc-editor.org/rfc/rfc3986
- Stoplight Spectral: https://docs.stoplight.io/docs/spectral/
- OpenAPI Tools GitHub: https://github.com/OpenAPITools/openapi-generator
