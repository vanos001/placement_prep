# Policy Gradient Methods

## Overview

Policy gradient methods directly optimize the **policy** $\pi_\theta(a|s)$ by gradient ascent on the expected return. Unlike value-based methods (Q-Learning) that derive a policy from learned Q-values, policy gradient methods learn the policy parameters $\theta$ end-to-end. This naturally handles **continuous action spaces** and **stochastic policies**, making it the foundation for modern RL algorithms including PPO and RLHF.

## Core Idea

Maximize the expected return:

$$J(\theta) = \mathbb{E}_{\tau \sim \pi_\theta}\left[\sum_{t=0}^{T} \gamma^t r_t\right]$$

Update via gradient ascent:

$$\theta \leftarrow \theta + \alpha \nabla_\theta J(\theta)$$

### The Policy Gradient Theorem

$$\nabla_\theta J(\theta) = \mathbb{E}_{\pi_\theta}\left[\sum_{t=0}^{T} \nabla_\theta \log \pi_\theta(a_t|s_t) \cdot G_t\right]$$

Where $G_t = \sum_{k=t}^{T} \gamma^{k-t} r_k$ is the return from time $t$.

**Intuition**: Increase the probability of actions that led to high returns, decrease the probability of actions that led to low returns.

## REINFORCE Algorithm

The simplest policy gradient algorithm:

```python
import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Categorical

class PolicyNetwork(nn.Module):
    def __init__(self, state_dim, action_dim, hidden_dim=128):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, action_dim),
            nn.Softmax(dim=-1)
        )
    
    def forward(self, x):
        return self.network(x)

def reinforce(policy, optimizer, env, gamma=0.99, episodes=1000):
    for episode in range(episodes):
        states, actions, rewards = [], [], []
        
        # Collect trajectory
        state = env.reset()
        while True:
            state_tensor = torch.FloatTensor(state)
            probs = policy(state_tensor)
            dist = Categorical(probs)
            action = dist.sample()
            
            next_state, reward, done, _ = env.step(action.item())
            
            states.append(state_tensor)
            actions.append(action)
            rewards.append(reward)
            
            state = next_state
            if done:
                break
        
        # Compute returns
        returns = []
        G = 0
        for r in reversed(rewards):
            G = r + gamma * G
            returns.insert(0, G)
        returns = torch.tensor(returns)
        returns = (returns - returns.mean()) / (returns.std() + 1e-8)  # Normalize
        
        # Compute loss
        loss = 0
        for s, a, G in zip(states, actions, returns):
            probs = policy(s)
            dist = Categorical(probs)
            loss -= dist.log_prob(a) * G  # Gradient ascent = minimize negative
        
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
```

### REINFORCE with Baseline

Subtract a baseline $b(s)$ to reduce variance without changing the expected gradient:

$$\nabla_\theta J(\theta) = \mathbb{E}\left[\nabla_\theta \log \pi_\theta(a_t|s_t) \cdot (G_t - b(s_t))\right]$$

Common baseline: $b(s) = V(s)$ (state value function).

## Actor-Critic Methods

Combine policy gradient (actor) with value function estimation (critic):

```mermaid
graph TD
    STATE[State s] --> ACTOR[Actor: π(a|s)]
    STATE --> CRITIC[Critic: V(s)]
    ACTOR --> ACTION[Action a]
    ACTION --> ENV[Environment]
    ENV --> REWARD[Reward r]
    ENV --> NEXT[Next state s']
    
    REWARD --> ADVANTAGE[Advantage: A = r + γV(s') - V(s)]
    NEXT --> ADVANTAGE
    CRITIC --> ADVANTAGE
    
    ADVANTAGE --> POLICY_UPDATE["Actor: ∇θ log π(a|s) · A"]
    ADVANTAGE --> VALUE_UPDATE["Critic: (r + γV(s') - V(s))²"]
```

### Advantage Function

$$A(s_t, a_t) = Q(s_t, a_t) - V(s_t)$$

Estimated using TD error:

$$\hat{A}_t = r_t + \gamma V(s_{t+1}) - V(s_t)$$

### Actor-Critic Implementation

```python
class ActorCritic(nn.Module):
    def __init__(self, state_dim, action_dim, hidden_dim=128):
        super().__init__()
        # Shared feature extractor
        self.shared = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU()
        )
        # Actor head
        self.actor = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, action_dim),
            nn.Softmax(dim=-1)
        )
        # Critic head
        self.critic = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1)
        )
    
    def forward(self, x):
        features = self.shared(x)
        action_probs = self.actor(features)
        state_value = self.critic(features)
        return action_probs, state_value

def actor_critic_update(model, optimizer, states, actions, rewards, 
                         next_states, dones, gamma=0.99):
    states = torch.FloatTensor(states)
    actions = torch.LongTensor(actions)
    rewards = torch.FloatTensor(rewards)
    next_states = torch.FloatTensor(next_states)
    dones = torch.FloatTensor(dones)
    
    # Get values
    action_probs, values = model(states)
    _, next_values = model(next_states)
    
    # Compute advantage (TD error)
    advantages = rewards + gamma * next_values.squeeze() * (1 - dones) - values.squeeze()
    
    # Actor loss (policy gradient)
    dist = Categorical(action_probs)
    actor_loss = -(dist.log_prob(actions) * advantages.detach()).mean()
    
    # Critic loss (value function)
    critic_loss = advantages.pow(2).mean()
    
    # Total loss
    loss = actor_loss + 0.5 * critic_loss
    
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()
```

## Generalized Advantage Estimation (GAE)

GAE balances bias and variance in advantage estimation:

$$\hat{A}_t^{\text{GAE}(\gamma, \lambda)} = \sum_{l=0}^{\infty} (\gamma \lambda)^l \delta_{t+l}$$

Where $\delta_t = r_t + \gamma V(s_{t+1}) - V(s_t)$ is the TD error.

- $\lambda = 0$: One-step TD (low variance, high bias)
- $\lambda = 1$: Monte Carlo (high variance, low bias)
- $\lambda = 0.95$: Typical sweet spot

```python
def compute_gae(rewards, values, next_values, dones, gamma=0.99, lam=0.95):
    advantages = []
    gae = 0
    for t in reversed(range(len(rewards))):
        delta = rewards[t] + gamma * next_values[t] * (1 - dones[t]) - values[t]
        gae = delta + gamma * lam * (1 - dones[t]) * gae
        advantages.insert(0, gae)
    return torch.tensor(advantages)
```

## Interview Questions

### Q1: What is the policy gradient theorem?
**Answer:** It states that the gradient of the expected return with respect to policy parameters is: $\nabla_\theta J(\theta) = \mathbb{E}[\nabla_\theta \log \pi_\theta(a|s) \cdot G_t]$. This lets us optimize the policy directly by increasing the probability of actions that led to high returns. The $\log \pi$ term comes from the likelihood ratio trick.

### Q2: Why is REINFORCE high variance?
**Answer:** REINFORCE uses Monte Carlo estimates of return $G_t$, which are noisy because they depend on all future rewards (including stochastic transitions and actions). A single bad transition can drastically change the return, leading to high variance. Solutions: baseline subtraction, actor-critic (use TD estimates), GAE.

### Q3: What is the advantage function and why use it?
**Answer:** $A(s,a) = Q(s,a) - V(s)$ measures how much better action $a$ is compared to the average action in state $s$. Using advantage instead of raw return: 1) Reduces variance (centered around zero), 2) Provides a relative measure (good vs. bad actions), 3) Enables bootstrapping (lower variance than Monte Carlo).

### Q4: What is the difference between REINFORCE and Actor-Critic?
**Answer:** REINFORCE is pure policy gradient — uses Monte Carlo returns to update the policy. Actor-Critic adds a learned value function (critic) to estimate advantages, enabling bootstrapping and reducing variance. Actor-Critic is more stable and sample-efficient but introduces bias from the value function estimate.

## Common Mistakes

- ❌ Not normalizing returns (exploding/vanishing gradients)
- ❌ Using raw rewards instead of advantages (high variance)
- ❌ Setting learning rate too high (policy collapse)
- ❌ Not clipping gradients (training instability)
- ❌ Confusing on-policy (REINFORCE, PPO) with off-policy (Q-Learning)

## Summary

Policy gradient methods directly optimize the policy using gradient ascent on expected return. REINFORCE is the simplest but has high variance. Actor-critic methods reduce variance by using a learned value function. GAE provides a tunable bias-variance tradeoff. These methods form the foundation for PPO and RLHF.

## Cross-References

- [Fundamentals →](fundamentals.md) MDP, value functions
- [Q-Learning →](q-learning.md) Value-based alternative
- [PPO →](ppo.md) Modern policy gradient
- [RLHF →](rlhf.md) Policy gradient for LLMs
