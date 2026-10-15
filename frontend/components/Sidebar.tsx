"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Map,
  BarChart3,
  PieChart,
  Truck,
  Factory,
  Leaf,
  ScanEye,
  UploadCloud,
  Award,
  Cpu,
  Boxes,
  Database,
  Route,
  BellRing,
  FileText,
  Settings,
  User,
  ChevronRight,
  Camera,
  Sparkles,
  ShieldCheck,
  Layers,
  BookmarkCheck,
  Users
} from "lucide-react";

import { useAuth } from "@/lib/auth-context";

interface SidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
}

export function Sidebar({ isOpen, onClose }: SidebarProps) {
  const pathname = usePathname();
  const { user } = useAuth();
  const isPublicUser = !user || user.role === "public" || user.role === "contributor";

  const publicNavGroups = [
    {
      title: "My Neighborhood",
      items: [
        { name: "My Area & Truck", href: "/", icon: LayoutDashboard },
        { name: "Sanitation Grievances", href: "/grievances", icon: FileText, badge: "Civic" },
        { name: "Live Waste Map", href: "/map", icon: Map },
        { name: "Environmental Impact", href: "/environmental", icon: Leaf },
        { name: "Segregation Guide", href: "/about-data", icon: BookmarkCheck },
      ],
    },
    {
      title: "Citizen AI Vision",
      items: [
        { name: "Live Camera Detection", href: "/live-detection", icon: Camera, badge: "Live" },
        { name: "AI Waste Detection", href: "/ai/detection", icon: ScanEye },
        { name: "Contribute to Improve AI", href: "/ai/contribute", icon: UploadCloud, badge: "Citizen AI" },
        { name: "My AI Memory", href: "/my-ai-memory", icon: Sparkles, badge: "Personal" },
        { name: "My Profile", href: "/profile", icon: User },
      ],
    },
  ];

  const staffNavGroups = [
    {
      title: "Overview",
      items: [
        { name: "Home Dashboard", href: "/", icon: LayoutDashboard },
        { name: "Live Waste Map", href: "/map", icon: Map },
      ],
    },
    {
      title: "Ward & Analytics",
      items: [
        { name: "Ward Analytics", href: "/wards", icon: BarChart3 },
        { name: "Waste Analysis", href: "/analytics/composition", icon: PieChart },
        { name: "Environmental Impact", href: "/environmental", icon: Leaf },
      ],
    },
    {
      title: "Fleet & Operations",
      items: [
        { name: "Collection Monitoring", href: "/collection", icon: Truck },
        { name: "Segregation Plants", href: "/plants", icon: Factory },
        { name: "Collection Optimization", href: "/optimization", icon: Route },
        { name: "Operational Alerts", href: "/alerts", icon: BellRing },
        { name: "Sanitation Grievances", href: "/grievances", icon: FileText, badge: "Workflow" },
      ],
    },
    {
      title: "Smart AI & Vision",
      items: [
        { name: "Live Camera Detection", href: "/live-detection", icon: Camera, badge: "Live" },
        { name: "AI Waste Detection", href: "/ai/detection", icon: ScanEye },
        { name: "AI Retraining Pipeline", href: "/admin/model-training", icon: Cpu, badge: "Retrain" },
      ],
    },
    {
      title: "Admin & AI Governance",
      items: [
        { name: "User Directory & Roles", href: "/admin/users", icon: Users, badge: "RBAC" },
        { name: "Admin Verification Queue", href: "/admin", icon: ShieldCheck, badge: "Admin" },
        { name: "Verified Dataset Hub", href: "/admin/dataset", icon: Layers },
        { name: "Model Registry & Rollback", href: "/admin/models", icon: BookmarkCheck },
        { name: "Raw Data Catalog", href: "/datasets", icon: Database },
        { name: "My Profile", href: "/profile", icon: User },
      ],
    },
  ];

  const navGroups = isPublicUser ? publicNavGroups : staffNavGroups;

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          onClick={onClose}
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 lg:hidden"
        />
      )}

      <aside
        className={`fixed top-16 bottom-0 left-0 w-64 bg-navy-950 text-slate-300 border-r border-navy-800 z-40 overflow-y-auto transition-transform duration-200 ease-in-out lg:translate-x-0 ${
          isOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="p-4 space-y-6">
          {navGroups.map((group, gIdx) => (
            <div key={gIdx} className="space-y-1">
              <h4 className="px-3 text-[11px] font-bold uppercase tracking-wider text-slate-400">
                {group.title}
              </h4>
              <nav className="space-y-0.5">
                {group.items.map((item) => {
                  const isActive = pathname === item.href;
                  const Icon = item.icon;
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      onClick={onClose}
                      className={`flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition group ${
                        isActive
                          ? "bg-teal-700/80 text-white font-semibold shadow-sm shadow-teal-900/50"
                          : "text-slate-300 hover:bg-navy-900 hover:text-white"
                      }`}
                    >
                      <div className="flex items-center space-x-2.5">
                        <Icon
                          className={`w-4 h-4 transition ${
                            isActive ? "text-teal-200" : "text-slate-400 group-hover:text-teal-300"
                          }`}
                        />
                        <span>{item.name}</span>
                      </div>
                      {item.badge ? (
                        <span className="px-1.5 py-0.5 text-[9px] font-bold rounded bg-teal-500/20 text-teal-300 border border-teal-500/30">
                          {item.badge}
                        </span>
                      ) : (
                        isActive && <ChevronRight className="w-3.5 h-3.5 text-teal-200" />
                      )}
                    </Link>
                  );
                })}
              </nav>
            </div>
          ))}

          {/* Greater Chennai Corporation Badge Footer */}
          <div className="pt-4 mt-6 border-t border-navy-800 text-[11px] text-slate-300 px-3">
            <p className="font-semibold text-slate-200">Greater Chennai Corporation</p>
            <p className="mt-0.5">Solid Waste Management Dept</p>
            <p className="text-[10px] mt-1 text-teal-400">Swachh Bharat Mission • AI Vision</p>
          </div>
        </div>
      </aside>
    </>
  );
}