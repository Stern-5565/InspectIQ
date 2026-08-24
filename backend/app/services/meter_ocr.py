"""Mock AI/OCR meter-reading detection (Phase 14, scope §11). Scope explicitly asks for a mock
provider first (`prompts/backend_prompt.md`'s own phase table: "AI/OCR meter reading (mock
provider first)"). `IMeterReadingOcrService` mirrors `IMediaStorageService`'s local-now/
swappable-later shape (app/services/media_storage.py) so a real OCR/vision API integration
later is a drop-in second implementation of the same Protocol, not a rewrite of every caller.

Never let the AI value become the confirmed one automatically (scope §11's own explicit rule) -
this module only ever produces a *detected* reading; nothing in it ever touches
`MeterReading.ConfirmedReading`, which only `meter_reading_service.update_meter_reading` sets,
and only from an inspector's own explicit input.
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import BinaryIO, Protocol


@dataclass
class OcrResult:
    detected_reading: Decimal | None
    confidence: Decimal | None


class IMeterReadingOcrService(Protocol):
    def detect_reading(self, photo_stream: BinaryIO) -> OcrResult: ...


class MockMeterReadingOcrService:
    """Returns a plausible fixed reading without ever inspecting the actual image bytes - a
    real implementation would call a genuine OCR/vision API here instead. Reuses scope §11's own
    illustrative example value ("AI detected reading: 018294.6") rather than an arbitrary
    placeholder, so a demo session's output matches the spec it's demonstrating."""

    def detect_reading(self, photo_stream: BinaryIO) -> OcrResult:
        return OcrResult(detected_reading=Decimal("18294.6"), confidence=Decimal("0.87"))


def get_ocr_service() -> IMeterReadingOcrService:
    return MockMeterReadingOcrService()
