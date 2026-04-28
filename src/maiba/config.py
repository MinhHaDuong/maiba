"""Configuration loader — reads config/maiba.yaml into typed models."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel


class ContactConfig(BaseModel):
    mailto: str


class HttpConfig(BaseModel):
    timeout_s: int
    max_retries: int
    backoff_s: float
    rate_limit_per_s: int
    cache_dir: str
    cache_ttl_s: int


class ResolverEndpoint(BaseModel):
    base_url: str
    search_rows: int = 20
    year_window: int = 1


class ResolversConfig(BaseModel):
    order: list[str]
    openalex: ResolverEndpoint
    crossref: ResolverEndpoint


class GapsConfig(BaseModel):
    required_fields: list[str]
    recommended_fields: list[str]
    forbidden_authors: list[str]


class MatchingConfig(BaseModel):
    title_similarity_min: float
    author_overlap_min: float
    apply_threshold: float


class LlmConfig(BaseModel):
    enabled: bool
    provider: str
    model: str
    endpoint_padme: str


class ProvenanceConfig(BaseModel):
    tag_prefix: str


class Config(BaseModel):
    contact: ContactConfig
    http: HttpConfig
    resolvers: ResolversConfig
    gaps: GapsConfig
    matching: MatchingConfig
    llm: LlmConfig
    provenance: ProvenanceConfig


def load_config(path: str | Path) -> Config:
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return Config.model_validate(raw)
