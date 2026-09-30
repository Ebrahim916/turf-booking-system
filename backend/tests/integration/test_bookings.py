"""Booking creation, double-booking prevention, and lifecycle."""

from datetime import timedelta

import pytest

from tests.conftest import auth_header, login

pytestmark = pytest.mark.integration


async def create_booking(client, token, turf_id: int, start, end=None):
    payload = {"turf_id": turf_id, "start_time": start.isoformat()}
    if end is not None:
        payload["end_time"] = end.isoformat()
    return await client.post("/api/v1/bookings", json=payload, headers=auth_header(token))


class TestBookingCreation:
    async def test_creates_a_confirmed_booking(self, client, seeded, turf, tomorrow):
        token = await login(client, "customer@example.com")
        response = await create_booking(
            client, token, turf.id, tomorrow, tomorrow + timedelta(hours=1)
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["status"] == "confirmed"
        assert body["payment_status"] == "unpaid"
        # 100.00/hour for one hour.
        assert float(body["total_price"]) == 100.0
        assert body["turf_name"] == "Test Arena"

    async def test_end_time_defaults_to_the_slot_duration(self, client, seeded, turf, tomorrow):
        token = await login(client, "customer@example.com")
        response = await create_booking(client, token, turf.id, tomorrow)
        assert response.status_code == 201
        start = response.json()["start_time"]
        end = response.json()["end_time"]
        assert (int(end[11:13]) * 60 + int(end[14:16])) - (
            int(start[11:13]) * 60 + int(start[14:16])
        ) == 60

    async def test_unauthenticated_is_401(self, client, seeded, turf, tomorrow):
        response = await create_booking(client, "", turf.id, tomorrow)
        assert response.status_code == 401

    async def test_unknown_turf_is_404(self, client, seeded, tomorrow):
        token = await login(client, "customer@example.com")
        response = await create_booking(client, token, 999999, tomorrow)
        assert response.status_code == 404

    async def test_past_booking_is_rejected(self, client, seeded, turf):
        from datetime import UTC, datetime

        token = await login(client, "customer@example.com")
        yesterday = datetime.now(UTC) - timedelta(days=1)
        response = await create_booking(client, token, turf.id, yesterday)
        assert response.status_code == 422
        assert "past" in response.json()["error"]["message"].lower()

    async def test_outside_availability_is_rejected(self, client, seeded, turf, tomorrow):
        """03:00 falls outside the turf's 08:00-22:00 window."""
        token = await login(client, "customer@example.com")
        early = tomorrow.replace(hour=3)
        response = await create_booking(client, token, turf.id, early)
        assert response.status_code == 422
        assert "availability" in response.json()["error"]["message"].lower()

    async def test_overlong_booking_is_rejected(self, client, seeded, turf, tomorrow):
        token = await login(client, "customer@example.com")
        response = await create_booking(
            client, token, turf.id, tomorrow, tomorrow + timedelta(hours=9)
        )
        assert response.status_code == 422


class TestDoubleBooking:
    async def test_exact_overlap_is_rejected(self, client, seeded, turf, tomorrow):
        token = await login(client, "customer@example.com")
        first = await create_booking(client, token, turf.id, tomorrow)
        assert first.status_code == 201

        second = await create_booking(
            client, token, turf.id, tomorrow, tomorrow + timedelta(hours=1)
        )
        assert second.status_code == 409
        assert second.json()["error"]["code"] == "booking_conflict"

    async def test_partial_overlap_is_rejected(self, client, seeded, turf, tomorrow):
        token = await login(client, "customer@example.com")
        await create_booking(client, token, turf.id, tomorrow, tomorrow + timedelta(hours=2))

        # Starts inside the existing window.
        overlapping = await create_booking(client, token, turf.id, tomorrow + timedelta(hours=1))
        assert overlapping.status_code == 409

    async def test_adjacent_booking_is_allowed(self, client, seeded, turf, tomorrow):
        """Back-to-back slots must not conflict: intervals are half-open."""
        token = await login(client, "customer@example.com")
        first = await create_booking(
            client, token, turf.id, tomorrow, tomorrow + timedelta(hours=1)
        )
        assert first.status_code == 201

        second = await create_booking(client, token, turf.id, tomorrow + timedelta(hours=1))
        assert second.status_code == 201, second.text

    async def test_cancelled_booking_frees_the_slot(self, client, seeded, turf, tomorrow):
        token = await login(client, "customer@example.com")
        first = await create_booking(client, token, turf.id, tomorrow)
        booking_id = first.json()["id"]

        cancel = await client.post(
            f"/api/v1/bookings/{booking_id}/cancel", headers=auth_header(token)
        )
        assert cancel.status_code == 200
        assert cancel.json()["status"] == "cancelled"

        rebook = await create_booking(client, token, turf.id, tomorrow)
        assert rebook.status_code == 201

    async def test_different_turfs_do_not_conflict(self, client, seeded, turf, tomorrow):
        # A second turf, created through the API as the owner.
        owner_token = await login(client, "owner@example.com")
        created = await client.post(
            "/api/v1/turfs",
            json={
                "name": "Other Arena",
                "address": "2 Other Street",
                "city": "Testville",
                "size": "7-a-side",
                "price_per_hour": "200.00",
            },
            headers=auth_header(owner_token),
        )
        assert created.status_code == 201, created.text
        other_id = created.json()["id"]

        # The same time on two different turfs must not conflict.
        customer_token = await login(client, "customer@example.com")
        first = await create_booking(client, customer_token, turf.id, tomorrow)
        assert first.status_code == 201
        second = await create_booking(client, customer_token, other_id, tomorrow)
        assert second.status_code == 201


class TestAvailability:
    async def test_slots_are_generated_for_a_day(self, client, seeded, turf, tomorrow):
        token = await login(client, "customer@example.com")
        response = await client.get(
            f"/api/v1/turfs/{turf.id}/availability",
            params={"date": tomorrow.date().isoformat()},
            headers=auth_header(token),
        )
        assert response.status_code == 200
        slots = response.json()
        # 08:00 through 22:00 in one-hour slots.
        assert len(slots) == 14
        assert all(slot["is_available"] for slot in slots)
        assert float(slots[0]["total_price"]) == 100.0

    async def test_booked_slot_is_marked_unavailable(self, client, seeded, turf, tomorrow):
        customer_token = await login(client, "customer@example.com")
        await create_booking(client, customer_token, turf.id, tomorrow)

        owner_token = await login(client, "owner@example.com")
        response = await client.get(
            f"/api/v1/turfs/{turf.id}/availability",
            params={"date": tomorrow.date().isoformat()},
            headers=auth_header(owner_token),
        )
        slots = {slot["start_time"]: slot for slot in response.json()}
        booked = next(
            s
            for start, s in slots.items()
            if s["start_time"].startswith(f"{tomorrow.date().isoformat()}T{tomorrow.hour:02d}")
        )
        assert booked["is_available"] is False

    async def test_malformed_date_is_422(self, client, seeded, turf):
        token = await login(client, "customer@example.com")
        response = await client.get(
            f"/api/v1/turfs/{turf.id}/availability",
            params={"date": "not-a-date"},
            headers=auth_header(token),
        )
        assert response.status_code == 422


class TestBookingLifecycle:
    async def test_customer_can_cancel_own_booking(self, client, seeded, turf, tomorrow):
        token = await login(client, "customer@example.com")
        created = await create_booking(client, token, turf.id, tomorrow)
        booking_id = created.json()["id"]

        response = await client.post(
            f"/api/v1/bookings/{booking_id}/cancel", headers=auth_header(token)
        )
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    async def test_cancelling_twice_is_rejected(self, client, seeded, turf, tomorrow):
        token = await login(client, "customer@example.com")
        created = await create_booking(client, token, turf.id, tomorrow)
        booking_id = created.json()["id"]
        await client.post(f"/api/v1/bookings/{booking_id}/cancel", headers=auth_header(token))

        again = await client.post(
            f"/api/v1/bookings/{booking_id}/cancel", headers=auth_header(token)
        )
        assert again.status_code == 422

    async def test_customer_cannot_change_status(self, client, seeded, turf, tomorrow):
        token = await login(client, "customer@example.com")
        created = await create_booking(client, token, turf.id, tomorrow)
        response = await client.patch(
            f"/api/v1/bookings/{created.json()['id']}",
            json={"status": "completed"},
            headers=auth_header(token),
        )
        assert response.status_code == 403

    async def test_admin_can_mark_payment_received(self, client, seeded, turf, tomorrow):
        customer_token = await login(client, "customer@example.com")
        created = await create_booking(client, customer_token, turf.id, tomorrow)

        admin_token = await login(client, "admin@example.com")
        response = await client.patch(
            f"/api/v1/bookings/{created.json()['id']}",
            json={"payment_status": "paid_on_site"},
            headers=auth_header(admin_token),
        )
        assert response.status_code == 200
        assert response.json()["payment_status"] == "paid_on_site"

    async def test_invalid_transition_is_rejected(self, client, seeded, turf, tomorrow):
        customer_token = await login(client, "customer@example.com")
        created = await create_booking(client, customer_token, turf.id, tomorrow)
        booking_id = created.json()["id"]

        await client.post(
            f"/api/v1/bookings/{booking_id}/cancel", headers=auth_header(customer_token)
        )

        admin_token = await login(client, "admin@example.com")
        response = await client.patch(
            f"/api/v1/bookings/{booking_id}",
            json={"status": "confirmed"},
            headers=auth_header(admin_token),
        )
        assert response.status_code == 422
        assert "cannot change" in response.json()["error"]["message"].lower()

    async def test_customer_cannot_read_another_customers_booking(
        self, client, seeded, turf, tomorrow
    ):
        first_token = await login(client, "customer@example.com")
        created = await create_booking(client, first_token, turf.id, tomorrow)

        # A second customer account.
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "other@example.com",
                "password": "Strong@123",
                "full_name": "Other Customer",
            },
        )
        other_token = await login(client, "other@example.com", "Strong@123")
        response = await client.get(
            f"/api/v1/bookings/{created.json()['id']}", headers=auth_header(other_token)
        )
        assert response.status_code == 403
