# Integration Testing

Integration tests verify that multiple components work correctly together. While unit tests verify pieces in isolation, integration tests verify the **connections** between pieces — the contracts, data flows, and interactions across boundaries.

## What Is Integration Testing?

An integration test exercises two or more components that communicate with each other:

```
┌─────────────┐     ┌──────────────┐     ┌────────────┐
│   Service A  │────▶│  Service B   │────▶│  Database   │
└─────────────┘     └──────────────┘     └────────────┘
                          │
        Integration       │  Integration
        Test (A↔B)        │  Test (B↔DB)
```

### Types of Integration

| Type                  | What's Being Tested                      |
|-----------------------|------------------------------------------|
| **Component integration** | Multiple classes within a service    |
| **Service integration**   | Communication between microservices  |
| **Database integration**  | Application ↔ database interaction   |
| **External API integration** | Application ↔ third-party APIs    |
| **UI integration**        | Frontend ↔ backend communication     |

## Integration Testing vs Unit Testing

| Aspect            | Unit Test                    | Integration Test               |
|-------------------|------------------------------|--------------------------------|
| **Scope**         | Single class/function        | Multiple components            |
| **Dependencies**  | Mocked/stubbed               | Real (or realistic)            |
| **Speed**         | Milliseconds                 | Seconds                        |
| **Failure tells** | Which unit broke             | Which integration broke        |
| **Setup**         | Simple                       | More complex                   |
| **Maintenance**   | Lower                        | Higher                         |

## Database Integration Testing

### In-Memory Databases

Use an in-memory database for fast, isolated database tests:

```python
# Python — SQLite in-memory with SQLAlchemy
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

class TestUserRepository:
    def test_create_and_retrieve_user(self, db_session):
        repo = UserRepository(db_session)

        repo.create(name="Alice", email="alice@test.com")
        user = repo.find_by_email("alice@test.com")

        assert user.name == "Alice"
        assert user.email == "alice@test.com"

    def test_unique_email_constraint(self, db_session):
        repo = UserRepository(db_session)
        repo.create(name="Alice", email="alice@test.com")

        with pytest.raises(IntegrityError):
            repo.create(name="Bob", email="alice@test.com")
```

```java
// Java — H2 in-memory database
@SpringBootTest
@AutoConfigureTestDatabase(replace = Replace.NONE)
class UserRepositoryTest {

    @Autowired
    private UserRepository repository;

    @Autowired
    private TestEntityManager entityManager;

    @Test
    void findByEmail_existingUser_returnsUser() {
        User user = new User("Alice", "alice@test.com");
        entityManager.persistAndFlush(user);

        Optional<User> found = repository.findByEmail("alice@test.com");

        assertThat(found).isPresent();
        assertThat(found.get().getName()).isEqualTo("Alice");
    }

    @Test
    void findByEmail_nonExistent_returnsEmpty() {
        Optional<User> found = repository.findByEmail("nobody@test.com");
        assertThat(found).isEmpty();
    }
}
```

### Testcontainers

Testcontainers run real Docker containers for integration testing — no more "works with H2 but fails with PostgreSQL":

```java
@Testcontainers
class UserRepositoryContainerTest {

    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16")
        .withDatabaseName("testdb")
        .withUsername("test")
        .withPassword("test");

    @DynamicPropertySource
    static void configureProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUrl);
        registry.add("spring.datasource.username", postgres::getUsername);
        registry.add("spring.datasource.password", postgres::getPassword);
    }

    @Autowired
    private UserRepository repository;

    @Test
    void createAndRetrieve_withRealPostgres() {
        User user = new User("Alice", "alice@test.com");
        repository.save(user);

        User found = repository.findByEmail("alice@test.com");
        assertThat(found.getName()).isEqualTo("Alice");
    }
}
```

```python
# Python — Testcontainers with pytest
import pytest
from testcontainers.postgres import PostgresContainer

@pytest.fixture(scope="module")
def postgres():
    with PostgresContainer("postgres:16") as pg:
        yield pg

@pytest.fixture
def db_session(postgres):
    engine = create_engine(postgres.get_connection_url())
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
```

### Testcontainers Benefits

- Tests against real database engines, not substitutes
- Catches SQL dialect differences
- Tests database-specific features (JSON columns, full-text search, etc.)
- Each test run gets a clean container

## Contract Testing

Contract testing verifies that two services agree on the format of requests and responses:

### Why Contract Tests?

```
Consumer (Order Service)          Provider (Payment Service)
        │                                     │
        │    POST /pay                        │
        │    { amount: 100, currency: "USD" } │
        │────────────────────────────────────▶│
        │                                     │
        │    { status: "success", id: "..." } │
        │◀────────────────────────────────────│
```

The contract defines: "If you send X, I'll respond with Y."

### Pact (Consumer-Driven Contracts)

```javascript
// Consumer test — defines expectations
const { Pact } = require('@pact-foundation/pact');

describe('Payment Service', () => {
  const provider = new Pact({
    consumer: 'OrderService',
    provider: 'PaymentService',
  });

  beforeAll(() => provider.setup());
  afterAll(() => provider.finalize());

  test('processes payment successfully', async () => {
    await provider.addInteraction({
      state: 'account has sufficient funds',
      uponReceiving: 'a payment request',
      withRequest: {
        method: 'POST',
        path: '/pay',
        body: { amount: 100, currency: 'USD' },
      },
      willRespondWith: {
        status: 200,
        body: { status: 'success', id: like('txn-123') },
      },
    });

    const result = await paymentClient.processPayment({
      amount: 100,
      currency: 'USD',
    });

    expect(result.status).toBe('success');
    expect(result.id).toBeDefined();
  });
});
```

```java
// Provider verification
@Provider("PaymentService")
@PactFolder("pacts")
@SpringBootTest
class PaymentServicePactTest {

    @TestTemplate
    @ExtendWith(PactVerificationSpringProvider.class)
    void verifyPact(Pact pact, Interaction interaction, HttpRequest request) {
        // Pact framework automatically verifies the provider
        // matches the consumer's expectations
    }

    @State("account has sufficient funds")
    void setupSufficientFunds() {
        testDatabase.seedAccount("test-account", 1000);
    }
}
```

## API Integration Testing

### Testing REST APIs

```python
# Python — Flask with test client
import pytest
from app import create_app

@pytest.fixture
def client():
    app = create_app({"TESTING": True, "DATABASE": "sqlite:///:memory:"})
    with app.test_client() as client:
        with app.app_context():
            init_db()
        yield client

class TestUserAPI:
    def test_create_user(self, client):
        response = client.post("/api/users", json={
            "name": "Alice",
            "email": "alice@test.com"
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data["name"] == "Alice"
        assert "id" in data

    def test_get_user(self, client):
        # Create
        create_resp = client.post("/api/users", json={
            "name": "Alice", "email": "alice@test.com"
        })
        user_id = create_resp.get_json()["id"]

        # Retrieve
        response = client.get(f"/api/users/{user_id}")
        assert response.status_code == 200
        assert response.get_json()["name"] == "Alice"

    def test_get_nonexistent_user_returns_404(self, client):
        response = client.get("/api/users/999")
        assert response.status_code == 404

    def test_create_user_duplicate_email_returns_409(self, client):
        client.post("/api/users", json={"name": "Alice", "email": "alice@test.com"})
        response = client.post("/api/users", json={"name": "Bob", "email": "alice@test.com"})
        assert response.status_code == 409
```

```javascript
// JavaScript — Supertest with Express
const request = require('supertest');
const app = require('../src/app');

describe('User API', () => {
  let authToken;

  beforeAll(async () => {
    const res = await request(app)
      .post('/api/auth/login')
      .send({ email: 'admin@test.com', password: 'password' });
    authToken = res.body.token;
  });

  test('POST /api/users creates a user', async () => {
    const res = await request(app)
      .post('/api/users')
      .set('Authorization', `Bearer ${authToken}`)
      .send({ name: 'Alice', email: 'alice@test.com' });

    expect(res.status).toBe(201);
    expect(res.body.name).toBe('Alice');
    expect(res.body.id).toBeDefined();
  });

  test('GET /api/users/:id returns user', async () => {
    const createRes = await request(app)
      .post('/api/users')
      .set('Authorization', `Bearer ${authToken}`)
      .send({ name: 'Bob', email: 'bob@test.com' });

    const res = await request(app)
      .get(`/api/users/${createRes.body.id}`)
      .set('Authorization', `Bearer ${authToken}`);

    expect(res.status).toBe(200);
    expect(res.body.name).toBe('Bob');
  });
});
```

### Testing GraphQL APIs

```javascript
const { createTestClient } = require('apollo-server-testing');
const { ApolloServer } = require('apollo-server');

describe('GraphQL User Queries', () => {
  let server, query, mutate;

  beforeAll(() => {
    server = new ApolloServer({ typeDefs, resolvers, context: () => ({}) });
    const testClient = createTestClient(server);
    query = testClient.query;
    mutate = testClient.mutate;
  });

  test('query user by id', async () => {
    const CREATE = gql`
      mutation { createUser(name: "Alice", email: "alice@test.com") { id } }
    `;
    const createResult = await mutate({ mutation: CREATE });

    const QUERY = gql`
      query GetUser($id: ID!) { user(id: $id) { name email } }
    `;
    const result = await query({
      query: QUERY,
      variables: { id: createResult.data.createUser.id },
    });

    expect(result.data.user.name).toBe('Alice');
  });
});
```

## Message Queue Integration Testing

Testing asynchronous message-driven systems:

```python
# Python — Testing with RabbitMQ (Testcontainers)
@pytest.fixture
def rabbitmq():
    with RabbitMqContainer("rabbitmq:3-management") as rabbit:
        yield rabbit

def test_order_published_to_queue(rabbitmq):
    connection = pika.BlockingConnection(rabbitmq.get_connection_params())
    channel = connection.channel()
    channel.queue_declare(queue="orders")

    order_service = OrderService(broker_url=rabbitmq.get_connection_url())
    order_service.place_order(item="widget", quantity=5)

    method, props, body = channel.basic_get("orders")
    assert method is not None
    order_data = json.loads(body)
    assert order_data["item"] == "widget"
    assert order_data["quantity"] == 5
```

## Service Mesh Integration Testing

For microservice architectures, test service-to-service communication:

```yaml
# Docker Compose for integration tests
version: '3.8'
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: testdb
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test

  redis:
    image: redis:7

  order-service:
    build: ./order-service
    environment:
      DATABASE_URL: postgresql://test:test@postgres:5432/testdb
      REDIS_URL: redis://redis:6379
      PAYMENT_SERVICE_URL: http://payment-service:8080
    depends_on:
      - postgres
      - redis
      - payment-service

  payment-service:
    build: ./payment-service
    environment:
      DATABASE_URL: postgresql://test:test@postgres:5432/testdb
    depends_on:
      - postgres
```

```bash
# Run integration tests with Docker Compose
docker-compose -f docker-compose.test.yml up -d
./run-integration-tests.sh
docker-compose -f docker-compose.test.yml down -v
```

## Testing External API Integrations

### Record and Replay

Record real API responses and replay them in tests:

```python
# Python — VCR.py
import vcr

@vcr.use_cassette('tests/cassettes/github_user.yaml')
def test_github_user_lookup():
    user = github_client.get_user("octocat")
    assert user.login == "octocat"
    assert user.public_repos > 0
```

```javascript
// JavaScript — nock
const nock = require('nock');

describe('GitHub API', () => {
  beforeEach(() => {
    nock('https://api.github.com')
      .get('/users/octocat')
      .reply(200, {
        login: 'octocat',
        public_repos: 8,
      });
  });

  afterEach(() => nock.cleanAll());

  test('fetches user data', async () => {
    const user = await githubClient.getUser('octocat');
    expect(user.login).toBe('octocat');
  });
});
```

### WireMock for HTTP Stubbing

```java
@Test
void testWithWireMock(WireMockRuntimeInfo wm) {
    stubFor(get(urlEqualTo("/api/weather?city=London"))
        .willReturn(aResponse()
            .withHeader("Content-Type", "application/json")
            .withBody("{\"temp\": 15, \"condition\": \"cloudy\"}")));

    WeatherService service = new WeatherService(wm.getHttpBaseUrl());
    Weather weather = service.getWeather("London");

    assertThat(weather.getTemp()).isEqualTo(15);
    assertThat(weather.getCondition()).isEqualTo("cloudy");
}
```

## Integration Test Patterns

### Strangler Fig Pattern
Gradually replace legacy systems while keeping integration tests green:
1. Write integration tests against the old system
2. Build the new system
3. Run the same tests against the new system
4. Switch over when all tests pass

### Health Check Pattern
Each service exposes a health endpoint that verifies its dependencies:

```python
@pytest.fixture
def ensure_services_healthy():
    services = [
        ("http://localhost:8080/health", "Order Service"),
        ("http://localhost:8081/health", "Payment Service"),
        ("http://localhost:5432", "PostgreSQL"),
    ]
    for url, name in services:
        response = requests.get(url, timeout=5)
        assert response.status_code == 200, f"{name} is not healthy"
```

## Managing Test Data

### Factory Pattern

```python
# Python — Factory Boy
import factory
from models import User, Order

class UserFactory(factory.Factory):
    class Meta:
        model = User

    name = factory.Sequence(lambda n: f"User {n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.name.lower().replace(' ', '.')}@test.com")
    is_active = True

class OrderFactory(factory.Factory):
    class Meta:
        model = Order

    user = factory.SubFactory(UserFactory)
    amount = factory.Faker('pydecimal', left_digits=4, right_digits=2, positive=True)
    status = "pending"

# Usage in tests
def test_order_total():
    user = UserFactory()
    order1 = OrderFactory(user=user, amount=100)
    order2 = OrderFactory(user=user, amount=200)
    assert user.total_orders() == 2
```

### Test Data Cleanup

```python
@pytest.fixture(autouse=True)
def cleanup_database(db_session):
    yield
    db_session.rollback()  # Or truncate all tables
    for table in reversed(Base.metadata.sorted_tables):
        db_session.execute(table.delete())
    db_session.commit()
```

## Best Practices

1. **Test realistic scenarios** — use real databases (Testcontainers), not just mocks
2. **Isolate test data** — each test creates its own data, no shared state
3. **Use transactions for cleanup** — rollback after each test for speed
4. **Test failure modes** — what happens when a service is down?
5. **Keep integration tests in a separate suite** — they're slower, run them on PRs not every commit
6. **Use health checks** — verify dependencies are available before testing
7. **Don't test business logic in integration tests** — that's what unit tests are for
8. **Document external dependencies** — make it clear what services/databases are needed

## Summary

| Concept            | Key Takeaway                                         |
|--------------------|------------------------------------------------------|
| **Scope**          | Tests how components work *together*                 |
| **Testcontainers** | Run real databases/services in Docker for tests      |
| **Contract tests** | Verify services agree on API format                  |
| **In-memory DBs**  | Fast but less realistic than real databases          |
| **Test data**      | Use factories, isolate per test, clean up after      |
| **External APIs**  | Record/replay or stub with WireMock/nock             |
