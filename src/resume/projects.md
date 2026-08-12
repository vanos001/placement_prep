# Projects on Your Resume

Projects are often the most important section for new grads and early-career engineers. They demonstrate your ability to build things, solve problems, and learn new technologies — all without needing prior work experience.

## What Makes a Good Resume Project

### The 3 Criteria

1. **Non-trivial** — Goes beyond tutorial-level work
2. **Complete** — Actually deployed/usable, not just a GitHub repo with boilerplate
3. **Relevant** — Demonstrates skills the target role requires

### Project Tiers

**Tier 1 — Standout Projects (include these first)**
- Full-stack applications with real users
- Open source contributions to well-known projects
- Research projects with published papers
- Hackathon winners
- Projects that solve real problems

**Tier 2 — Solid Projects (good to include)**
- Well-built clones of complex applications (with your own twist)
- Developer tools or utilities others actually use
- Contributing to class projects that shipped
- Technical blog posts with code

**Tier 3 — Basic Projects (include only if needed)**
- Standard class projects (to-do apps, calculators)
- Tutorial-following projects
- Projects with no deployment or users

## How to Describe Projects

### The Format

```
PROJECT NAME | Tech Stack
Live: url.com | GitHub: github.com/user/repo
- [What you built — the core functionality]
- [Technical challenge you solved]
- [Impact — users, performance, metrics]
```

### Key Principles

**1. Lead with what it does, not how you built it**

❌ "Used React and Node.js to make a web app"
✅ "Built a real-time collaborative whiteboard supporting 20+ concurrent users with live cursor tracking"

**2. Highlight technical decisions and tradeoffs**

❌ "Used a database for storing data"
✅ "Chose MongoDB over PostgreSQL for flexible document schema, handling 10K+ user-generated content items with sub-50ms query times"

**3. Show the full picture**

Include: Frontend + Backend + Database + Deployment + Scale

**4. Quantify where possible**

- Number of users
- Data volume processed
- Performance metrics
- Lines of code (only if impressive)
- GitHub stars/forks

## Project Description Examples

### Full-Stack Web Application

```
TASKFLOW — Collaborative Project Management Tool
React, TypeScript, Node.js, PostgreSQL, Redis, Docker | github.com/jane/taskflow
- Built a Trello-like project management app with real-time drag-and-drop boards,
  supporting 300+ registered users and 50+ daily active users
- Implemented WebSocket-based live updates using Socket.io, enabling instant
  synchronization across clients with <100ms latency
- Designed RESTful API with JWT authentication, rate limiting, and comprehensive
  input validation using Zod schemas
- Deployed on AWS EC2 with Docker Compose, Nginx reverse proxy, and automated
  CI/CD via GitHub Actions
```

### Machine Learning Project

```
SENTIFY — Real-Time Sentiment Analysis Pipeline
Python, PyTorch, FastAPI, Kafka, React | github.com/jane/sentify
- Developed end-to-end ML pipeline processing 5K+ tweets/minute with BERT-based
  sentiment classifier achieving 91% accuracy on custom-labeled dataset
- Built streaming data ingestion using Apache Kafka, processing and classifying
  tweets in real-time with <200ms end-to-end latency
- Created interactive React dashboard displaying live sentiment trends with
  D3.js visualizations, used by 3 research teams
- Published findings as workshop paper at NAACL 2026 Student Research Workshop
```

### Developer Tool

```
GODETECT — Static Analysis Tool for Go Security Vulnerabilities
Go, AST parsing, CI/CD integration | github.com/jane/godetect | 200+ GitHub stars
- Built CLI tool that analyzes Go source code ASTs to detect 12 common security
  vulnerability patterns including SQL injection and path traversal
- Implemented as both standalone CLI and GitHub Action, integrated into 15+
  open source project CI pipelines
- Achieved 95% true positive rate on benchmark dataset of 500 vulnerable code
  samples, outperforming existing tools by 8%
```

### Systems/Infrastructure Project

```
MINIKV — Distributed Key-Value Store
C++, gRPC, Raft Consensus | github.com/jane/minikv
- Implemented a distributed key-value store from scratch supporting GET, PUT,
  and DELETE operations with strong consistency guarantees
- Built Raft consensus protocol for leader election and log replication across
  3-5 node clusters with automatic failover in <500ms
- Benchmarked at 50K reads/sec and 20K writes/sec on 3-node cluster,
  with P99 latency under 10ms
- Added snapshotting and log compaction, reducing storage overhead by 70%
  for long-running clusters
```

### Mobile Application

```
FITTRACK — AI-Powered Fitness Tracking App
React Native, TypeScript, Firebase, TensorFlow Lite | github.com/jane/fittrack
- Built cross-platform mobile app with AI-powered exercise form detection using
  on-device TensorFlow Lite model, processing camera feed at 30fps
- Implemented offline-first architecture with Firebase sync, allowing full
  functionality without internet connection
- Designed custom UI components and animations, achieving 4.7/5 rating from
  200+ beta testers on TestFlight
```

## How to Choose Which Projects to Include

### Decision Matrix

Ask yourself these questions for each project:

| Question | Weight |
|----------|--------|
| Is it relevant to the target role? | High |
| Does it demonstrate technical depth? | High |
| Is it complete/deployed? | Medium |
| Can you talk about it confidently in interviews? | High |
| Does it show breadth vs. depth? | Medium |
| Is the code clean and well-documented? | Medium |

### Tailoring to Roles

**Frontend Role:** Emphasize UI/UX, React/Vue/Angular projects, performance optimization, accessibility

**Backend Role:** Emphasize APIs, databases, distributed systems, scalability, system design

**Full-Stack Role:** Show end-to-end projects, mention both frontend and backend contributions

**ML/Data Role:** Emphasize data pipelines, model training, evaluation metrics, real-world applications

**DevOps/SRE Role:** Emphasize infrastructure, CI/CD, monitoring, deployment automation

## Presenting Class Projects

Class projects can be resume-worthy if you elevate them:

### Before (Class Project)
"Built a chat application for CS 320 class project"

### After (Elevated)
```
REAL-TIME CHAT PLATFORM
Node.js, React, Socket.io, MongoDB, Redis | github.com/jane/chatter
- Built a real-time messaging platform supporting 100+ concurrent users with
  features including group chats, file sharing, and message search
- Implemented Redis pub/sub for horizontal scaling across multiple server instances
- Added end-to-end message encryption using Web Crypto API
```

### How to Elevate

1. **Add features beyond requirements** — Don't just meet the rubric
2. **Deploy it** — Heroku, Vercel, Railway, AWS free tier
3. **Add tests** — Shows engineering maturity
4. **Write a README** — With setup instructions, screenshots, architecture diagram
5. **Make it public** — Open source if possible
6. **Get users** — Even 10 users is better than zero

## Open Source Contributions

Open source contributions are highly valued:

### How to Present Them

```
APACHE KAFKA — Open Source Contributor
github.com/apache/kafka (PRs: #12345, #12400, #12450)
- Fixed race condition in consumer group rebalancing affecting 1000+ production clusters
- Added metrics for monitoring partition reassignment lag, merged into v3.8 release
- Reviewed 20+ community PRs and triaged 15+ issues as part of contributor program
```

### Tips

- Link to specific PRs
- Mention the project's scale/importance
- Describe the impact of your contribution
- Include review/triage work, not just code

## Project Presentation Tips

### GitHub Repository

Your GitHub is an extension of your resume:

1. **README.md** — Every project needs one with:
   - What it does (with screenshots/GIFs)
   - How to set it up
   - Tech stack
   - Architecture overview
   - What you learned

2. **Clean commit history** — Meaningful commit messages, not "fix stuff"

3. **Pin your best repos** — GitHub lets you pin 6 repositories

4. **Green contribution graph** — Shows consistency (but don't game it)

### Live Demos

If possible, deploy your projects:
- **Frontend:** Vercel, Netlify, GitHub Pages
- **Full-stack:** Railway, Render, Fly.io
- **Mobile:** TestFlight, Google Play Beta
- **APIs:** Document with Swagger/OpenAPI

### Talking About Projects in Interviews

Prepare a 2-minute pitch for each project:

1. **What it is** — One sentence
2. **Why you built it** — Motivation/problem
3. **How it works** — Architecture overview
4. **Key technical decisions** — Tradeoffs you made
5. **Challenges** — Hard problems you solved
6. **Impact** — Users, metrics, what you learned

## Common Project Mistakes

1. **Listing too many** — 2-4 strong projects > 8 mediocre ones
2. **No deployment** — A GitHub repo without a live demo is half-finished
3. **Tutorial clones** — "Built Netflix clone following YouTube tutorial" doesn't impress
4. **No README** — If your repo has no README, it looks abandoned
5. **Overcomplicating** — Simple project done well > complex project done poorly
6. **Not being able to discuss it** — If you can't explain your architecture choices, you'll struggle in interviews
