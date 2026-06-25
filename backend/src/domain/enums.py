"""Domain enums and value objects (framework-free)."""

from __future__ import annotations

from enum import Enum


class MaturityBand(str, Enum):
    """Product-facing band for a dimension (aggregate of sub-dimensions)."""

    SIT = "sit"
    CRAWL = "crawl"
    WALK = "walk"
    RUN = "run"


class QueryDialect(str, Enum):
    """Supported connector query languages (extensible)."""

    PROMQL = "promql"
    LOGQL = "logql"
    SQL = "sql"
    REST_JSONPATH = "rest_jsonpath"
    GITHUB_GRAPHQL = "github_graphql"


class EvidenceConfidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"
