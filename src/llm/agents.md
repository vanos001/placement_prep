# LLM Agents in Production

## Overview

An LLM agent uses a language model as its reasoning core to plan, use tools, and iterate on complex tasks. Unlike a single-turn LLM call (prompt → response), an agent operates in a loop: observe, reason, act, observe again. This page covers agent design from the LLM engineering perspective — how to build, deploy, and evaluate agents reliably. For detailed architecture patterns, see [ml/agents/](../ml/agents/README.md).

## Agent Architectures

### ReAct (Reasoning + Acting)

The foundational agent pattern. The model alternates between reasoning ("Thought") and action ("Action") steps, observing results before deciding the next step.

```
Thought: I need to find the user's order status. I'll search for it.
Action: search_orders(user_id="usr_123")
Observation: Order #4521, status: shipped, tracking: 1Z999...
Thought: I have the tracking info. I'll provide it to the user.
Answer: Your order #4521 has been shipped. Tracking: 1Z999...
```

ReAct is the default for most frameworks (LangChain, OpenAI Assistants API). It is transparent and debuggable because each reasoning step is logged.

### Plan-and-Execute

Separate planning from execution. The model first creates a full plan, then executes steps sequentially.

| Aspect | ReAct | Plan-and-Execute |
---|---|---|
| Planning | Implicit (one step at a time) | Explicit (full plan upfront) |
| Adaptability | High (adjusts after each observation) | Medium (replans when steps fail) |
| Token usage | Lower per step | Higher upfront (full plan) |
| Best for | Open-ended exploration | Well-structured multi-step tasks |

### Reflection

After generating an output, the model critiques its own work and regenerates. Used when output quality is critical.

```
Initial: [model generates answer]
Critique: The answer missed point X and had an error in calculation Y.
Revised: [model generates improved answer]
```

Reflection adds latency (2-3× LLM calls) but improves accuracy on complex tasks. Reference: [Shinn et al., "Reflexion", NeurIPS 2023](https://arxiv.org/abs/2303.11366).

## Tool Use and Function Calling

### OpenAI/Anthropic Function Calling

Modern providers support structured function calling where the model outputs a JSON object with the function name and arguments instead of free text:

```json
// Model output (not free text)
{"name": "search_orders", "arguments": {"user_id": "usr_123", "status": "shipped"}}
```

The application executes the function, returns the result as an observation, and the model reasons about the next step. This is the standard mechanism for agent tool use in production. Reference: [OpenAI: Function Calling](https://platform.openai.com/docs/guides/function-calling), [Anthropic: Tool Use](https://docs.anthropic.com/en/docs/build-with-claude/tool-use).

### Tool Design Principles

| Principle | Example |
---|---|
| **Descriptive names** | `search_customer_orders` not `query` |
---|
| **Clear descriptions** | "Search for orders by customer ID. Returns order ID, status, date, and total." |
| **Explicit parameters** | Use enums, required fields, and descriptions for every parameter |
| **Idempotent when possible** | Same input → same output, safe to retry |
| **Bounded output** | Paginate results; don't return unbounded lists |
| **Fail clearly** | Return structured error messages the model can reason about |

### MCP (Model Context Protocol)

MCP is Anthropic's open standard for connecting AI models to tools and data sources. It provides a standardized JSON-RPC interface that decouples the model from tool implementations. A single MCP client can connect to any MCP server, and a single MCP server can serve any MCP client — eliminating the N×M integration problem. See [MCP Protocol](../ml/agents/mcp.md) for full details.

## Multi-Agent Systems

Multiple specialized agents collaborate on complex tasks. Each agent has a distinct role, tools, and expertise.

| Pattern | Description | Example |
---|---|---|
| **Sequential** | Agents hand off in a fixed pipeline | Researcher → Writer → Editor |
| **Hierarchical** | A supervisor agent delegates to worker agents | Manager assigns tasks to specialist agents |
| **Debate** | Agents critique each other's outputs | Two agents propose solutions, a judge picks the best |
| **Blackboard** | Agents read/write to a shared state | Multiple agents contribute to a shared document |

**Production concern:** Multi-agent systems are significantly more expensive (N agents × M LLM calls) and harder to debug (complex interaction patterns). Start with a single agent and add agents only when the task genuinely requires distinct expertise. Reference: [Multi-Agent Systems](../ml/agents/multi-agent.md).

## Production Agent Reliability

### Guardrails

| Guardrail | Mechanism |
---|---|
| **Max iterations** | Hard limit on the agent loop (typically 10-25) to prevent infinite loops |
| **Max tool calls per step** | Prevent cascading tool calls that exhaust resources |
| **Budget caps** | Track token usage across the agent loop; abort if budget exceeded |
| **Allowed tools per task** | Restrict the tool set based on the task type (a chatbot shouldn't access the database) |
| **Human-in-the-loop** | Require approval for irreversible actions (send email, delete data, execute code) |
| **Timeout** | Set per-step and total execution timeouts |

### Agent Evaluation

Evaluating agents requires measuring the full task completion, not just individual LLM outputs. See [Agent Evaluation](../ml/agents/evaluation.md) for detailed frameworks.

| Metric | How to Measure |
---|---|
| **Task success rate** | Did the agent complete the task correctly? (binary, on a golden test set) |
| **Tool call accuracy** | Were the right tools called with correct arguments? (per-step evaluation) |
| **Efficiency** | How many steps/tokens/cost to complete the task? (fewer = better) |
| **Error recovery** | When a tool fails, does the agent recover gracefully? (scenario-based testing) |
| **Latency** | End-to-end time from user query to final answer |

### Observability

Log every component of the agent loop: input, reasoning trace, tool calls (name, arguments, result), token usage per step, and final output. Tools: LangSmith, Langfuse, Phoenix (Arize), OpenTelemetry with custom spans. Without full trace logging, debugging agent failures is nearly impossible.

## Interview Questions

### Q1: When would you use an agent vs. a simple RAG system?
**Answer:** Use RAG when the task is a single retrieval + generation step (question answering, document Q&A). Use an agent when the task requires multiple steps, tool use, or conditional logic: (1) The query type varies (some need retrieval, some need computation, some need API calls). (2) The task requires iteration (search → evaluate results → refine → generate). (3) External actions are needed (book a flight, update a record, send a notification). The trade-off is cost and latency — agents make multiple LLM calls and may invoke expensive tools. Start simple; add agency only when the task demands it.

### Q2: How do you prevent an agent from entering an infinite loop?
**Answer:** Multiple guardrails: (1) **Max iterations** — hard limit on the reasoning-acting loop (typically 10-25). (2) **Max tool calls** — limit total tool invocations per request. (3) **Budget cap** — track cumulative token usage and abort when a threshold is exceeded. (4) **Timeout** — wall-clock timeout on the entire agent execution and per-tool-call timeouts. (5) **Loop detection** — detect if the agent is repeating the same action/observation cycle and force it to try a different approach. (6) **Escalation** — if the agent can't solve the task within limits, return a graceful failure with context rather than spinning forever.

### Q3: Explain MCP and why it matters for agent development.
**Answer:** MCP (Model Context Protocol) is Anthropic's open standard for connecting AI models to external tools and data sources via a JSON-RPC interface. Without MCP, every model-tool integration is custom (N models × M tools = N×M integrations). With MCP, each model implements MCP once, and each tool implements MCP once (N + M integrations). MCP servers expose tools, resources (data), and prompts. This standardization enables tool portability — a tool built for Claude works with any MCP-compatible model. MCP is gaining rapid adoption (OpenAI, Google, LangChain support) and is becoming the de facto standard for agent tool integration.

### Q4: How do you evaluate an agent in production?
**Answer:** Multi-level evaluation: (1) **Golden test set**: 50-200 end-to-end task scenarios with expected outcomes. Measure task success rate. (2) **Per-step evaluation**: Log each reasoning-action-observation step and verify tool call accuracy offline. (3) **Efficiency metrics**: Track average steps, tokens, and cost per task completion. (4) **Error recovery testing**: Inject tool failures and verify the agent recovers. (5) **User feedback**: Thumbs up/down and task completion rates from real users. (6) **A/B testing**: Compare agent versions on a subset of traffic before full rollout. Full trace logging is essential — without it, you cannot diagnose failures.

## References

1. Yao et al., "ReAct: Synergizing Reasoning and Acting in Language Models", ICLR 2023
2. Shinn et al., "Reflexion: Language Agents with Verbal Reinforcement Learning", NeurIPS 2023
3. Anthropic, "Model Context Protocol Specification" — https://modelcontextprotocol.io/
4. OpenAI, "Function Calling Guide" — https://platform.openai.com/docs/guides/function-calling
5. Park et al., "Generative Agents: Interactive Simulacra of Human Behavior", UIST 2023
6. Hong et al., "MetaGPT: Meta Programming for A Multi-Agent Collaborative Framework", ICLR 2024

## Cross-References

- [Agent Architecture →](../ml/agents/architecture.md) Detailed agent design patterns
- [ReAct →](../ml/agents/react.md) ReAct pattern deep dive
- [MCP →](../ml/agents/mcp.md) Model Context Protocol
- [Multi-Agent →](../ml/agents/multi-agent.md) Multi-agent collaboration patterns
- [Tool Calling →](../ml/agents/tool-calling.md) Function calling implementation
- [Agent Frameworks →](../ml/agents/frameworks.md) LangChain, CrewAI, AutoGen
- [Agent Evaluation →](../ml/agents/evaluation.md) Evaluation frameworks
- [LLM Security →](llm-security.md) Agent security (excessive agency, prompt injection)
