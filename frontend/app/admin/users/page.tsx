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
  ArrowRight
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

  const isSystemAdmin = currentUser?.role === "system_admin";

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
                User Directory & Role Management
              </h1>
              <p className="text-xs text-slate-500 mt-0.5">
                Authorized Municipal Administrative Directory with Role-Based Access Control (RBAC) & Audit Integrity
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-700 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-teal-600" />
            <span>Total Accounts:</span>
            <strong className="text-navy-950 font-bold">{totalCount}</strong>
          </div>
          <button
            onClick={() => fetchUsers(currentPage)}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-semibold transition"
            title="Refresh Directory"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
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
                          <button
                            onClick={() => setSelectedUser(u)}
                            className="p-1.5 text-slate-500 hover:text-navy-950 hover:bg-slate-100 rounded-lg transition"
                            title="View Administrative Details"
                          >
                            <Eye className="w-3.5 h-3.5" />
                          </button>

                          {isSystemAdmin ? (
                            <button
                              onClick={() => handleOpenRoleModal(u)}
                              disabled={isSelf}
                              className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold border transition ${
                                isSelf
                                  ? "opacity-40 cursor-not-allowed bg-slate-50 text-slate-400 border-slate-200"
                                  : "bg-white hover:bg-rose-50 text-slate-700 hover:text-rose-700 border-slate-200 hover:border-rose-200 shadow-sm"
                              }`}
                              title={isSelf ? "Self-role modification disabled for safety" : "Change User Role"}
                            >
                              <Edit2 className="w-3 h-3 text-rose-600" />
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

      {/* User Details Modal */}
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

            <div className="flex justify-end pt-2">
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

      {/* Role Assignment Dialog Modal */}
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
