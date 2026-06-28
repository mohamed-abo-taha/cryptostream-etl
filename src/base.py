"""Abstract base classes that define the ETL contract.

This is the OOP backbone of the project. Each stage of the pipeline is an
*interface* (an abstract base class). Concrete implementations — a REST
extractor, a mock extractor, a SQLite loader — are interchangeable as long as
they honour the contract. The ``Pipeline`` orchestrator depends only on these
abstractions, not on the concrete classes (dependency inversion).
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Iterable

from .models import Coin

logger = logging.getLogger("cryptostream")


class Extractor(ABC):
    """Pulls raw records from some source system (the 'E' in ETL)."""

    @abstractmethod
    def extract(self) -> list[dict]:
        """Return a list of raw, source-shaped dictionaries."""
        raise NotImplementedError


class Transformer(ABC):
    """Cleans and reshapes raw records into domain objects (the 'T')."""

    @abstractmethod
    def transform(self, raw_records: list[dict]) -> list[Coin]:
        raise NotImplementedError


class Loader(ABC):
    """Persists domain objects into a destination system (the 'L')."""

    @abstractmethod
    def load(self, coins: Iterable[Coin]) -> int:
        """Persist the records and return how many rows were written."""
        raise NotImplementedError
