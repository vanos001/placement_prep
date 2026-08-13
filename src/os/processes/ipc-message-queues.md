# Message Queues

## Overview

**Message queues** allow processes to exchange data in discrete **messages** rather than a continuous byte stream. Unlike pipes, message queues preserve message boundaries and can support priorities.

> **Interview one-liner:** "Message queues are IPC mechanisms that pass discrete, typed messages between processes — unlike pipes, they preserve message boundaries and support priorities."

## POSIX vs System V Message Queues

| Feature | POSIX (`mqueue`) | System V (`msgget`) |
|---------|-----------------|---------------------|
| API style | File-like (`mq_open`, `mq_send`) | System call (`msgget`, `msgsnd`) |
| Naming | `/name` (like filesystem) | Integer key (`ftok()`) |
| Message priority | Yes (0 to `MQ_PRIO_MAX`) | Yes (type field) |
| Notification | Signal or thread on arrival | None built-in |
| Max messages | Configurable | `MSGMNI` limit |
| Max message size | `MQ_MSGSIZE` limit | `MSGMAX` limit |
| Persistence | Removed when all closed | Persists until `msgctl(IPC_RMID)` |
| Linux support | Requires `CONFIG_POSIX_MQUEUE` | Always built-in |

## POSIX Message Queue API

### Creation and Opening

```c
#include <mqueue.h>
#include <fcntl.h>
#include <sys/stat.h>

// Create or open a message queue
mqd_t mq = mq_open("/myqueue", O_CREAT | O_RDWR, 0644, NULL);

// With attributes
struct mq_attr attr = {
    .mq_flags = 0,
    .mq_maxmsg = 10,      // Max messages in queue
    .mq_msgsize = 256,     // Max message size
    .mq_curmsgs = 0        // Current messages (read-only)
};
mqd_t mq = mq_open("/myqueue", O_CREAT | O_RDWR, 0644, &attr);
```

### Sending and Receiving

```c
// Send a message
const char *msg = "Hello, queue!";
mq_send(mq, msg, strlen(msg), 0);  // priority 0

// Send with priority
mq_send(mq, msg, strlen(msg), 5);  // priority 5 (higher = more urgent)

// Receive a message
char buffer[256];
unsigned int priority;
ssize_t len = mq_receive(mq, buffer, sizeof(buffer), &priority);
printf("Received: %.*s (priority: %u)\n", (int)len, buffer, priority);

// Non-blocking send/receive
mq_send(mq, msg, strlen(msg), 0);  // blocks if full
// or set O_NONBLOCK flag
```

### Example: Producer-Consumer

```c
#include <mqueue.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/wait.h>

#define QUEUE_NAME "/example_queue"
#define MAX_MSG_SIZE 256

int main() {
    mqd_t mq;
    pid_t pid;
    
    // Create queue
    struct mq_attr attr = {0, 10, MAX_MSG_SIZE, 0};
    mq = mq_open(QUEUE_NAME, O_CREAT | O_RDWR, 0644, &attr);
    
    pid = fork();
    
    if (pid == 0) {
        // Producer
        mqd_t mq = mq_open(QUEUE_NAME, O_WRONLY);
        for (int i = 0; i < 5; i++) {
            char msg[MAX_MSG_SIZE];
            snprintf(msg, sizeof(msg), "Message %d", i);
            mq_send(mq, msg, strlen(msg) + 1, 0);
            printf("Sent: %s\n", msg);
            usleep(100000);
        }
        mq_close(mq);
        exit(0);
    } else {
        // Consumer
        mqd_t mq = mq_open(QUEUE_NAME, O_RDONLY);
        char buffer[MAX_MSG_SIZE];
        unsigned int prio;
        
        for (int i = 0; i < 5; i++) {
            ssize_t len = mq_receive(mq, buffer, sizeof(buffer), &prio);
            printf("Received: %.*s\n", (int)len, buffer);
        }
        
        wait(NULL);
        mq_close(mq);
        mq_unlink(QUEUE_NAME);
    }
    
    return 0;
}
```

### Async Notification

```c
#include <signal.h>

void notification_handler(union sigval sv) {
    mqd_t mq = *(mqd_t *)sv.sival_ptr;
    char buffer[256];
    unsigned int prio;
    
    ssize_t len = mq_receive(mq, buffer, sizeof(buffer), &prio);
    printf("Async received: %.*s\n", (int)len, buffer);
    
    // Re-register for next notification
    struct sigevent sev;
    sev.sigev_notify = SIGEV_THREAD;
    sev.sigev_notify_function = notification_handler;
    sev.sigev_notify_attributes = NULL;
    sev.sigev_value.sival_ptr = &mq;
    mq_notify(mq, &sev);
}

// Register for notification
struct sigevent sev;
sev.sigev_notify = SIGEV_THREAD;
sev.sigev_notify_function = notification_handler;
sev.sigev_notify_attributes = NULL;
sev.sigev_value.sival_ptr = &mq;
mq_notify(mq, &sev);
```

## System V Message Queue API

### Creation

```c
#include <sys/ipc.h>
#include <sys/msg.h>

// Generate a key
key_t key = ftok("/tmp/myfile", 'A');

// Create message queue
int msqid = msgget(key, IPC_CREAT | 0644);
```

### Message Structure

```c
struct msgbuf {
    long mtype;       // Message type (must be > 0)
    char mtext[256];  // Message data
};

// Send
struct msgbuf msg;
msg.mtype = 1;  // Type 1
strcpy(msg.mtext, "Hello!");
msgsnd(msqid, &msg, strlen(msg.mtext) + 1, 0);

// Receive (type 0 = any type, >0 = specific type)
struct msgbuf msg;
ssize_t len = msgrcv(msqid, &msg, sizeof(msg.mtext), 0, 0);
// or receive only type 2:
ssize_t len = msgrcv(msqid, &msg, sizeof(msg.mtext), 2, 0);
```

### Priority with Message Types

Message types enable priority-based consumption:

```c
// Producer sends different priority messages
struct msgbuf urgent; urgent.mtype = 1; strcpy(urgent.mtext, "URGENT");
struct msgbuf normal; normal.mtype = 5; strcpy(normal.mtext, "normal");
struct msgbuf low;    low.mtype = 10;  strcpy(low.mtext, "low priority");

msgsnd(msqid, &low, strlen(low.mtext) + 1, 0);
msgsnd(msqid, &urgent, strlen(urgent.mtext) + 1, 0);
msgsnd(msqid, &normal, strlen(normal.mtext) + 1, 0);

// Consumer receives lowest type number first (highest priority)
msgrcv(msqid, &msg, sizeof(msg.mtext), 0, 0);  // Gets "URGENT" (type 1)
```

## Message Queue Internals

```
┌─────────────────────────────────────────────┐
│              Message Queue                   │
│  ┌─────────────────────────────────────┐    │
│  │ Queue Header                        │    │
│  │  - max messages                     │    │
│  │  - current message count            │    │
│  │  - max message size                 │    │
│  │  - permissions                      │    │
│  └─────────────────────────────────────┘    │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐       │
│  │Msg 1 │→│Msg 2 │→│Msg 3 │→│Msg 4 │       │
│  │type=1│ │type=3│ │type=1│ │type=5│       │
│  │prio=H│ │prio=M│ │prio=H│ │prio=L│       │
│  └──────┘ └──────┘ └──────┘ └──────┘       │
│  ↑                                    ↑     │
│  Head                            Tail       │
└─────────────────────────────────────────────┘
```

### Blocking Behavior

| Operation | Default | `IPC_NOWAIT` / `O_NONBLOCK` |
|-----------|---------|---------------------------|
| `mq_send` / `msgsnd` (full) | Blocks until space | Returns -1, `errno = EAGAIN` |
| `mq_receive` / `msgrcv` (empty) | Blocks until message | Returns -1, `errno = EAGAIN` |

## Linux Limits and Configuration

```bash
# POSIX message queue limits
cat /proc/sys/fs/mqueue/msg_max       # Max messages per queue (default: 10)
cat /proc/sys/fs/mqueue/msgsize_max   # Max message size (default: 8192)
cat /proc/sys/fs/mqueue/queues_max    # Max queues system-wide (default: 256)

# System V message queue limits
ipcs -q    # List queues
cat /proc/sys/kernel/msgmni   # Max queues (default: 32000)
cat /proc/sys/kernel/msgmax   # Max message size (default: 8192)
cat /proc/sys/kernel/msgmnb   # Max queue size in bytes (default: 16384)
```

## Interview Questions

### Beginner

**Q1: What is a message queue?**  
A: A message queue is an IPC mechanism where processes send and receive discrete messages. Unlike pipes (byte streams), message queues preserve message boundaries and can support message priorities.

**Q2: What is the difference between a pipe and a message queue?**  
A: Pipes are byte streams (no message boundaries), unidirectional, and typically used between related processes. Message queues pass discrete messages (boundaries preserved), can be accessed by unrelated processes, and support priorities.

### Intermediate

**Q3: How do message types work in System V message queues?**  
A: Each message has a `mtype` field (positive integer). Receivers can specify which type to receive: 0 = any type, >0 = specific type. This enables priority-based queuing (lower type = higher priority) and selective consumption.

**Q4: When would you choose POSIX over System V message queues?**  
A: POSIX queues: cleaner API, file-like interface, async notification support, better for new code. System V queues: always available on Linux, persist after process exit (useful for recovery), type-based selective receive. For new projects, POSIX is generally preferred.

**Q5: What happens when a message queue is full?**  
A: `mq_send()`/`msgsnd()` blocks by default until space is available. With `IPC_NOWAIT`/`O_NONBLOCK`, it returns immediately with an error (`EAGAIN`).

### FAANG-Level

**Q6: Design a priority-based task distribution system using message queues.**  
A: Use message types for priority levels (1 = critical, 2 = high, 3 = normal, 4 = low). Workers call `msgrcv(msqid, &msg, size, 0, 0)` to receive the highest-priority message. For starvation prevention: implement aging — periodically increase priority of long-waiting messages. Alternative: use POSIX queues with different priorities or multiple queues with a dispatcher.

**Q7: Compare message queues with publish-subscribe systems like Kafka.**  
A: Message queues: point-to-point, message consumed once, kernel-managed, limited scalability. Kafka: pub-sub, messages persisted and consumed by multiple subscribers, distributed, horizontally scalable, supports replay. Use kernel message queues for simple IPC on a single machine; use Kafka for distributed event streaming.

**Q8: How would you implement reliable message delivery with message queues?**  
A: 1) **Persistence:** System V queues persist across process crashes, 2) **Acknowledgments:** Receiver sends ack; sender retransmits on timeout, 3) **Dead letter queue:** Failed messages go to a separate queue for inspection, 4) **Idempotency:** Include message IDs; receiver deduplicates, 5) **Transactions:** Group related messages; commit/rollback semantics. Note: kernel message queues don't natively support all of this — application-level logic needed.

## Common Mistakes

1. **Forgetting to clean up:** System V queues persist until explicitly removed (`msgctl(IPC_RMID)`). POSIX queues need `mq_unlink()`.
2. **Ignoring message size limits:** Messages exceeding `MSGMAX` or `mq_msgsize` will fail.
3. **Not handling `SIGPIPE` equivalent:** Message queues don't generate SIGPIPE, but `msgsnd` can fail if the queue is removed.
4. **Assuming FIFO ordering within same priority:** System V queues are FIFO within the same message type. POSIX queues are FIFO within the same priority.
5. **Memory leak with large messages:** Allocating large message buffers in a tight loop without freeing.

## Summary

| Feature | POSIX MQ | System V MQ |
|---------|----------|-------------|
| API | `mq_open/send/receive/close` | `msgget/msgsnd/msgrcv/msgctl` |
| Naming | String (`/name`) | Key (`ftok()`) |
| Priority | Integer priority | Message type field |
| Notification | Signal/thread | None |
| Persistence | Until `mq_unlink` | Until `msgctl(IPC_RMID)` |
| Max msg size | 8192 (default) | 8192 (default) |

## Cross-References

- [IPC Overview](./ipc.md) - All IPC mechanisms
- [Pipes](./ipc-pipes.md) - Simpler byte-stream IPC
- [Shared Memory](./ipc-shared-memory.md) - Faster alternative
- [Sockets](./ipc-sockets.md) - Network-capable alternative
- [Semaphores](../synchronization/semaphores.md) - Synchronization with queues


## Cross References

- [IPC Overview](ipc.md)
- [Message Queues](../../distributed/messaging/queues.md)
- [Kafka](../../distributed/messaging/kafka.md)
- [Sockets](ipc-sockets.md)
