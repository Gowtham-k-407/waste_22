"use client";

import React, { useState, useEffect } from "react";
import { useAuth } from "@/lib/auth-context";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { api } from "@/lib/api";
import { 
  User, Mail, Building, MapPin, Award, Shield, 
  KeyRound, CheckCircle, AlertCircle, Sparkles, 
  FileCheck, Clock, Check, Eye, EyeOff, Camera
} from "lucide-react";

const ROLE_DISPLAY: Record<string, { label: string; color: string }> = {
  public: { label: "Public Visitor", color: "bg-slate-100 text-slate-700 border-slate-300" },
  contributor: { label: "Registered Contributor", color: "bg-teal-50 text-teal-700 border-teal-300" },
  municipal_officer: { label: "Municipal Officer (GCC)", color: "bg-blue-50 text-blue-700 border-blue-300" },
  plant_operator: { label: "Plant Operator", color: "bg-amber-50 text-amber-700 border-amber-300" },
  ai_admin: { label: "AI Administrator", color: "bg-purple-50 text-purple-700 border-purple-300" },
  system_admin: { label: "System Administrator", color: "bg-rose-50 text-rose-700 border-rose-300" },
};

export default function ProfilePage() {
  const { user, updateProfile, switchRole, restoreSession, logout } = useAuth();

  const handlePersonaSwitch = async (roleKey: string) => {
    try {
      if (roleKey === "system_admin") {
        try {
          await restoreSession();
        } catch {
          await switchRole(roleKey);
        }
      } else {
        await switchRole(roleKey);
      }
    } catch (e: any) {
      console.error("Persona switch failed:", e);
    }
  };

  // Profile form state
  const [fullName, setFullName] = useState("");

  const [organization, setOrganization] = useState("");
  const [city, setCity] = useState("Chennai");
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileSuccess, setProfileSuccess] = useState("");
  const [profileError, setProfileError] = useState("");

  // Password change state
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showCurrentPw, setShowCurrentPw] = useState(false);
  const [showNewPw, setShowNewPw] = useState(false);
  const [pwSaving, setPwSaving] = useState(false);
  const [pwSuccess, setPwSuccess] = useState("");
  const [pwError, setPwError] = useState("");

  // Contributor stats
  const [stats, setStats] = useState<any>(null);
  const [statsLoading, setStatsLoading] = useState(true);

  // Initialize fields when user is loaded
  useEffect(() => {
    if (user) {
      setFullName(user.full_name || "");
      setOrganization(user.organization || "");
      setCity(user.city || "Chennai");
    }
  }, [user]);

  // Fetch contributor stats
  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await api.getProfileStats();
        setStats(data);
      } catch (err) {
        console.error("Failed to fetch user stats:", err);
      } finally {
        setStatsLoading(false);
      }
    };

    if (user) {
      fetchStats();
    }
  }, [user]);

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setProfileError("");
    setProfileSuccess("");

    if (!fullName.trim()) {
      setProfileError("Full Name cannot be blank.");
      return;
    }

    setProfileSaving(true);
    try {
      await updateProfile({
        full_name: fullName.trim(),
        organization: organization.trim(),
        city: city.trim(),
      });
      setProfileSuccess("Your profile details have been saved successfully!");
      setTimeout(() => setProfileSuccess(""), 4000);
    } catch (err: any) {
      setProfileError(err.message || "Failed to update profile.");
    } finally {
      setProfileSaving(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPwError("");
    setPwSuccess("");

    if (!currentPassword || !newPassword) {
      setPwError("Please enter your current and new password.");
      return;
    }

    if (newPassword.length < 6) {
      setPwError("New password must be at least 6 characters long.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setPwError("New passwords do not match.");
      return;
    }

    setPwSaving(true);
    try {
      await api.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      setPwSuccess("Your password was updated successfully.");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setTimeout(() => setPwSuccess(""), 4000);
    } catch (err: any) {
      setPwError(err.message || "Failed to update password. Verify your current password.");
    } finally {
      setPwSaving(false);
    }
  };

  return (
    <ProtectedRoute>
      <div className="space-y-8 max-w-6xl mx-auto">
        {/* Profile Header Banner */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="h-32 bg-gradient-to-r from-navy-900 via-navy-800 to-teal-800 relative">
            <div className="absolute top-4 right-4 flex items-center space-x-2">
              <span className={`px-3 py-1 rounded-full text-xs font-semibold border ${ROLE_DISPLAY[user?.role || 'public']?.color || 'bg-slate-100 text-slate-800'}`}>
                {ROLE_DISPLAY[user?.role || 'public']?.label || user?.role}
              </span>
            </div>
          </div>

          <div className="px-6 pb-6 pt-0 sm:flex sm:items-end sm:justify-between relative">
            <div className="sm:flex sm:items-center sm:space-x-5 -mt-14">
              <div className="w-24 h-24 rounded-2xl bg-teal-600 text-white flex items-center justify-center text-3xl font-extrabold border-4 border-white shadow-md">
                {user?.full_name ? user.full_name.charAt(0).toUpperCase() : "U"}
              </div>
              <div className="mt-4 sm:mt-14">
                <h1 className="text-2xl font-bold text-slate-900">{user?.full_name}</h1>
                <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500 mt-1">
                  <span className="flex items-center">
                    <Mail className="w-3.5 h-3.5 mr-1 text-slate-400" />
                    {user?.email}
                  </span>
                  <span>•</span>
                  <span className="flex items-center">
                    <Building className="w-3.5 h-3.5 mr-1 text-slate-400" />
                    {user?.organization || "Citizen Contributor"}
                  </span>
                  <span>•</span>
                  <span className="flex items-center">
                    <MapPin className="w-3.5 h-3.5 mr-1 text-slate-400" />
                    {user?.city || "Chennai"}
                  </span>
                </div>
              </div>
            </div>

            <div className="mt-5 sm:mt-0 flex items-center space-x-3">
              <div className="bg-teal-50 border border-teal-200 px-4 py-2 rounded-xl text-center">
                <div className="text-xs text-teal-700 font-medium">Eco Points</div>
                <div className="text-xl font-extrabold text-teal-800 flex items-center justify-center">
                  <Sparkles className="w-4 h-4 text-amber-500 mr-1" />
                  {user?.contribution_points || stats?.eco_points || 50}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Contributor Impact Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Uploads</span>
              <Camera className="w-4 h-4 text-teal-600" />
            </div>
            <div className="text-2xl font-bold text-slate-900 mt-2">
              {statsLoading ? "..." : stats?.total_contributions || 0}
            </div>
            <span className="text-[11px] text-slate-500">Waste photos submitted</span>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Model Validated</span>
              <CheckCircle className="w-4 h-4 text-emerald-600" />
            </div>
            <div className="text-2xl font-bold text-slate-900 mt-2">
              {statsLoading ? "..." : stats?.validated_contributions || 0}
            </div>
            <span className="text-[11px] text-emerald-600 font-medium">Staged in training dataset</span>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">AI Corrections</span>
              <FileCheck className="w-4 h-4 text-amber-600" />
            </div>
            <div className="text-2xl font-bold text-slate-900 mt-2">
              {statsLoading ? "..." : stats?.user_corrections || 0}
            </div>
            <span className="text-[11px] text-slate-500">Human verified labels</span>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Badges Earned</span>
              <Award className="w-4 h-4 text-purple-600" />
            </div>
            <div className="text-2xl font-bold text-slate-900 mt-2">
              {stats?.badges ? stats.badges.length : 2}
            </div>
            <span className="text-[11px] text-purple-600 font-medium">Civic recognition</span>
          </div>
        </div>

        {/* Badges List */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
          <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-3 flex items-center">
            <Award className="w-4 h-4 text-amber-500 mr-2" />
            Municipal Badges & Recognition
          </h3>
          <div className="flex flex-wrap gap-2">
            {(stats?.badges || ["Eco Citizen", "Early Adopter", "Civic Waste Champion"]).map((badge: string, i: number) => (
              <span
                key={i}
                className="inline-flex items-center px-3 py-1.5 rounded-xl text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-200"
              >
                <Sparkles className="w-3.5 h-3.5 text-amber-500 mr-1.5" />
                {badge}
              </span>
            ))}
          </div>
        </div>

        {/* Edit Details & Change Password Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {/* Edit Profile Information */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-bold text-slate-900 flex items-center">
                <User className="w-5 h-5 text-teal-600 mr-2" />
                Edit Profile Details
              </h3>
            </div>

            {profileSuccess && (
              <div className="mb-4 bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs rounded-xl p-3 flex items-center space-x-2">
                <Check className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                <span>{profileSuccess}</span>
              </div>
            )}

            {profileError && (
              <div className="mb-4 bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl p-3 flex items-center space-x-2">
                <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
                <span>{profileError}</span>
              </div>
            )}

            <form onSubmit={handleUpdateProfile} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  Full Name
                </label>
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:outline-none focus:ring-2 focus:ring-teal-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  Email Address
                </label>
                <input
                  type="email"
                  disabled
                  value={user?.email || ""}
                  className="w-full px-3 py-2 bg-slate-100 border border-slate-200 rounded-xl text-sm text-slate-500 cursor-not-allowed"
                />
                <span className="text-[11px] text-slate-400 mt-1 block">
                  Municipal ID login email cannot be changed.
                </span>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  Organization / Department
                </label>
                <input
                  type="text"
                  value={organization}
                  onChange={(e) => setOrganization(e.target.value)}
                  placeholder="e.g. GCC Solid Waste Management / Volunteer"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:outline-none focus:ring-2 focus:ring-teal-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  City
                </label>
                <input
                  type="text"
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:outline-none focus:ring-2 focus:ring-teal-500"
                />
              </div>

              <button
                type="submit"
                disabled={profileSaving}
                className="w-full py-2.5 px-4 bg-teal-600 hover:bg-teal-700 text-white rounded-xl text-sm font-semibold transition-all disabled:opacity-60 shadow-sm"
              >
                {profileSaving ? "Saving..." : "Save Profile Details"}
              </button>
            </form>
          </div>

          {/* Change Password */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-bold text-slate-900 flex items-center">
                <KeyRound className="w-5 h-5 text-teal-600 mr-2" />
                Change Password
              </h3>
            </div>

            {pwSuccess && (
              <div className="mb-4 bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs rounded-xl p-3 flex items-center space-x-2">
                <Check className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                <span>{pwSuccess}</span>
              </div>
            )}

            {pwError && (
              <div className="mb-4 bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl p-3 flex items-center space-x-2">
                <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
                <span>{pwError}</span>
              </div>
            )}

            <form onSubmit={handleChangePassword} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  Current Password
                </label>
                <div className="relative">
                  <input
                    type={showCurrentPw ? "text" : "password"}
                    required
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    placeholder="Enter current password"
                    className="w-full px-3 py-2 pr-10 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:outline-none focus:ring-2 focus:ring-teal-500"
                  />
                  <button
                    type="button"
                    onClick={() => setShowCurrentPw(!showCurrentPw)}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-600"
                  >
                    {showCurrentPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  New Password
                </label>
                <div className="relative">
                  <input
                    type={showNewPw ? "text" : "password"}
                    required
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="At least 6 characters"
                    className="w-full px-3 py-2 pr-10 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:outline-none focus:ring-2 focus:ring-teal-500"
                  />
                  <button
                    type="button"
                    onClick={() => setShowNewPw(!showNewPw)}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-600"
                  >
                    {showNewPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  Confirm New Password
                </label>
                <input
                  type={showNewPw ? "text" : "password"}
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Re-enter new password"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:outline-none focus:ring-2 focus:ring-teal-500"
                />
              </div>

              <button
                type="submit"
                disabled={pwSaving}
                className="w-full py-2.5 px-4 bg-navy-900 hover:bg-navy-800 text-white rounded-xl text-sm font-semibold transition-all disabled:opacity-60 shadow-sm"
              >
                {pwSaving ? "Updating Password..." : "Update Password"}
              </button>
            </form>
          </div>
        </div>

        {/* Demo Persona Role Switcher */}
        <div className="bg-slate-50 border border-slate-200 rounded-2xl p-6">
          <div className="flex items-center space-x-3 mb-3">
            <Shield className="w-5 h-5 text-teal-600" />
            <h3 className="text-base font-bold text-slate-900">Switch Municipal Persona</h3>
          </div>
          <p className="text-xs text-slate-600 mb-4 max-w-2xl leading-relaxed">
            For evaluation, you can switch your active persona to explore how different municipal dashboards, models, and restriction policies adapt in real time.
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2">
            {Object.entries(ROLE_DISPLAY).map(([roleKey, { label }]) => (
              <button
                key={roleKey}
                onClick={() => handlePersonaSwitch(roleKey)}
                className={`p-3 rounded-xl border text-xs font-semibold text-center transition-all ${
                  user?.role === roleKey
                    ? "bg-teal-600 text-white border-teal-600 shadow-sm"
                    : "bg-white text-slate-700 border-slate-200 hover:border-teal-400 hover:bg-teal-50"
                }`}
              >
                <div className="truncate">{label}</div>
                {user?.role === roleKey && <div className="text-[10px] mt-1 text-teal-100 font-normal">Active</div>}
              </button>
            ))}
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}