# Written Communication for Engineers

## Technical Writing Principles

### The Inverted Pyramid

Put the most important information first:

```
TL;DR / Summary (1-2 sentences)
├── Key findings / decisions
├── Supporting details
└── Background / context
```

Engineers skim. If they stop reading after the first paragraph, they should still get the key message.

### Writing Style

- **Active voice**: "The server processes requests" not "Requests are processed by the server"
- **Short sentences**: One idea per sentence. < 25 words when possible.
- **Concrete language**: "Latency increased by 200ms" not "Performance degraded"
- **Avoid jargon**: If you must use it, define it on first use

## Documentation Types

### README

Every project needs one. Structure:

```markdown
# Project Name
One-line description.

## Quick Start
5 steps to get running.

## Architecture
High-level diagram and explanation.

## Development
How to build, test, lint.

## Deployment
How to deploy to production.

## Contributing
PR process, code style, testing requirements.
```

### Architecture Decision Records (ADRs)

Capture decisions and their context:

```markdown
# ADR-001: Use PostgreSQL as Primary Database

## Status
Accepted (2024-01-15)

## Context
We need a relational database for the user management system.
Requirements: ACID transactions, JSON support, full-text search.

## Decision
Use PostgreSQL 16.

## Consequences
+ Strong ACID compliance
+ JSONB for flexible schemas
+ Full-text search built-in
- Team has more MySQL experience
- Need to learn PostgreSQL-specific features

## Alternatives Considered
- MySQL 8: Less JSON support, weaker full-text search
- CockroachDB: Overkill for current scale
```

### RFCs (Request for Comments)

For proposing significant changes:

```markdown
# RFC: Migrate Authentication to OAuth 2.0

## Summary
Replace custom auth with OAuth 2.0 + JWT.

## Motivation
Current auth has security issues and doesn't support SSO.

## Detailed Design
[Architecture, API changes, migration plan]

## Drawbacks
Migration effort, breaking changes for existing clients.

## Alternatives
Keep current auth + fix issues, use SAML instead.

## Unresolved Questions
Token expiry policy, refresh token strategy.
```

### Runbooks

Operational procedures for common tasks/incidents:

```markdown
# Runbook: Database Failover

## Symptoms
- Alerts: `db_replication_lag > 30s`, `db_primary_down`
- Users: 500 errors on write endpoints

## Diagnosis
1. Check primary health: `pg_isready -h primary.db`
2. Check replication: `SELECT * FROM pg_stat_replication;`
3. Check disk: `df -h /var/lib/postgresql`

## Resolution
1. If primary is down, promote replica:
   `pg_ctlcluster 16 main promote`
2. Update DNS to point to new primary
3. Verify application connectivity
4. Notify team via #incidents channel

## Post-Incident
- File incident report
- Update runbook if new learnings
```

## Email Communication

### Structure

```
Subject: [ACTION REQUIRED] or [FYI] + clear topic

TL;DR: 1-2 sentence summary

Details: Supporting information

Action items: What you need from the recipient
- [ ] @person: specific task by date

Context: Links, attachments, background
```

### Tips

- Subject line is the most important part
- One topic per email
- Bold key information
- Use bullet points, not paragraphs
- Clear call to action at the end

## Design Documents

### Template

```markdown
# Design: [Feature Name]

## Problem Statement
What problem are we solving? Why now?

## Goals and Non-Goals
What we will/won't do.

## Proposed Solution
Architecture diagram, API design, data model.

## Alternatives Considered
What else we thought about and why we rejected it.

## Timeline
Milestones and dependencies.

## Open Questions
What we still need to figure out.
```

## Interview Questions

**Q: How do you write a good technical document?**
A: (1) Start with the TL;DR, (2) use the inverted pyramid (most important info first), (3) include diagrams for architecture, (4) be specific with numbers and examples, (5) write for your audience (executives vs engineers), (6) include alternatives considered, (7) keep it updated.

**Q: What makes a good ADR?**
A: Context (why the decision was needed), decision (what was chosen), consequences (both positive and negative), and alternatives considered. ADRs help future team members understand why things are the way they are.

## References

- [Google Technical Writing Course](https://developers.google.com/tech-writing)
- [Markdown ADR Tools](https://adr.github.io/)
- [Docs as Code](https://docs-as-code.com/)
