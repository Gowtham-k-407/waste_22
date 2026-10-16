"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  Users,
  Search,
  Filter,
  Shield,
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RefreshCw,
  UserCheck,
  Edit2,
  Eye,
  ChevronLeft,
  ChevronRight,
  Clock,
  Building,
  Mail,
  User as UserIcon,
  Phone,
  Calendar,
  Award,
  Sparkles,
  Lock,
  ArrowRight,
  UserPlus,
  KeyRound,
  UserCog,
  Copy,
  Check,
  ExternalLink,
  MapPin
} from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { AdminNav } from "@/components/AdminNav";

interface UserAdminItem {
  id: number;
  username: string;
  email: string;
  full_name: string;
  role: string;
  organization?: string;
  city?: string;
  phone_number?: string;
  is_active: boolean;
  email_verified: boolean;
  must_change_password?: boolean;
  contribution_points: number;
  badges: string;
  created_at: string;
  updated_at?: string;
  last_login_at?: string;
  assigned_ward?: number;
  staff_profile?: {
    employee_id?: string;
    job_title?: string;
    role_code?: string;
    department?: string;
    employment_status?: string;
    assigned_zone_number?: number;
    assigned_ward_number?: number;
    assigned_facility_name?: string;
    shift?: string;
  };
}

interface RoleDefinition {
  role: string;
  title: string;
  department: string;
  scope?: string;
  description?: string;
  is_staff: boolean;
  is_admin: boolean;
}

const ROLE_BADGE_STYLES: Record<string, string> = {
  system_admin: "bg-rose-100 text-rose-800 border-rose-300",
  ai_admin: "bg-purple-100 text-purple-800 border-purple-300",
  municipal_officer: "bg-blue-100 text-blue-800 border-blue-300",
  municipal_commissioner: "bg-indigo-100 text-indigo-800 border-indigo-300",
  solid_waste_management_officer: "bg-blue-100 text-blue-800 border-blue-300",
  waste_processing_plant_operator: "bg-amber-100 text-amber-800 border-amber-300",
  plant_operator: "bg-amber-100 text-amber-800 border-amber-300",
  contributor: "bg-teal-100 text-teal-800 border-teal-300",
  public: "bg-slate-100 text-slate-700 border-slate-300",
};

export default function AdminUsersPage() {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState<UserAdminItem[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [currentPage, setCurrentPage] = useState(1);
  const [limit] = useState(15);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [roleFilter, setRoleFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [rolesCatalog, setRolesCatalog] = useState<RoleDefinition[]>([]);

  // Feedback notifications
  const [notification, setNotification] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Detail Modal
  const [selectedUser, setSelectedUser] = useState<UserAdminItem | null>(null);

  // Role Change Modal
  const [roleModalUser, setRoleModalUser] = useState<UserAdminItem | null>(null);
  const [targetRole, setTargetRole] = useState("");
  const [changeReason, setChangeReason] = useState("");
  const [confirmSafetyChecked, setConfirmSafetyChecked] = useState(false);
  const [isUpdatingRole, setIsUpdatingRole] = useState(false);

  // Add User Modal State
  const [addUserModalOpen, setAddUserModalOpen] = useState(false);
  const [newUserData, setNewUserData] = useState({
    full_name: "",
    email: "",
    username: "",
    role: "contributor",
    organization: "",
    city: "Chennai",
    phone_number: "",
    assigned_ward: "",
    is_active: true,
    employee_id: "",
    department: "",
    job_title: ""
  });
  const [isCreatingUser, setIsCreatingUser] = useState(false);

  // Edit User Details Modal State
  const [editModalUser, setEditModalUser] = useState<UserAdminItem | null>(null);
  const [editFormData, setEditFormData] = useState({
    full_name: "",
    organization: "",
    city: "Chennai",
    phone_number: "",
    assigned_ward: "",
    is_active: true
  });
  const [isUpdatingDetails, setIsUpdatingDetails] = useState(false);

  // Password Reset Modal State
  const [resetModalUser, setResetModalUser] = useState<UserAdminItem | null>(null);
  const [isResettingPassword, setIsResettingPassword] = useState(false);

  // Token Link Modal (Activation or Reset Link Presentation)
  const [tokenResultModal, setTokenResultModal] = useState<{
    title: string;
    subtitle: string;
    targetEmail: string;
    token: string;
    url: string;
    emailDeliveryStatus: string;
  } | null>(null);
  const [copiedLink, setCopiedLink] = useState(false);

  const isSystemAdmin = currentUser?.role === "system_admin";

  const fetchRoles = useCallback(async () => {
    try {
      const data = await api.getAdminRoles();
      setRolesCatalog(data);
    } catch (err) {
      console.error("Failed to load roles catalog:", err);
    }
  }, []);

  const fetchUsers = useCallback(async (page: number = 1) => {
    setLoading(true);
    try {
      const data = await api.getAdminUsers({
        q: searchQuery,
        role: roleFilter,
        status: statusFilter,
        page,
        limit,
      });
      setUsers(data.items || []);
      setTotalCount(data.total || 0);
      setTotalPages(data.total_pages || 1);
      setCurrentPage(data.page || 1);
    } catch (err: any) {
      console.error("Failed to load users:", err);
      setNotification({
        type: "error",
        message: err.message || "Failed to load user directory. Administrative access required.",
      });
    } finally {
      setLoading(false);
    }
  }, [searchQuery, roleFilter, statusFilter, limit]);

  useEffect(() => {
    fetchRoles();
  }, [fetchRoles]);

  useEffect(() => {
    fetchUsers(1);
  }, [fetchUsers]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchUsers(1);
  };

  // Role Modal Handlers
  const handleOpenRoleModal = (u: UserAdminItem) => {
    setRoleModalUser(u);
    setTargetRole(u.role);
    setChangeReason("");
    setConfirmSafetyChecked(false);
  };

  const handleSaveRoleChange = async () => {
    if (!roleModalUser || !targetRole) return;
    if (targetRole === roleModalUser.role) {
      setRoleModalUser(null);
      return;
    }

    setIsUpdatingRole(true);
    setNotification(null);

    try {
      const res = await api.updateUserRole(roleModalUser.id, {
        role: targetRole,
        reason: changeReason || "Admin Directory Update",
      });

      setNotification({
        type: "success",
        message: res.message || `Successfully assigned role '${targetRole}' to ${roleModalUser.full_name}.`,
      });
      setRoleModalUser(null);
      fetchUsers(currentPage);
    } catch (err: any) {
      console.error("Failed to update role:", err);
      setNotification({
        type: "error",
        message: err.message || "Role change failed. Check administrator authorization or safety restrictions.",
      });
    } finally {
      setIsUpdatingRole(false);
    }
  };

  // Add User Handlers
  const handleOpenAddUser = () => {
    setNewUserData({
      full_name: "",
      email: "",
      username: "",
      role: "contributor",
      organization: "",
      city: "Chennai",
      phone_number: "",
      assigned_ward: "",
      is_active: true,
      employee_id: "",
      department: "",
      job_title: ""
    });
    setAddUserModalOpen(true);
  };

  const handleCreateUserSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newUserData.full_name.trim() || !newUserData.email.trim()) {
      setNotification({ type: "error", message: "Full Name and Email are required." });
      return;
    }

    setIsCreatingUser(true);
    setNotification(null);

    try {
      const payload: any = {
        full_name: newUserData.full_name.trim(),
        email: newUserData.email.trim(),
        role: newUserData.role,
        organization: newUserData.organization.trim() || undefined,
        city: newUserData.city.trim() || "Chennai",
        phone_number: newUserData.phone_number.trim() || undefined,
        is_active: newUserData.is_active,
      };

      if (newUserData.username.trim()) {
        payload.username = newUserData.username.trim();
      }
      if (newUserData.assigned_ward.trim()) {
        payload.assigned_ward = parseInt(newUserData.assigned_ward.trim(), 10);
      }
      if (newUserData.employee_id.trim()) {
        payload.employee_id = newUserData.employee_id.trim();
      }
      if (newUserData.department.trim()) {
        payload.department = newUserData.department.trim();
      }
      if (newUserData.job_title.trim()) {
        payload.job_title = newUserData.job_title.trim();
      }

      const res = await api.createAdminUser(payload);
      setAddUserModalOpen(false);

      if (res.activation_token) {
        setTokenResultModal({
          title: "User Account Created",
          subtitle: `Account for ${res.user.full_name} has been provisioned. A secure, single-use activation invitation has been generated.`,
          targetEmail: res.user.email,
          token: res.activation_token,
          url: `${window.location.origin}${res.activation_url}`,
          emailDeliveryStatus: res.email_delivery_status || "not_configured"
        });
      } else {
        setNotification({
          type: "success",
          message: `User '${res.user.username}' created successfully.`,
        });
      }

      fetchUsers(1);
    } catch (err: any) {
      console.error("Create user failed:", err);
      setNotification({
        type: "error",
        message: err.message || "Failed to create user. Verify email uniqueness and authorized role.",
      });
    } finally {
      setIsCreatingUser(false);
    }
  };

  // Edit User Details Handlers
  const handleOpenEditModal = (u: UserAdminItem) => {
    setEditModalUser(u);
    setEditFormData({
      full_name: u.full_name || "",
      organization: u.organization || "",
      city: u.city || "Chennai",
      phone_number: u.phone_number || "",
      assigned_ward: u.assigned_ward ? u.assigned_ward.toString() : "",
      is_active: u.is_active
    });
  };

  const handleSaveUserDetails = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editModalUser) return;

    setIsUpdatingDetails(true);
    setNotification(null);

    try {
      const payload: any = {
        full_name: editFormData.full_name.trim(),
        organization: editFormData.organization.trim(),
        city: editFormData.city.trim(),
        phone_number: editFormData.phone_number.trim(),
        is_active: editFormData.is_active
      };

      if (editFormData.assigned_ward.trim()) {
        payload.assigned_ward = parseInt(editFormData.assigned_ward.trim(), 10);
      }

      const res = await api.updateAdminUser(editModalUser.id, payload);

      setNotification({
        type: "success",
        message: `Successfully updated details for ${res.full_name}.`,
      });
      setEditModalUser(null);
      if (selectedUser?.id === editModalUser.id) {
        setSelectedUser(res);
      }
      fetchUsers(currentPage);
    } catch (err: any) {
      console.error("Failed to update user details:", err);
      setNotification({
        type: "error",
        message: err.message || "Failed to update user details. Ensure safety restrictions are met.",
      });
    } finally {
      setIsUpdatingDetails(false);
    }
  };

  // Password Reset Handlers
  const handleOpenResetModal = (u: UserAdminItem) => {
    setResetModalUser(u);
  };

  const handleConfirmPasswordReset = async () => {
    if (!resetModalUser) return;

    setIsResettingPassword(true);
    setNotification(null);

    try {
      const res = await api.resetUserPasswordByAdmin(resetModalUser.id);
      setResetModalUser(null);

      setTokenResultModal({
        title: "Password Reset Initiated",
        subtitle: `A single-use password reset token has been issued for ${resetModalUser.full_name}.`,
        targetEmail: res.email,
        token: res.reset_token,
        url: `${window.location.origin}${res.reset_url}`,
        emailDeliveryStatus: res.email_delivery_status || "not_configured"
      });
    } catch (err: any) {
      console.error("Password reset failed:", err);
      setNotification({
        type: "error",
        message: err.message || "Failed to initiate password reset. Administrative authorization required.",
      });
    } finally {
      setIsResettingPassword(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2500);
  };

  const isMunicipalStaffRole = (role: string) => {
    return role.startsWith("staff_") || [
      "waste_processing_plant_operator",
      "sanitary_officer",
      "municipal_commissioner",
      "environmental_engineer",
      "assistant_engineer"
    ].includes(role);
  };

  return (
    <div className="space-y-6">
      {/* Top Admin Sub-Navigation */}
      <AdminNav />

      {/* Page Title & System Description */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-rose-50 text-rose-700 rounded-xl border border-rose-200">
              <Users className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-xl font-black text-navy-950 tracking-tight">
                User Directory & Access Management
              </h1>
              <p className="text-xs text-slate-500 mt-0.5">
                Authorized Municipal Administrative Directory with Role-Based Access Control (RBAC) & Audit Integrity
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2.5 flex-wrap">
          <div className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-700 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-teal-600" />
            <span>Total Accounts:</span>
            <strong className="text-navy-950 font-bold">{totalCount}</strong>
          </div>

          <button
            onClick={() => fetchUsers(currentPage)}
            className="flex items-center gap-1.5 px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-semibold transition"
            title="Refresh Directory"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>

          {isSystemAdmin ? (
            <button
              onClick={handleOpenAddUser}
              className="flex items-center gap-1.5 px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-xs font-bold transition shadow-sm"
              title="Add New User Account"
            >
              <UserPlus className="w-4 h-4" />
              <span>Add User</span>
            </button>
          ) : (
            <button
              disabled
              className="flex items-center gap-1.5 px-3 py-2 bg-slate-100 text-slate-400 rounded-xl text-xs font-semibold cursor-not-allowed opacity-60"
              title="Only System Administrators can provision accounts"
            >
              <UserPlus className="w-4 h-4" />
              <span>Add User</span>
            </button>
          )}
        </div>
      </div>

      {/* Notification Banner */}
      {notification && (
        <div
          className={`p-4 rounded-xl text-xs font-semibold flex items-center justify-between shadow-sm animate-in fade-in duration-200 ${
            notification.type === "success"
              ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
              : "bg-rose-50 text-rose-800 border border-rose-200"
          }`}
        >
          <div className="flex items-center gap-2">
            {notification.type === "success" ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
            ) : (
              <AlertTriangle className="w-4 h-4 text-rose-600 flex-shrink-0" />
            )}
            <span>{notification.message}</span>
          </div>
          <button
            onClick={() => setNotification(null)}
            className="text-slate-400 hover:text-slate-700 transition"
          >
            &times;
          </button>
        </div>
      )}

      {/* Directory Filter & Search Bar */}
      <div className="bg-white rounded-2xl p-4 border border-slate-200 shadow-sm space-y-3">
        <form onSubmit={handleSearchSubmit} className="grid grid-cols-1 md:grid-cols-12 gap-3">
          {/* Search Input */}
          <div className="md:col-span-5 relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search by name, email, or username..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500 transition"
            />
          </div>

          {/* Role Filter */}
          <div className="md:col-span-3">
            <select
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value)}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500 transition"
            >
              <option value="all">All Assigned Roles</option>
              <option value="system_admin">System Administrator</option>
              <option value="ai_admin">AI Administrator</option>
              <option value="municipal_officer">Municipal Officer</option>
              <option value="waste_processing_plant_operator">Plant Operator</option>
              <option value="contributor">Citizen Contributor</option>
              <option value="public">Public Citizen</option>
              {rolesCatalog
                .filter((r) => !["system_admin", "ai_admin", "municipal_officer", "contributor", "public"].includes(r.role))
                .map((r) => (
                  <option key={r.role} value={r.role}>
                    {r.title}
                  </option>
                ))}
            </select>
          </div>

          {/* Status Filter */}
          <div className="md:col-span-2">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500 transition"
            >
              <option value="all">All Statuses</option>
              <option value="active">Active Only</option>
              <option value="inactive">Inactive Only</option>
            </select>
          </div>

          {/* Action Buttons */}
          <div className="md:col-span-2 flex items-center gap-2">
            <button
              type="submit"
              className="w-full py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-xl text-xs font-bold transition shadow-sm"
            >
              Search
            </button>
            <button
              type="button"
              onClick={() => {
                setSearchQuery("");
                setRoleFilter("all");
                setStatusFilter("all");
              }}
              className="px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-bold transition"
              title="Reset Filters"
            >
              Reset
            </button>
          </div>
        </form>
      </div>

      {/* Directory Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-12 text-center space-y-3">
            <RefreshCw className="w-6 h-6 text-teal-600 animate-spin mx-auto" />
            <p className="text-xs font-medium text-slate-500">Loading authorized directory records...</p>
          </div>
        ) : users.length === 0 ? (
          <div className="p-12 text-center space-y-2">
            <Users className="w-8 h-8 text-slate-300 mx-auto" />
            <h3 className="text-sm font-bold text-slate-800">No users found</h3>
            <p className="text-xs text-slate-500">
              No registered user accounts match the current search query and filters.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-500 font-bold uppercase tracking-wider text-[10px]">
                  <th className="py-3.5 px-4">User Identity</th>
                  <th className="py-3.5 px-4">Assigned Role</th>
                  <th className="py-3.5 px-4">Organization / Scope</th>
                  <th className="py-3.5 px-4">Status</th>
                  <th className="py-3.5 px-4">Created Date</th>
                  <th className="py-3.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {users.map((u) => {
                  const roleStyle = ROLE_BADGE_STYLES[u.role] || "bg-slate-100 text-slate-800 border-slate-200";
                  const isSelf = currentUser?.email === u.email;

                  return (
                    <tr key={u.id} className="hover:bg-slate-50/60 transition-colors group">
                      {/* Identity */}
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-navy-900 text-white font-bold flex items-center justify-center text-xs flex-shrink-0">
                            {u.full_name ? u.full_name.charAt(0).toUpperCase() : "U"}
                          </div>
                          <div>
                            <div className="font-bold text-navy-950 flex items-center gap-1.5">
                              <span>{u.full_name}</span>
                              {isSelf && (
                                <span className="text-[9px] px-1.5 py-0.2 bg-teal-100 text-teal-800 rounded font-bold">
                                  You
                                </span>
                              )}
                            </div>
                            <div className="text-[11px] text-slate-500 font-mono">{u.email}</div>
                          </div>
                        </div>
                      </td>

                      {/* Assigned Role */}
                      <td className="py-3 px-4">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-semibold border ${roleStyle}`}
                        >
                          {u.role.replace(/_/g, " ")}
                        </span>
                        {u.staff_profile && (
                          <div className="text-[10px] text-slate-500 mt-0.5">
                            ID: {u.staff_profile.employee_id} • {u.staff_profile.job_title}
                          </div>
                        )}
                      </td>

                      {/* Organization / Scope */}
                      <td className="py-3 px-4">
                        <div className="text-slate-800 font-medium truncate max-w-[180px]">
                          {u.organization || "Public Citizen"}
                        </div>
                        <div className="text-[10px] text-slate-400">
                          {u.city || "Chennai"} {u.assigned_ward ? `• Ward ${u.assigned_ward}` : ""}
                        </div>
                      </td>

                      {/* Status */}
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-1.5">
                          {u.is_active ? (
                            <span className="inline-flex items-center gap-1 text-emerald-700 text-[11px] font-semibold">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                              Active
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-slate-400 text-[11px] font-semibold">
                              <span className="w-1.5 h-1.5 rounded-full bg-slate-300" />
                              Inactive
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Created Date */}
                      <td className="py-3 px-4 text-slate-500 text-[11px]">
                        {u.created_at ? new Date(u.created_at).toLocaleDateString() : "—"}
                      </td>

                      {/* Actions */}
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {/* View Details */}
                          <button
                            onClick={() => setSelectedUser(u)}
                            className="p-1.5 text-slate-500 hover:text-navy-950 hover:bg-slate-100 rounded-lg transition"
                            title="View Administrative Profile"
                          >
                            <Eye className="w-3.5 h-3.5" />
                          </button>

                          {/* Edit Details */}
                          {isSystemAdmin && (
                            <button
                              onClick={() => handleOpenEditModal(u)}
                              className="p-1.5 text-slate-500 hover:text-teal-700 hover:bg-teal-50 rounded-lg transition"
                              title="Edit Permitted Details"
                            >
                              <UserCog className="w-3.5 h-3.5 text-teal-600" />
                            </button>
                          )}

                          {/* Change Role */}
                          {isSystemAdmin ? (
                            <button
                              onClick={() => handleOpenRoleModal(u)}
                              disabled={isSelf}
                              className={`flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-semibold border transition ${
                                isSelf
                                  ? "opacity-40 cursor-not-allowed bg-slate-50 text-slate-400 border-slate-200"
                                  : "bg-white hover:bg-rose-50 text-slate-700 hover:text-rose-700 border-slate-200 hover:border-rose-200 shadow-sm"
                              }`}
                              title={isSelf ? "Self-role modification disabled for safety" : "Change User Role"}
                            >
                              <ShieldAlert className="w-3 h-3 text-rose-600" />
                              <span>Role</span>
                            </button>
                          ) : (
                            <span
                              className="text-[10px] text-slate-400 px-2 py-0.5 bg-slate-50 rounded border border-slate-100"
                              title="Role changes restricted to System Administrators"
                            >
                              View Only
                            </span>
                          )}

                          {/* Reset Password */}
                          {isSystemAdmin && (
                            <button
                              onClick={() => handleOpenResetModal(u)}
                              className="flex items-center gap-1 px-2 py-1 bg-white hover:bg-amber-50 text-slate-700 hover:text-amber-800 rounded-lg text-xs font-semibold border border-slate-200 hover:border-amber-200 shadow-sm transition"
                              title="Initiate Secure Password Reset"
                            >
                              <KeyRound className="w-3 h-3 text-amber-600" />
                              <span>Reset</span>
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Footer */}
        <div className="px-4 py-3 bg-slate-50/70 border-t border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-500">
          <div>
            Showing <strong className="text-slate-800">{users.length}</strong> of{" "}
            <strong className="text-slate-800">{totalCount}</strong> users (Page {currentPage} of{" "}
            {totalPages})
          </div>

          <div className="flex items-center gap-1.5">
            <button
              onClick={() => fetchUsers(currentPage - 1)}
              disabled={currentPage <= 1 || loading}
              className="p-1.5 rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition"
              title="Previous Page"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="px-2 text-xs font-semibold text-slate-700">
              {currentPage} / {totalPages}
            </span>
            <button
              onClick={() => fetchUsers(currentPage + 1)}
              disabled={currentPage >= totalPages || loading}
              className="p-1.5 rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition"
              title="Next Page"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* ============================================================== */}
      {/* 1. ADD USER MODAL */}
      {/* ============================================================== */}
      {addUserModalOpen && (
        <div className="fixed inset-0 bg-slate-950/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-xl w-full p-6 shadow-2xl border border-slate-200 space-y-4 max-h-[90vh] overflow-y-auto animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="p-2 bg-rose-50 text-rose-700 rounded-xl border border-rose-200">
                  <UserPlus className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-navy-950">Add User Account</h3>
                  <p className="text-xs text-slate-400">
                    Register a new citizen, plant operator, or municipal staff account
                  </p>
                </div>
              </div>
              <button
                onClick={() => setAddUserModalOpen(false)}
                className="text-slate-400 hover:text-slate-700 text-lg transition"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleCreateUserSubmit} className="space-y-4 text-xs">
              {/* Core Identity */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="font-bold text-slate-700">Full Name *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Ramesh Kumar"
                    value={newUserData.full_name}
                    onChange={(e) => setNewUserData({ ...newUserData, full_name: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500"
                  />
                </div>
                <div className="space-y-1">
                  <label className="font-bold text-slate-700">Email Address *</label>
                  <input
                    type="email"
                    required
                    placeholder="e.g. ramesh.swm@chennaiswm.gov.in"
                    value={newUserData.email}
                    onChange={(e) => setNewUserData({ ...newUserData, email: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="font-bold text-slate-700">Username (Optional)</label>
                  <input
                    type="text"
                    placeholder="Leave blank to auto-derive from email"
                    value={newUserData.username}
                    onChange={(e) => setNewUserData({ ...newUserData, username: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500"
                  />
                </div>
                <div className="space-y-1">
                  <label className="font-bold text-slate-700">Account Role *</label>
                  <select
                    value={newUserData.role}
                    onChange={(e) => setNewUserData({ ...newUserData, role: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 font-semibold focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500"
                  >
                    <option value="contributor">Citizen Contributor (contributor)</option>
                    <option value="public">Public Citizen (public)</option>
                    <option value="waste_processing_plant_operator">Processing Plant Operator (waste_processing_plant_operator)</option>
                    <option value="municipal_officer">Municipal SWM Officer (municipal_officer)</option>
                    <option value="ai_admin">AI Administrator & ML Lead (ai_admin)</option>
                    <option value="system_admin">System Security Administrator (system_admin)</option>
                    {rolesCatalog
                      .filter(
                        (r) =>
                          ![
                            "system_admin",
                            "ai_admin",
                            "municipal_officer",
                            "waste_processing_plant_operator",
                            "contributor",
                            "public",
                          ].includes(r.role)
                      )
                      .map((r) => (
                        <option key={r.role} value={r.role}>
                          {r.title} ({r.role})
                        </option>
                      ))}
                  </select>
                </div>
              </div>

              {/* Organization and Ward */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="space-y-1 sm:col-span-2">
                  <label className="font-bold text-slate-700">Organization / Department</label>
                  <input
                    type="text"
                    placeholder="e.g. GCC Zone 8 Anna Nagar / Perungudi Plant"
                    value={newUserData.organization}
                    onChange={(e) => setNewUserData({ ...newUserData, organization: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500"
                  />
                </div>
                <div className="space-y-1">
                  <label className="font-bold text-slate-700">Assigned Ward (1-200)</label>
                  <input
                    type="number"
                    min="1"
                    max="200"
                    placeholder="e.g. 102"
                    value={newUserData.assigned_ward}
                    onChange={(e) => setNewUserData({ ...newUserData, assigned_ward: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500"
                  />
                </div>
              </div>

              {/* Contact & Status */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="space-y-1">
                  <label className="font-bold text-slate-700">City</label>
                  <input
                    type="text"
                    value={newUserData.city}
                    onChange={(e) => setNewUserData({ ...newUserData, city: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800"
                  />
                </div>
                <div className="space-y-1">
                  <label className="font-bold text-slate-700">Phone Number</label>
                  <input
                    type="text"
                    placeholder="+91 98400 12345"
                    value={newUserData.phone_number}
                    onChange={(e) => setNewUserData({ ...newUserData, phone_number: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800"
                  />
                </div>
                <div className="space-y-1">
                  <label className="font-bold text-slate-700">Account Status</label>
                  <select
                    value={newUserData.is_active ? "active" : "inactive"}
                    onChange={(e) => setNewUserData({ ...newUserData, is_active: e.target.value === "active" })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 font-semibold"
                  >
                    <option value="active">Active</option>
                    <option value="inactive">Inactive</option>
                  </select>
                </div>
              </div>

              {/* Staff-specific fields */}
              {isMunicipalStaffRole(newUserData.role) && (
                <div className="p-3.5 bg-teal-50/70 border border-teal-200 rounded-xl space-y-3">
                  <div className="flex items-center gap-1.5 text-teal-900 font-bold">
                    <UserCheck className="w-4 h-4 text-teal-700" />
                    <span>Municipal Staff Details (Database B Record)</span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                    <div className="space-y-1">
                      <label className="text-[10px] uppercase font-bold text-teal-800">Employee ID</label>
                      <input
                        type="text"
                        placeholder="e.g. GCC-EMP-045"
                        value={newUserData.employee_id}
                        onChange={(e) => setNewUserData({ ...newUserData, employee_id: e.target.value })}
                        className="w-full px-2.5 py-1.5 bg-white border border-teal-200 rounded-lg text-xs"
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-[10px] uppercase font-bold text-teal-800">Department</label>
                      <input
                        type="text"
                        placeholder="e.g. Solid Waste Management"
                        value={newUserData.department}
                        onChange={(e) => setNewUserData({ ...newUserData, department: e.target.value })}
                        className="w-full px-2.5 py-1.5 bg-white border border-teal-200 rounded-lg text-xs"
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-[10px] uppercase font-bold text-teal-800">Job Title</label>
                      <input
                        type="text"
                        placeholder="e.g. Senior Plant Supervisor"
                        value={newUserData.job_title}
                        onChange={(e) => setNewUserData({ ...newUserData, job_title: e.target.value })}
                        className="w-full px-2.5 py-1.5 bg-white border border-teal-200 rounded-lg text-xs"
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* Security Policy Reminder */}
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-amber-900 leading-relaxed text-[11px] flex items-start gap-2">
                <ShieldCheck className="w-4 h-4 text-amber-700 flex-shrink-0 mt-0.5" />
                <span>
                  <strong>Zero Shared Password Policy:</strong> A cryptographically secure, single-use activation invitation token will be generated. The user will establish their own password upon first access.
                </span>
              </div>

              {/* Form Buttons */}
              <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setAddUserModalOpen(false)}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-xl text-xs transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isCreatingUser}
                  className="flex items-center gap-1.5 px-4 py-2 bg-rose-600 hover:bg-rose-700 disabled:opacity-50 text-white font-bold rounded-xl text-xs transition shadow-sm"
                >
                  {isCreatingUser && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                  <span>Provision Account</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ============================================================== */}
      {/* 2. EDIT USER DETAILS MODAL */}
      {/* ============================================================== */}
      {editModalUser && (
        <div className="fixed inset-0 bg-slate-950/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 space-y-4 animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="p-2 bg-teal-50 text-teal-700 rounded-xl border border-teal-200">
                  <UserCog className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-navy-950">Edit User Details</h3>
                  <p className="text-xs text-slate-400">Account: {editModalUser.username} ({editModalUser.email})</p>
                </div>
              </div>
              <button
                onClick={() => setEditModalUser(null)}
                className="text-slate-400 hover:text-slate-700 text-lg transition"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleSaveUserDetails} className="space-y-3.5 text-xs">
              <div className="space-y-1">
                <label className="font-bold text-slate-700">Full Name *</label>
                <input
                  type="text"
                  required
                  value={editFormData.full_name}
                  onChange={(e) => setEditFormData({ ...editFormData, full_name: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="font-bold text-slate-700">Organization</label>
                  <input
                    type="text"
                    value={editFormData.organization}
                    onChange={(e) => setEditFormData({ ...editFormData, organization: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800"
                  />
                </div>
                <div className="space-y-1">
                  <label className="font-bold text-slate-700">City</label>
                  <input
                    type="text"
                    value={editFormData.city}
                    onChange={(e) => setEditFormData({ ...editFormData, city: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="font-bold text-slate-700">Phone Number</label>
                  <input
                    type="text"
                    value={editFormData.phone_number}
                    onChange={(e) => setEditFormData({ ...editFormData, phone_number: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800"
                  />
                </div>
                <div className="space-y-1">
                  <label className="font-bold text-slate-700">Assigned Ward (1-200)</label>
                  <input
                    type="number"
                    min="1"
                    max="200"
                    value={editFormData.assigned_ward}
                    onChange={(e) => setEditFormData({ ...editFormData, assigned_ward: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800"
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="font-bold text-slate-700">Account Status</label>
                <select
                  value={editFormData.is_active ? "active" : "inactive"}
                  onChange={(e) => setEditFormData({ ...editFormData, is_active: e.target.value === "active" })}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 font-semibold"
                >
                  <option value="active">Active</option>
                  <option value="inactive">Inactive (Deactivated)</option>
                </select>
              </div>

              <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setEditModalUser(null)}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-xl text-xs transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isUpdatingDetails}
                  className="flex items-center gap-1.5 px-4 py-2 bg-teal-600 hover:bg-teal-700 disabled:opacity-50 text-white font-bold rounded-xl text-xs transition shadow-sm"
                >
                  {isUpdatingDetails && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                  <span>Save Details</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ============================================================== */}
      {/* 3. RESET PASSWORD CONFIRMATION MODAL */}
      {/* ============================================================== */}
      {resetModalUser && (
        <div className="fixed inset-0 bg-slate-950/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 space-y-4 animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="p-2 bg-amber-50 text-amber-700 rounded-xl border border-amber-200">
                  <KeyRound className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-navy-950">Reset User Password</h3>
                  <p className="text-xs text-slate-400">Target Account #{resetModalUser.id}</p>
                </div>
              </div>
              <button
                onClick={() => setResetModalUser(null)}
                className="text-slate-400 hover:text-slate-700 text-lg transition"
              >
                &times;
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 space-y-1.5">
                <div className="font-bold text-navy-950 text-sm">{resetModalUser.full_name}</div>
                <div className="font-mono text-slate-500">{resetModalUser.email}</div>
                <div className="text-[11px] text-slate-400">Current Role: {resetModalUser.role}</div>
              </div>

              <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-amber-900 leading-relaxed text-[11px] space-y-1">
                <p className="font-bold flex items-center gap-1.5">
                  <AlertTriangle className="w-4 h-4 text-amber-700 flex-shrink-0" />
                  Security Notice
                </p>
                <p>
                  Initiating a reset will immediately invalidate any previous reset tokens. A fresh single-use, time-limited token will be issued. Existing passwords are never retrieved or stored in plaintext.
                </p>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setResetModalUser(null)}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-xl text-xs transition"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmPasswordReset}
                disabled={isResettingPassword}
                className="flex items-center gap-1.5 px-4 py-2 bg-amber-600 hover:bg-amber-700 disabled:opacity-50 text-white font-bold rounded-xl text-xs transition shadow-sm"
              >
                {isResettingPassword && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                <span>Confirm & Issue Reset Token</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ============================================================== */}
      {/* 4. TOKEN PRESENTATION MODAL (Activation or Reset Link) */}
      {/* ============================================================== */}
      {tokenResultModal && (
        <div className="fixed inset-0 bg-slate-950/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 space-y-4 animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="p-2 bg-emerald-50 text-emerald-700 rounded-xl border border-emerald-200">
                  <CheckCircle2 className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-navy-950">{tokenResultModal.title}</h3>
                  <p className="text-xs text-slate-400">{tokenResultModal.targetEmail}</p>
                </div>
              </div>
              <button
                onClick={() => setTokenResultModal(null)}
                className="text-slate-400 hover:text-slate-700 text-lg transition"
              >
                &times;
              </button>
            </div>

            <p className="text-xs text-slate-600 leading-relaxed">
              {tokenResultModal.subtitle}
            </p>

            {/* Email Provider Status Banner */}
            {tokenResultModal.emailDeliveryStatus === "not_configured" ? (
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-[11px] text-amber-900 leading-relaxed space-y-1">
                <div className="font-bold flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-700" />
                  <span>Email Provider Status: Missing Configuration</span>
                </div>
                <p>
                  No external SMTP provider is configured in environment variables (<code className="font-mono text-amber-800">SMTP_HOST</code>, <code className="font-mono text-amber-800">SMTP_USER</code>).
                  Please copy and securely provide the single-use setup link below to the account owner.
                </p>
              </div>
            ) : tokenResultModal.emailDeliveryStatus === "delivered" ? (
              <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-[11px] text-emerald-900 leading-relaxed flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                <span>Invitation email successfully dispatched to <strong>{tokenResultModal.targetEmail}</strong>.</span>
              </div>
            ) : (
              <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-[11px] text-rose-900 leading-relaxed flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-rose-600 flex-shrink-0" />
                <span>Email dispatch failed. Please provide the setup link below directly to the user.</span>
              </div>
            )}

            {/* Secure Setup Link Display */}
            <div className="space-y-1.5 text-xs">
              <label className="font-bold text-slate-700">Single-Use Setup Link (Expires in 2-24 hours)</label>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  readOnly
                  value={tokenResultModal.url}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl font-mono text-[11px] text-slate-800 select-all"
                />
                <button
                  type="button"
                  onClick={() => copyToClipboard(tokenResultModal.url)}
                  className="px-3 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-xs font-bold transition flex items-center gap-1.5 shrink-0 shadow-sm"
                >
                  {copiedLink ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copiedLink ? "Copied!" : "Copy"}</span>
                </button>
              </div>
            </div>

            <div className="flex justify-end pt-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setTokenResultModal(null)}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-xl text-xs transition"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ============================================================== */}
      {/* 5. USER DETAILS MODAL */}
      {/* ============================================================== */}
      {selectedUser && (
        <div className="fixed inset-0 bg-slate-950/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 space-y-5 animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="p-2 bg-navy-950 text-white rounded-xl">
                  <UserIcon className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-navy-950">{selectedUser.full_name}</h3>
                  <p className="text-xs text-slate-400">Account ID #{selectedUser.id}</p>
                </div>
              </div>
              <button
                onClick={() => setSelectedUser(null)}
                className="text-slate-400 hover:text-slate-700 text-lg transition"
              >
                &times;
              </button>
            </div>

            <div className="space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-slate-50 p-3 rounded-xl border border-slate-100">
                  <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Username</span>
                  <p className="font-semibold text-slate-900 mt-0.5">{selectedUser.username}</p>
                </div>
                <div className="bg-slate-50 p-3 rounded-xl border border-slate-100">
                  <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Assigned Role</span>
                  <p className="font-semibold text-slate-900 mt-0.5">{selectedUser.role}</p>
                </div>
              </div>

              <div className="bg-slate-50 p-3 rounded-xl border border-slate-100 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Contact & Org</span>
                  <span className="text-emerald-700 font-semibold">{selectedUser.is_active ? "Active" : "Inactive"}</span>
                </div>
                <p className="font-medium text-slate-800 flex items-center gap-1.5">
                  <Mail className="w-3.5 h-3.5 text-slate-400" />
                  {selectedUser.email}
                </p>
                <p className="font-medium text-slate-800 flex items-center gap-1.5">
                  <Building className="w-3.5 h-3.5 text-slate-400" />
                  {selectedUser.organization || "Public Citizen"} ({selectedUser.city || "Chennai"})
                </p>
                {selectedUser.phone_number && (
                  <p className="font-medium text-slate-800 flex items-center gap-1.5">
                    <Phone className="w-3.5 h-3.5 text-slate-400" />
                    {selectedUser.phone_number}
                  </p>
                )}
                {selectedUser.assigned_ward && (
                  <p className="font-medium text-slate-800 flex items-center gap-1.5">
                    <MapPin className="w-3.5 h-3.5 text-slate-400" />
                    Assigned Ward: {selectedUser.assigned_ward}
                  </p>
                )}
              </div>

              {/* Staff Profile Details (Database B link) */}
              {selectedUser.staff_profile ? (
                <div className="bg-teal-50/60 border border-teal-200 p-3.5 rounded-xl space-y-2">
                  <div className="flex items-center gap-1.5 text-teal-900 font-bold">
                    <UserCheck className="w-3.5 h-3.5 text-teal-700" />
                    <span>Linked GCC Municipal Staff Profile</span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-[11px] text-teal-950">
                    <div>Employee ID: <strong>{selectedUser.staff_profile.employee_id}</strong></div>
                    <div>Department: <strong>{selectedUser.staff_profile.department}</strong></div>
                    <div>Job Title: <strong>{selectedUser.staff_profile.job_title}</strong></div>
                    <div>Ward: <strong>{selectedUser.staff_profile.assigned_ward_number || "—"}</strong></div>
                  </div>
                </div>
              ) : (
                <div className="bg-slate-50 border border-slate-200/60 p-3 rounded-xl text-slate-500 text-[11px]">
                  No municipal staff employee profile linked. Registered as citizen contributor.
                </div>
              )}

              <div className="text-[10px] text-slate-400 flex items-center justify-between pt-1">
                <span>Created: {new Date(selectedUser.created_at).toLocaleString()}</span>
                {selectedUser.last_login_at && (
                  <span>Last login: {new Date(selectedUser.last_login_at).toLocaleString()}</span>
                )}
              </div>
            </div>

            {/* Modal Action Controls */}
            <div className="flex items-center justify-between pt-2 border-t border-slate-100">
              <div className="flex items-center gap-2">
                {isSystemAdmin && (
                  <>
                    <button
                      onClick={() => {
                        const target = selectedUser;
                        setSelectedUser(null);
                        handleOpenEditModal(target);
                      }}
                      className="px-3 py-1.5 bg-teal-50 hover:bg-teal-100 text-teal-700 font-bold rounded-xl text-xs transition flex items-center gap-1"
                    >
                      <UserCog className="w-3.5 h-3.5" />
                      <span>Edit Details</span>
                    </button>

                    <button
                      onClick={() => {
                        const target = selectedUser;
                        setSelectedUser(null);
                        handleOpenResetModal(target);
                      }}
                      className="px-3 py-1.5 bg-amber-50 hover:bg-amber-100 text-amber-800 font-bold rounded-xl text-xs transition flex items-center gap-1"
                    >
                      <KeyRound className="w-3.5 h-3.5" />
                      <span>Reset Password</span>
                    </button>
                  </>
                )}
              </div>

              <button
                onClick={() => setSelectedUser(null)}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-xl text-xs transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ============================================================== */}
      {/* 6. ROLE ASSIGNMENT DIALOG MODAL */}
      {/* ============================================================== */}
      {roleModalUser && (
        <div className="fixed inset-0 bg-slate-950/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 space-y-5 animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="p-2 bg-rose-50 text-rose-700 rounded-xl border border-rose-200">
                  <ShieldAlert className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-navy-950">Modify User Role</h3>
                  <p className="text-xs text-slate-400">Target Account: {roleModalUser.username}</p>
                </div>
              </div>
              <button
                onClick={() => setRoleModalUser(null)}
                className="text-slate-400 hover:text-slate-700 text-lg transition"
              >
                &times;
              </button>
            </div>

            {/* Account Summary */}
            <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 space-y-2 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-bold text-navy-950">{roleModalUser.full_name}</span>
                <span className="text-[11px] font-mono text-slate-500">{roleModalUser.email}</span>
              </div>
              <div className="flex items-center gap-2 pt-1">
                <span className="text-slate-500">Current Role:</span>
                <span
                  className={`px-2 py-0.5 rounded text-[11px] font-bold border ${
                    ROLE_BADGE_STYLES[roleModalUser.role] || "bg-slate-100 text-slate-800"
                  }`}
                >
                  {roleModalUser.role}
                </span>
                <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
                <span className="text-slate-500">Proposed Role:</span>
                <span className="font-bold text-rose-700">{targetRole}</span>
              </div>
            </div>

            {/* Select Target Role */}
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-700">Select New Role</label>
              <select
                value={targetRole}
                onChange={(e) => setTargetRole(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 font-semibold focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500 transition"
              >
                <option value="system_admin">System Security Administrator (system_admin)</option>
                <option value="ai_admin">AI Administrator & ML Lead (ai_admin)</option>
                <option value="municipal_officer">Municipal SWM Officer (municipal_officer)</option>
                <option value="waste_processing_plant_operator">Processing Plant Operator (waste_processing_plant_operator)</option>
                <option value="contributor">Citizen Contributor (contributor)</option>
                <option value="public">Public Citizen (public)</option>
                {rolesCatalog
                  .filter(
                    (r) =>
                      ![
                        "system_admin",
                        "ai_admin",
                        "municipal_officer",
                        "waste_processing_plant_operator",
                        "contributor",
                        "public",
                      ].includes(r.role)
                  )
                  .map((r) => (
                    <option key={r.role} value={r.role}>
                      {r.title} ({r.role})
                    </option>
                  ))}
              </select>
            </div>

            {/* Audit Reason */}
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-700">Administrative Reason (Audit Log)</label>
              <input
                type="text"
                placeholder="Reason for role change (e.g., Promotion, Duty Transfer, SWM Staff Onboarding)..."
                value={changeReason}
                onChange={(e) => setChangeReason(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500 transition"
              />
            </div>

            {/* Explicit Confirmation Checkbox */}
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl space-y-2">
              <div className="flex items-start gap-2">
                <input
                  type="checkbox"
                  id="safetyCheck"
                  checked={confirmSafetyChecked}
                  onChange={(e) => setConfirmSafetyChecked(e.target.checked)}
                  className="mt-0.5 rounded border-amber-300 text-rose-600 focus:ring-rose-500"
                />
                <label htmlFor="safetyCheck" className="text-xs text-amber-900 leading-tight">
                  <strong>Explicit Confirmation:</strong> I confirm this role modification is authorized under GCC Municipal SWM policy and will be recorded in the security audit logs.
                </label>
              </div>
            </div>

            {/* Modal Buttons */}
            <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setRoleModalUser(null)}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-xl text-xs transition"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSaveRoleChange}
                disabled={!confirmSafetyChecked || isUpdatingRole || targetRole === roleModalUser.role}
                className="flex items-center gap-1.5 px-4 py-2 bg-rose-600 hover:bg-rose-700 disabled:opacity-40 disabled:cursor-not-allowed text-white font-bold rounded-xl text-xs transition shadow-sm"
              >
                {isUpdatingRole && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                <span>Confirm & Persist Role</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
