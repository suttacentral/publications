from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    bilara_data_url = "https://github.com/suttacentral/bilara-data"
    publication_number: str

    @classmethod
    def from_publication(cls, publication_number: str) -> Config:
        return cls(publication_number=publication_number)
