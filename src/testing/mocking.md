# Mocking

Mocking is the technique of replacing real dependencies with controlled substitutes (test doubles) to isolate the code under test. Understanding the different types of test doubles and when to use each is essential for writing effective unit tests.

## Test Doubles

A **test double** is any object that stands in for a real dependency during testing. There are several types:

```
                    Test Doubles
                        │
        ┌───────┬───────┼───────┬───────┐
        │       │       │       │       │
      Dummy  Stub   Spy   Mock    Fake
```

### Dummy

A dummy is passed around but never actually used. It satisfies a parameter requirement:

```python
class DummyLogger:
    def log(self, message):
        pass  # Does nothing

# The test doesn't care about logging
def test_calculate_total():
    service = OrderService(logger=DummyLogger())
    total = service.calculate_total([Item(price=10), Item(price=20)])
    assert total == 30
```

### Stub

A stub provides **canned answers** to calls made during the test. It doesn't care how many times it's called or in what order:

```python
class StubWeatherService:
    def get_temperature(self, city):
        if city == "London":
            return 15
        return 20

def test_clothing_recommendation_for_cold_weather():
    service = ClothingRecommender(weather=StubWeatherService())
    recommendation = service.recommend("London")
    assert recommendation == "wear a jacket"

def test_clothing_recommendation_for_warm_weather():
    service = ClothingRecommender(weather=StubWeatherService())
    recommendation = service.recommend("Miami")
    assert recommendation == "wear a t-shirt"
```

```java
// Java — Stub
when(weatherService.getTemperature("London")).thenReturn(15);

ClothingRecommender recommender = new ClothingRecommender(weatherService);
String recommendation = recommender.recommend("London");
assertEquals("wear a jacket", recommendation);
```

### Spy

A spy **records calls** made to it so you can verify them later. It wraps a real object or has default behavior:

```python
class SpyEmailService:
    def __init__(self):
        self.sent_emails = []

    def send(self, to, subject, body):
        self.sent_emails.append({
            "to": to, "subject": subject, "body": body
        })

def test_welcome_email_sent_on_registration():
    spy = SpyEmailService()
    service = UserService(email_service=spy)

    service.register("alice@test.com", "Alice")

    assert len(spy.sent_emails) == 1
    assert spy.sent_emails[0]["to"] == "alice@test.com"
    assert "Welcome" in spy.sent_emails[0]["subject"]
```

```java
// Java — Mockito Spy
List<String> spyList = spy(new ArrayList<>());
spyList.add("one");
spyList.add("two");

verify(spyList, times(2)).add(anyString());
assertEquals(2, spyList.size());
```

### Mock

A mock **verifies behavior** — it checks that the correct calls were made with the correct arguments. Mocks fail the test if expected interactions don't happen:

```python
from unittest.mock import Mock

def test_order_placement_sends_confirmation_email():
    mock_email = Mock()
    service = OrderService(email=mock_email)

    service.place_order(item="Widget", quantity=1, email="alice@test.com")

    mock_email.send.assert_called_once_with(
        to="alice@test.com",
        subject="Order Confirmation",
        body=ANY  # Don't care about exact body
    )
```

```java
// Java — Mockito Mock
@Mock
private EmailService emailService;

@Test
void placeOrder_sendsConfirmationEmail() {
    OrderService service = new OrderService(emailService);

    service.placeOrder("Widget", 1, "alice@test.com");

    verify(emailService).send(
        eq("alice@test.com"),
        eq("Order Confirmation"),
        anyString()
    );
}
```

### Fake

A fake is a **working implementation** that takes shortcuts. It has real behavior but isn't suitable for production:

```python
class InMemoryUserRepository:
    """Fake repository — real behavior, in-memory storage."""
    def __init__(self):
        self._users = {}
        self._next_id = 1

    def save(self, user):
        user.id = self._next_id
        self._users[self._next_id] = user
        self._next_id += 1
        return user

    def find_by_id(self, user_id):
        return self._users.get(user_id)

    def find_by_email(self, email):
        for user in self._users.values():
            if user.email == email:
                return user
        return None

    def delete(self, user_id):
        self._users.pop(user_id, None)

def test_user_service_creates_and_retrieves_user():
    repo = InMemoryUserRepository()
    service = UserService(repo)

    service.create_user("Alice", "alice@test.com")
    user = repo.find_by_email("alice@test.com")

    assert user.name == "Alice"
```

```java
// Java — Fake
public class FakePaymentGateway implements PaymentGateway {
    private final Map<String, PaymentResult> results = new HashMap<>();

    public void setResult(String orderId, PaymentResult result) {
        results.put(orderId, result);
    }

    @Override
    public PaymentResult charge(String orderId, BigDecimal amount) {
        return results.getOrDefault(orderId, PaymentResult.success(orderId));
    }
}
```

## Comparison Table

| Type   | Has Behavior? | Verifies Calls? | Real Logic? | When to Use                     |
|--------|---------------|-----------------|-------------|----------------------------------|
| Dummy  | No            | No              | No          | Satisfy parameter requirements   |
| Stub   | Yes (canned)  | No              | No          | Provide test data                |
| Spy    | Yes           | Yes (after)     | Partial     | Record interactions for later    |
| Mock   | Yes           | Yes (expects)   | No          | Verify specific interactions     |
| Fake   | Yes           | No              | Yes (simplified) | Fast, isolated testing      |

## Mocking in Python

### unittest.mock

```python
from unittest.mock import Mock, MagicMock, patch, call

# Mock — generic mock object
mock = Mock()
mock.method.return_value = 42
assert mock.method() == 42
mock.method.assert_called_once()

# MagicMock — supports magic methods (__len__, __iter__, etc.)
magic = MagicMock()
magic.__len__.return_value = 3
assert len(magic) == 3

# patch — replace objects during test
@patch('myapp.services.EmailService')
def test_sends_email(MockEmailService):
    mock_instance = MockEmailService.return_value
    mock_instance.send.return_value = True

    service = UserService()
    service.register("alice@test.com", "Alice")

    mock_instance.send.assert_called_once_with(
        to="alice@test.com",
        subject="Welcome"
    )

# patch as context manager
def test_fetches_user_data():
    with patch('myapp.api.requests.get') as mock_get:
        mock_get.return_value = Mock(
            status_code=200,
            json=lambda: {"name": "Alice"}
        )

        user = fetch_user(1)
        assert user.name == "Alice"
        mock_get.assert_called_once_with("https://api.example.com/users/1")

# Side effects — simulate errors
def test_handles_api_failure():
    with patch('myapp.api.requests.get') as mock_get:
        mock_get.side_effect = ConnectionError("Service unavailable")

        result = fetch_user(1)
        assert result is None

# Argument matchers
def test_creates_order():
    mock_api = Mock()
    service = OrderService(api=mock_api)

    service.create("Widget", quantity=3)

    mock_api.post.assert_called_once()
    args = mock_api.post.call_args
    assert args[1]["quantity"] == 3
```

### pytest-mock

```python
import pytest

def test_sends_notification(mocker):
    # mocker is a pytest fixture from pytest-mock
    mock_send = mocker.patch('myapp.notifications.send')

    notify_user("alice@test.com", "Hello!")

    mock_send.assert_called_once_with("alice@test.com", "Hello!")

def test_stubs_external_api(mocker):
    mock_get = mocker.patch('myapp.api.requests.get')
    mock_get.return_value.json.return_value = {"status": "ok"}

    result = health_check()
    assert result.is_healthy
```

## Mocking in Java

### Mockito

```java
@ExtendWith(MockitoExtension.class)
class OrderServiceTest {

    @Mock
    private PaymentGateway paymentGateway;

    @Mock
    private EmailService emailService;

    @Mock
    private InventoryService inventoryService;

    @InjectMocks
    private OrderService orderService;

    @Test
    void placeOrder_successfulPayment_sendsConfirmation() {
        // Arrange
        when(paymentGateway.charge(anyString(), any(BigDecimal.class)))
            .thenReturn(PaymentResult.success("txn-123"));
        when(inventoryService.reserve("Widget", 1))
            .thenReturn(true);

        // Act
        Order order = orderService.placeOrder("Widget", 1, "alice@test.com");

        // Assert
        assertEquals("CONFIRMED", order.getStatus());
        verify(emailService).send(eq("alice@test.com"), contains("Confirmation"));
        verify(inventoryService).reserve("Widget", 1);
    }

    @Test
    void placeOrder_paymentFails_orderNotCreated() {
        // Arrange
        when(paymentGateway.charge(anyString(), any(BigDecimal.class)))
            .thenReturn(PaymentResult.failure("Insufficient funds"));

        // Act & Assert
        assertThrows(PaymentFailedException.class, () ->
            orderService.placeOrder("Widget", 1, "alice@test.com")
        );
        verify(emailService, never()).send(anyString(), anyString());
    }

    @Test
    void placeOrder_outOfStock_cancelsOrder() {
        when(inventoryService.reserve("Widget", 1)).thenReturn(false);

        assertThrows(OutOfStockException.class, () ->
            orderService.placeOrder("Widget", 1, "alice@test.com")
        );
        verify(paymentGateway, never()).charge(anyString(), any());
    }
}
```

### Argument Matchers

```java
// Exact values
verify(mock).method("exact string");
verify(mock).method(42);

// Any value
verify(mock).method(any());
verify(mock).method(anyString());
verify(mock).method(anyInt());
verify(mock).method(any(BigDecimal.class));

// Specific matchers
verify(mock).method(eq("hello"));
verify(mock).method(notNull());
verify(mock).method(startsWith("hello"));
verify(mock).method(contains("world"));
verify(mock).method(matches("\\d{3}-\\d{4}"));

// Captors — capture arguments for detailed assertions
ArgumentCaptor<String> captor = ArgumentCaptor.forClass(String.class);
verify(mock).send(captor.capture());
assertEquals("alice@test.com", captor.getValue());
```

## Mocking in JavaScript

### Jest Mocks

```javascript
// Manual mock
const mockSend = jest.fn();
mockSend.mockResolvedValue({ success: true });

// Mock module
jest.mock('./email-service', () => ({
  sendEmail: jest.fn().mockResolvedValue({ success: true }),
}));

// Mock implementation
const mockDb = {
  query: jest.fn(),
  insert: jest.fn(),
  update: jest.fn(),
};

describe('UserService', () => {
  let service;

  beforeEach(() => {
    jest.clearAllMocks();
    mockDb.query.mockReset();
    service = new UserService(mockDb);
  });

  test('creates user and sends welcome email', async () => {
    mockDb.insert.mockResolvedValue({ id: 1, name: 'Alice' });

    const user = await service.createUser({
      name: 'Alice',
      email: 'alice@test.com',
    });

    expect(user.id).toBe(1);
    expect(mockDb.insert).toHaveBeenCalledWith('users', {
      name: 'Alice',
      email: 'alice@test.com',
    });
  });

  test('throws on duplicate email', async () => {
    mockDb.query.mockResolvedValue([{ id: 1, email: 'alice@test.com' }]);

    await expect(
      service.createUser({ name: 'Bob', email: 'alice@test.com' })
    ).rejects.toThrow('Email already exists');
  });
});

// Spy on existing method
test('calls logger on error', () => {
  const spy = jest.spyOn(console, 'error').mockImplementation();

  service.processInvalidInput('');

  expect(spy).toHaveBeenCalledWith('Invalid input provided');
  spy.mockRestore();
});
```

### Sinon.js

```javascript
const sinon = require('sinon');

describe('OrderService', () => {
  let sandbox;

  beforeEach(() => { sandbox = sinon.createSandbox(); });
  afterEach(() => { sandbox.restore(); });

  test('sends email after order', async () => {
    const emailStub = sandbox.stub(emailService, 'send').resolves();
    const inventoryStub = sandbox.stub(inventoryService, 'reserve').resolves(true);

    await orderService.placeOrder('Widget', 1, 'alice@test.com');

    sinon.assert.calledOnce(emailStub);
    sinon.assert.calledWith(emailStub, 'alice@test.com');
  });
});
```

## Dependency Injection for Testing

Dependency Injection (DI) makes code testable by allowing dependencies to be swapped:

### Without DI (Hard to Test)

```python
class OrderService:
    def place_order(self, item, quantity):
        # Hard-coded dependency — can't mock!
        db = PostgreSQLDatabase("production-db-url")
        email = SMTPEmailService("smtp.example.com")
        payment = StripePaymentGateway("sk_live_...")

        db.save_order(item, quantity)
        payment.charge(item.price * quantity)
        email.send_confirmation(...)
```

### With DI (Easy to Test)

```python
class OrderService:
    def __init__(self, db, email, payment):
        self.db = db
        self.email = email
        self.payment = payment

    def place_order(self, item, quantity):
        self.db.save_order(item, quantity)
        self.payment.charge(item.price * quantity)
        self.email.send_confirmation(...)

# Production
service = OrderService(
    db=PostgreSQLDatabase(url),
    email=SMTPEmailService(smtp_host),
    payment=StripePaymentGateway(api_key)
)

# Test
service = OrderService(
    db=InMemoryDatabase(),
    email=SpyEmailService(),
    payment=FakePaymentGateway()
)
```

### DI in Java (Spring)

```java
@Service
public class OrderService {
    private final PaymentGateway paymentGateway;
    private final EmailService emailService;

    @Autowired
    public OrderService(PaymentGateway paymentGateway, EmailService emailService) {
        this.paymentGateway = paymentGateway;
        this.emailService = emailService;
    }
}

// Test — inject mocks
@ExtendWith(MockitoExtension.class)
class OrderServiceTest {
    @Mock PaymentGateway paymentGateway;
    @Mock EmailService emailService;
    @InjectMocks OrderService orderService;

    @Test
    void test() {
        when(paymentGateway.charge(...)).thenReturn(...);
        // ...
    }
}
```

## Over-Mocking

The most common mocking mistake — mocking too much:

```python
# ❌ Over-mocked — testing implementation, not behavior
def test_create_user_over_mocked():
    mock_db = Mock()
    mock_validator = Mock()
    mock_hasher = Mock()
    mock_id_gen = Mock()

    mock_validator.validate.return_value = True
    mock_hasher.hash.return_value = "hashed"
    mock_id_gen.generate.return_value = "uuid-123"
    mock_db.insert.return_value = None

    service = UserService(mock_db, mock_validator, mock_hasher, mock_id_gen)
    service.create_user("Alice", "alice@test.com")

    mock_validator.validate.assert_called_once_with("alice@test.com")
    mock_hasher.hash.assert_called_once()
    mock_id_gen.generate.assert_called_once()
    mock_db.insert.assert_called_once_with(...)

# ✅ Better — test behavior with a fake
def test_create_user_with_fake():
    repo = InMemoryUserRepository()
    service = UserService(repo)

    user = service.create_user("Alice", "alice@test.com")

    assert user.name == "Alice"
    assert user.email == "alice@test.com"
    assert repo.find_by_email("alice@test.com") == user
```

### Rules of Thumb

1. **Mock at the boundary** — external services, databases, file systems
2. **Don't mock what you own** — use fakes for internal collaborators
3. **Don't mock value objects** — just create real ones
4. **If you're mocking 5+ things** — the design needs work

## Best Practices

1. **Prefer fakes over mocks** — fakes have real behavior, mocks are brittle
2. **Mock at boundaries** — databases, APIs, file systems, not internal classes
3. **Don't mock what you don't own** — wrap third-party code, mock the wrapper
4. **Keep mocks simple** — if the mock is complex, the test is too complex
5. **Reset mocks between tests** — `beforeEach` / `setUp`
6. **Verify important interactions only** — don't verify every internal call
7. **Use DI to enable testing** — constructor injection is the gold standard
8. **Name mocks clearly** — `mockEmailService` not `mock1`

## Summary

| Concept       | Key Takeaway                                           |
|---------------|-------------------------------------------------------|
| **Dummy**     | Placeholder, never used                                |
| **Stub**      | Returns canned data                                    |
| **Spy**       | Records calls for later verification                   |
| **Mock**      | Verifies expected interactions                         |
| **Fake**      | Real but simplified implementation                     |
| **DI**        | Makes code testable by swapping dependencies           |
| **Over-mocking** | Test behavior, not implementation details          |
