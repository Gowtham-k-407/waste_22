"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { 
  Building2, 
  MapPin, 
  Bell, 
  UserCheck, 
  Zap, 
  AlertTriangle,
  Menu,
  ChevronDown,
  LogIn,
  UserPlus,
  User as UserIcon,
  LogOut,
  Sparkles,
  Award,
  Camera
} from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

interface NavbarProps {
  onToggleSidebar?: () => void;
}

const ROLE_LABELS: Record<string, { title: string; color: string }> = {
  public: { title: "Public Citizen", color: "bg-slate-700 text-slate-100" },
  contributor: { title: "Citizen Contributor", color: "bg-teal-700 text-teal-100" },
  municipal_officer: { title: "Municipal Officer (GCC)", color: "bg-blue-700 text-blue-100" },
  plant_operator: { title: "Plant Operator", color: "bg-amber-700 text-amber-100" },
  ai_admin: { title: "AI Administrator", color: "bg-purple-700 text-purple-100" },
  system_admin: { title: "System Administrator", color: "bg-rose-700 text-rose-100" },
};

export function Navbar({ onToggleSidebar }: NavbarProps) {
  const { user, isAuthenticated, logout, switchRole, restoreSession } = useAuth();
  const [simulationMode, setSimulationMode] = useState(false);
  const [alertCount, setAlertCount] = useState(5);
  const [userDropdownOpen, setUserDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.getSimulationStatus()
      .then((data) => setSimulationMode(data.simulation_mode))
      .catch(() => {});
    
    api.getAlerts("Critical")
      .then((data) => setAlertCount(data.length || 3))
      .catch(() => {});
  }, []);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setUserDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleToggleSimulation = async () => {
    try {
      const res = await api.toggleSimulation();
      setSimulationMode(res.simulation_mode);
      window.location.reload();
    } catch (e) {
      console.error(e);
    }
  };

  const handleRoleChange = async (newRole: string) => {
    try {
      if (newRole === "system_admin") {
        try {
          await restoreSession();
        } catch {
          await switchRole(newRole);
        }
      } else {
        await switchRole(newRole);
      }
      setUserDropdownOpen(false);
    } catch (e) {
      console.error(e);
    }
  };

  const activeRole = user?.role || "public";

  return (
    <>
      {/* Persistent Global Simulation Banner when active */}
      {simulationMode && (
        <div className="bg-amber-500 text-slate-950 px-4 py-1.5 text-xs font-bold text-center flex items-center justify-center gap-2 tracking-wide shadow-inner z-50 sticky top-0">
          <AlertTriangle className="w-4 h-4 flex-shrink-0 animate-bounce" />
          <span>SIMULATION MODE ACTIVE — Demonstrating synthetic collection telemetry, truck GPS, and AI feeds. Real government figures are labeled accordingly.</span>
          <button 
            onClick={handleToggleSimulation}
            className="underline ml-2 text-slate-950 hover:text-white transition cursor-pointer"
          >
            [Switch to Verified Data]
          </button>
        </div>
      )}

      <header className="bg-navy-950 text-white border-b border-navy-800 sticky top-0 z-40 shadow-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
          
          {/* Logo & City Title */}
          <div className="flex items-center space-x-3">
            <button 
              onClick={onToggleSidebar} 
              className="lg:hidden p-2 rounded-md hover:bg-navy-800 text-slate-300"
              aria-label="Toggle navigation menu"
            >
              <Menu className="w-5 h-5" />
            </button>

            <Link href="/" className="flex items-center space-x-2.5 group">
              <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-teal-500 to-emerald-600 flex items-center justify-center shadow-lg shadow-teal-900/30">
                <Building2 className="w-5 h-5 text-white" />
              </div>
              <div>
                <div className="flex items-center gap-1.5">
                  <span className="font-extrabold text-sm sm:text-base tracking-tight text-white group-hover:text-teal-400 transition">
                    GCC Smart Waste
                  </span>
                  <span className="hidden sm:inline-block px-1.5 py-0.2 bg-teal-800/60 text-teal-300 text-[10px] font-semibold rounded uppercase tracking-wider border border-teal-700/50">
                    Chennai
                  </span>
                </div>
                <p className="hidden md:block text-[11px] text-slate-400 leading-none">
                  Municipal Solid Waste Segregation & AI Optimization
                </p>
              </div>
            </Link>
          </div>

          {/* Right Controls: City Selector, Simulation Toggle, Roles, Alerts, Auth */}
          <div className="flex items-center space-x-2 sm:space-x-3">
            
            {/* City Selector */}
            <div className="hidden sm:flex items-center space-x-1.5 px-2.5 py-1 bg-navy-900 rounded-lg border border-navy-800 text-xs text-slate-300">
              <MapPin className="w-3.5 h-3.5 text-teal-400" />
              <select className="bg-transparent border-none focus:outline-none text-slate-200 text-xs cursor-pointer font-medium">
                <option value="chennai" className="bg-navy-900 text-white">Chennai, TN</option>
                <option value="coimbatore" disabled className="bg-navy-900 text-slate-500">Coimbatore (Phase 2)</option>
                <option value="madurai" disabled className="bg-navy-900 text-slate-500">Madurai (Phase 2)</option>
              </select>
            </div>

            {/* Simulation Mode Toggle Button */}
            <button
              onClick={handleToggleSimulation}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold border transition ${
                simulationMode 
                  ? "bg-amber-500/20 text-amber-300 border-amber-500/50 hover:bg-amber-500/30" 
                  : "bg-navy-900 text-slate-300 border-navy-700 hover:bg-navy-800"
              }`}
              title="Toggle between Verified Municipal Baseline Data and Live Simulation Feed"
            >
              <Zap className={`w-3.5 h-3.5 ${simulationMode ? "text-amber-400 fill-amber-400" : "text-slate-400"}`} />
              <span className="hidden md:inline">Sim Mode:</span>
              <span className={simulationMode ? "text-amber-400 font-bold" : "text-slate-400 font-normal"}>
                {simulationMode ? "ON" : "OFF"}
              </span>
            </button>

            {/* Alerts Bell */}
            <Link
              href="/alerts"
              className="relative p-2 rounded-lg bg-navy-900 hover:bg-navy-800 text-slate-300 transition"
              title="View Active Operational Alerts"
            >
              <Bell className="w-4 h-4" />
              {alertCount > 0 && (
                <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-rose-600 text-white text-[10px] font-bold flex items-center justify-center animate-pulse">
                  {alertCount}
                </span>
              )}
            </Link>

            {/* User Profile / Auth State */}
            {isAuthenticated && user ? (
              <div className="relative" ref={dropdownRef}>
                <button
                  onClick={() => setUserDropdownOpen(!userDropdownOpen)}
                  className="flex items-center gap-2 p-1.5 pl-2.5 pr-2 bg-navy-900 hover:bg-navy-800 rounded-xl border border-navy-700 text-xs transition"
                >
                  <div className="w-6 h-6 rounded-full bg-teal-600 text-white font-bold flex items-center justify-center text-xs">
                    {user.full_name ? user.full_name.charAt(0).toUpperCase() : "U"}
                  </div>
                  <div className="hidden lg:flex flex-col text-left">
                    <span className="font-semibold text-slate-200 text-xs max-w-[120px] truncate leading-tight">
                      {user.full_name}
                    </span>
                    <span className="text-[10px] text-teal-400 leading-tight">
                      {ROLE_LABELS[activeRole]?.title || activeRole}
                    </span>
                  </div>
                  <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
                </button>

                {userDropdownOpen && (
                  <div className="absolute right-0 mt-2 w-64 bg-white rounded-2xl shadow-2xl py-2 z-50 border border-slate-200 text-slate-800 animate-in fade-in zoom-in-95">
                    {/* User Summary Header */}
                    <div className="px-4 py-3 border-b border-slate-100">
                      <p className="text-xs font-bold text-slate-900 truncate">{user.full_name}</p>
                      <p className="text-[11px] text-slate-500 truncate">{user.email}</p>
                      <div className="mt-2 flex items-center justify-between">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${ROLE_LABELS[activeRole]?.color || "bg-slate-100 text-slate-800"}`}>
                          {ROLE_LABELS[activeRole]?.title || activeRole}
                        </span>
                        <span className="text-[10px] font-semibold text-teal-700 bg-teal-50 px-2 py-0.5 rounded border border-teal-200 flex items-center">
                          <Sparkles className="w-3 h-3 text-amber-500 mr-1" />
                          {user.contribution_points || 50} pts
                        </span>
                      </div>
                    </div>

                    {/* Navigation Options */}
                    <div className="py-1">
                      <Link
                        href="/profile"
                        onClick={() => setUserDropdownOpen(false)}
                        className="w-full text-left px-4 py-2 text-xs flex items-center text-slate-700 hover:bg-slate-50 hover:text-teal-700 transition"
                      >
                        <UserIcon className="w-3.5 h-3.5 mr-2 text-slate-400" />
                        My Profile & Settings
                      </Link>
                      <Link
                        href="/my-ai-memory"
                        onClick={() => setUserDropdownOpen(false)}
                        className="w-full text-left px-4 py-2 text-xs flex items-center text-slate-700 hover:bg-slate-50 hover:text-purple-700 transition"
                      >
                        <Sparkles className="w-3.5 h-3.5 mr-2 text-purple-600" />
                        <span>My AI Memory</span>
                        <span className="ml-auto text-[9px] font-bold bg-purple-100 text-purple-800 px-1.5 py-0.2 rounded">Personal</span>
                      </Link>
                      <Link
                        href="/live-detection"
                        onClick={() => setUserDropdownOpen(false)}
                        className="w-full text-left px-4 py-2 text-xs flex items-center text-slate-700 hover:bg-slate-50 hover:text-teal-700 transition"
                      >
                        <Camera className="w-3.5 h-3.5 mr-2 text-teal-600" />
                        <span>Live Camera Detection</span>
                        <span className="ml-auto text-[9px] font-bold bg-teal-100 text-teal-800 px-1.5 py-0.2 rounded">WebCam</span>
                      </Link>
                      <Link
                        href="/ai/my-contributions"
                        onClick={() => setUserDropdownOpen(false)}
                        className="w-full text-left px-4 py-2 text-xs flex items-center text-slate-700 hover:bg-slate-50 hover:text-teal-700 transition"
                      >
                        <Award className="w-3.5 h-3.5 mr-2 text-slate-400" />
                        My Waste Contributions
                      </Link>
                    </div>

                    {/* Persona Switcher for Evaluation */}
                    <div className="border-t border-slate-100 px-4 pt-2 pb-1">
                      <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5 flex items-center">
                        <UserCheck className="w-3 h-3 text-teal-600 mr-1" />
                        Switch Municipal Persona
                      </div>
                      <div className="grid grid-cols-2 gap-1">
                        {Object.entries(ROLE_LABELS).map(([roleKey, item]) => (
                          <button
                            key={roleKey}
                            onClick={() => handleRoleChange(roleKey)}
                            className={`text-left px-2 py-1 rounded text-[10px] transition truncate ${
                              activeRole === roleKey
                                ? "bg-teal-50 text-teal-800 font-bold border border-teal-200"
                                : "text-slate-600 hover:bg-slate-100"
                            }`}
                          >
                            {item.title.split(" ")[0]}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Sign Out Button */}
                    <div className="border-t border-slate-100 pt-1 mt-1">
                      <button
                        onClick={() => {
                          setUserDropdownOpen(false);
                          logout();
                        }}
                        className="w-full text-left px-4 py-2 text-xs flex items-center text-red-600 hover:bg-red-50 transition"
                      >
                        <LogOut className="w-3.5 h-3.5 mr-2 text-red-500" />
                        Sign Out
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex items-center space-x-2">
                <Link
                  href="/login"
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-navy-700 bg-navy-900 hover:bg-navy-800 text-xs font-semibold text-slate-200 hover:text-white transition"
                >
                  <LogIn className="w-3.5 h-3.5 text-teal-400" />
                  <span>Sign In</span>
                </Link>
                <Link
                  href="/register"
                  className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-700 text-xs font-semibold text-white shadow-sm transition"
                >
                  <UserPlus className="w-3.5 h-3.5" />
                  <span>Register</span>
                </Link>
              </div>
            )}

          </div>
        </div>
      </header>
    </>
  );
}