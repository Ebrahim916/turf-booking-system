"""Unit tests for the pure booking/slot logic."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import ClassVar

import pytest

from app.services.slot import MAX_DAYS_AHEAD, overlaps, price_for


def utc(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 1, 5, hour, minute, tzinfo=UTC)  # a Monday


class TestOverlap:
    def test_identical_intervals_overlap(self):
        assert overlaps(utc(10), utc(11), utc(10), utc(11))

    def test_partial_overlap_on_both_sides(self):
        assert overlaps(utc(10), utc(12), utc(11), utc(13))
        assert overlaps(utc(11), utc(13), utc(10), utc(12))

    def test_contained_interval_overlaps(self):
        assert overlaps(utc(9), utc(17), utc(10), utc(11))
        assert overlaps(utc(10), utc(11), utc(9), utc(17))

    def test_adjacent_intervals_do_not_overlap(self):
        """Back-to-back bookings must be allowed, which is why intervals are
        half-open: [10, 11) and [11, 12) share no time."""
        assert not overlaps(utc(10), utc(11), utc(11), utc(12))
        assert not overlaps(utc(11), utc(12), utc(10), utc(11))

    def test_disjoint_intervals_do_not_overlap(self):
        assert not overlaps(utc(8), utc(9), utc(10), utc(11))


class TestPriceFor:
    def test_full_hour(self):
        assert price_for(Decimal("800.00"), utc(10), utc(11)) == Decimal("800.00")

    def test_two_hours(self):
        assert price_for(Decimal("800.00"), utc(10), utc(12)) == Decimal("1600.00")

    def test_partial_hour_is_prorated(self):
        assert price_for(Decimal("600.00"), utc(10), utc(10, 30)) == Decimal("300.00")

    def test_quarter_hour(self):
        assert price_for(Decimal("800.00"), utc(10), utc(10, 15)) == Decimal("200.00")

    def test_result_is_quantised_to_two_places(self):
        price = price_for(Decimal("100.00"), utc(10), utc(10, 20))
        assert price == Decimal("33.33")
        assert price.as_tuple().exponent == -2


class TestSlotWindow:
    async def test_far_future_date_is_rejected(self):
        from app.core.exceptions import ValidationError
        from app.services.slot import generate_slots

        class FakeTurf:
            schedules: ClassVar[list] = []
            price_per_hour = Decimal("100.00")
            slot_duration_minutes = 60
            id = 1

        too_far = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(
            days=MAX_DAYS_AHEAD + 1
        )
        # The date guard runs before any query, so no session is needed.
        with pytest.raises(ValidationError):
            await generate_slots(None, FakeTurf(), too_far)  # type: ignore[arg-type]
