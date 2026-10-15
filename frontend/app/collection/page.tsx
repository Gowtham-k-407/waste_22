"use client";

import React, { useEffect, useState } from "react";
import { 
  Truck, 
  BatteryCharging, 
  MapPin, 
  Phone, 
  Gauge, 
  Video, 
  CheckCircle2, 
  Clock, 
  AlertCircle,
  Search,
  Filter
} from "lucide-react";
import { api } from "@/lib/api";
import { DataProvenanceBadge } from "@/components/DataProvenanceBadge";
import { ProtectedRoute } from "@/components/ProtectedRoute";

const STAFF_ROLES = [
  "system_admin",
  "municipal_officer",
  "sanitary_inspector",
  "assistant_engineer",
  "ward_supervisor",
  "field_officer",
  "municipal_commissioner",
  "solid_waste_management_officer",
  "ai_admin"
];

export default function CollectionMonitoringPage() {
  return (
    <ProtectedRoute allowedRoles={STAFF_ROLES} requiredPermissionTitle="Municipal Fleet Monitoring">
      <CollectionMonitoringContent />
    </ProtectedRoute>
  );
}

function CollectionMonitoringContent() {
  const [vehicles, setVehicles] = useState<any[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadVehicles() {
      try {
        setLoading(true);
        const data = await api.getVehicles();
        setVehicles(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadVehicles();

    // Live refresh every 15 seconds
    const interval = setInterval(loadVehicles, 15000);
    return () => clearInterval(interval);
  }, []);

  const filteredVehicles = vehicles.filter((v) => {
    const matchesStatus = statusFilter === "all" || v.status.toLowerCase() === statusFilter.toLowerCase();
    const matchesSearch =
      v.vehicle_code.toLowerCase().includes(search.toLowerCase()) ||
      v.driver_name.toLowerCase().includes(search.toLowerCase()) ||
      v.assigned_route.toLowerCase().includes(search.toLowerCase());
    return matchesStatus && matchesSearch;
  });

  const getFillColor = (fill: number) => {
    if (fill >= 80) return "bg-rose-500 text-rose-700";
    if (fill >= 60) return "bg-amber-500 text-amber-700";
    return "bg-emerald-500 text-emerald-700";
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl sm:text-2xl font-extrabold text-navy-950">
              Smart Garbage Truck Fleet Telemetry & Monitoring
            </h1>
            <DataProvenanceBadge
              provenance={{
                source: "GCC Municipal Fleet GPS & Compactor On-Board Diagnostics",
                dataset_name: "Smart Compactor Live Fleet Feed",
                last_updated: "Live (15s Auto-refresh)",
                data_type: "NEAR REAL-TIME DATA",
                reliability: "Direct GPS & Load Sensor Telemetry",
              }}
              metricTitle="Fleet Telemetry"
            />
          </div>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Real-time tracking of 24 smart collection trucks equipped with automated waste detection cameras,
            hydraulic load-cells, and driver tracking.
          </p>
        </div>
      </div>

      {/* Fleet Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm">
          <span className="text-xs font-semibold text-slate-500">Total Fleet Active</span>
          <p className="text-2xl font-extrabold text-navy-950 mt-1">
            {vehicles.length} <span className="text-xs font-normal">Vehicles</span>
          </p>
          <span className="text-[11px] text-emerald-600 font-medium">100% Online</span>
        </div>

        <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm">
          <span className="text-xs font-semibold text-slate-500">Actively Collecting</span>
          <p className="text-2xl font-extrabold text-teal-700 mt-1">
            {vehicles.filter(v => v.status === "collecting").length}
          </p>
          <span className="text-[11px] text-slate-500">Door-to-door / Bins</span>
        </div>

        <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm">
          <span className="text-xs font-semibold text-slate-500">In Transit to Plants</span>
          <p className="text-2xl font-extrabold text-sky-700 mt-1">
            {vehicles.filter(v => v.status === "in_transit").length}
          </p>
          <span className="text-[11px] text-slate-500">En route Perungudi/Kodungaiyur</span>
        </div>

        <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm">
          <span className="text-xs font-semibold text-slate-500">Average Fill Level</span>
          <p className="text-2xl font-extrabold text-navy-900 mt-1">
            {Math.round(vehicles.reduce((acc, v) => acc + v.current_fill_pct, 0) / (vehicles.length || 1))}%
          </p>
          <span className="text-[11px] text-slate-500">Fleet compaction index</span>
        </div>
      </div>

      {/* Search & Filter Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-white p-3.5 rounded-xl border border-slate-200 shadow-sm">
        <div className="relative w-full sm:w-72">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search vehicle ID, driver, route..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-1 focus:ring-teal-500"
          />
        </div>

        <div className="flex items-center gap-1.5 w-full sm:w-auto overflow-x-auto text-xs">
          {["all", "collecting", "in_transit", "unloading"].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1.5 rounded-lg font-semibold capitalize transition ${
                statusFilter === st
                  ? "bg-navy-900 text-white shadow-sm"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              {st === "all" ? "All Vehicles" : st.replace("_", " ")}
            </button>
          ))}
        </div>
      </div>

      {/* Vehicles Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredVehicles.map((v) => (
          <div
            key={v.id}
            className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm hover:border-teal-300 transition space-y-4"
          >
            {/* Card Header */}
            <div className="flex items-start justify-between">
              <div className="flex items-center space-x-2.5">
                <div className="w-9 h-9 rounded-lg bg-sky-50 border border-sky-200 flex items-center justify-center text-sky-700">
                  <Truck className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-extrabold text-navy-950 flex items-center gap-2">
                    <span>{v.vehicle_code}</span>
                    <span className="text-[10px] font-mono text-slate-400 font-normal">{v.registration_no}</span>
                  </h3>
                  <p className="text-[11px] text-slate-500">{v.assigned_route}</p>
                </div>
              </div>

              <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                v.status === "collecting" ? "bg-emerald-50 text-emerald-700 border border-emerald-200" :
                v.status === "in_transit" ? "bg-sky-50 text-sky-700 border border-sky-200" :
                "bg-amber-50 text-amber-700 border border-amber-200"
              }`}>
                {v.status.replace("_", " ")}
              </span>
            </div>

            {/* Bin Fill Level Progress Bar */}
            <div className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-500 font-medium">Bin Fill Level:</span>
                <span className="font-extrabold text-navy-900">{v.current_fill_pct}%</span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                <div
                  className={`h-2 rounded-full transition-all duration-300 ${getFillColor(v.current_fill_pct).split(' ')[0]}`}
                  style={{ width: `${v.current_fill_pct}%` }}
                ></div>
              </div>
            </div>

            {/* Telemetry Metrics */}
            <div className="grid grid-cols-2 gap-2 text-[11px] bg-slate-50 p-2.5 rounded-lg border border-slate-100">
              <div className="flex items-center space-x-1.5 text-slate-600">
                <BatteryCharging className="w-3.5 h-3.5 text-emerald-600" />
                <span>Battery: <strong>{v.battery_or_fuel_pct}%</strong></span>
              </div>
              <div className="flex items-center space-x-1.5 text-slate-600">
                <Gauge className="w-3.5 h-3.5 text-teal-600" />
                <span>Speed: <strong>{v.current_speed_kmh} km/h</strong></span>
              </div>
              <div className="flex items-center space-x-1.5 text-slate-600">
                <Phone className="w-3.5 h-3.5 text-slate-400" />
                <span className="truncate">{v.driver_name}</span>
              </div>
              <div className="flex items-center space-x-1.5 text-slate-600">
                <MapPin className="w-3.5 h-3.5 text-slate-400" />
                <span>Ward {v.assigned_ward_id}</span>
              </div>
            </div>

            {/* Camera Status */}
            <div className="flex items-center justify-between text-[11px] pt-1 border-t border-slate-100">
              <div className="flex items-center space-x-1 text-teal-700 font-medium">
                <Video className="w-3 h-3 text-teal-600 animate-pulse" />
                <span>AI Camera Streaming</span>
              </div>
              <span className="text-slate-400 text-[10px]">
                Ping: Just now
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}