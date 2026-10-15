"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { 
  Trash2, 
  Recycle, 
  CheckCircle2, 
  Leaf, 
  Truck, 
  Factory, 
  BarChart3, 
  ArrowRight, 
  Map, 
  ScanEye, 
  UploadCloud, 
  AlertCircle,
  Clock,
  Sparkles,
  Building2,
  MapPin,
  FileText,
  ShieldAlert,
  ChevronRight,
  PlusCircle
} from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { MetricCard } from "@/components/MetricCard";
import { DataProvenanceBadge } from "@/components/DataProvenanceBadge";
import { MetricTooltip } from "@/components/MetricTooltip";

export default function HomePage() {
  const { user } = useAuth();
  const isPublicUser = user && ["public", "contributor"].includes(user.role);

  const [summary, setSummary] = useState<any>(null);
  const [recentDetections, setRecentDetections] = useState<any[]>([]);
  const [publicData, setPublicData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadData() {
    try {
      setLoading(true);
      setError(null);
      if (isPublicUser) {
        const pData = await api.getPublicDashboard();
        setPublicData(pData);
      } else {
        const [dashData, detData] = await Promise.all([
          api.getDashboardSummary(),
          api.getRecentDetections(undefined, 6),
        ]);
        setSummary(dashData);
        setRecentDetections(detData);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load dashboard metrics");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, [isPublicUser]);

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-20 bg-slate-200 rounded-xl"></div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="h-32 bg-slate-200 rounded-xl"></div>
          ))}
        </div>
      </div>
    );
  }

  if (isPublicUser) {
    if (error || !publicData) {
      return (
        <div className="p-8 text-center bg-white rounded-xl border border-rose-200 shadow-sm max-w-xl mx-auto my-12">
          <AlertCircle className="w-12 h-12 text-rose-500 mx-auto mb-3" />
          <h3 className="text-lg font-bold text-slate-800">Connection Error</h3>
          <p className="text-sm text-slate-600 mt-1">
            {error || "Something went wrong while loading your neighborhood dashboard."}
          </p>
          <button
            onClick={() => loadData()}
            className="mt-4 px-4 py-2 bg-navy-800 text-white text-xs font-semibold rounded-lg hover:bg-navy-900 transition"
          >
            Retry Connection
          </button>
        </div>
      );
    }
    return <ResidentDashboardView publicData={publicData} />;
  }

  if (error || !summary) {
    return (
      <div className="p-8 text-center bg-white rounded-xl border border-rose-200 shadow-sm max-w-xl mx-auto my-12">
        <AlertCircle className="w-12 h-12 text-rose-500 mx-auto mb-3" />
        <h3 className="text-lg font-bold text-slate-800">Connection Error</h3>
        <p className="text-sm text-slate-600 mt-1">
          Something went wrong while loading municipal information. Please ensure the backend server is running.
        </p>
        <button
          onClick={() => window.location.reload()}
          className="mt-4 px-4 py-2 bg-navy-800 text-white text-xs font-semibold rounded-lg hover:bg-navy-900 transition"
        >
          Retry Connection
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Hero Welcome Banner */}
      <div className="bg-gradient-to-r from-navy-950 via-navy-900 to-teal-950 text-white rounded-2xl p-6 sm:p-8 shadow-lg border border-navy-800 relative overflow-hidden">
        <div className="relative z-10 max-w-3xl">
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-teal-500/20 border border-teal-500/30 text-teal-300 text-xs font-semibold mb-3">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Chennai Municipal Corporation • AI Vision Fleet & Recycling Operations</span>
          </div>
          <h1 className="text-2xl sm:text-4xl font-extrabold tracking-tight">
            Commercial Solid Waste Segregation Optimization
          </h1>
          <p className="mt-2 text-sm sm:text-base text-slate-300 leading-relaxed">
            Real-time municipal surveillance across 15 Zones & 200 Wards. Combining Smart Garbage Truck computer vision,
            GIS logistics mapping, and community-powered continuous AI model retraining.
          </p>

          <div className="mt-6 flex flex-wrap gap-3">
            <Link
              href="/map"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-teal-600 hover:bg-teal-500 text-white text-xs font-bold transition shadow-sm"
            >
              <Map className="w-4 h-4" />
              <span>Explore Live GIS Map</span>
            </Link>
            <Link
              href="/ai/contribute"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-white/10 hover:bg-white/20 text-white text-xs font-semibold transition border border-white/20"
            >
              <UploadCloud className="w-4 h-4" />
              <span>Contribute Waste Photos to Train AI</span>
            </Link>
            <Link
              href="/optimization"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-white/10 hover:bg-white/20 text-white text-xs font-semibold transition border border-white/20"
            >
              <Trash2 className="w-4 h-4" />
              <span>AI Recommendations</span>
            </Link>
          </div>
        </div>
      </div>

      {/* Primary KPI Section: Total Waste Volume */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-navy-950 flex items-center gap-2">
              <Trash2 className="w-5 h-5 text-teal-600" />
              <span>City-Wide Waste Collection Aggregates</span>
            </h2>
            <p className="text-xs text-slate-500">
              Aggregated clearing volume across all 200 wards of Greater Chennai Corporation.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <MetricCard
            title={summary.total_waste_today_tons.title}
            value={summary.total_waste_today_tons.value}
            unit={summary.total_waste_today_tons.unit}
            trend={summary.total_waste_today_tons.trend}
            trendDirection={summary.total_waste_today_tons.trend_direction}
            trendIsGood={summary.total_waste_today_tons.trend_is_good}
            explanation={summary.total_waste_today_tons.explanation}
            provenance={summary.total_waste_today_tons.provenance}
            icon={<Clock className="w-4 h-4" />}
          />
          <MetricCard
            title={summary.total_waste_week_tons.title}
            value={summary.total_waste_week_tons.value}
            unit={summary.total_waste_week_tons.unit}
            trend={summary.total_waste_week_tons.trend}
            trendDirection={summary.total_waste_week_tons.trend_direction}
            trendIsGood={summary.total_waste_week_tons.trend_is_good}
            explanation={summary.total_waste_week_tons.explanation}
            provenance={summary.total_waste_week_tons.provenance}
          />
          <MetricCard
            title={summary.total_waste_month_tons.title}
            value={summary.total_waste_month_tons.value}
            unit={summary.total_waste_month_tons.unit}
            trend={summary.total_waste_month_tons.trend}
            trendDirection={summary.total_waste_month_tons.trend_direction}
            trendIsGood={summary.total_waste_month_tons.trend_is_good}
            explanation={summary.total_waste_month_tons.explanation}
            provenance={summary.total_waste_month_tons.provenance}
          />
        </div>
      </section>

      {/* Operational & Environmental KPIs */}
      <section className="space-y-3">
        <h2 className="text-lg font-bold text-navy-950 flex items-center gap-2">
          <CheckCircle2 className="w-5 h-5 text-teal-600" />
          <span>Operational Efficiency & Environmental Indicators</span>
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            title={summary.segregation_efficiency.title}
            value={summary.segregation_efficiency.value}
            unit={summary.segregation_efficiency.unit}
            trend={summary.segregation_efficiency.trend}
            trendDirection={summary.segregation_efficiency.trend_direction}
            trendIsGood={summary.segregation_efficiency.trend_is_good}
            explanation={summary.segregation_efficiency.explanation}
            provenance={summary.segregation_efficiency.provenance}
            icon={<Recycle className="w-4 h-4 text-emerald-600" />}
          />
          <MetricCard
            title={summary.recycling_rate.title}
            value={summary.recycling_rate.value}
            unit={summary.recycling_rate.unit}
            trend={summary.recycling_rate.trend}
            trendDirection={summary.recycling_rate.trend_direction}
            trendIsGood={summary.recycling_rate.trend_is_good}
            explanation={summary.recycling_rate.explanation}
            provenance={summary.recycling_rate.provenance}
            icon={<CheckCircle2 className="w-4 h-4 text-sky-600" />}
          />
          <MetricCard
            title={summary.estimated_environmental_co2e.title}
            value={summary.estimated_environmental_co2e.value}
            unit={summary.estimated_environmental_co2e.unit}
            trend={summary.estimated_environmental_co2e.trend}
            trendDirection={summary.estimated_environmental_co2e.trend_direction}
            trendIsGood={summary.estimated_environmental_co2e.trend_is_good}
            explanation={summary.estimated_environmental_co2e.explanation}
            provenance={summary.estimated_environmental_co2e.provenance}
            icon={<Leaf className="w-4 h-4 text-emerald-500" />}
          />
          <MetricCard
            title={summary.plant_capacity_utilization_pct.title}
            value={summary.plant_capacity_utilization_pct.value}
            unit={summary.plant_capacity_utilization_pct.unit}
            trend={summary.plant_capacity_utilization_pct.trend}
            trendDirection={summary.plant_capacity_utilization_pct.trend_direction}
            trendIsGood={summary.plant_capacity_utilization_pct.trend_is_good}
            explanation={summary.plant_capacity_utilization_pct.explanation}
            provenance={summary.plant_capacity_utilization_pct.provenance}
            icon={<Factory className="w-4 h-4 text-amber-500" />}
          />
        </div>
      </section>

      {/* Fleet & Processing Capacities */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <MetricCard
          title={summary.active_vehicles_count.title}
          value={summary.active_vehicles_count.value}
          unit={summary.active_vehicles_count.unit}
          trend={summary.active_vehicles_count.trend}
          trendDirection={summary.active_vehicles_count.trend_direction}
          trendIsGood={summary.active_vehicles_count.trend_is_good}
          explanation={summary.active_vehicles_count.explanation}
          provenance={summary.active_vehicles_count.provenance}
          icon={<Truck className="w-4 h-4 text-sky-500" />}
        />
        <MetricCard
          title={summary.active_plants_count.title}
          value={summary.active_plants_count.value}
          unit={summary.active_plants_count.unit}
          trend={summary.active_plants_count.trend}
          trendDirection={summary.active_plants_count.trend_direction}
          trendIsGood={summary.active_plants_count.trend_is_good}
          explanation={summary.active_plants_count.explanation}
          provenance={summary.active_plants_count.provenance}
          icon={<Factory className="w-4 h-4 text-teal-500" />}
        />
        <MetricCard
          title={summary.total_processing_capacity_tpd.title}
          value={summary.total_processing_capacity_tpd.value}
          unit={summary.total_processing_capacity_tpd.unit}
          trend={summary.total_processing_capacity_tpd.trend}
          trendDirection={summary.total_processing_capacity_tpd.trend_direction}
          trendIsGood={summary.total_processing_capacity_tpd.trend_is_good}
          explanation={summary.total_processing_capacity_tpd.explanation}
          provenance={summary.total_processing_capacity_tpd.provenance}
        />
      </div>

      {/* The 11 Waste Categories Breakdown */}
      <section className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-100">
          <div>
            <h3 className="text-base font-bold text-navy-950 flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-teal-600" />
              <span>Waste Stream Composition — 11 Municipal Categories</span>
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Daily weight distribution and recyclability potential across Chennai.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 font-medium">Most Generated:</span>
            <span className="px-2 py-0.5 bg-emerald-50 text-emerald-800 text-xs font-bold rounded-md border border-emerald-200">
              {summary.top_waste_category}
            </span>
          </div>
        </div>

        {/* Categories Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {summary.categories.map((cat: any) => (
            <div
              key={cat.id}
              className="p-3.5 rounded-lg border border-slate-100 bg-slate-50/50 hover:bg-slate-50 hover:border-slate-200 transition"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <span
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: cat.color }}
                  ></span>
                  <span className="text-xs font-bold text-slate-800">{cat.name}</span>
                </div>
                <span className="text-xs font-extrabold text-navy-900">
                  {cat.percentage}%
                </span>
              </div>

              {/* Progress Bar */}
              <div className="w-full bg-slate-200 rounded-full h-1.5 mt-2 overflow-hidden">
                <div
                  className="h-1.5 rounded-full"
                  style={{
                    width: `${cat.percentage}%`,
                    backgroundColor: cat.color,
                  }}
                ></div>
              </div>

              <div className="mt-2 flex items-center justify-between text-[11px] text-slate-500">
                <span>{cat.quantity_tons} Tons/day</span>
                <span className="text-emerald-700 font-medium">{cat.recyclability_pct}% Recyclable</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Smart Garbage Truck Live AI Camera Detection Stream */}
      <section className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-100">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping"></span>
              <h3 className="text-base font-bold text-navy-950 flex items-center gap-2">
                <ScanEye className="w-4 h-4 text-teal-600" />
                <span>Smart Garbage Truck Live AI Detection Feed</span>
              </h3>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Live automated waste classification from truck cameras (Vehicles GC-01 to GC-24).
            </p>
          </div>
          <Link
            href="/ai/detection"
            className="text-xs font-bold text-teal-600 hover:text-teal-700 inline-flex items-center gap-1"
          >
            <span>Open Truck Camera Feed</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {recentDetections.map((det) => (
            <div
              key={det.id}
              className="p-3.5 rounded-xl border border-slate-200 bg-white shadow-xs hover:border-teal-300 transition"
            >
              <div className="flex items-start justify-between">
                <div>
                  <span className="text-[10px] font-bold text-teal-700 uppercase tracking-wider bg-teal-50 px-1.5 py-0.5 rounded border border-teal-200">
                    {det.vehicle_code} • Ward {det.ward_number}
                  </span>
                  <h4 className="text-sm font-bold text-navy-900 mt-1">
                    {det.waste_category}
                  </h4>
                </div>
                <span className="text-xs font-extrabold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                  {Math.round(det.confidence * 100)}% Conf.
                </span>
              </div>

              <div className="mt-2 text-[11px] text-slate-500 flex items-center justify-between border-t border-slate-100 pt-2">
                <span>{det.location_name}</span>
                <span>{new Date(det.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Citizen Call to Action Banner */}
      <section className="bg-gradient-to-r from-teal-800 to-emerald-900 text-white rounded-xl p-6 sm:p-8 flex flex-col sm:flex-row items-center justify-between gap-6 shadow-md">
        <div className="space-y-1 text-center sm:text-left">
          <h3 className="text-xl font-bold">Community-Powered Continuous AI Training</h3>
          <p className="text-xs sm:text-sm text-teal-100 max-w-xl">
            Your contribution helps train our municipal AI vision models. Snap a photo of waste, verify the category,
            and help improve waste detection accuracy for all Chennai recycling plants.
          </p>
        </div>
        <Link
          href="/ai/contribute"
          className="px-5 py-2.5 bg-white text-teal-900 rounded-lg text-xs font-extrabold hover:bg-teal-50 transition shadow whitespace-nowrap"
        >
          Contribute Images Now
        </Link>
      </section>
    </div>
  );
}

function ResidentDashboardView({ publicData }: { publicData: any }) {
  const { user, collection_schedule, assigned_truck, ward_stats, my_grievances } = publicData;

  return (
    <div className="space-y-6">
      {/* Resident Welcome Banner */}
      <div className="bg-gradient-to-r from-navy-950 via-navy-900 to-teal-950 text-white rounded-2xl p-6 sm:p-8 shadow-sm border border-navy-800 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-2 max-w-2xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-teal-500/20 border border-teal-500/30 text-teal-300 text-xs font-semibold">
            <Building2 className="w-3.5 h-3.5" />
            <span>Verified Citizen Dashboard • {user?.area_name}</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
            Welcome, {user?.full_name}
          </h1>
          <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
            Neighborhood waste collection schedule, assigned collection truck tracking, and civic sanitation grievance redressal for your registered municipal ward.
          </p>
        </div>

        <div className="flex flex-wrap gap-2.5 shrink-0">
          <Link
            href="/grievances"
            className="inline-flex items-center gap-1.5 px-4 py-2.5 bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold rounded-xl shadow-sm transition"
          >
            <PlusCircle className="w-4 h-4" />
            <span>Report Grievance</span>
          </Link>
          <Link
            href="/live-detection"
            className="inline-flex items-center gap-1.5 px-4 py-2.5 bg-white/10 hover:bg-white/20 text-white text-xs font-semibold rounded-xl border border-white/20 transition"
          >
            <ScanEye className="w-4 h-4" />
            <span>AI Waste Camera</span>
          </Link>
        </div>
      </div>

      {/* Grid: Schedule, Assigned Truck, Ward Waste Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Collection Schedule */}
        <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <div className="w-9 h-9 rounded-xl bg-teal-50 text-teal-700 flex items-center justify-center">
              <Clock className="w-5 h-5" />
            </div>
            <span className="px-2.5 py-0.5 text-[10px] font-bold rounded-full bg-teal-100 text-teal-800 uppercase">
              {collection_schedule?.status?.replace("_", " ")}
            </span>
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-800">Collection Schedule</h3>
            <p className="text-xs text-slate-500 mt-0.5">{collection_schedule?.area_name}</p>
          </div>
          <div className="space-y-1.5 pt-2 border-t border-slate-100 text-xs">
            <div className="flex justify-between text-slate-600">
              <span>Shift:</span>
              <span className="font-semibold text-slate-800">{collection_schedule?.collection_shift}</span>
            </div>
            <div className="flex justify-between text-slate-600">
              <span>Timing:</span>
              <span className="font-semibold text-slate-800">{collection_schedule?.timing}</span>
            </div>
            <div className="flex justify-between text-slate-600">
              <span>Frequency:</span>
              <span className="font-semibold text-slate-800">{collection_schedule?.frequency}</span>
            </div>
          </div>
        </div>

        {/* Assigned Collection Truck */}
        <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <div className="w-9 h-9 rounded-xl bg-sky-50 text-sky-700 flex items-center justify-center">
              <Truck className="w-5 h-5" />
            </div>
            <span className={`px-2.5 py-0.5 text-[10px] font-bold rounded-full uppercase ${
              assigned_truck?.assigned ? "bg-sky-100 text-sky-800" : "bg-slate-100 text-slate-600"
            }`}>
              {assigned_truck?.status}
            </span>
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-800">Assigned Collection Truck</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              {assigned_truck?.assigned ? assigned_truck.vehicle_type : "No active truck in ward"}
            </p>
          </div>
          {assigned_truck?.assigned ? (
            <div className="space-y-1.5 pt-2 border-t border-slate-100 text-xs">
              <div className="flex justify-between text-slate-600">
                <span>Vehicle Code:</span>
                <span className="font-mono font-bold text-teal-800">{assigned_truck.vehicle_code}</span>
              </div>
              <div className="flex justify-between text-slate-600">
                <span>Location:</span>
                <span className="font-semibold text-slate-800">
                  {assigned_truck.latitude?.toFixed(4)}, {assigned_truck.longitude?.toFixed(4)}
                </span>
              </div>
              <div className="flex justify-between text-slate-600">
                <span>Data Mode:</span>
                <span className="font-bold text-amber-700 text-[10px] uppercase">
                  {assigned_truck.data_mode} ({assigned_truck.is_stale ? "Stale Signal" : "Scheduled Dispatch"})
                </span>
              </div>
            </div>
          ) : (
            <p className="text-xs text-slate-500 pt-2 border-t border-slate-100">
              No municipal truck is currently dispatched to your ward for this shift.
            </p>
          )}
        </div>

        {/* Ward Waste Performance */}
        <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm space-y-3">
          <div className="w-9 h-9 rounded-xl bg-emerald-50 text-emerald-700 flex items-center justify-center">
            <Leaf className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-800">Ward Segregation & Volume</h3>
            <p className="text-xs text-slate-500 mt-0.5">Municipal recycling metrics</p>
          </div>
          <div className="space-y-1.5 pt-2 border-t border-slate-100 text-xs">
            <div className="flex justify-between text-slate-600">
              <span>Daily Waste:</span>
              <span className="font-bold text-slate-800">{ward_stats?.daily_waste_tons} Tons / Day</span>
            </div>
            <div className="flex justify-between text-slate-600">
              <span>Segregation Rate:</span>
              <span className="font-bold text-emerald-700">{ward_stats?.segregation_efficiency}</span>
            </div>
            <div className="flex justify-between text-slate-600">
              <span>Ward Population:</span>
              <span className="font-semibold text-slate-800">{ward_stats?.population?.toLocaleString()}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Citizen Grievance Tracker Widget */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <FileText className="w-5 h-5 text-teal-600" />
            <h3 className="text-sm font-bold text-slate-800">My Submitted Sanitation Grievances</h3>
          </div>
          <Link
            href="/grievances"
            className="text-xs font-semibold text-teal-700 hover:text-teal-800 inline-flex items-center"
          >
            <span>View All & Escalate</span>
            <ChevronRight className="w-4 h-4 ml-0.5" />
          </Link>
        </div>

        {my_grievances && my_grievances.length > 0 ? (
          <div className="divide-y divide-slate-100">
            {my_grievances.map((g: any) => (
              <div key={g.id} className="p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="font-mono text-xs font-bold text-teal-800">{g.complaint_code}</span>
                    <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-slate-100 text-slate-700 uppercase">
                      {g.status?.replace("_", " ")}
                    </span>
                    {g.current_escalation_tier > 0 && (
                      <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-amber-50 text-amber-800 border border-amber-300">
                        Tier {g.current_escalation_tier} Escalated
                      </span>
                    )}
                  </div>
                  <h4 className="text-xs font-bold text-slate-800">{g.category?.replace(/_/g, " ").toUpperCase()}</h4>
                  <p className="text-xs text-slate-600 line-clamp-1">{g.description}</p>
                </div>
                <Link
                  href="/grievances"
                  className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg shrink-0 transition"
                >
                  Track / Follow Up
                </Link>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-8 text-center text-xs text-slate-500 space-y-2">
            <p>You have not filed any sanitation grievances yet.</p>
            <Link
              href="/grievances"
              className="inline-block text-teal-700 font-semibold hover:underline"
            >
              Report a civic sanitation issue in your street
            </Link>
          </div>
        )}
      </div>

      {/* Citizen Resources */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Link
          href="/live-detection"
          className="p-5 bg-gradient-to-br from-teal-50 to-white rounded-2xl border border-teal-100 hover:border-teal-300 transition shadow-sm space-y-2 group"
        >
          <div className="w-8 h-8 rounded-lg bg-teal-600 text-white flex items-center justify-center">
            <ScanEye className="w-4 h-4" />
          </div>
          <h4 className="text-xs font-bold text-slate-800 group-hover:text-teal-700">AI Waste Camera</h4>
          <p className="text-[11px] text-slate-500 leading-relaxed">
            Real-time computer vision classifier to check recyclability of plastic, paper, and food waste.
          </p>
        </Link>

        <Link
          href="/about-data"
          className="p-5 bg-gradient-to-br from-sky-50 to-white rounded-2xl border border-sky-100 hover:border-sky-300 transition shadow-sm space-y-2 group"
        >
          <div className="w-8 h-8 rounded-lg bg-sky-600 text-white flex items-center justify-center">
            <Trash2 className="w-4 h-4" />
          </div>
          <h4 className="text-xs font-bold text-slate-800 group-hover:text-sky-700">GCC 3-Bin Guide</h4>
          <p className="text-[11px] text-slate-500 leading-relaxed">
            Official guidelines for separating Green (Wet), Blue (Dry), and Red (Hazardous) household bins.
          </p>
        </Link>

        <Link
          href="/environmental"
          className="p-5 bg-gradient-to-br from-emerald-50 to-white rounded-2xl border border-emerald-100 hover:border-emerald-300 transition shadow-sm space-y-2 group"
        >
          <div className="w-8 h-8 rounded-lg bg-emerald-600 text-white flex items-center justify-center">
            <Leaf className="w-4 h-4" />
          </div>
          <h4 className="text-xs font-bold text-slate-800 group-hover:text-emerald-700">Environmental Savings</h4>
          <p className="text-[11px] text-slate-500 leading-relaxed">
            Calculate your household CO2e reduction, trees saved, and landfill diversion impact.
          </p>
        </Link>
      </div>
    </div>
  );
}