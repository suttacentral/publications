from dataclasses import dataclass


@dataclass(frozen=True)
class IngestResult:
    content: str
