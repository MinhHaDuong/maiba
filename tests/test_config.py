from maiba.config import load_config


def test_load_default_config():
    cfg = load_config("config/maiba.yaml")
    assert cfg.contact.mailto == "minh.ha-duong@cnrs.fr"
    assert cfg.http.timeout_s == 10
    assert cfg.resolvers.order == ["openalex", "crossref"]
    assert "TI" in cfg.gaps.required_fields
    assert cfg.matching.title_similarity_min == 0.85
    assert cfg.llm.enabled is False
    assert cfg.provenance.tag_prefix == "maiba"
