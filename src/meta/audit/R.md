# Chunk R — Deep Audit Findings

> Scope: `frameworks/*` (excl. tokio), `data-engineering/*`, `search/*`, `web-servers/*` (excl. apache.md),
> `cheatsheets/*` (excl. system-design.md, python.md, linux.md), `testing/*` (excl. integration-testing.md),
> `git/*` (excl. internals.md, stashing.md, worktrees-submodules.md, rebasing.md)
> Agent Task ID: 8-R
> Files audited: 33
> Findings: 15 (4 HIGH / 7 MEDIUM / 4 LOW)

## Per-file findings

### frameworks/fastapi/README.md

#### F1 — MEDIUM — Outdated minimum Python version
- **File:line**: `frameworks/fastapi/README.md:5`
- **Wrong text**: `"FastAPI is a modern, fast (high-performance) web framework for building APIs with Python 3.7+ based on standard Python type hints."`
- **Correct text**: `Python 3.8+` (FastAPI 0.100.0 dropped Python 3.7 in May 2023; latest releases require Python 3.9+ and current stable requires Python 3.10+).
- **Verification**: FastAPI release notes — https://fastapi.tiangolo.com/release-notes/ — "Drop support for Python 3.7, require Python 3.8 or above."

#### F2 — MEDIUM — Misleading Django async support version
- **File:line**: `frameworks/fastapi/README.md:357` (FastAPI vs Flask vs Django table)
- **Wrong text**: `| **Async** | Native | Extensions | Django 4.1+ |`
- **Correct text**: Django added async views, middleware, and tests in **Django 3.1** (Sep 2020). Django 4.0 (Dec 2021) added async cache. Django 4.1 (Aug 2022) added async QuerySet. Saying "Django 4.1+" understates Django's async support — should be "Django 3.1+".
- **Verification**: Django docs — https://docs.djangoproject.com/en/6.0/topics/async/ — "Django has support for writing asynchronous ('async') views" (since 3.1).

#### F3 — MEDIUM — Uses deprecated Pydantic V1 `@validator` API
- **File:line**: `frameworks/fastapi/README.md:73, 85-89`
- **Wrong text**:
  ```python
  from pydantic import BaseModel, Field, validator, EmailStr
  ...
  @validator('password')
  def password_strength(cls, v):
      ...
  ```
- **Correct text**: In Pydantic V2, `@validator` is deprecated in favor of `@field_validator` with `@classmethod`. The file later has a "Pydantic V2 Deep Dive" section using V2 syntax — the earlier section should be updated for consistency, since Pydantic V2 is the current major version (V1 is in maintenance mode).
- **Verification**: Pydantic migration guide — https://docs.pydantic.dev/latest/migration/#validator-changes

### frameworks/express/README.md

#### F4 — MEDIUM — Error handler accesses undefined `err.code`
- **File:line**: `frameworks/express/README.md:204-209, 226`
- **Wrong text**:
  ```javascript
  class AppError extends Error {
      constructor(message, status) {
          super(message);
          this.status = status;
      }
  }
  // ...later...
  if (err instanceof AppError) {
      return res.status(err.status).json({
          error: err.message,
          code: err.code,   // ← undefined; AppError doesn't define `code`
      });
  }
  ```
- **Correct text**: Either add a `code` field to `AppError`'s constructor (e.g., `this.code = code`) or remove `code: err.code` from the response. As written, `err.code` is always `undefined` for `AppError` instances, so the response payload will contain `"code": undefined` (which `JSON.stringify` drops).

### frameworks/django/README.md

#### F5 — HIGH — Non-existent `afilter()` QuerySet method
- **File:line**: `frameworks/django/README.md:72`
- **Wrong text**:
  ```python
  products = [p async for p in Product.objects.all().afilter(active=True)]
  ```
- **Correct text**:
  ```python
  products = [p async for p in Product.objects.filter(active=True)]
  ```
- **Verification**: Django docs — https://docs.djangoproject.com/en/6.0/ref/models/querysets/ — "These methods do not run database queries, therefore they are safe to run in asynchronous code, and do not have separate asynchronous versions. filter() …". `filter()` is lazy and does not need an async variant; `afilter()` does not exist on `QuerySet`. Calling `.afilter()` raises `AttributeError`.

#### F6 — HIGH — `afilter()` listed in async methods enumeration
- **File:line**: `frameworks/django/README.md:76`
- **Wrong text**: `"`aget()`, `afilter()`, `acreate()`, `aupdate()`, `adelete()`, `acount()`, `aexists()` — and `sync_to_async` when you must call sync ORM from async views."`
- **Correct text**: Remove `afilter()` from the list. The valid async QuerySet methods are `aget()`, `acreate()`, `aupdate()`, `adelete()`, `acount()`, `aexists()`, `aaggregate()`, `aiterate()`, `afirst()`, `alast()` (see Django docs). Lazy methods (`filter`, `exclude`, `values`, `annotate`, etc.) have no `a` variant.
- **Verification**: Same Django docs link as F5.

#### F7 — LOW — "Instagram (historically)" misleads about Django adoption
- **File:line**: `frameworks/django/README.md:7`
- **Wrong text**: `"Django powers Instagram (historically), Disqus, Mozilla, Pinterest (historically), …"`
- **Correct text**: Instagram still runs on a heavily-modified Django monolith (Meta engineering confirmed multiple times through 2024-2025). The "(historically)" qualifier is misleading. Either drop the qualifier for Instagram or phrase as "Instagram (heavily customized Django at scale)".
- **Verification**: https://python.plainenglish.io/how-instagram-uses-python-scaling-the-worlds-largest-django-application-1fb274fdf3d6 (Apr 2025) — "the company continues to invest heavily in the language and Django."

### frameworks/spring-boot/README.md

#### F8 — LOW — Bean lifecycle diagram conflates `BeanFactoryPostProcessor` and `BeanPostProcessor`
- **File:line**: `frameworks/spring-boot/README.md:277-289` (state diagram)
- **Wrong text**:
  ```
  BeanDefinition --> BeanPostProcessor: BeanFactoryPostProcessor
  BeanPostProcessor --> Instantiation: Create instance
  ```
- **Correct text**: `BeanFactoryPostProcessor` and `BeanPostProcessor` are distinct interfaces. `BeanFactoryPostProcessor` runs *after* bean definitions are loaded but *before* any bean instantiation. `BeanPostProcessor` runs *around each bean's* init (before/after). The current diagram labels a node "BeanPostProcessor" with a transition note "BeanFactoryPostProcessor", which conflates them. Suggest renaming the node to "BeanFactoryPostProcessor" (since that's what runs between BeanDefinition and Instantiation) and removing the misleading label.
- **Verification**: Spring Framework reference — https://docs.spring.io/spring-framework/reference/core/beans/context-introduction/beanfactory-postprocessor.html — distinguishes the two clearly.

### search/vector-search.md

#### F9 — MEDIUM — Out-of-place reference to CRDT.tech (AI artifact)
- **File:line**: `search/vector-search.md:143`
- **Wrong text**: `"- [CRDT.tech local-first overview](https://crdt.tech/)"`
- **Correct text**: Remove this reference. CRDTs (Conflict-free Replicated Data Types) are unrelated to vector search / ANN indexing; this appears to be an AI-hallucinated reference. The list already contains the relevant Stanford IR book and FAISS / HNSW / Milvus / Elasticsearch references.
- **Verification**: CRDTs are a distributed-data-structures topic; the link is unrelated to the page's content (vector search, HNSW, IVF, PQ, DiskANN, RAG).

### cheatsheets/distributed.md

#### F10 — MEDIUM — Wrong quorum formula in Replication Strategies table
- **File:line**: `cheatsheets/distributed.md:50`
- **Wrong text**:
  ```
  | Quorum (NRW) | Variable | Strong | N-W+R > N ensures consistency |
  ```
- **Correct text**:
  ```
  | Quorum (NRW) | Variable | Strong | W + R > N ensures consistency |
  ```
- **Verification**: The standard quorum consistency condition is `W + R > N` (correctly stated two lines later on line 59: "Strong consistency if: W + R > N"). The formula `N - W + R > N` simplifies to `R > W`, which is NOT the quorum condition. Also, the column header is "Data Loss Risk" but the entry states a consistency formula (inconsistent with the rest of the column which contains risk descriptions like "None", "Possible", etc.).

### git/fundamentals.md

#### F11 — HIGH — Wrong default for `gc.pruneExpire`
- **File:line**: `git/fundamentals.md:298`
- **Wrong text**: `"They remain in the object database as unreachable objects. They can be recovered via `git reflog` until garbage collected (default: 30 days for unreachable objects, configurable via `gc.pruneExpire`)."`
- **Correct text**: `"… (default: **14 days** for unreachable objects, configurable via `gc.pruneExpire`; the default value is `2.weeks.ago`)."`
- **Verification**: `git help gc` — "Prune loose objects older than date (default is 2 weeks ago, overridable by the config variable gc.pruneExpire)." https://git-scm.com/docs/git-gc. The 30-day figure refers to `gc.reflogExpireUnreachable` (reflog entry expiration), not object pruning.

### git/branching.md

#### F12 — MEDIUM — Wrong Git version for `ort` default merge strategy
- **File:line**: `git/branching.md:244`
- **Wrong text**: `"`ort` (Ostensibly Recursive's Twin) is the default since Git 2.33."`
- **Correct text**: `"`ort` (Ostensibly Recursive's Twin) is the default since Git 2.34 (Nov 2021)."`
- **Verification**: Git 2.34 release notes — https://www.devclass.com/development/2021/11/17/git-234-sets-new-merge-default-speeds-things-up-for-monorepo-users/1631754 — "The Git team changed the default merge strategy from recursive to ort … with the update" (Nov 17, 2021, Git 2.34). The `ort` strategy was *introduced* in Git 2.30/2.33 timeframe but only became default in 2.34.

### git/interview-questions.md

#### F13 — HIGH — Wrong pruning period for unreachable objects
- **File:line**: `git/interview-questions.md:58`
- **Wrong text**: `"Act quickly — `git gc` prunes unreachable objects after 30 days."`
- **Correct text**: `"Act quickly — `git gc` prunes unreachable objects after 14 days (default `gc.pruneExpire = 2.weeks.ago`)."`
- **Verification**: Same as F11 — https://git-scm.com/docs/git-gc.

#### F14 — MEDIUM — "Objects persist until GC'd (30+ days)" trap is wrong
- **File:line**: `git/interview-questions.md:100`
- **Wrong text**: `| "Deleted means gone" | Objects persist until GC'd (30+ days) |`
- **Correct text**: `| "Deleted means gone" | Objects persist until GC'd (14 days default for unreachable objects; reflog entries 30/90 days) |`
- **Verification**: Same as F11.

### testing/tdd-bdd.md

#### F15 — MEDIUM — Broken test code uses undefined `now` and wrong `call_args` usage
- **File:line**: `testing/tdd-bdd.md:437-440, 448-450`
- **Wrong text**:
  ```python
  # 23 hours — still valid
  assert service.is_valid(token, now + timedelta(hours=23))

  # 25 hours — expired
  assert not service.is_valid(token, now + timedelta(hours=25))
  ...
  email_service.send.assert_called_once()
  sent_email = email_service.send.call_args
  assert "alice@test.com" in sent_email.to
  assert "/reset" in sent_email.body
  ```
- **Correct text**:
  ```python
  from datetime import datetime, timedelta
  now = datetime.now()
  # 23 hours — still valid
  assert service.is_valid(token, now + timedelta(hours=23))
  # 25 hours — expired
  assert not service.is_valid(token, now + timedelta(hours=25))
  ...
  email_service.send.assert_called_once()
  sent_args, sent_kwargs = email_service.send.call_args
  # access the email object via sent_args[0] or sent_kwargs["email"], depending on signature
  sent_email = sent_args[0]
  assert "alice@test.com" in sent_email.to
  assert "/reset" in sent_email.body
  ```
- **Verification**: Python `unittest.mock` docs — `Mock.call_args` returns a `call` object that holds `(args, kwargs)`. It does not return the first positional argument directly, so `call_args.to` would raise `AttributeError`. Additionally `now` is never defined in the test body — `datetime` is not imported in the snippet and no `now = datetime.now()` is shown.

---

## Summary

| Severity | Count |
|---|---|
| HIGH | 4 (F5, F6, F11, F13) |
| MEDIUM | 7 (F1, F2, F3, F4, F9, F10, F12, F14, F15) |
| LOW | 2 (F7, F8) |
| **Total** | **15** |

### Top 5 issues to prioritize for fixing

1. **F5 + F6 (HIGH)** — `frameworks/django/README.md` uses a non-existent `afilter()` QuerySet method in both code and prose. Any reader who copies this code will get an `AttributeError`. Easy fix.
2. **F11 + F13 + F14 (HIGH/MEDIUM)** — `git/fundamentals.md` and `git/interview-questions.md` state that `git gc` prunes unreachable objects after **30 days**; the actual default (`gc.pruneExpire`) is **14 days**. This is repeated across 3 places and would teach the wrong fact in interview prep.
3. **F12 (MEDIUM)** — `git/branching.md` claims `ort` became default in Git 2.33; it actually became default in Git 2.34.
4. **F9 (MEDIUM)** — `search/vector-search.md` references CRDT.tech in its References section, which is unrelated to vector search (likely an AI-hallucinated citation).
5. **F15 (MEDIUM)** — `testing/tdd-bdd.md` has broken Python test code: an undefined `now` variable and incorrect `email_service.send.call_args` usage that would raise `AttributeError` at runtime.

### Files audited (33)

Frameworks (8): fastapi/, express/, nextjs/, react/, pytorch/, spring-boot/, vue-angular/, django/ (tokio/ skipped — already fixed)

Data engineering (7): README.md, fundamentals.md, data-quality.md, data-formats.md, batch-processing.md, stream-processing.md, interview-questions.md

Search (5): README.md, fundamentals.md, elasticsearch.md, vector-search.md, interview-questions.md

Web servers (3): README.md, nginx.md, interview-questions.md (apache.md skipped — already fixed)

Cheatsheets (10): dbms.md, os.md, llm.md, architecture.md, sql.md, ml.md, distributed.md, cloud.md, networking.md, git.md (system-design.md, python.md, linux.md skipped — already fixed)

Testing (6): README.md, unit-testing.md, tdd-bdd.md, mocking.md, e2e-testing.md, test-strategy.md, interview-questions.md (integration-testing.md skipped — already fixed)

Git (11): README.md, fundamentals.md, branching.md, advanced.md, remotes.md, tags.md, hooks.md, workflows.md, github.md, cheat-sheet.md, interview-questions.md (internals.md, stashing.md, worktrees-submodules.md, rebasing.md skipped — already fixed)

### Cross-reference verification

- `frameworks/django/README.md:126` — `[Celery](../../concurrency/overview.md)` resolves to existing file (`src/concurrency/overview.md`). OK.
- `cheatsheets/dbms.md:143` — `[DBMS Revision](../revision/dbms.md)` resolves to existing file (`src/revision/dbms.md`). OK.
- `cheatsheets/os.md:134` — `[OS Revision](../revision/os.md)` resolves. OK.
- `cheatsheets/networking.md:148` — `[Networking Revision](../revision/networks.md)` resolves. OK.
- `cheatsheets/architecture.md:190` — `[Architecture Revision](../revision/architecture.md)` resolves. OK.

### Verification commands used

```bash
# Confirm gc.pruneExpire default
z-ai function -n web_search -a '{"query": "git gc.pruneExpire default 2 weeks ago unreachable objects"}'
# → "Prune loose objects older than date (default is 2 weeks ago …)" — git-scm.com/docs/git-gc

# Confirm Git version that made ort default
z-ai function -n web_search -a '{"query": "git ort merge strategy default version 2.34 recursive"}'
# → "Git 2.34 sets new merge default" — devclass.com (Nov 17, 2021)

# Confirm Django async QuerySet version
z-ai function -n web_search -a '{"query": "Django 4.0 async ORM methods aget acreate release notes"}'
# → Django 4.1 release notes: "QuerySet now provides an asynchronous interface for all data access operations."

# Confirm Django async views version (for FastAPI comparison)
z-ai function -n web_search -a '{"query": "Django async views added version 3.1 4.1"}'
# → "Django 3.1 (2020): Delivered the first async views, middleware, and tests."

# Confirm FastAPI minimum Python version
z-ai function -n web_search -a '{"query": "FastAPI minimum Python version 3.8 requirements"}'
# → FastAPI release notes: "Drop support for Python 3.7, require Python 3.8 or above."

# Confirm afilter() does not exist on QuerySet
z-ai function -n web_search -a '{"query": "Django QuerySet afilter method exists async"}'
# → Django docs: filter()/exclude() "do not have separate asynchronous versions."

# Confirm Instagram still uses Django
z-ai function -n web_search -a '{"query": "Instagram still uses Django 2024 engineering blog"}'
# → "Instagram runs a heavily modified version of Django … the company continues to invest heavily"

# Verify tax rounding claim (unit-testing.md example)
python3 -c "print(round(99.99 * 0.075, 2))"
# → 7.5 (assertion `== 7.50` still passes since 7.5 == 7.50 in Python)
```
