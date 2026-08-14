# Real-Time Leaderboard — Machine Coding Problem

## Problem Statement

Design a real-time leaderboard system that maintains ranked scores for players, supports efficient score updates, retrieves top-K players with pagination, and handles concurrent updates from thousands of simultaneous users.

## Requirements Gathering

### Functional Requirements
1. Add or update a player's score
2. Retrieve the top-K players (ranked by score, highest first)
3. Get a specific player's rank and score
4. Paginated retrieval of the full leaderboard
5. Support multiple leaderboards (daily, weekly, all-time)
6. Handle ties (same score — order by timestamp of achievement)
7. Efficient rank computation on every update

### Non-Functional Requirements
- Score update latency < 10ms
- Top-K retrieval < 5ms for K = 100
- Thread-safe concurrent updates
- Handle 10,000+ score updates per second

### Clarifying Questions
- "Are scores monotonically increasing (like in gaming), or can they decrease?"
- "What's the expected player count — hundreds, thousands, millions?"
- "Should there be a separate leaderboard per game/region?"
- "How frequently is the leaderboard queried vs. updated?"

## Class Design

### Entity Identification
```
Nouns: Leaderboard, Player, Score, Entry, Rank, LeaderboardType
```

### Class Diagram

```
┌───────────────────────────┐
│      Leaderboard            │
├───────────────────────────┤
│ - name: String             │
│ - entries: Map<playerId, Entry>│
│ - sorted: bool             │
│ - dirty: bool              │
├───────────────────────────┤
│ + updateScore(playerId, score)│
│ + getTopK(k): List<Entry> │
│ + getPlayerRank(playerId)│
│ + getPlayerEntry(playerId)│
│ + getPaginated(page, size)│
│ + getSize(): int           │
└───────────────────────────┘
              │
              ▼
┌───────────────────────────┐
│     Entry                  │
├───────────────────────────┤
│ - playerId: String        │
│ - score: float            │
│ - lastUpdated: DateTime   │
│ - rank: int               │
├───────────────────────────┤
│ + updateScore(newScore)   │
│ + compareTo(other): int   │
└───────────────────────────┘
```

### Data Structure Choices

| Approach | Update | Top-K | Rank Lookup | Notes |
|---------|--------|-------|-------------|-------|
| Sorted array | O(N) | O(K) | O(1) | Simple, good for reads |
| Heap (max) | O(log N) | O(K log N) | O(N) | Good for top-K only |
| Balanced BST (Skip list) | O(log N) | O(K) | O(log N) | Best overall |
| Sortedcontainers (Python) | O(log N) | O(K) | O(log N) | Practical choice |

## Implementation

### Python Implementation (Sorted List Approach)

```python
import threading
from datetime import datetime
from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass, field
from bisect import insort, bisect_left


@dataclass
class Entry:
    player_id: str
    score: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)
    rank: int = 0

    def __lt__(self, other):
        """Higher scores come first. Ties broken by earlier update time."""
        if self.score != other.score:
            return self.score > other.score  # descending
        return self.last_updated < other.last_updated

    def __eq__(self, other):
        return (self.player_id == other.player_id
                and self.score == other.score)


class Leaderboard:
    def __init__(self, name: str = "global"):
        self.name = name
        self._entries: Dict[str, Entry] = {}     # player_id → Entry
        self._sorted: List[Entry] = []            # sorted by score desc
        self._lock = threading.RLock()

    def update_score(self, player_id: str, score: float) -> int:
        """Update a player's score and return their new rank."""
        with self._lock:
            # Remove old entry if exists
            if player_id in self._entries:
                old = self._entries[player_id]
                try:
                    self._sorted.remove(old)
                except ValueError:
                    pass

            # Create or update entry
            if player_id in self._entries:
                entry = self._entries[player_id]
                entry.score = score
                entry.last_updated = datetime.now()
            else:
                entry = Entry(player_id=player_id, score=score)
                self._entries[player_id] = entry

            # Insert into sorted list
            insort(self._sorted, entry)

            # Compute rank
            rank = self._sorted.index(entry) + 1
            entry.rank = rank
            return rank

    def get_top_k(self, k: int = 10) -> List[Entry]:
        """Get the top K players."""
        with self._lock:
            return list(self._sorted[:k])

    def get_player_rank(self, player_id: str) -> Optional[int]:
        """Get the rank of a specific player."""
        with self._lock:
            entry = self._entries.get(player_id)
            if entry:
                return entry.rank
            return None

    def get_player_entry(self, player_id: str) -> Optional[Entry]:
        """Get a player's full entry."""
        with self._lock:
            return self._entries.get(player_id)

    def get_paginated(self, page: int, page_size: int = 10) -> Tuple[List[Entry], dict]:
        """Get a page of the leaderboard with pagination metadata."""
        with self._lock:
            total = len(self._sorted)
            total_pages = (total + page_size - 1) // page_size
            start = (page - 1) * page_size
            end = start + page_size
            entries = self._sorted[start:end]
            meta = {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
            }
            return list(entries), meta

    def get_size(self) -> int:
        with self._lock:
            return len(self._sorted)

    def get_neighbours(self, player_id: str, count: int = 3) -> dict:
        """Get players around the given player (above and below)."""
        with self._lock:
            entry = self._entries.get(player_id)
            if not entry:
                return {"above": [], "self": None, "below": []}
            idx = self._sorted.index(entry)
            above = self._sorted[max(0, idx - count):idx]
            below = self._sorted[idx + 1:idx + 1 + count]
            return {
                "above": [e.rank for e in reversed(above)],
                "self": {"rank": entry.rank, "score": entry.score},
                "below": [e.rank for e in below],
            }

    def display(self, k: int = 10):
        """Display the top K players."""
        with self._lock:
            print(f"\n{'='*40}")
            print(f"  Leaderboard: {self.name}")
            print(f"{'='*40}")
            for entry in self._sorted[:k]:
                medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(entry.rank, "  ")
                print(f"  {medal} #{entry.rank:<4} {entry.player_id:<20} "
                      f"{entry.score:>10.1f}")
            if len(self._sorted) > k:
                print(f"  ... and {len(self._sorted) - k} more players")
            print(f"{'='*40}\n")


class MultiLeaderboardManager:
    """Manages multiple leaderboards (daily, weekly, all-time)."""

    def __init__(self):
        self.boards: Dict[str, Leaderboard] = {}
        self._lock = threading.Lock()

    def register(self, name: str, board: Leaderboard):
        with self._lock:
            self.boards[name] = board

    def get(self, name: str) -> Optional[Leaderboard]:
        return self.boards.get(name)

    def update_all(self, player_id: str, score: float) -> Dict[str, int]:
        """Update score across all registered leaderboards."""
        results = {}
        for name, board in self.boards.items():
            rank = board.update_score(player_id, score)
            results[name] = rank
        return results


def main():
    lb = Leaderboard("Global High Scores")

    # Simulate score updates
    import random
    players = [f"Player_{i:03d}" for i in range(1, 51)]

    for pid in players:
        score = random.uniform(100, 10000)
        lb.update_score(pid, score)

    lb.display(15)

    # Update a specific player
    rank = lb.update_score("Player_007", 99999.9)
    print(f"Player_007 updated to rank {rank}")

    lb.display(10)

    # Get neighbours
    neighbours = lb.get_neighbours("Player_007", count=2)
    print(f"\nPlayer_007's neighbours: {neighbours}")

    # Pagination
    entries, meta = lb.get_paginated(page=2, page_size=10)
    print(f"\nPage {meta['page']}/{meta['total_pages']}:")
    for e in entries:
        print(f"  #{e.rank} {e.player_id} — {e.score:.1f}")


if __name__ == "__main__":
    main()
```

## Scaling Discussion

### The N-Sorting Problem
The `bisect.insort` approach has O(N) insertion because Python lists shift elements. For 10K+ players, this becomes noticeable. Alternatives:

| Scale | Recommended Data Structure |
|-------|---------------------------|
| < 10K players | Sorted array with bisect (simple, sufficient) |
| 10K–100K players | Skip list or balanced BST |
| 100K+ players | Redis Sorted Set (ZSET) — O(log N) operations built-in |
| Millions of players | Sharded leaderboards by region/skill group |

### Redis ZSET Approach (Production)

Redis provides sorted sets natively:
```
ZADD leaderboard 9500 "player_001"   # O(log N)
ZREVRANGE leaderboard 0 9            # Top 10 — O(log(N)+K)
ZREVRANK leaderboard "player_001"    # Rank — O(log N)
```

This is the industry-standard approach for game leaderboards. In an interview, mentioning this shows production awareness.

## Extensions and Discussion Points

### 1. Score Decay
Implement time-based decay: `effective_score = raw_score * decay_factor^hours_since_update`. This prevents stale scores from dominating all-time leaderboards.

### 2. Tiered Leaderboards
Partition players into tiers (Bronze, Silver, Gold, Diamond) based on score ranges, each with its own leaderboard.

### 3. Snapshot Leaderboards
Take periodic snapshots (daily at midnight, weekly on Sunday) and freeze them. Current play goes into a "live" board that resets each period.

### 4. Cache Warming
Pre-compute and cache the top-100 result, invalidating only when updates affect the top-100 region.

## Complexity Analysis

| Operation | Sorted List | Redis ZSET |
|-----------|-------------|-------------|
| Update score | O(N) | O(log N) |
| Top-K | O(K) | O(log N + K) |
| Rank lookup | O(N) or O(log N) with dict | O(log N) |
| Pagination | O(page_size) | O(log N + page_size) |

## Interview Tips

1. **Start with the simple sorted-list approach**, then discuss how to scale it
2. **Mention Redis ZSET** as the production solution — it's the expected answer
3. **Discuss tie-breaking**: timestamp of last update vs. alphabetical vs. random
4. **Concurrent updates**: `threading.RLock` for in-memory; Redis handles atomicity natively
5. **The write-heavy vs. read-heavy trade-off**: gaming leaderboards are both; Redis handles this well
6. **Discuss partitioning**: for millions of players, shard by region or score range
