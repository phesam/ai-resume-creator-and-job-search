"""Public technical terms: what postings ask for, and what makes a bullet read as engineering rather than a task."""

from __future__ import annotations

import re

_TERMS = """TypeScript; JavaScript; Python; Java; Go|Golang; Rust; C\\+\\+; C#; Ruby; PHP; Kotlin; Swift; Scala; SQL; Bash;
React; Next\\.js; Angular; Vue; Svelte; Node\\.js|NodeJS; Express; Django; Flask; FastAPI; Spring|Spring Boot; Rails;
\\.NET; GraphQL; gRPC; REST|RESTful; Redux; Tailwind; HTML; CSS; React Native; Electron; Flutter;
PostgreSQL|Postgres; MySQL; MongoDB; Redis; Elasticsearch|OpenSearch; DynamoDB; Cassandra; Snowflake; BigQuery;
Kafka; RabbitMQ; SQS; NATS; Spark; Airflow; dbt; Flink; Hadoop;
AWS|Amazon Web Services; GCP|Google Cloud; Azure; Kubernetes|K8s; Docker; Terraform; Helm; Ansible; Linux; CI/CD;
GitHub Actions; Jenkins; Datadog; Grafana; Prometheus; Sentry; OpenTelemetry; Observability; On-call|on call;
Microservices; Distributed systems; System design; Full stack|full-stack|fullstack; Backend|back-end; Frontend|front-end;
PyTorch; TensorFlow; LLM|LLMs; RAG; Machine learning|\\bML\\b; Generative AI|GenAI; AI agents?|agentic;
Embedded; Firmware; RTOS; ROS|ROS 2; CAN bus; Real-time|realtime; WebSockets?; WebRTC; A/B test\\w*|experimentation;
Figma; Testing|unit tests?; Playwright|Cypress; Jest; pytest; Git"""
# Ordinary English words: only their capitalized form means the technology ("go to market" isn't Go).
_EXACT_CASE = {"Go", "Rust", "Swift", "Express", "Spring", "Rails", "REST", "Spark", "Flutter", "Vue", "Scala", "Bash",
               "Git", "Jest", "Helm", "Angular", "Testing"}


def _term(raw: str) -> tuple[str, re.Pattern]:
    raw = raw.strip()
    label = re.sub(r"\\w\*|\\b|\?|\\", "", raw.split("|")[0])
    label = re.sub(r"s$", "", label) if raw.split("|")[0].endswith("s?") else label
    flags = 0 if label in _EXACT_CASE else re.I
    return label, re.compile(r"(?<![\w+#.])(?:" + raw + r")(?![\w+#])", flags)


TERMS = [_term(t) for t in _TERMS.replace("\n", " ").split(";") if t.strip()]


_ACRONYM = re.compile(r"\b(?:[A-Z]{2,}[A-Za-z0-9]*|[A-Za-z]+[0-9]+[A-Za-z0-9]*|[a-z]+[A-Z][A-Za-z0-9]*)\b")
_NOT_TECH = {"US", "USA", "UK", "AI", "ARR", "MRR", "GMV", "ROI", "KPI", "CEO", "CTO", "VP", "SVP", "HR", "PM", "OK", "QA"}


def technical_terms(text: str) -> set[str]:
    """Distinct technical terms in a text: the public list above, plus acronyms and coined names (BM25, gRPC, pgvector-style
    camelCase). A proxy for how much engineering a page shows, not a keyword score."""
    found = {label for label, rx in TERMS if rx.search(text)}
    found |= {m for m in _ACRONYM.findall(text) if m not in _NOT_TECH}
    return found
