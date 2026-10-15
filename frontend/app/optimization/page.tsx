"use client";

import React, { useEffect, useState } from "react";
import { 
  Route, 
  Sparkles, 
  CheckCircle2, 
  Clock, 
  TrendingUp, 
  Fuel, 
  AlertTriangle, 
  ArrowRight,
  ShieldCheck,
  Check
} from "lucide-react";
import { api } from "@/lib/api";
import { DataProvenanceBadge } from "@/components/DataProvenanceBadge";
import { ProtectedRoute } from "@/components/ProtectedRoute";

const OPTIMIZATION_ROLES = [
  "system_admin",
  "municipal_officer",
  "waste_management_data_analyst",
  "municipal_commissioner",
  "assistant_engineer",
  "ai_admin"
];

export default function CollectionOptimizationPage() {
  return (
    <ProtectedRoute allowedRoles={OPTIMIZATION_ROLES} requiredPermissionTitle="Municipal Collection Optimization">
      <CollectionOptimizationContent />
    </ProtectedRoute>
  );
}

function CollectionOptimizationContent() {
  const [recommendations, setRecommendations] = useState<any[]>([]);
  const [implementedIds, setImplementedIds] = useState<number[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadRecs() {
      try {
        setLoading(true);
        const data = await api.getRecommendations();
        setRecommendations(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadRecs();
  }, []);

  const handleImplement = (id: number) => {
    setImplementedIds([...implementedIds, id]);
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl sm:text-2xl font-extrabold text-navy-950">
              Smart Garbage Collection Fleet & Route Optimization
            </h1>
            <DataProvenanceBadge
              provenance={{
                source: "GCC Swachh City AI Decision Support Engine",
                dataset_name: "GIS Dynamic Route & Facility Allocation Model",
                last_updated: "Real-Time Optimization Engine",
                data_type: "AI-DETECTED DATA",
                reliability: "High (Multi-Criteria GIS Optimization)",
              }}
              metricTitle="AI Route Optimization"
            />
          </div>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Predictive dispatch, plant load balancing, and collection frequency scheduling based on waste volume and road traffic data.
          </p>
        </div>
      </div>

      {/* Mandatory Recommendation Rule Notice */}
      <div className="p-4 bg-teal-50 rounded-xl border border-teal-200 text-xs text-teal-950 flex items-start gap-3 shadow-xs">
        <Sparkles className="w-5 h-5 text-teal-600 flex-shrink-0 mt-0.5" />
        <div>
          <span className="font-bold uppercase tracking-wider text-[11px] block">
            Advisory Classification: AI RECOMMENDATION
          </span>
          <p className="mt-0.5 leading-relaxed">
            Recommendations are algorithmic advisory proposals synthesized from IoT telemetry, ward volume surge patterns, and facility capacity margins.
            They are intended to support municipal officers and are not automatic government executive decisions.
          </p>
        </div>
      </div>

      {/* Primary KPI Impact Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm space-y-1">
          <span className="text-xs text-slate-500 font-semibold">Fleet Diesel Conservation</span>
          <p className="text-2xl font-extrabold text-emerald-700">~18.5% Savings</p>
          <p className="text-[11px] text-slate-400">Via dynamic off-peak scheduling</p>
        </div>

        <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm space-y-1">
          <span className="text-xs text-slate-500 font-semibold">Plant Processing Equilibrium</span>
          <p className="text-2xl font-extrabold text-teal-700">92% Balanced</p>
          <p className="text-[11px] text-slate-400">Diverts south overflow to Bio-CNG</p>
        </div>

        <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm space-y-1">
          <span className="text-xs text-slate-500 font-semibold">Bin Spillage Prevention</span>
          <p className="text-2xl font-extrabold text-sky-700">-44% Spill Incidents</p>
          <p className="text-[11px] text-slate-400">Mid-day commercial auxiliary pickups</p>
        </div>
      </div>

      {/* AI Recommendations List */}
      <div className="space-y-4">
        <h2 className="text-sm font-bold text-navy-950 uppercase tracking-wide">
          Active Municipal Dispatch Recommendations ({recommendations.length})
        </h2>

        <div className="space-y-4">
          {recommendations.map((rec) => {
            const isDone = implementedIds.includes(rec.id);

            return (
              <div
                key={rec.id}
                className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm hover:border-teal-300 transition space-y-4"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-100">
                  <div className="flex items-center gap-2">
                    <span className="px-2.5 py-1 rounded-full text-xs font-extrabold bg-teal-100 text-teal-900 border border-teal-300">
                      {rec.tag}
                    </span>
                    <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                      {rec.category}
                    </span>
                  </div>

                  <span className="text-xs text-emerald-700 font-extrabold">
                    AI Confidence: {Math.round(rec.confidence_score * 100)}%
                  </span>
                </div>

                <div className="space-y-2">
                  <h3 className="text-base font-bold text-navy-950">
                    {rec.title}
                  </h3>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    {rec.description}
                  </p>
                </div>

                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2 text-xs">
                  <div className="flex items-center gap-2 text-slate-700">
                    <span className="font-bold text-slate-500">Projected Impact:</span>
                    <span className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 font-semibold border border-emerald-200">
                      {rec.expected_benefit}
                    </span>
                  </div>

                  <button
                    onClick={() => handleImplement(rec.id)}
                    disabled={isDone}
                    className={`px-4 py-2 rounded-lg font-bold text-xs transition flex items-center gap-1.5 ${
                      isDone
                        ? "bg-slate-100 text-slate-400 border border-slate-200 cursor-default"
                        : "bg-teal-600 hover:bg-teal-700 text-white shadow-sm"
                    }`}
                  >
                    {isDone ? (
                      <>
                        <Check className="w-4 h-4 text-emerald-600" />
                        <span>Recommendation Dispatched</span>
                      </>
                    ) : (
                      <>
                        <CheckCircle2 className="w-4 h-4" />
                        <span>Dispatch to Field Officer</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}