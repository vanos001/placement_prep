#!/usr/bin/env python3
"""Add cross-references to files missing them."""
import os
import re

BASE = "/home/work/.openclaw/workspace/placement_prep/src"

# Mapping: relative_path -> list of (display_name, relative_link)
CROSSREFS = {
    # ===== INTERVIEW =====
    "interview/ml-questions.md": [
        ("ML Fundamentals", "../ml/foundations/README.md"),
        ("Deep Learning", "../ml/deep-learning/README.md"),
        ("Transformers", "../ml/transformers/README.md"),
        ("ML System Design", "../ml/system-design/README.md"),
        ("Interview Overview", "./overview.md"),
    ],
    "interview/system-design/ads.md": [
        ("Rate Limiter", "./rate-limiter.md"),
        ("Metrics & Monitoring", "./metrics.md"),
        ("Streaming Systems", "./video-streaming.md"),
        ("Estimation", "./estimation.md"),
        ("Real-World: Google Search", "./real-world/google-search.md"),
    ],
    "interview/system-design/availability-patterns.md": [
        ("Consistency Patterns", "./consistency-patterns.md"),
        ("Backpressure", "./backpressure.md"),
        ("Latency vs Throughput", "./latency-vs-throughput.md"),
        ("Performance vs Scalability", "./performance-vs-scalability.md"),
        ("Cloud Overview", "../../cloud/overview.md"),
    ],
    "interview/system-design/backpressure.md": [
        ("Rate Limiter", "./rate-limiter.md"),
        ("Availability Patterns", "./availability-patterns.md"),
        ("Latency vs Throughput", "./latency-vs-throughput.md"),
        ("Messaging Systems", "./hld/messaging-systems.md"),
        ("Concurrency Overview", "../../concurrency/overview.md"),
    ],
    "interview/system-design/consistency-patterns.md": [
        ("Availability Patterns", "./availability-patterns.md"),
        ("CAP Theorem", "./hld/consistency-tradeoffs.md"),
        ("Distributed File System", "./dfs.md"),
        ("Key-Value Store", "./kv-store.md"),
        ("Storage Distributed", "../../storage/distributed.md"),
    ],
    "interview/system-design/estimation.md": [
        ("Latency Numbers", "./latency-numbers.md"),
        ("Capacity Planning", "./hld/capacity-planning.md"),
        ("Performance vs Scalability", "./performance-vs-scalability.md"),
        ("Framework", "./framework.md"),
    ],
    "interview/system-design/google-maps.md": [
        ("Search Engine", "./search.md"),
        ("Distributed File System", "./dfs.md"),
        ("Key-Value Store", "./kv-store.md"),
        ("Estimation", "./estimation.md"),
        ("Real-World: Google Search", "./real-world/google-search.md"),
    ],
    "interview/system-design/hld/README.md": [
        ("System Design Framework", "../framework.md"),
        ("LLD Overview", "../lld/README.md"),
        ("Estimation", "../estimation.md"),
        ("Latency Numbers", "../latency-numbers.md"),
    ],
    "interview/system-design/latency-numbers.md": [
        ("Estimation", "./estimation.md"),
        ("Latency vs Throughput", "./latency-vs-throughput.md"),
        ("Performance vs Scalability", "./performance-vs-scalability.md"),
        ("Caching Strategy", "./hld/caching-strategy.md"),
        ("Storage: SSD vs HDD", "../../storage/ssd.md"),
    ],
    "interview/system-design/latency-vs-throughput.md": [
        ("Performance vs Scalability", "./performance-vs-scalability.md"),
        ("Latency Numbers", "./latency-numbers.md"),
        ("Backpressure", "./backpressure.md"),
        ("Load Balancing", "./hld/load-balancing-design.md"),
    ],
    "interview/system-design/metrics.md": [
        ("Monitoring & Observability", "./hld/monitoring-observability.md"),
        ("Cloud Observability", "../../cloud/observability/README.md"),
        ("MLOps Monitoring", "../../ml/mlops/monitoring.md"),
        ("Latency vs Throughput", "./latency-vs-throughput.md"),
    ],
    "interview/system-design/pastebin.md": [
        ("URL Shortener", "./url-shortener.md"),
        ("Distributed File System", "./dfs.md"),
        ("Object Storage", "../../storage/object-storage.md"),
        ("Key-Value Store", "./kv-store.md"),
        ("Estimation", "./estimation.md"),
    ],
    "interview/system-design/payment.md": [
        ("Notification System", "./notifications.md"),
        ("Consistency Patterns", "./consistency-patterns.md"),
        ("Availability Patterns", "./availability-patterns.md"),
        ("Stock Exchange", "./stock-exchange.md"),
        ("Real-World: Uber", "./real-world/uber.md"),
    ],
    "interview/system-design/performance-vs-scalability.md": [
        ("Latency vs Throughput", "./latency-vs-throughput.md"),
        ("Latency Numbers", "./latency-numbers.md"),
        ("Load Balancing", "./hld/load-balancing-design.md"),
        ("Scalability", "./hld/scalability.md"),
        ("Cloud Overview", "../../cloud/overview.md"),
    ],
    "interview/system-design/real-world/dropbox.md": [
        ("Distributed File System", "../dfs.md"),
        ("Object Storage", "../../../storage/object-storage.md"),
        ("Consistency Patterns", "../consistency-patterns.md"),
        ("Key-Value Store", "../kv-store.md"),
    ],
    "interview/system-design/real-world/google-search.md": [
        ("Search Engine Design", "../search.md"),
        ("Typeahead", "../typeahead.md"),
        ("Web Crawler", "../web-crawler.md"),
        ("Ads System", "../ads.md"),
        ("Caching Strategy", "../hld/caching-strategy.md"),
    ],
    "interview/system-design/real-world/instagram.md": [
        ("News Feed", "../news-feed.md"),
        ("Social Graph", "../social-graph.md"),
        ("Video Streaming", "../video-streaming.md"),
        ("Object Storage", "../../../storage/object-storage.md"),
        ("CDN & Caching", "../hld/caching-strategy.md"),
    ],
    "interview/system-design/real-world/netflix.md": [
        ("Video Streaming", "../video-streaming.md"),
        ("Recommendation System", "../../../ml/system-design/recommendation.md"),
        ("Availability Patterns", "../availability-patterns.md"),
        ("CDN & Caching", "../hld/caching-strategy.md"),
    ],
    "interview/system-design/real-world/twitter.md": [
        ("News Feed", "../news-feed.md"),
        ("Social Graph", "../social-graph.md"),
        ("Rate Limiter", "../rate-limiter.md"),
        ("Fanout & Messaging", "../hld/messaging-systems.md"),
        ("Caching Strategy", "../hld/caching-strategy.md"),
    ],
    "interview/system-design/real-world/uber.md": [
        ("Google Maps", "../google-maps.md"),
        ("Notification System", "../notifications.md"),
        ("Payment System", "../payment.md"),
        ("Rate Limiter", "../rate-limiter.md"),
        ("Real-Time Location", "../search.md"),
    ],
    "interview/system-design/real-world/whatsapp.md": [
        ("Chat System", "../chat.md"),
        ("Notification System", "../notifications.md"),
        ("Consistency Patterns", "../consistency-patterns.md"),
        ("End-to-End Encryption", "../hld/security-design.md"),
    ],
    "interview/system-design/real-world/youtube.md": [
        ("Video Streaming", "../video-streaming.md"),
        ("Search Engine", "../search.md"),
        ("Recommendation", "../../../ml/system-design/recommendation.md"),
        ("Object Storage", "../../../storage/object-storage.md"),
        ("CDN & Caching", "../hld/caching-strategy.md"),
    ],
    "interview/system-design/rpc.md": [
        ("API Design", "./hld/api-design.md"),
        ("Consistency Patterns", "./consistency-patterns.md"),
        ("Messaging Systems", "./hld/messaging-systems.md"),
        ("Cloud Networking", "../../cloud/aws/vpc.md"),
    ],
    "interview/system-design/social-graph.md": [
        ("News Feed", "./news-feed.md"),
        ("Graph Neural Networks", "../../ml/gnn/README.md"),
        ("Key-Value Store", "./kv-store.md"),
        ("Distributed File System", "./dfs.md"),
    ],
    "interview/system-design/stock-exchange.md": [
        ("Payment System", "./payment.md"),
        ("Latency vs Throughput", "./latency-vs-throughput.md"),
        ("Consistency Patterns", "./consistency-patterns.md"),
        ("Concurrency Overview", "../../concurrency/overview.md"),
    ],
    "interview/system-design/typeahead.md": [
        ("Search Engine", "./search.md"),
        ("Trie Data Structure", "../coding/data-structures.md"),
        ("Caching Strategy", "./hld/caching-strategy.md"),
        ("Estimation", "./estimation.md"),
        ("ML Search Ranking", "../../ml/system-design/search-ranking.md"),
    ],
    "interview/system-design/web-crawler.md": [
        ("Search Engine", "./search.md"),
        ("Distributed File System", "./dfs.md"),
        ("BFS / Graph Traversal", "../coding/patterns.md"),
        ("Robots.txt & Ethics", "./hld/security-design.md"),
        ("Object Storage", "../../storage/object-storage.md"),
    ],

    # ===== ML =====
    "ml/classical/README.md": [
        ("ML Foundations", "../foundations/README.md"),
        ("Deep Learning", "../deep-learning/README.md"),
        ("Ensemble Methods", "./ensemble.md"),
        ("Feature Engineering", "../foundations/feature-engineering.md"),
        ("ML Interview Questions", "../../interview/ml-questions.md"),
    ],
    "ml/deep-learning/README.md": [
        ("Neural Network Basics", "./nn-basics.md"),
        ("Transformers", "../transformers/README.md"),
        ("Classical ML", "../classical/README.md"),
        ("Optimizers", "./optimizers.md"),
        ("GPU Architecture", "../../cloud/virtualization/README.md"),
    ],
    "ml/deep-learning/transfer-learning.md": [
        ("Fine-Tuning (LLM)", "../../llm/llm-serving/sft.md"),
        ("Transformers", "../transformers/README.md"),
        ("Vision Transformers", "../transformers/vit.md"),
        ("Knowledge Distillation", "../advanced/distillation.md"),
        ("MLOps Deployment", "../mlops/deployment.md"),
    ],
    "ml/foundations/README.md": [
        ("Linear Algebra", "./linear-algebra.md"),
        ("Probability", "./probability.md"),
        ("Loss Functions", "./loss-functions.md"),
        ("Classical ML", "../classical/README.md"),
        ("ML Interview Questions", "../../interview/ml-questions.md"),
    ],
    "ml/mlops/README.md": [
        ("ML Pipelines", "./pipelines.md"),
        ("Model Deployment", "./deployment.md"),
        ("Monitoring", "./monitoring.md"),
        ("Cloud Kubernetes", "../../cloud/kubernetes/README.md"),
        ("CI/CD", "../../cloud/cicd/README.md"),
    ],
    "ml/mlops/cicd.md": [
        ("Cloud CI/CD", "../../cloud/cicd/pipelines.md"),
        ("GitOps", "../../cloud/cicd/gitops.md"),
        ("ML Pipelines", "./pipelines.md"),
        ("Model Registry", "./model-registry.md"),
        ("Deployment Strategies", "./deployment.md"),
    ],
    "ml/mlops/feature-store.md": [
        ("ML Feature Engineering", "../foundations/feature-engineering.md"),
        ("Data Pipeline", "../system-design/data-pipeline.md"),
        ("Storage Distributed", "../../storage/distributed.md"),
        ("MLOps Pipelines", "./pipelines.md"),
        ("System Design Feature Store", "../system-design/feature-store.md"),
    ],
    "ml/mlops/infrastructure.md": [
        ("Cloud Overview", "../../cloud/overview.md"),
        ("Kubernetes", "../../cloud/kubernetes/README.md"),
        ("GPU in Cloud", "../../cloud/virtualization/README.md"),
        ("MLOps Platforms", "./platforms.md"),
        ("Storage Overview", "../../storage/overview.md"),
    ],
    "ml/mlops/model-registry.md": [
        ("MLflow", "./mlflow.md"),
        ("Model Deployment", "./deployment.md"),
        ("Model Monitoring", "./monitoring.md"),
        ("Versioning & Storage", "../../storage/overview.md"),
    ],
    "ml/mlops/monitoring.md": [
        ("Cloud Observability", "../../cloud/observability/README.md"),
        ("Model Drift", "./drift.md"),
        ("A/B Testing", "./ab-testing.md"),
        ("Metrics & Logging", "../../cloud/observability/logging.md"),
        ("ML System Design Monitoring", "../system-design/monitoring.md"),
    ],
    "ml/mlops/pipelines.md": [
        ("Kubeflow", "./kubeflow.md"),
        ("Airflow / Orchestration", "../../cloud/cicd/pipelines.md"),
        ("Data Pipeline", "../system-design/data-pipeline.md"),
        ("Feature Store", "./feature-store.md"),
        ("Cloud Kubernetes", "../../cloud/kubernetes/README.md"),
    ],
    "ml/rl/README.md": [
        ("Q-Learning", "./q-learning.md"),
        ("Policy Gradient", "./policy-gradient.md"),
        ("PPO", "./ppo.md"),
        ("RLHF", "./rlhf.md"),
        ("LLM RLHF", "../../llm/llm-serving/rlhf.md"),
    ],
    "ml/rl/dpo.md": [
        ("RLHF", "./rlhf.md"),
        ("GRPO", "./grpo.md"),
        ("LLM SFT", "../../llm/llm-serving/sft.md"),
        ("LLM RLHF", "../../llm/llm-serving/rlhf.md"),
        ("Policy Gradient", "./policy-gradient.md"),
    ],
    "ml/rl/fundamentals.md": [
        ("Q-Learning", "./q-learning.md"),
        ("Policy Gradient", "./policy-gradient.md"),
        ("PPO", "./ppo.md"),
        ("Agent Architecture", "../agents/architecture.md"),
    ],
    "ml/rl/grpo.md": [
        ("DPO", "./dpo.md"),
        ("RLHF", "./rlhf.md"),
        ("PPO", "./ppo.md"),
        ("LLM RLHF", "../../llm/llm-serving/rlhf.md"),
        ("DeepSeek", "../../llm/sota/deepseek.md"),
    ],
    "ml/rl/policy-gradient.md": [
        ("PPO", "./ppo.md"),
        ("REINFORCE / Fundamentals", "./fundamentals.md"),
        ("Q-Learning", "./q-learning.md"),
        ("RLHF", "./rlhf.md"),
        ("Agent Planning", "../agents/planning.md"),
    ],
    "ml/rl/ppo.md": [
        ("Policy Gradient", "./policy-gradient.md"),
        ("RLHF", "./rlhf.md"),
        ("DPO", "./dpo.md"),
        ("LLM RLHF", "../../llm/llm-serving/rlhf.md"),
        ("ChatGPT / InstructGPT", "../../llm/sota/gpt4.md"),
    ],
    "ml/rl/q-learning.md": [
        ("Fundamentals", "./fundamentals.md"),
        ("Policy Gradient", "./policy-gradient.md"),
        ("Agent Architecture", "../agents/architecture.md"),
        ("Deep Learning", "../deep-learning/README.md"),
    ],
    "ml/rl/rlhf.md": [
        ("LLM RLHF", "../../llm/llm-serving/rlhf.md"),
        ("PPO", "./ppo.md"),
        ("DPO", "./dpo.md"),
        ("LLM SFT", "../../llm/llm-serving/sft.md"),
        ("Agent Safety", "../agents/safety.md"),
    ],
    "ml/time-series/README.md": [
        ("ARIMA", "./arima.md"),
        ("Anomaly Detection", "./anomaly.md"),
        ("Transformers for Time Series", "./transformers.md"),
        ("Deep Learning RNN/LSTM", "../deep-learning/rnn-lstm.md"),
        ("ML Foundations", "../foundations/README.md"),
    ],
    "ml/time-series/anomaly.md": [
        ("Time Series Overview", "./README.md"),
        ("ARIMA", "./arima.md"),
        ("ML Evaluation", "../foundations/evaluation.md"),
        ("MLOps Monitoring", "../mlops/monitoring.md"),
        ("Cloud Observability", "../../cloud/observability/README.md"),
    ],
    "ml/time-series/arima.md": [
        ("Time Series Overview", "./README.md"),
        ("Prophet", "./prophet.md"),
        ("Anomaly Detection", "./anomaly.md"),
        ("Transformers for Time Series", "./transformers.md"),
        ("ML Foundations Probability", "../foundations/probability.md"),
    ],
    "ml/time-series/prophet.md": [
        ("ARIMA", "./arima.md"),
        ("Time Series Overview", "./README.md"),
        ("Anomaly Detection", "./anomaly.md"),
        ("Feature Engineering", "../foundations/feature-engineering.md"),
    ],
    "ml/time-series/transformers.md": [
        ("Transformer Architecture", "../transformers/architecture.md"),
        ("Attention Mechanism", "../deep-learning/attention.md"),
        ("Time Series Overview", "./README.md"),
        ("ARIMA", "./arima.md"),
        ("LLM Architecture", "../../llm/llm-serving/architecture.md"),
    ],
}

def has_crossref_section(filepath):
    """Check if file already has a cross-references section."""
    with open(filepath, 'r') as f:
        content = f.read()
    return bool(re.search(r'^## .*[Cc]ross', content, re.MULTILINE) or 
                re.search(r'^## .*[Rr]elated', content, re.MULTILINE) or
                re.search(r'^## .*See [Aa]lso', content, re.MULTILINE) or
                re.search(r'^## .*🔗', content, re.MULTILINE))

def add_crossrefs(filepath, refs):
    """Add cross-references section to a file."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    if has_crossref_section(filepath):
        print(f"  SKIP (already has cross-refs): {filepath}")
        return False
    
    # Build cross-references section
    section = "\n## Cross-References\n\n"
    for name, link in refs:
        section += f"- [{name}]({link})\n"
    section += "\n"
    
    # Add at end
    content = content.rstrip() + "\n" + section
    
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"  OK: {filepath} ({len(refs)} refs)")
    return True

def main():
    count = 0
    for relpath, refs in sorted(CROSSREFS.items()):
        filepath = os.path.join(BASE, relpath)
        if not os.path.exists(filepath):
            print(f"  MISSING: {filepath}")
            continue
        if add_crossrefs(filepath, refs):
            count += 1
    print(f"\nDone. Added cross-refs to {count} files.")

if __name__ == "__main__":
    main()
