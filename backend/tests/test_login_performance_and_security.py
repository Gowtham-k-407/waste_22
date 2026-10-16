import time
import pytest
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient

from app.main import app
from app.core.security import hash_password, create_access_token
from app.core.database import UserSessionLocal
from app.models.user import User, AuthAuditLog

client = TestClient(app)

@pytest.fixture(scope="module")
def user_db_session():
    db = UserSessionLocal()
    yield db
    db.close()

@pytest.fixture(scope="module")
def setup_test_users(user_db_session):
    db = user_db_session

    # 1. Active Test User
    active_user = db.query(User).filter(User.email == "perf_test_user@chennaiswm.gov.in").first()
    if not active_user:
        active_user = User(
            username="perf_test_user",
            email="perf_test_user@chennaiswm.gov.in",
            hashed_password=hash_password("ValidPassword123!"),
            full_name="Performance Test User",
            role="municipal_officer",
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        db.add(active_user)
        db.commit()
        db.refresh(active_user)
    else:
        active_user.hashed_password = hash_password("ValidPassword123!")
        active_user.is_active = True
        db.commit()

    # 2. Deactivated User
    deact_user = db.query(User).filter(User.email == "perf_deact_user@chennaiswm.gov.in").first()
    if not deact_user:
        deact_user = User(
            username="perf_deact_user",
            email="perf_deact_user@chennaiswm.gov.in",
            hashed_password=hash_password("ValidPassword123!"),
            full_name="Deactivated Test User",
            role="contributor",
            is_active=False,
            created_at=datetime.now(timezone.utc)
        )
        db.add(deact_user)
        db.commit()
        db.refresh(deact_user)
    else:
        deact_user.is_active = False
        db.commit()

    return {
        "active_user": active_user,
        "deact_user": deact_user,
        "valid_password": "ValidPassword123!"
    }


# =========================================================================
# 1. LOGIN ACCURACY, HEADERS, AND TIMING TELEMETRY TESTS
# =========================================================================

def test_login_success_with_server_timing_headers(setup_test_users):
    """Verify valid login returns 200, JWT token, user object, and W3C Server-Timing header."""
    user = setup_test_users["active_user"]
    pw = setup_test_users["valid_password"]

    res = client.post("/api/auth/login", json={"email": user.email, "password": pw})
    assert res.status_code == 200

    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == user.email
    assert data["user"]["role"] == user.role

    # Security check: passwords and password hashes must NEVER be exposed
    assert "hashed_password" not in data["user"]
    assert "password" not in data["user"]

    # Observability check: W3C Server-Timing header must be emitted
    assert "Server-Timing" in res.headers
    timing_header = res.headers["Server-Timing"]
    assert "db_lookup;dur=" in timing_header
    assert "hash_verify;dur=" in timing_header
    assert "db_commit;dur=" in timing_header
    assert "token_gen;dur=" in timing_header
    assert "total;dur=" in timing_header


def test_login_with_normalized_email_and_username(setup_test_users):
    """Verify login handles case-insensitivity, whitespace trimming, and username fallback."""
    user = setup_test_users["active_user"]
    pw = setup_test_users["valid_password"]

    # 1. Mixed-case email with whitespace
    res_mixed = client.post("/api/auth/login", json={
        "email": f"  {user.email.upper()}  ",
        "password": pw
    })
    assert res_mixed.status_code == 200
    assert res_mixed.json()["user"]["email"] == user.email

    # 2. Login by username
    res_username = client.post("/api/auth/login", json={
        "email": user.username,
        "password": pw
    })
    assert res_username.status_code == 200
    assert res_username.json()["user"]["username"] == user.username


def test_login_invalid_password_rejected_and_audited(setup_test_users, user_db_session):
    """Verify incorrect password returns 400 and writes login_failure to auth_audit_logs."""
    user = setup_test_users["active_user"]

    res = client.post("/api/auth/login", json={
        "email": user.email,
        "password": "WrongPassword999!"
    })
    assert res.status_code == 400
    assert "incorrect" in res.json()["detail"].lower()

    # Verify audit failure entry in DB
    user_db_session.expire_all()
    failed_log = user_db_session.query(AuthAuditLog).filter(
        AuthAuditLog.user_id == user.id,
        AuthAuditLog.action == "login_failure"
    ).order_by(AuthAuditLog.id.desc()).first()
    assert failed_log is not None


def test_login_deactivated_account_rejected(setup_test_users):
    """Verify deactivated user receives 403 Forbidden and cannot acquire access token."""
    deact_user = setup_test_users["deact_user"]
    pw = setup_test_users["valid_password"]

    res = client.post("/api/auth/login", json={
        "email": deact_user.email,
        "password": pw
    })
    assert res.status_code == 403
    assert "deactivated" in res.json()["detail"].lower()


# =========================================================================
# 2. PERFORMANCE & CONCURRENCY BENCHMARK TESTS
# =========================================================================

def test_login_duration_performance_under_threshold(setup_test_users):
    """Verify warm backend login execution time is under 150ms locally."""
    user = setup_test_users["active_user"]
    pw = setup_test_users["valid_password"]

    # Warm run
    client.post("/api/auth/login", json={"email": user.email, "password": pw})

    # Measured run
    t0 = time.perf_counter()
    res = client.post("/api/auth/login", json={"email": user.email, "password": pw})
    dur_ms = (time.perf_counter() - t0) * 1000

    assert res.status_code == 200
    assert dur_ms < 150, f"Login took {dur_ms:.2f}ms, expected < 150ms"


def test_concurrent_logins_safe_under_wal(setup_test_users):
    """Verify 10 parallel login requests complete successfully without SQLite locking errors."""
    user = setup_test_users["active_user"]
    pw = setup_test_users["valid_password"]

    def perform_single_login():
        return client.post("/api/auth/login", json={"email": user.email, "password": pw})

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(perform_single_login) for _ in range(10)]
        results = [f.result() for f in futures]

    for r in results:
        assert r.status_code == 200
        assert "access_token" in r.json()


def test_login_token_validity_and_role_preservation(setup_test_users):
    """Verify access token returned by login can be used to query authenticated endpoints."""
    user = setup_test_users["active_user"]
    pw = setup_test_users["valid_password"]

    res_login = client.post("/api/auth/login", json={"email": user.email, "password": pw})
    assert res_login.status_code == 200
    token = res_login.json()["access_token"]

    # Query /auth/me with bearer token
    res_me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res_me.status_code == 200
    me_data = res_me.json()
    assert me_data["email"] == user.email
    assert me_data["role"] == user.role
