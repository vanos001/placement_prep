# Library Management System — Machine Coding Problem

## Problem Statement

Design a library management system that handles book cataloging, member management, borrowing, returning, reservations, and fine calculation.

## Requirements

### Functional Requirements
1. Add/remove books to the catalog
2. Register library members
3. Borrow and return books
4. Track book availability (copies)
5. Reserve books when all copies are borrowed
6. Calculate fines for late returns
7. Search books by title, author, ISBN, genre
8. View borrowing history for a member

### Non-Functional Requirements
- Handle concurrent borrow/return operations
- Efficient search (consider indexing)
- Configurable fine rates and borrowing limits

## Class Design

```
┌──────────────────────────────────────────────────────────┐
│                     LibrarySystem                         │
├──────────────────────────────────────────────────────────┤
│ - catalog: BookCatalog                                   │
│ - memberRegistry: MemberRegistry                         │
│ - borrowingService: BorrowingService                     │
│ - fineCalculator: FineCalculator                         │
├──────────────────────────────────────────────────────────┤
│ + addBook(book, copies)                                  │
│ + registerMember(member)                                 │
│ + borrowBook(memberId, isbn): Receipt                    │
│ + returnBook(memberId, isbn): Receipt                    │
│ + reserveBook(memberId, isbn)                            │
│ + searchBooks(query): List<Book>                         │
│ + getMemberHistory(memberId): List<Transaction>          │
└──────────────────────────────────────────────────────────┘

┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│    Book       │    │  BookItem    │    │    Author     │
├──────────────┤    ├──────────────┤    ├──────────────┤
│ - isbn        │◄───│ - itemId     │    │ - authorId   │
│ - title       │    │ - book (ref) │    │ - name       │
│ - authors     │    │ - condition  │    │ - bio        │
│ - genre       │    │ - status     │    └──────────────┘
│ - publishYear │    └──────────────┘
├──────────────┘              │
│ + getAuthors() |            │
│ + isAvailable()│     ┌──────┴───────┐
└──────────────┘     │ BookStatus    │
                     ├──────────────┤
                     │ AVAILABLE    │
                     │ BORROWED     │
                     │ RESERVED     │
                     │ LOST         │
                     │ MAINTENANCE  │
                     └──────────────┘

┌──────────────┐    ┌──────────────────┐    ┌──────────────┐
│   Member     │    │  BorrowRecord    │    │  Reservation  │
├──────────────┤    ├──────────────────┤    ├──────────────┤
│ - memberId   │───>│ - recordId       │    │ - reservationId│
│ - name       │    │ - member (ref)   │    │ - member      │
│ - email      │    │ - bookItem (ref) │    │ - book        │
│ - borrowedBooks│   │ - borrowDate     │    │ - reserveDate │
│ - borrowLimit │    │ - dueDate        │    │ - status      │
├──────────────┤    │ - returnDate     │    └──────────────┘
│ + canBorrow()│    │ - fine: double   │
│ + borrow()   │    └──────────────────┘
│ + returnBook()│
└──────────────┘

┌──────────────────┐    ┌──────────────────┐
│  FineCalculator  │    │  BookCatalog     │
├──────────────────┤    ├──────────────────┤
│ - ratePerDay     │    │ - books: Map     │
├──────────────────┤    │ - searchIndex    │
│ + calculate()    │    ├──────────────────┤
│ + waive()        │    │ + addBook()      │
└──────────────────┘    │ + search()       │
                        │ + findByISBN()   │
                        └──────────────────┘
```

## Implementation (Python)

```python
from enum import Enum
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from dataclasses import dataclass, field
import uuid


# ==================== Enums ====================

class BookStatus(Enum):
    AVAILABLE = "available"
    BORROWED = "borrowed"
    RESERVED = "reserved"
    LOST = "lost"
    MAINTENANCE = "maintenance"


class BookCondition(Enum):
    NEW = "new"
    GOOD = "good"
    WORN = "worn"
    DAMAGED = "damaged"


class Genre(Enum):
    FICTION = "fiction"
    NON_FICTION = "non_fiction"
    SCIENCE = "science"
    TECHNOLOGY = "technology"
    HISTORY = "history"
    BIOGRAPHY = "biography"


# ==================== Models ====================

@dataclass
class Author:
    author_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    bio: str = ""


@dataclass
class Book:
    isbn: str
    title: str
    authors: List[Author] = field(default_factory=list)
    genre: Genre = Genre.FICTION
    publish_year: int = 0

    def __str__(self):
        author_names = ", ".join(a.name for a in self.authors)
        return f"'{self.title}' by {author_names} ({self.isbn})"


@dataclass
class BookItem:
    """Represents a physical copy of a book."""
    item_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    book: Optional[Book] = None
    condition: BookCondition = BookCondition.GOOD
    status: BookStatus = BookStatus.AVAILABLE

    def is_available(self) -> bool:
        return self.status == BookStatus.AVAILABLE


@dataclass
class Member:
    member_id: str
    name: str
    email: str
    borrow_limit: int = 5
    borrowed_items: List[str] = field(default_factory=list)  # item_ids
    borrow_history: List[str] = field(default_factory=list)  # record_ids

    def can_borrow(self) -> bool:
        return len(self.borrowed_items) < self.borrow_limit

    def __str__(self):
        return f"Member {self.member_id}: {self.name} " \
               f"({len(self.borrowed_items)}/{self.borrow_limit} borrowed)"


@dataclass
class BorrowRecord:
    record_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    member_id: str = ""
    item_id: str = ""
    book_title: str = ""
    borrow_date: datetime = field(default_factory=datetime.now)
    due_date: datetime = field(default_factory=lambda: datetime.now() + timedelta(days=14))
    return_date: Optional[datetime] = None
    fine: float = 0.0

    @property
    def is_returned(self) -> bool:
        return self.return_date is not None

    @property
    def is_overdue(self) -> bool:
        check_date = self.return_date or datetime.now()
        return check_date > self.due_date


@dataclass
class Reservation:
    reservation_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    member_id: str = ""
    isbn: str = ""
    reserve_date: datetime = field(default_factory=datetime.now)
    status: str = "active"  # active, fulfilled, cancelled


# ==================== Services ====================

class FineCalculator:
    def __init__(self, rate_per_day: float = 1.0, max_fine: float = 50.0):
        self.rate_per_day = rate_per_day
        self.max_fine = max_fine

    def calculate(self, due_date: datetime, 
                  return_date: datetime = None) -> float:
        check_date = return_date or datetime.now()
        if check_date <= due_date:
            return 0.0
        overdue_days = (check_date - due_date).days
        fine = min(overdue_days * self.rate_per_day, self.max_fine)
        return round(fine, 2)


class BookCatalog:
    def __init__(self):
        self.books: Dict[str, Book] = {}           # isbn -> Book
        self.items: Dict[str, BookItem] = {}        # item_id -> BookItem
        self.isbn_items: Dict[str, List[str]] = {}  # isbn -> [item_ids]
        self.title_index: Dict[str, List[str]] = {} # lowercase word -> [isbns]
        self.author_index: Dict[str, List[str]] = {}# author_name_lower -> [isbns]

    def add_book(self, book: Book, copies: int = 1):
        if book.isbn in self.books:
            # Add more copies
            for _ in range(copies):
                item = BookItem(book=book)
                self.items[item.item_id] = item
                self.isbn_items[book.isbn].append(item.item_id)
        else:
            self.books[book.isbn] = book
            self.isbn_items[book.isbn] = []
            for _ in range(copies):
                item = BookItem(book=book)
                self.items[item.item_id] = item
                self.isbn_items[book.isbn].append(item.item_id)
            self._index_book(book)

    def _index_book(self, book: Book):
        for word in book.title.lower().split():
            self.title_index.setdefault(word, []).append(book.isbn)
        for author in book.authors:
            self.author_index.setdefault(
                author.name.lower(), []).append(book.isbn)

    def get_available_item(self, isbn: str) -> Optional[BookItem]:
        if isbn not in self.isbn_items:
            return None
        for item_id in self.isbn_items[isbn]:
            item = self.items[item_id]
            if item.is_available():
                return item
        return None

    def get_item(self, item_id: str) -> Optional[BookItem]:
        return self.items.get(item_id)

    def search_by_title(self, query: str) -> List[Book]:
        words = query.lower().split()
        isbn_sets = []
        for word in words:
            matches = set()
            for key, isbns in self.title_index.items():
                if word in key:
                    matches.update(isbns)
            isbn_sets.append(matches)
        if not isbn_sets:
            return []
        result_isbns = isbn_sets[0]
        for s in isbn_sets[1:]:
            result_isbns &= s
        return [self.books[isbn] for isbn in result_isbns if isbn in self.books]

    def search_by_author(self, author_name: str) -> List[Book]:
        isbns = self.author_index.get(author_name.lower(), [])
        return [self.books[isbn] for isbn in isbns if isbn in self.books]

    def get_availability(self, isbn: str) -> Dict:
        if isbn not in self.isbn_items:
            return {"total": 0, "available": 0, "borrowed": 0}
        items = [self.items[iid] for iid in self.isbn_items[isbn]]
        available = sum(1 for i in items if i.is_available())
        return {
            "total": len(items),
            "available": available,
            "borrowed": len(items) - available
        }


class BorrowingService:
    BORROW_DAYS = 14

    def __init__(self, catalog: BookCatalog, fine_calculator: FineCalculator):
        self.catalog = catalog
        self.fine_calc = fine_calculator
        self.records: Dict[str, BorrowRecord] = {}
        self.reservations: Dict[str, List[Reservation]] = {}  # isbn -> [reservations]

    def borrow(self, member: Member, isbn: str) -> BorrowRecord:
        if not member.can_borrow():
            raise ValueError(
                f"Borrow limit reached ({member.borrow_limit})")

        item = self.catalog.get_available_item(isbn)
        if not item:
            raise ValueError(f"No available copies for ISBN {isbn}")

        # Check if member already has a copy
        if item.item_id in member.borrowed_items:
            raise ValueError("Member already has this book")

        item.status = BookStatus.BORROWED
        member.borrowed_items.append(item.item_id)

        record = BorrowRecord(
            member_id=member.member_id,
            item_id=item.item_id,
            book_title=item.book.title,
            due_date=datetime.now() + timedelta(days=self.BORROW_DAYS)
        )
        self.records[record.record_id] = record
        member.borrow_history.append(record.record_id)
        return record

    def return_book(self, member: Member, 
                    item_id: str) -> tuple:
        if item_id not in member.borrowed_items:
            raise ValueError("Member doesn't have this book")

        item = self.catalog.get_item(item_id)
        if not item:
            raise ValueError(f"Item {item_id} not found")

        # Find the active borrow record
        record = None
        for rid in member.borrow_history:
            r = self.records[rid]
            if r.item_id == item_id and not r.is_returned:
                record = r
                break

        if not record:
            raise ValueError("No active borrow record found")

        record.return_date = datetime.now()
        record.fine = self.fine_calc.calculate(
            record.due_date, record.return_date)

        item.status = BookStatus.AVAILABLE
        member.borrowed_items.remove(item_id)

        # Check reservations
        isbn = item.book.isbn
        if isbn in self.reservations and self.reservations[isbn]:
            next_res = self.reservations[isbn].pop(0)
            next_res.status = "fulfilled"
            item.status = BookStatus.RESERVED
            print(f"  → Book reserved for member {next_res.member_id}")

        return record, record.fine

    def reserve(self, member: Member, isbn: str) -> Reservation:
        if isbn not in self.catalog.books:
            raise ValueError(f"Book with ISBN {isbn} not found")

        avail = self.catalog.get_availability(isbn)
        if avail["available"] > 0:
            raise ValueError("Book is available, no need to reserve")

        reservation = Reservation(
            member_id=member.member_id,
            isbn=isbn
        )
        self.reservations.setdefault(isbn, []).append(reservation)
        return reservation


class MemberRegistry:
    def __init__(self):
        self.members: Dict[str, Member] = {}

    def register(self, member_id: str, name: str, 
                 email: str, borrow_limit: int = 5) -> Member:
        if member_id in self.members:
            raise ValueError(f"Member {member_id} already exists")
        member = Member(member_id, name, email, borrow_limit)
        self.members[member_id] = member
        return member

    def get(self, member_id: str) -> Optional[Member]:
        return self.members.get(member_id)


# ==================== Main System ====================

class LibrarySystem:
    def __init__(self, fine_rate: float = 1.0):
        self.catalog = BookCatalog()
        self.members = MemberRegistry()
        self.fine_calc = FineCalculator(rate_per_day=fine_rate)
        self.borrowing = BorrowingService(self.catalog, self.fine_calc)

    def add_book(self, book: Book, copies: int = 1):
        self.catalog.add_book(book, copies)
        print(f"Added {copies}x {book}")

    def register_member(self, member_id: str, name: str, 
                       email: str) -> Member:
        member = self.members.register(member_id, name, email)
        print(f"Registered: {member}")
        return member

    def borrow_book(self, member_id: str, isbn: str) -> BorrowRecord:
        member = self.members.get(member_id)
        if not member:
            raise ValueError(f"Member {member_id} not found")
        record = self.borrowing.borrow(member, isbn)
        print(f"{member.name} borrowed '{record.book_title}' "
              f"(due: {record.due_date.strftime('%Y-%m-%d')})")
        return record

    def return_book(self, member_id: str, 
                    item_id: str) -> tuple:
        member = self.members.get(member_id)
        if not member:
            raise ValueError(f"Member {member_id} not found")
        record, fine = self.borrowing.return_book(member, item_id)
        fine_str = f", fine: ${fine}" if fine > 0 else ""
        print(f"{member.name} returned '{record.book_title}'{fine_str}")
        return record, fine

    def reserve_book(self, member_id: str, isbn: str) -> Reservation:
        member = self.members.get(member_id)
        if not member:
            raise ValueError(f"Member {member_id} not found")
        reservation = self.borrowing.reserve(member, isbn)
        print(f"{member.name} reserved book (ISBN: {isbn})")
        return reservation

    def search(self, query: str) -> List[Book]:
        results = self.catalog.search_by_title(query)
        if not results:
            results = self.catalog.search_by_author(query)
        return results

    def display_catalog(self):
        print(f"\n{'='*60}")
        print("  Library Catalog")
        print(f"{'='*60}")
        for isbn, book in self.catalog.books.items():
            avail = self.catalog.get_availability(isbn)
            print(f"  {book}")
            print(f"    Available: {avail['available']}/{avail['total']} "
                  f"copies")
        print(f"{'='*60}\n")


# ==================== Demo ====================

def main():
    lib = LibrarySystem(fine_rate=2.0)

    # Add books
    author1 = Author(name="J.K. Rowling")
    author2 = Author(name="George Orwell")
    author3 = Author(name="Robert Martin")

    lib.add_book(Book("978-0747532743", "Harry Potter", [author1], Genre.FICTION), copies=3)
    lib.add_book(Book("978-0451524935", "1984", [author2], Genre.FICTION), copies=2)
    lib.add_book(Book("978-0132350884", "Clean Code", [author3], Genre.TECHNOLOGY), copies=1)

    # Register members
    lib.register_member("M001", "Alice", "alice@email.com")
    lib.register_member("M002", "Bob", "bob@email.com")

    # Borrow books
    lib.borrow_book("M001", "978-0747532743")
    lib.borrow_book("M002", "978-0747532743")
    lib.borrow_book("M001", "978-0451524935")

    lib.display_catalog()

    # Search
    results = lib.search("Harry")
    print(f"Search 'Harry': {[str(b) for b in results]}")

    # Reserve when no copies available
    lib.borrow_book("M002", "978-0132350884")  # last copy
    lib.reserve_book("M001", "978-0132350884")

    print("\nDemo complete!")


if __name__ == "__main__":
    main()
```

## Key Design Decisions

1. **Book vs BookItem**: `Book` is the abstract concept (ISBN), `BookItem` is a physical copy. One `Book` can have many `BookItem`s.

2. **Reservation Queue**: Reservations are FIFO — first person to reserve gets the book when returned.

3. **Fine Calculation**: Configurable rate per day with a maximum cap.

4. **Search Indexing**: Title and author indexes for O(1) lookup by keyword.

5. **Strategy Pattern**: FineCalculator is injectable — can swap different fine policies.

## Interview Follow-ups

1. **"How would you handle overdue notifications?"**
   → Observer pattern with a notification service

2. **"How would you add e-books?"**
   → Abstract `BookItem` → `PhysicalBookItem` and `EBookItem`

3. **"How would you handle multiple branches?"**
   → Each branch has its own catalog; system-level registry

4. **"How would you add a recommendation system?"**
   → Track borrowing patterns, suggest based on genre/author similarity
