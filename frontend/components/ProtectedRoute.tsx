"use client";

import React from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { ShieldAlert, LogIn, ArrowRight, UserCheck, ShieldCheck, Home } from "lucide-react";

interface ProtectedRouteProps {
  children: React.ReactNode;
  allowedRoles?: string[];
  requiredPermissionTitle?: string;
}

const ROLE_TITLES: Record<string, string> = {
  public: "Public Citizen",
  contributor: "Registered Contributor",
  municipal_officer: "Municipal Officer (GCC)",
  plant_operator: "Plant Operator",
  ai_admin: "AI Administrator",
  system_admin: "System Administrator",
};

export function ProtectedRoute({
  children,
  allowedRoles = [],
  requiredPermissionTitle,
}: ProtectedRouteProps) {
  const { user, loading, isAuthenticated, switchRole } = useAuth();

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] py-16">
        <div className="w-12 h-12 border-4 border-teal-600 border-t-transparent rounded-full animate-spin mb-4" />
        <p className="text-sm font-medium text-slate-600">Verifying municipal credentials...</p>
      </div>
    );
  }

  // If user is not signed in
  if (!isAuthenticated || !user) {
    return (
      <div className="max-w-2xl mx-auto my-12 bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden text-center">
        <div className="bg-gradient-to-r from-navy-900 to-navy-800 text-white p-8">
          <div className="w-16 h-16 bg-teal-500/20 text-teal-400 border border-teal-400/30 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <LogIn className="w-8 h-8" />
          </div>
          <h2 className="text-2xl font-bold">Sign In Required</h2>
          <p className="text-navy-200 text-sm mt-2 max-w-md mx-auto">
            {requiredPermissionTitle || "This section of the Chennai Waste Management Portal requires an authorized account to access."}
          </p>
        </div>

        <div className="p-8 space-y-6">
          <div className="bg-slate-50 border border-slate-100 rounded-xl p-4 text-left">
            <h4 className="text-sm font-semibold text-slate-800 mb-1">Why do I need to sign in?</h4>
            <p className="text-xs text-slate-600 leading-relaxed">
              To upload waste photos, verify AI detections, record plant operations, or adjust municipal optimization settings, we verify identity to ensure data accuracy for the Greater Chennai Corporation.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link
              href="/login"
              className="w-full sm:w-auto inline-flex items-center justify-center px-6 py-3 bg-teal-600 hover:bg-teal-700 text-white text-sm font-semibold rounded-xl shadow-sm transition-all"
            >
              Sign In to WasteVision AI
              <ArrowRight className="w-4 h-4 ml-2" />
            </Link>
            <Link
              href="/register"
              className="w-full sm:w-auto inline-flex items-center justify-center px-6 py-3 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-sm font-semibold rounded-xl transition-all"
            >
              Create Contributor Account
            </Link>
          </div>

          <div className="pt-4 border-t border-slate-100">
            <Link href="/" className="inline-flex items-center text-xs text-slate-500 hover:text-teal-700">
              <Home className="w-3.5 h-3.5 mr-1" />
              Return to Public Overview
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // If user is signed in, check role permission
  const isAuthorized =
    allowedRoles.length === 0 ||
    user.role === "system_admin" ||
    allowedRoles.includes(user.role);

  if (!isAuthorized) {
    const targetTitles = allowedRoles.map((r) => ROLE_TITLES[r] || r).join(" or ");
    const currentRoleTitle = ROLE_TITLES[user.role] || user.role;

    return (
      <div className="max-w-2xl mx-auto my-12 bg-white rounded-2xl shadow-sm border border-amber-200 overflow-hidden">
        <div className="bg-gradient-to-r from-amber-500 to-amber-600 text-white p-8 text-center">
          <div className="w-16 h-16 bg-white/20 text-white rounded-2xl flex items-center justify-center mx-auto mb-4">
            <ShieldAlert className="w-8 h-8" />
          </div>
          <h2 className="text-2xl font-bold">Access Restricted</h2>
          <p className="text-amber-100 text-sm mt-2">
            This module requires <span className="font-semibold text-white underline">{targetTitles}</span> privileges.
          </p>
        </div>

        <div className="p-8 space-y-6">
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
            <div className="flex items-start space-x-3">
              <UserCheck className="w-5 h-5 text-amber-700 flex-shrink-0 mt-0.5" />
              <div className="text-sm">
                <p className="font-medium text-amber-900">
                  You are currently signed in as: <span className="font-bold">{user.full_name}</span>
                </p>
                <p className="text-amber-800 text-xs mt-1">
                  Active Role: <span className="inline-block px-2 py-0.5 bg-amber-200 text-amber-900 font-semibold rounded">{currentRoleTitle}</span>
                </p>
                <p className="text-slate-600 text-xs mt-2">
                  Different municipal roles have dedicated capabilities to protect critical processing plant equipment, fleet telemetry, and model weights.
                </p>
              </div>
            </div>
          </div>

          {/* Access Policy Notice */}
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-4">
            <p className="text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1 flex items-center">
              <ShieldCheck className="w-4 h-4 text-teal-600 mr-1.5" />
              Role-Based Access Enforcement
            </p>
            <p className="text-xs text-slate-500 leading-relaxed">
              If your municipal job duty requires access to this operational module, please coordinate with your GCC Department Supervisor or the System Administrator to update your official staff profile.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
            <Link
              href="/"
              className="inline-flex items-center text-sm text-slate-600 hover:text-slate-900 font-medium"
            >
              <Home className="w-4 h-4 mr-1.5" />
              Return to Public Overview
            </Link>
            <Link
              href="/profile"
              className="inline-flex items-center text-sm text-teal-700 hover:text-teal-800 font-semibold"
            >
              View My Profile & Permissions
              <ArrowRight className="w-4 h-4 ml-1" />
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}