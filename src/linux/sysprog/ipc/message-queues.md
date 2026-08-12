# Message Queues

## Introduction

Message queues provide a mechanism for processes to exchange data in discrete messages rather than continuous byte streams. Linux supports two distinct message queue interfaces: **System V IPC** (`msgget`, `msgsnd`, `msgrcv`) and **POSIX message queues** (`mq_open`, `mq_send`, `mq_receive`). Each has different semantics, performance characteristics, and use cases.

## System V Message Queues

### Overview

System V IPC is the older interface, originating from AT&T UNIX System V (1983). Messages are identified by a key (typically derived from a pathname via `ftok`) and have a type field that enables selective receiving.

### Creating a Queue

```c
#include <sys/ipc.h>
#include <sys/msg.h>
#include <stdio.h>

int main(void) {
    /* Generate a key from a pathname */
    key_t key = ftok("/tmp/myqueue", 42);
    if (key == -1) { perror("ftok"); return 1; }

    /* Create or access the queue */
    int msqid = msgget(key, IPC_CREAT | 0644);
    if (msqid == -1) { perror("msgget"); return 1; }

    printf("Queue ID: %d\n", msqid);
    return 0;
}
```

### Message Structure

Every message must start with a `long mtype` field:

```c
#include <sys/msg.h>

struct msgbuf {
    long mtype;      /* Message type (> 0) */
    char mtext[256]; /* Message data */
};
```

### Sending Messages

```c
#include <sys/ipc.h>
#include <sys/msg.h>
#include <stdio.h>
#include <string.h>

struct msgbuf {
    long mtype;
    char mtext[256];
};

int main(void) {
    key_t key = ftok("/tmp/myqueue", 42);
    int msqid = msgget(key, IPC_CREAT | 0644);

    struct msgbuf msg;
    msg.mtype = 1;  /* Message type 1 */
    strcpy(msg.mtext, "Hello from sender!");

    if (msgsnd(msqid, &msg, strlen(msg.mtext) + 1, 0) == -1) {
        perror("msgsnd");
        return 1;
    }
    printf("Sent: %s\n", msg.mtext);

    /* Non-blocking send */
    msg.mtype = 2;
    strcpy(msg.mtext, "Urgent message");
    if (msgsnd(msqid, &msg, strlen(msg.mtext) + 1, IPC_NOWAIT) == -1) {
        perror("msgsnd nonblock");
    }
    return 0;
}
```

### Receiving Messages

```c
#include <sys/ipc.h>
#include <sys/msg.h>
#include <stdio.h>
#include <string.h>

struct msgbuf {
    long mtype;
    char mtext[256];
};

int main(void) {
    key_t key = ftok("/tmp/myqueue", 42);
    int msqid = msgget(key, IPC_CREAT | 0644);

    struct msgbuf msg;

    /* Receive any message type */
    ssize_t len = msgrcv(msqid, &msg, sizeof(msg.mtext), 0, 0);
    if (len == -1) { perror("msgrcv"); return 1; }
    printf("Received (type %ld): %s\n", msg.mtype, msg.mtext);

    /* Receive only type 2 messages */
    len = msgrcv(msqid, &msg, sizeof(msg.mtext), 2, 0);
    if (len == -1) { perror("msgrcv type2"); return 1; }
    printf("Type 2: %s\n", msg.mtext);

    /* Receive with type filtering semantics */
    /* mtype > 0: exact match */
    /* mtype == 0: any type */
    /* mtype < 0: type ≤ |mtype| (lowest first) */
    len = msgrcv(msqid, &msg, sizeof(msg.mtext), -5, 0);
    /* Gets message with lowest type ≤ 5 */

    return 0;
}
```

### Type-Based Selective Receive

The `mtype` parameter in `msgrcv` enables powerful selective receive:

```c
/* Type filtering rules */
msgrcv(qid, &msg, size, 0, 0);   /* Any type, FIFO order */
msgrcv(qid, &msg, size, 1, 0);   /* Only type 1 */
msgrcv(qid, &msg, size, 5, 0);   /* Only type 5 */
msgrcv(qid, &msg, size, -3, 0);  /* Any type ≤ 3, lowest first */
msgrcv(qid, &msg, size, -1, 0);  /* Lowest type available */
```

This is useful for priority-based message routing:

```mermaid
graph TD
    A[Sender] -->|mtype=1 LOW| Q[Message Queue]
    A -->|mtype=2 MED| Q
    A -->|mtype=3 HIGH| Q
    Q -->|msgrcv type=-3| R[Receiver: lowest first]
    Q -->|msgrcv type=3| S[Receiver: HIGH only]
```

### Queue Management

```c
#include <sys/ipc.h>
#include <sys/msg.h>

/* Get queue info */
struct msqid_ds info;
msgctl(msqid, IPC_STAT, &info);
printf("Messages: %lu\n", info.msg_qnum);
printf("Bytes:    %lu\n", info.msg_cbytes);
printf("Max bytes:%lu\n", info.msg_qbytes);

/* Set queue limits */
info.msg_qbytes = 65536;  /* Increase max bytes */
msgctl(msqid, IPC_SET, &info);

/* Delete queue */
msgctl(msqid, IPC_RMID, NULL);

/* List all IPC resources from shell */
ipcs -q
```

### System V Limits

```bash
# View IPC limits
ipcs -l

# Key parameters in /proc/sys/kernel/
cat /proc/sys/kernel/msgmni   # Max queues (default: 32000)
cat /proc/sys/kernel/msgmnb   # Max bytes per queue (default: 16384)
cat /proc/sys/kernel/msgmax   # Max message size (default: 8192)
```

## POSIX Message Queues

### Overview

POSIX message queues (Linux kernel 2.6.6+) offer a cleaner API, file-system visibility (`/dev/mqueue/`), priority support, and notification mechanisms.

### Creating and Opening

```c
#include <mqueue.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <stdio.h>

int main(void) {
    /* Create a queue */
    struct mq_attr attr = {
        .mq_flags   = 0,
        .mq_maxmsg  = 10,        /* Max messages in queue */
        .mq_msgsize = 256,       /* Max message size */
        .mq_curmsgs = 0          /* Current messages (read-only) */
    };

    mqd_t mq = mq_open("/myqueue", O_CREAT | O_RDWR, 0644, &attr);
    if (mq == (mqd_t)-1) {
        perror("mq_open");
        return 1;
    }

    printf("Queue opened: fd=%d\n", mq);
    return 0;
}
```

### Sending and Receiving

```c
#include <mqueue.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

/* Sender */
int sender(void) {
    mqd_t mq = mq_open("/myqueue", O_WRONLY);
    if (mq == (mqd_t)-1) { perror("mq_open"); return 1; }

    const char *msg = "Hello, POSIX MQ!";
    unsigned int prio = 5;  /* Priority 0-31 (higher = more urgent) */

    if (mq_send(mq, msg, strlen(msg), prio) == -1) {
        perror("mq_send");
        return 1;
    }
    printf("Sent: %s (priority %u)\n", msg, prio);

    mq_close(mq);
    return 0;
}

/* Receiver */
int receiver(void) {
    mqd_t mq = mq_open("/myqueue", O_RDONLY);
    if (mq == (mqd_t)-1) { perror("mq_open"); return 1; }

    struct mq_attr attr;
    mq_getattr(mq, &attr);

    char *buf = malloc(attr.mq_msgsize);
    unsigned int prio;
    ssize_t len;

    while ((len = mq_receive(mq, buf, attr.mq_msgsize, &prio)) > 0) {
        printf("Received: %.*s (priority %u)\n", (int)len, buf, prio);
    }

    free(buf);
    mq_close(mq);
    return 0;
}
```

### Non-blocking and Timed Operations

```c
#include <mqueue.h>
#include <fcntl.h>
#include <time.h>
#include <errno.h>

/* Non-blocking */
mqd_t mq = mq_open("/myqueue", O_RDONLY | O_NONBLOCK);
char buf[256];
unsigned int prio;
ssize_t len = mq_receive(mq, buf, sizeof(buf), &prio);
if (len == -1 && errno == EAGAIN) {
    printf("Queue empty (non-blocking)\n");
}

/* Timed receive */
struct timespec ts;
clock_gettime(CLOCK_REALTIME, &ts);
ts.tv_sec += 5;  /* 5 second timeout */

len = mq_timedreceive(mq, buf, sizeof(buf), &prio, &ts);
if (len == -1 && errno == ETIMEDOUT) {
    printf("Timed out after 5 seconds\n");
}

/* Timed send */
struct timespec send_ts;
clock_gettime(CLOCK_REALTIME, &send_ts);
send_ts.tv_sec += 2;
mq_timedsend(mq, "msg", 3, 1, &send_ts);
```

### Asynchronous Notification

POSIX MQs can notify via signals or threads when messages arrive:

```c
#include <mqueue.h>
#include <signal.h>
#include <stdio.h>
#include <unistd.h>

static volatile int got_message = 0;

static void notification_handler(int sig) {
    got_message = 1;
}

int main(void) {
    mqd_t mq = mq_open("/myqueue", O_RDONLY | O_NONBLOCK);

    /* Register for signal notification */
    struct sigevent sev;
    sev.sigev_notify = SIGEV_SIGNAL;
    sev.sigev_signo  = SIGUSR1;
    signal(SIGUSR1, notification_handler);

    mq_notify(mq, &sev);

    while (1) {
        pause();  /* Wait for signal */
        if (got_message) {
            got_message = 0;

            /* Drain all messages */
            char buf[256];
            unsigned int prio;
            while (mq_receive(mq, buf, sizeof(buf), &prio) > 0) {
                printf("Got: %.*s\n", 256, buf);
            }

            /* Re-register (one-shot!) */
            mq_notify(mq, &sev);
        }
    }
}
```

**Important**: `mq_notify` is one-shot. You must re-register after each notification.

### Thread-Based Notification

```c
#include <mqueue.h>
#include <pthread.h>
#include <stdio.h>

static void *notify_thread(void *arg) {
    union sigval sv = *(union sigval *)arg;
    mqd_t mq = (mqd_t)sv.sival_int;

    char buf[256];
    unsigned int prio;
    ssize_t len = mq_receive(mq, buf, sizeof(buf), &prio);
    printf("Thread notified, received: %.*s\n", (int)len, buf);
    return NULL;
}

int main(void) {
    mqd_t mq = mq_open("/myqueue", O_RDONLY | O_NONBLOCK);

    struct sigevent sev;
    sev.sigev_notify          = SIGEV_THREAD;
    sev.sigev_notify_function = notify_thread;
    sev.sigev_notify_attributes = NULL;
    sev.sigev_value.sival_int = mq;

    mq_notify(mq, &sev);
    /* Thread will be spawned when a message arrives */
    pause();
}
```

## Filesystem Visibility

POSIX MQs are visible in the filesystem:

```bash
# Mount the mqueue filesystem
sudo mount -t mqueue none /dev/mqueue

# List queues
ls /dev/mqueue/
# myqueue

# Inspect queue attributes
cat /dev/mqueue/myqueue
# QSIZE:1234  NOTIFY:0  SIGNO:0  NOTIFY_PID:0  CB:0

# Delete from filesystem
rm /dev/mqueue/myqueue
```

## System V vs POSIX Comparison

| Feature | System V | POSIX |
|---|---|---|
| **API** | `msgget`/`msgsnd`/`msgrcv` | `mq_open`/`mq_send`/`mq_receive` |
| **Identification** | Integer key → ID | Named path (string) |
| **Message priority** | Type-based filtering | Explicit priority (0-31) |
| **Max message size** | 8192 (default, tunable) | Configurable at open |
| **Notification** | None (poll only) | Signal or thread |
| **Filesystem** | No (`ipcs` command) | `/dev/mqueue/` |
| **Portability** | Most UNIX | POSIX (limited on macOS) |
| **Performance** | Good | Better (newer kernel path) |
| **Close semantics** | `msgctl(IPC_RMID)` | `mq_unlink()` |

## Practical Example: Producer-Consumer

```c
#include <mqueue.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define QUEUE_NAME "/work_queue"
#define NUM_ITEMS  20
#define NUM_WORKERS 4

static mqd_t work_queue;

static void *producer(void *arg) {
    for (int i = 0; i < NUM_ITEMS; i++) {
        char msg[64];
        snprintf(msg, sizeof(msg), "task-%d", i);
        mq_send(work_queue, msg, strlen(msg), i % 5);  /* Varying priority */
        printf("Produced: %s (prio=%d)\n", msg, i % 5);
        usleep(50000);
    }
    /* Send poison pills */
    for (int i = 0; i < NUM_WORKERS; i++) {
        mq_send(work_queue, "DONE", 4, 0);
    }
    return NULL;
}

static void *consumer(void *arg) {
    int id = *(int *)arg;
    char buf[64];
    unsigned int prio;

    while (1) {
        ssize_t len = mq_receive(work_queue, buf, sizeof(buf), &prio);
        if (len <= 0) break;

        buf[len] = '\0';
        if (strcmp(buf, "DONE") == 0) break;

        printf("  Worker %d: processing %s (prio=%u)\n", id, buf, prio);
        usleep(100000);  /* Simulate work */
    }
    return NULL;
}

int main(void) {
    struct mq_attr attr = { 0, 50, 64, 0 };
    work_queue = mq_open(QUEUE_NAME, O_CREAT | O_RDWR, 0644, &attr);

    pthread_t prod, workers[NUM_WORKERS];
    int ids[NUM_WORKERS];

    pthread_create(&prod, NULL, producer, NULL);
    for (int i = 0; i < NUM_WORKERS; i++) {
        ids[i] = i;
        pthread_create(&workers[i], NULL, consumer, &ids[i]);
    }

    pthread_join(prod, NULL);
    for (int i = 0; i < NUM_WORKERS; i++)
        pthread_join(workers[i], NULL);

    mq_close(work_queue);
    mq_unlink(QUEUE_NAME);
    return 0;
}
```

```bash
gcc -o mq_demo mq_demo.c -lpthread -lrt
```

## Performance Considerations

- POSIX MQs use a kernel-managed circular buffer
- Messages are copied between user and kernel space (not zero-copy)
- For large data, consider shared memory + semaphore instead
- System V queues have a fixed max message size; POSIX queues are more flexible
- Both interfaces are slower than pipes for simple byte-stream IPC

## Kernel Implementation Details

### System V Message Queue Internals

System V message queues are implemented in `ipc/msg.c`:

```c
/* Kernel representation of a message queue */
struct msg_queue {
    struct kern_ipc_perm q_perm;
    time_t q_stime;           /* Last msgsnd time */
    time_t q_rtime;           /* Last msgrcv time */
    time_t q_ctime;           /* Last change time */
    unsigned long q_cbytes;   /* Current bytes in queue */
    unsigned long q_qnum;     /* Number of messages */
    unsigned long q_qbytes;   /* Max bytes allowed */
    pid_t q_lspid;            /* Last msgsnd PID */
    pid_t q_lrpid;            /* Last msgrcv PID */
    struct list_head q_messages;  /* List of messages */
    struct list_head q_receivers; /* Waiting receivers */
    struct list_head q_senders;   /* Waiting senders */
};

/* Individual message */
struct msg_msg {
    struct list_head m_list;
    long m_type;
    size_t m_ts;              /* Message text size */
    struct msg_msgseg *next;  /* For messages > 1 page */
    /* Followed by message text */
};
```

### Message Queue Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Created: msgget()
    Created --> HasMessages: msgsnd()
    HasMessages --> HasMessages: msgsnd()/msgrcv()
    HasMessages --> Empty: msgrcv() drains last msg
    Empty --> HasMessages: msgsnd()
    Empty --> Created: (queue still exists)
    HasMessages --> Destroyed: msgctl(IPC_RMID)
    Empty --> Destroyed: msgctl(IPC_RMID)
    Destroyed --> [*]
    note right of Destroyed
        Messages remain readable
        until process exits
        (marked for deletion)
    end note
```

### POSIX MQ Kernel Implementation

POSIX message queues use a different implementation:

```c
/* fs/mqueue.c */
struct mqueue_inode_info {
    struct inode vfs_inode;
    wait_queue_head_t wait_q;      /* Waiting senders/receivers */
    struct rb_root msg_tree;       /* Messages in priority order */
    struct posix_msg_tree_node *node_cache;
    struct mq_attr attr;           /* Queue attributes */
    struct sigevent notify;        /* Notification setup */
    struct pid *notify_owner;      /* Process to notify */
    struct user_namespace *notify_user_ns;
    struct user_struct *user;      /* User who created */
    struct sock *notify_sock;      /* Netlink for notification */
    struct sk_buff *notify_cookie;
};
```

## Security Considerations

### System V MQ Security

```bash
# IPC permissions are checked at msgget()/msgsnd()/msgrcv()
# Key permissions:
# 0600 — owner only
# 0644 — owner read/write, others read
# 0666 — everyone read/write (DANGEROUS)

# Check IPC security
cat /proc/sys/kernel/msgmni   # Max queues system-wide
cat /proc/sys/kernel/msgmnb   # Max bytes per queue
cat /proc/sys/kernel/msgmax   # Max single message size

# List all message queues with permissions
ipcs -q
# ------ Message Queues --------
# key        msqid      owner      perms      used-bytes   messages
# 0x0000002a 0          user       644        1234         5

# Security risks:
# - World-writable queues allow message injection
# - Large queues can exhaust kernel memory
# - Queue keys can be guessed (ftok is deterministic)
```

### POSIX MQ Security

```bash
# POSIX MQs use filesystem permissions
ls -la /dev/mqueue/myqueue
# -rw-r--r-- 1 user user 80 Jul 22 10:00 myqueue

# Set permissions on creation
mq_open("/myqueue", O_CREAT | O_RDWR, 0600, &attr);

# Namespace isolation
# POSIX MQs are visible system-wide (not namespace-aware)
# Use different names for different security domains
```

### Resource Limits

```bash
# System V limits
cat /proc/sys/kernel/msgmni   # Max queues (default: 32000)
cat /proc/sys/kernel/msgmnb   # Max bytes/queue (default: 16384)
cat /proc/sys/kernel/msgmax   # Max message size (default: 8192)

# POSIX MQ limits (per-user)
# /proc/sys/fs/mqueue/msg_max       — max messages per queue (default: 10)
# /proc/sys/fs/mqueue/msgsize_max   — max message size (default: 8192)
# /proc/sys/fs/mqueue/queues_max    — max queues system-wide (default: 256)

cat /proc/sys/fs/mqueue/msg_max
cat /proc/sys/fs/mqueue/msgsize_max
cat /proc/sys/fs/mqueue/queues_max

# Adjust POSIX MQ limits
sudo sysctl -w fs.mqueue.msg_max=100
sudo sysctl -w fs.mqueue.msgsize_max=65536
```

## Comparison with Other IPC Mechanisms

| Mechanism | Latency | Throughput | Complexity | Persistence |
|-----------|---------|------------|------------|-------------|
| POSIX MQ | Low | Medium | Low | Kernel (until unlink) |
| System V MQ | Low-Med | Medium | Medium | Kernel (until RMID) |
| Unix socket | Lowest | High | Medium | Process lifetime |
| Pipe | Lowest | High | Lowest | Process lifetime |
| Shared memory | Lowest | Highest | Highest | Kernel (until shmctl) |
| TCP socket | Higher | Medium | Highest | Network |

### When to Use Message Queues

**Use POSIX MQs when:**
- You need priority-based message delivery
- You need signal/thread notification on message arrival
- You want filesystem visibility for monitoring
- You need to pass data between unrelated processes

**Use System V MQs when:**
- You need type-based selective receive (powerful filtering)
- You're porting from other UNIX systems
- You need the `ipcs`/`ipcrm` management tools

**Use Unix sockets when:**
- You need the highest throughput
- You need to pass file descriptors (SCM_RIGHTS)
- You're doing request-response patterns
- You need bidirectional communication

**Use shared memory when:**
- You need zero-copy data transfer
- You're sharing large data structures
- You can handle synchronization separately (semaphores)

## Advanced Patterns

### Request-Reply with POSIX MQs

```c
/* Client sends request with reply queue name */
struct request {
    char reply_queue[64];
    char data[256];
};

/* Client */
mqd_t reply_q = mq_open("/reply_1234", O_CREAT | O_RDONLY, 0600, NULL);
struct request req;
strncpy(req.reply_queue, "/reply_1234", sizeof(req.reply_queue));
strncpy(req.data, "get_status", sizeof(req.data));
mq_send(request_q, (char *)&req, sizeof(req), 1);

/* Wait for reply on dedicated queue */
char buf[512];
unsigned int prio;
ssize_t len = mq_receive(reply_q, buf, sizeof(buf), &prio);

/* Server */
char buf[sizeof(struct request)];
unsigned int prio;
mq_receive(request_q, buf, sizeof(buf), &prio);
struct request *req = (struct request *)buf;

/* Process and send reply */
mqd_t reply_q = mq_open(req->reply_queue, O_WRONLY);
mq_send(reply_q, "status: ok", 10, 1);
mq_close(reply_q);
```

### Priority-Based Task Distribution

```c
/* Producer assigns priorities based on urgency */
void submit_task(const char *task, int urgency) {
    /* urgency 0 = background, 1-3 = normal, 4-5 = high, 6-7 = urgent, 8+ = critical */
    mq_send(work_queue, task, strlen(task), urgency);
}

/* Consumer processes highest priority first */
/* POSIX MQs automatically dequeue by priority */
void *worker(void *arg) {
    char buf[256];
    unsigned int prio;
    while (1) {
        ssize_t len = mq_receive(work_queue, buf, sizeof(buf), &prio);
        if (len <= 0) break;
        printf("Processing (prio=%u): %.*s\n", prio, (int)len, buf);
        /* Higher prio tasks always processed first */
    }
    return NULL;
}
```

## References

- [msgget(2) man page](https://man7.org/linux/man-pages/man2/msgget.2.html)
- [mq_overview(7) man page](https://man7.org/linux/man-pages/man7/mq_overview.7.html)
- [POSIX Message Queues (Linux kernel docs)](https://www.kernel.org/doc/html/latest/userspace-api/sysVipc.html)
- [Beej's Guide to Unix IPC](https://beej.us/guide/bgipc/)
- [Linux kernel source: ipc/msg.c](https://elixir.bootlin.com/linux/latest/source/ipc/msg.c)
- [Linux kernel source: fs/mqueue.c](https://elixir.bootlin.com/linux/latest/source/fs/mqueue.c)

## Related Topics

- [POSIX Semaphores](./semaphores.md) — synchronization for shared resources
- [Unix Domain Sockets](./unix-sockets.md) — alternative IPC mechanism
- [Event-Driven Programming](../event-driven.md) — integrating message queues into event loops
- [Shared Memory](./shared-memory.md) — zero-copy IPC alternative
- [Pipes](./pipes.md) — simplest IPC mechanism
