"""Turf CRUD, schedules, and role-based access control."""

import pytest

from tests.conftest import auth_header, login

pytestmark = pytest.mark.integration

TURF_PAYLOAD = {
    "name": "New Pitch",
    "description": "A nice pitch",
    "address": "9 New Road",
    "city": "Testville",
    "size": "5-a-side",
    "surface": "artificial",
    "price_per_hour": "600.00",
    "slot_duration_minutes": 60,
}


class TestTurfCrud:
    async def test_owner_can_create_a_turf(self, client, seeded):
        token = await login(client, "owner@example.com")
        response = await client.post("/api/v1/turfs", json=TURF_PAYLOAD, headers=auth_header(token))
        assert response.status_code == 201, response.text
        assert response.json()["name"] == "New Pitch"

    async def test_customer_cannot_create_a_turf(self, client, seeded):
        token = await login(client, "customer@example.com")
        response = await client.post("/api/v1/turfs", json=TURF_PAYLOAD, headers=auth_header(token))
        assert response.status_code == 403

    async def test_anonymous_cannot_create_a_turf(self, client, seeded):
        assert (await client.post("/api/v1/turfs", json=TURF_PAYLOAD)).status_code == 401

    async def test_price_must_be_positive(self, client, seeded):
        token = await login(client, "owner@example.com")
        response = await client.post(
            "/api/v1/turfs",
            json={**TURF_PAYLOAD, "price_per_hour": "0"},
            headers=auth_header(token),
        )
        assert response.status_code == 422

    async def test_owner_can_update_their_turf(self, client, seeded, turf):
        token = await login(client, "owner@example.com")
        response = await client.patch(
            f"/api/v1/turfs/{turf.id}",
            json={"price_per_hour": "750.00"},
            headers=auth_header(token),
        )
        assert response.status_code == 200
        assert float(response.json()["price_per_hour"]) == 750.0

    async def test_a_second_owner_cannot_update_the_turf(self, client, seeded, turf):
        created = await client.post(
            "/api/v1/users",
            json={
                "email": "rival@example.com",
                "password": "Strong@123",
                "full_name": "Rival Owner",
                "role": "owner",
            },
            headers=auth_header(await login(client, "admin@example.com")),
        )
        assert created.status_code == 201, created.text
        rival_token = await login(client, "rival@example.com", "Strong@123")
        response = await client.patch(
            f"/api/v1/turfs/{turf.id}",
            json={"price_per_hour": "1.00"},
            headers=auth_header(rival_token),
        )
        assert response.status_code == 403

    async def test_admin_can_update_any_turf(self, client, seeded, turf):
        token = await login(client, "admin@example.com")
        response = await client.patch(
            f"/api/v1/turfs/{turf.id}",
            json={"price_per_hour": "900.00"},
            headers=auth_header(token),
        )
        assert response.status_code == 200

    async def test_delete_is_a_soft_delete(self, client, seeded, turf):
        token = await login(client, "owner@example.com")
        response = await client.delete(f"/api/v1/turfs/{turf.id}", headers=auth_header(token))
        assert response.status_code == 200

        # Still retrievable by id (bookings reference it) but hidden from the list.
        assert (
            await client.get(f"/api/v1/turfs/{turf.id}", headers=auth_header(token))
        ).status_code == 200
        listing = await client.get("/api/v1/turfs", headers=auth_header(token))
        assert turf.id not in [t["id"] for t in listing.json()]

    async def test_unknown_turf_is_404(self, client, seeded):
        token = await login(client, "customer@example.com")
        assert (
            await client.get("/api/v1/turfs/999999", headers=auth_header(token))
        ).status_code == 404


class TestSchedules:
    async def test_duplicate_day_is_rejected(self, client, seeded, turf):
        token = await login(client, "owner@example.com")
        response = await client.post(
            f"/api/v1/turfs/{turf.id}/schedules",
            json={"day_of_week": 0, "open_time": "09:00:00", "close_time": "11:00:00"},
            headers=auth_header(token),
        )
        assert response.status_code == 409

    async def test_close_before_open_is_rejected(self, client, seeded, turf):
        token = await login(client, "owner@example.com")
        response = await client.post(
            f"/api/v1/turfs/{turf.id}/schedules",
            json={"day_of_week": 0, "open_time": "18:00:00", "close_time": "06:00:00"},
            headers=auth_header(token),
        )
        assert response.status_code == 422

    async def test_day_out_of_range_is_rejected(self, client, seeded, turf):
        token = await login(client, "owner@example.com")
        response = await client.post(
            f"/api/v1/turfs/{turf.id}/schedules",
            json={"day_of_week": 9, "open_time": "09:00:00", "close_time": "11:00:00"},
            headers=auth_header(token),
        )
        assert response.status_code == 422

    async def test_customer_cannot_manage_schedules(self, client, seeded, turf):
        token = await login(client, "customer@example.com")
        response = await client.get(
            f"/api/v1/turfs/{turf.id}/schedules", headers=auth_header(token)
        )
        assert response.status_code == 403


class TestUserAdministration:
    async def test_admin_can_provision_an_owner(self, client, seeded):
        token = await login(client, "admin@example.com")
        response = await client.post(
            "/api/v1/users",
            json={
                "email": "newowner@example.com",
                "password": "Strong@123",
                "full_name": "New Owner",
                "role": "owner",
            },
            headers=auth_header(token),
        )
        assert response.status_code == 201, response.text
        assert response.json()["role"] == "owner"
        assert response.json()["is_verified"] is True

    async def test_non_admin_cannot_provision_users(self, client, seeded):
        token = await login(client, "owner@example.com")
        response = await client.post(
            "/api/v1/users",
            json={
                "email": "sneaky@example.com",
                "password": "Strong@123",
                "full_name": "Sneaky",
                "role": "admin",
            },
            headers=auth_header(token),
        )
        assert response.status_code == 403

    async def test_admin_cannot_demote_themselves(self, client, seeded):
        token = await login(client, "admin@example.com")
        me = await client.get("/api/v1/users/me", headers=auth_header(token))
        response = await client.patch(
            f"/api/v1/users/{me.json()['id']}",
            json={"role": "customer"},
            headers=auth_header(token),
        )
        assert response.status_code == 422

    async def test_deactivating_a_user_revokes_sessions(self, client, seeded):
        # Owner logs in, creating a session.
        owner_login = await client.post(
            "/api/v1/auth/login",
            json={"email": "owner@example.com", "password": "Test@12345"},
        )
        owner_refresh = owner_login.cookies["refresh_token"]

        admin_token = await login(client, "admin@example.com")
        users = await client.get("/api/v1/users", headers=auth_header(admin_token))
        owner_id = next(u["id"] for u in users.json() if u["email"] == "owner@example.com")

        response = await client.delete(
            f"/api/v1/users/{owner_id}", headers=auth_header(admin_token)
        )
        assert response.status_code == 200

        # The already-issued refresh token must no longer work.
        client.cookies.clear()
        client.cookies.set("refresh_token", owner_refresh, path="/api/v1/auth")
        assert (await client.post("/api/v1/auth/refresh")).status_code == 401

    async def test_password_change_revokes_sessions(self, client, seeded):
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": "customer@example.com", "password": "Test@12345"},
        )
        refresh = login_response.cookies["refresh_token"]
        token = login_response.json()["access_token"]

        response = await client.patch(
            "/api/v1/users/me/password",
            json={"current_password": "Test@12345", "new_password": "BrandNew@123"},
            headers=auth_header(token),
        )
        assert response.status_code == 200

        client.cookies.clear()
        client.cookies.set("refresh_token", refresh, path="/api/v1/auth")
        assert (await client.post("/api/v1/auth/refresh")).status_code == 401

        # And the new password works.
        assert (
            await client.post(
                "/api/v1/auth/login",
                json={"email": "customer@example.com", "password": "BrandNew@123"},
            )
        ).status_code == 200

    async def test_password_change_requires_the_current_password(self, client, seeded):
        token = await login(client, "customer@example.com")
        response = await client.patch(
            "/api/v1/users/me/password",
            json={"current_password": "Wrong@1234", "new_password": "BrandNew@123"},
            headers=auth_header(token),
        )
        assert response.status_code == 422


class TestHealth:
    async def test_health_reports_ok(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] in ("ok", "degraded")
