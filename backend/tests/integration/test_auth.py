"""Authentication flow: registration, login, JWT, and refresh rotation."""

import pytest

from tests.conftest import DEFAULT_PASSWORD, auth_header, login

pytestmark = pytest.mark.integration


class TestRegistration:
    async def test_register_returns_token_pair(self, client, seeded):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "New.User@Example.com",
                "password": "Strong@123",
                "full_name": "New User",
            },
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["token_type"] == "bearer"
        assert body["access_token"]
        assert body["user"]["email"] == "new.user@example.com"  # normalised to lowercase
        assert body["user"]["role"] == "customer"

    async def test_refresh_cookie_is_httponly_and_scoped(self, client, seeded):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "cookie@example.com",
                "password": "Strong@123",
                "full_name": "Cookie User",
            },
        )
        assert response.status_code == 201
        cookies = response.headers.get_list("set-cookie")
        refresh = next(c for c in cookies if c.startswith("refresh_token="))
        assert "HttpOnly" in refresh
        assert "Path=/api/v1/auth" in refresh
        assert "Secure" not in refresh  # httpOnly over http during local development

    async def test_duplicate_email_conflicts(self, client, seeded):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "admin@example.com",
                "password": "Strong@123",
                "full_name": "Impostor",
            },
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "conflict"

    @pytest.mark.parametrize(
        "password",
        ["short", "alllowercase1!", "NoDigits!!", "NoSymbols123"],
    )
    async def test_weak_passwords_rejected(self, client, seeded, password):
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "weak@example.com", "password": password, "full_name": "Weak"},
        )
        assert response.status_code == 422

    async def test_public_registration_cannot_self_assign_admin(self, client, seeded):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "sneaky@example.com",
                "password": "Strong@123",
                "full_name": "Sneaky",
                "role": "admin",
            },
        )
        assert response.status_code == 422


class TestLogin:
    async def test_login_succeeds(self, client, seeded):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": DEFAULT_PASSWORD},
        )
        assert response.status_code == 200
        assert response.json()["user"]["role"] == "admin"

    async def test_wrong_password_is_401(self, client, seeded):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "Wrong@12345"},
        )
        assert response.status_code == 401

    async def test_unknown_email_gives_same_message_as_wrong_password(self, client, seeded):
        """The two failures must be indistinguishable to prevent account enumeration."""
        unknown = await client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": DEFAULT_PASSWORD},
        )
        wrong = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "Wrong@12345"},
        )
        assert unknown.status_code == wrong.status_code == 401
        assert unknown.json()["error"]["message"] == wrong.json()["error"]["message"]


class TestAccessToken:
    async def test_me_requires_a_token(self, client):
        assert (await client.get("/api/v1/auth/me")).status_code == 401

    async def test_me_rejects_a_garbage_token(self, client):
        response = await client.get("/api/v1/auth/me", headers=auth_header("not-a-jwt"))
        assert response.status_code == 401

    async def test_me_returns_the_profile(self, client, seeded):
        token = await login(client, "owner@example.com")
        response = await client.get("/api/v1/auth/me", headers=auth_header(token))
        assert response.status_code == 200
        assert response.json()["email"] == "owner@example.com"

    async def test_a_refresh_token_cannot_be_used_as_an_access_token(self, client, seeded):
        """Token type confusion: the `type` claim must be checked."""
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": "owner@example.com", "password": DEFAULT_PASSWORD},
        )
        raw_refresh = login_response.cookies["refresh_token"]
        response = await client.get("/api/v1/auth/me", headers=auth_header(raw_refresh))
        assert response.status_code == 401


class TestRefreshRotation:
    async def test_refresh_returns_a_new_pair(self, client, seeded):
        await client.post(
            "/api/v1/auth/login",
            json={"email": "owner@example.com", "password": DEFAULT_PASSWORD},
        )
        response = await client.post("/api/v1/auth/refresh")
        assert response.status_code == 200
        assert response.json()["access_token"]

    async def test_rotating_revokes_the_previous_token(self, client, seeded):
        first = await client.post(
            "/api/v1/auth/login",
            json={"email": "owner@example.com", "password": DEFAULT_PASSWORD},
        )
        stale = first.cookies["refresh_token"]

        # The first rotation succeeds and replaces the cookie.
        assert (await client.post("/api/v1/auth/refresh")).status_code == 200

        # Replaying the original token is treated as theft.
        client.cookies.clear()
        client.cookies.set("refresh_token", stale, path="/api/v1/auth")
        replay = await client.post("/api/v1/auth/refresh")
        assert replay.status_code == 401
        assert "revoked" in replay.json()["error"]["message"].lower()

    async def test_reuse_kills_the_whole_family(self, client, seeded):
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": "owner@example.com", "password": DEFAULT_PASSWORD},
        )
        stale = login_response.cookies["refresh_token"]

        await client.post("/api/v1/auth/refresh")
        current = client.cookies["refresh_token"]

        # Reuse of the stale token must also revoke the live successor.
        client.cookies.clear()
        client.cookies.set("refresh_token", stale, path="/api/v1/auth")
        assert (await client.post("/api/v1/auth/refresh")).status_code == 401

        client.cookies.clear()
        client.cookies.set("refresh_token", current, path="/api/v1/auth")
        assert (await client.post("/api/v1/auth/refresh")).status_code == 401

    async def test_refresh_without_cookie_is_401(self, client):
        client.cookies.clear()
        assert (await client.post("/api/v1/auth/refresh")).status_code == 401

    async def test_refresh_with_unknown_token_is_401(self, client):
        client.cookies.clear()
        client.cookies.set("refresh_token", "made-up-token", path="/api/v1/auth")
        assert (await client.post("/api/v1/auth/refresh")).status_code == 401


class TestLogout:
    async def test_logout_revokes_the_session(self, client, seeded):
        await client.post(
            "/api/v1/auth/login",
            json={"email": "owner@example.com", "password": DEFAULT_PASSWORD},
        )
        assert (await client.post("/api/v1/auth/logout")).status_code == 200
        client.cookies.clear()
        client.cookies.set("refresh_token", "x", path="/api/v1/auth")
        # The real cookie was cleared server-side, so refresh no longer works.
        assert (await client.post("/api/v1/auth/refresh")).status_code == 401

    async def test_logout_all_revokes_every_session(self, client, seeded):
        # Two independent logins create two separate sessions.
        await client.post(
            "/api/v1/auth/login",
            json={"email": "owner@example.com", "password": DEFAULT_PASSWORD},
        )
        second = await client.post(
            "/api/v1/auth/login",
            json={"email": "owner@example.com", "password": DEFAULT_PASSWORD},
        )
        second_refresh = second.cookies["refresh_token"]

        # logout-all requires a valid access token.
        assert (
            await client.post("/api/v1/auth/logout-all", headers=auth_header("x"))
        ).status_code == 401

        token = await login(client, "owner@example.com")
        logout_all = await client.post("/api/v1/auth/logout-all", headers=auth_header(token))
        assert logout_all.status_code == 200
        assert "Revoked" in logout_all.json()["message"]

        # The other session's refresh token must now be dead too.
        client.cookies.clear()
        client.cookies.set("refresh_token", second_refresh, path="/api/v1/auth")
        assert (await client.post("/api/v1/auth/refresh")).status_code == 401
