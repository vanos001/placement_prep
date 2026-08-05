# API Design

APIs (Application Programming Interfaces) are contracts between services. Good API design is critical for system scalability, developer experience, and long-term maintainability.

## In This Section

- [REST](./rest.md) — Representational State Transfer principles and best practices
- [gRPC](./grpc.md) — High-performance RPC with Protocol Buffers
- [GraphQL](./graphql.md) — Flexible query language for APIs
- [API Gateway](./api-gateway.md) — Centralized entry point for microservices

## Choosing an API Style

| Criteria | REST | gRPC | GraphQL |
|----------|------|------|---------|
| Protocol | HTTP/1.1 | HTTP/2 | HTTP |
| Data Format | JSON | Protobuf | JSON |
| Schema | OpenAPI | .proto | SDL |
| Streaming | Limited | Full | Subscriptions |
| Browser Support | Native | gRPC-Web | Native |
| Caching | HTTP Caching | Manual | Manual |
| Learning Curve | Low | Medium | Medium |
