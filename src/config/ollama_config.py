import yaml
from dataclasses import dataclass


@dataclass
class OllamaConfig:
    enabled: bool
    ollama_url: str
    model: str
    top_n: int
    timeout_ms: int
    retries: int
    accuracy_threshold: float
    mode: str


def load_config(path: str = "config/ollama.yml") -> OllamaConfig:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return OllamaConfig(
        enabled=data.get("enabled", True),
        ollama_url=data.get("ollama_url", "http://localhost:11434"),
        model=data.get("model", "moondream-v1"),
        top_n=data.get("top_n", 3),
        timeout_ms=data.get("timeout_ms", 2000),
        retries=data.get("retries", 3),
        accuracy_threshold=data.get("accuracy_threshold", 0.7),
        mode=data.get("mode", "realtime"),
    )
