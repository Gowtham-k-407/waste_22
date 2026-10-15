"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Layers,
  Cpu,
  BookmarkCheck,
  Video,
  ShieldCheck,
  Sparkles,
  RefreshCw,
  LogOut,
  Users
} from "lucide-react";
import { api } from "@/lib/api";

export function AdminNav({ pendingCount }: { pendingCount?: number }) {
  const pathname = usePathname();
  const [activeModel, setActiveModel] = useState<any>(null);
  const [userProfile, setUserProfile] = useState<any>(null);

  useEffect(() => {
    async function loadMeta() {
      try {
        const m = await api.getActiveAdminModel();
        setActiveModel(m);
      } catch (err) {
        console.error("Could not fetch active model", err);
      }

      if (typeof window !== "undefined") {
        const storedUser = localStorage.getItem("wastevision_user");
        if (storedUser) {
          try {
            setUserProfile(JSON.parse(storedUser));
          } catch (e) {}
        }
      }
    }
    loadMeta();
  }, []);

  const navItems = [
    {
      href: "/admin/users",
      label: "User Directory & Roles",
      icon: Users,
    },
    {
      href: "/admin",
      label: "Verification Queue",
      icon: LayoutDashboard,
      badge: pendingCount !== undefined && pendingCount > 0 ? pendingCount : null,
      badgeClass: "bg-amber-500 text-white"
    },
    {
      href: "/admin/dataset",
      label: "Verified Dataset",
      icon: Layers,
    },
    {
      href: "/admin/model-training",
      label: "AI Retraining Pipeline",
      icon: Cpu,
    },
    {
      href: "/admin/models",
      label: "Model Registry & Rollback",
      icon: BookmarkCheck,
    },
    {
      href: "/live-detection",
      label: "Live Camera Feed",
      icon: Video,
    },
  ];

  return (
    <div className="bg-white rounded-2xl p-4 border border-slate-200 shadow-sm space-y-4">
      {/* Top bar: Role & Active Model indicator */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100 text-xs">
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-purple-100 rounded-lg text-purple-700">
            <ShieldCheck className="w-4 h-4" />
          </div>
          <div>
            <span className="font-extrabold text-navy-950">
              {userProfile?.full_name || "Dr. Ananya Natarajan (Lead AI Scientist)"}
            </span>
            <span className="text-slate-400 ml-1.5 text-[11px]">
              • {userProfile?.role || "ai_admin"} • Greater Chennai Corporation
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {activeModel && (
            <div className="flex items-center gap-1.5 px-2.5 py-1 bg-teal-50 border border-teal-200 rounded-lg text-teal-800 text-[11px] font-semibold">
              <span className="w-2 h-2 rounded-full bg-teal-500 animate-pulse" />
              <span>Active Model:</span>
              <strong className="font-bold">{activeModel.model_name || activeModel.version}</strong>
              <span>({Math.round((activeModel.accuracy || 0.92) * 100)}% Acc)</span>
            </div>
          )}

          <Link
            href="/uploads"
            className="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-[11px] font-bold transition"
          >
            + User Uploads
          </Link>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex flex-wrap items-center gap-2">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`inline-flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-bold transition ${
                isActive
                  ? "bg-navy-900 text-white shadow-xs"
                  : "bg-slate-50 text-slate-600 hover:bg-slate-100 hover:text-navy-950 border border-slate-200"
              }`}
            >
              <Icon className={`w-3.5 h-3.5 ${isActive ? "text-teal-400" : "text-slate-400"}`} />
              <span>{item.label}</span>
              {item.badge !== null && item.badge !== undefined && (
                <span className={`px-1.5 py-0.2 rounded-full text-[10px] font-extrabold ${item.badgeClass || "bg-teal-600 text-white"}`}>
                  {item.badge}
                </span>
              )}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
