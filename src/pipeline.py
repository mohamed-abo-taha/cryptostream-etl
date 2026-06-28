"""Pipeline orchestrator — wires Extractor -> Transformer -> Loader together.

The orchestrator knows *nothing* about REST, JSON or SQLite. It only talks to
the abstract interfaces, so any stage can be swapped without touching this file.
That is the whole point of the OOP design.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from .base import Extractor, Loader, Transformer

logger = logging.getLogger("cryptostream")


@dataclass
class PipelineResult:
    extracted: int
    transformed: int
    loaded: int
    duration_s: float


class Pipeline:
    """Run a single extract -> transform -> load cycle."""

    def __init__(
        self,
        extractor: Extractor,
        transformer: Transformer,
        loader: Loader,
    ) -> None:
        self.extractor = extractor
        self.transformer = transformer
        self.loader = loader

    def run(self) -> PipelineResult:
        start = time.perf_counter()
        logger.info("=== Pipeline run started ===")

        raw = self.extractor.extract()
        coins = self.transformer.transform(raw)
        loaded = self.loader.load(coins)

        duration = time.perf_counter() - start
        result = PipelineResult(
            extracted=len(raw),
            transformed=len(coins),
            loaded=loaded,
            duration_s=round(duration, 3),
        )
        logger.info(
            "=== Pipeline finished in %ss: %d extracted, %d transformed, %d loaded ===",
            result.duration_s,
            result.extracted,
            result.transformed,
            result.loaded,
        )
        return result
