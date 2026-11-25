"""Process slot-level inventory predictions and stock alerts."""

from dataclasses import asdict, dataclass
from enum import StrEnum

DEFAULT_CONFIDENCE_THRESHOLD = 0.70


class StockStatus(StrEnum):
    """Represent the inventory status of a vending machine slot."""

    EMPTY = "empty"
    LOW_STOCK = "low_stock"
    IN_STOCK = "in_stock"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class InventoryResult:
    """Store the processed inventory result of a single slot."""

    machine_id: str
    slot_id: str
    product_name: str
    status: StockStatus
    confidence: float
    alert: bool

    def to_dict(self) -> dict:
        """Convert the inventory result into a serializable dictionary."""
        result = asdict(self)
        result["status"] = self.status.value
        return result


def determine_status(
    class_name: str,
    confidence: float,
    threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> StockStatus:
    """Determine stock status from a classification prediction."""

    if not 0.0 <= confidence <= 1.0:
        raise ValueError("Confidence must be between 0 and 1.")

    if not 0.0 <= threshold <= 1.0:
        raise ValueError("Threshold must be between 0 and 1.")

    if confidence < threshold:
        return StockStatus.UNKNOWN

    try:
        return StockStatus(class_name.strip().lower())
    except ValueError:
        return StockStatus.UNKNOWN


def should_alert(status: StockStatus) -> bool:
    """Return whether the inventory status requires a stock alert."""

    return status in (
        StockStatus.EMPTY,
        StockStatus.LOW_STOCK,
    )


# pylint: disable=too-many-arguments
# pylint: disable=too-many-positional-arguments
def build_inventory_result(
    machine_id: str,
    slot_id: str,
    product_name: str,
    class_name: str,
    confidence: float,
    threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> InventoryResult:
    """Build a structured inventory result from a slot prediction."""

    status = determine_status(
        class_name,
        confidence,
        threshold,
    )

    return InventoryResult(
        machine_id=machine_id,
        slot_id=slot_id,
        product_name=product_name,
        status=status,
        confidence=confidence,
        alert=should_alert(status),
    )


def collect_alerts(results: list[InventoryResult]) -> list[dict]:
    """Collect inventory results that require stock alerts."""

    return [result.to_dict() for result in results if result.alert]
