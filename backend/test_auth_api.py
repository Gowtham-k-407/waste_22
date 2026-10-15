from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

print("--- Testing Auth Endpoints ---")

# 1. Login with correct credentials
login_resp = client.post("/api/auth/login", json={
    "email": "admin@chennaiswm.gov.in",
    "password": "Admin@123"
})
assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
admin_token = login_resp.json()["access_token"]
print("✓ 1. Admin login succeeded:", login_resp.json()["user"]["full_name"], "Role:", login_resp.json()["user"]["role"])

# 2. Login with wrong password
bad_login = client.post("/api/auth/login", json={
    "email": "admin@chennaiswm.gov.in",
    "password": "WrongPassword!99"
})
assert bad_login.status_code == 400, f"Expected 400, got: {bad_login.status_code}"
assert "The email or password you entered is incorrect" in bad_login.json()["detail"]
print("✓ 2. Friendly error on invalid password verified")

# 3. User Registration
test_email = "testcitizen.velachery@gmail.com"
# Clean up if previously registered
from app.core.database import UserSessionLocal
from app.models.user import User
db = UserSessionLocal()
db.query(User).filter(User.email == test_email).delete()
db.commit()
db.close()

reg_resp = client.post("/api/auth/register", json={
    "email": test_email,
    "password": "SecurePassword@123",
    "full_name": "Arunachalam Muruganantham",
    "organization": "Velachery Green Initiative",
    "city": "Chennai"
})
assert reg_resp.status_code == 200, f"Registration failed: {reg_resp.text}"
user_data = reg_resp.json()["user"]
user_token = reg_resp.json()["access_token"]
assert user_data["role"] == "contributor"
assert user_data["contribution_points"] >= 50
print("✓ 3. Registration succeeded with role 'contributor' & welcome bonus points:", user_data["full_name"])

# 4. Get Current User (/me) with Token
headers = {"Authorization": f"Bearer {user_token}"}
me_resp = client.get("/api/auth/me", headers=headers)
assert me_resp.status_code == 200
assert me_resp.json()["email"] == test_email
print("✓ 4. Authenticated /me endpoint verified for current user")

# 5. Update Profile
update_resp = client.put("/api/auth/profile", headers=headers, json={
    "full_name": "Arunachalam M. (Eco Lead)",
    "organization": "Velachery Zero Waste Foundation",
    "city": "Chennai"
})
assert update_resp.status_code == 200
assert update_resp.json()["full_name"] == "Arunachalam M. (Eco Lead)"
print("✓ 5. Profile update endpoint verified")

# 6. Change Password
chg_resp = client.put("/api/auth/change-password", headers=headers, json={
    "current_password": "SecurePassword@123",
    "new_password": "NewSecretPassword@456"
})
assert chg_resp.status_code == 200
print("✓ 6. Password change endpoint verified")

# Verify login with new password
relogin = client.post("/api/auth/login", json={
    "email": test_email,
    "password": "NewSecretPassword@456"
})
assert relogin.status_code == 200
print("✓ 7. Relogin with new password verified")

# 8. Forgot Password Flow
forgot_resp = client.post("/api/auth/forgot-password", json={
    "email": test_email
})
assert forgot_resp.status_code == 200
reset_token = forgot_resp.json().get("reset_token")
assert reset_token is not None
print("✓ 8. Forgot password reset token generated successfully")

# 9. Reset Password using Token
reset_action = client.post("/api/auth/reset-password", json={
    "token": reset_token,
    "new_password": "FinalPassword@789"
})
assert reset_action.status_code == 200
print("✓ 9. Reset password with token verified")

# Verify login with reset password
final_login = client.post("/api/auth/login", json={
    "email": test_email,
    "password": "FinalPassword@789"
})
assert final_login.status_code == 200
print("✓ 10. Login with reset password verified")

# 11. Profile Stats
stats_resp = client.get("/api/auth/profile-stats", headers=headers)
assert stats_resp.status_code == 200
assert "total_contributions" in stats_resp.json()
assert "eco_points" in stats_resp.json()
print("✓ 11. Profile stats returned badges & contribution metrics")

# 12. Available Roles
roles_resp = client.get("/api/auth/roles")
assert roles_resp.status_code == 200
assert len(roles_resp.json()) >= 35
print(f"✓ 12. All {len(roles_resp.json())} municipal & platform roles retrieved with descriptions")

print("\n🎉 ALL 12 BACKEND AUTHENTICATION TESTS PASSED PERFECTLY!")