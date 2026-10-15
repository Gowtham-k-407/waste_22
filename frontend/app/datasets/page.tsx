"use client";

import React, { useEffect, useState } from "react";
import { 
  Database, 
  Upload, 
  CheckCircle2, 
  FileSpreadsheet, 
  Link as LinkIcon, 
  Layers, 
  ExternalLink,
  ShieldCheck,
  RefreshCw,
  Table
} from "lucide-react";
import { api } from "@/lib/api";
import { DataProvenanceBadge } from "@/components/DataProvenanceBadge";
import { ProtectedRoute } from "@/components/ProtectedRoute";

export default function DatasetManagementPage() {
  const [sources, setSources] = useState<any[]>([]);
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [normalizing, setNormalizing] = useState(false);
  const [normalizationResult, setNormalizationResult] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadSources() {
      try {
        setLoading(true);
        const data = await api.getDatasetSources();
        setSources(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadSources();
  }, []);

  const handleUploadCsv = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!csvFile) return;
    try {
      setNormalizing(true);
      const fd = new FormData();
      fd.append("file", csvFile);
      fd.append("source_name", "Municipal CSV Import");
      const res = await api.uploadCsv(fd);
      setNormalizationResult(res);
    } catch (err) {
      console.error(err);
    } finally {
      setNormalizing(false);
    }
  };

  return (
    <ProtectedRoute allowedRoles={["system_admin", "ai_admin", "waste_management_data_analyst", "municipal_officer"]}>
      <div className="space-y-8">
        {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl sm:text-2xl font-extrabold text-navy-950">
              Data Connectors & Dataset Ingestion Architecture
            </h1>
            <DataProvenanceBadge
              provenance={{
                source: "Greater Chennai Corporation & Open Government Data (OGD) Connectors",
                dataset_name: "Automated Data Normalization Pipeline",
                last_updated: "07 September 2026",
                data_type: "HISTORICAL DATA",
                reliability: "Strict Schema-Validated Ingestion",
              }}
              metricTitle="Data Connector Pipeline"
            />
          </div>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Modular data connector framework integrating official GCC portals, CPCB benchmarks, IoT vehicle streams, and community uploads.
          </p>
        </div>
      </div>

      {/* Architecture Pipeline Diagram Card */}
      <div className="bg-gradient-to-r from-navy-950 to-teal-950 text-white p-6 rounded-2xl border border-navy-800 shadow-md">
        <h2 className="text-sm font-bold uppercase tracking-wider text-teal-400 mb-3">
          Modular Data Pipeline Architecture
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-7 gap-2 text-center text-[11px] font-mono">
          <div className="p-2.5 bg-white/10 rounded-lg border border-white/15">Data Source</div>
          <div className="hidden sm:flex items-center justify-center text-teal-400">→</div>
          <div className="p-2.5 bg-white/10 rounded-lg border border-white/15">Data Connector</div>
          <div className="hidden sm:flex items-center justify-center text-teal-400">→</div>
          <div className="p-2.5 bg-white/10 rounded-lg border border-white/15">Normalization</div>
          <div className="hidden sm:flex items-center justify-center text-teal-400">→</div>
          <div className="p-2.5 bg-teal-500/20 text-teal-300 rounded-lg border border-teal-500/40 font-bold">Central DB & Analytics</div>
        </div>
      </div>

      {/* Active Data Connectors Catalog */}
      <section className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm space-y-4">
        <h3 className="text-sm font-bold text-navy-950 uppercase tracking-wide flex items-center gap-2">
          <Layers className="w-4 h-4 text-teal-600" />
          <span>Active Data Connectors & Verified Sources</span>
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {sources.map((src) => (
            <div
              key={src.id}
              className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-slate-50 transition space-y-3 flex flex-col justify-between"
            >
              <div className="space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <h4 className="text-sm font-bold text-navy-950">
                    {src.name}
                  </h4>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                    src.dataset_type === "LIVE DATA" ? "bg-emerald-100 text-emerald-800" :
                    src.dataset_type === "AI-DETECTED DATA" ? "bg-teal-100 text-teal-800" :
                    src.dataset_type === "USER-CONTRIBUTED DATA" ? "bg-purple-100 text-purple-800" :
                    "bg-blue-100 text-blue-800"
                  }`}>
                    {src.dataset_type}
                  </span>
                </div>

                <p className="text-xs text-slate-600 leading-relaxed">
                  {src.description}
                </p>

                <div className="text-[11px] text-slate-500 space-y-1 pt-2 border-t border-slate-200">
                  <p><strong>Provider:</strong> {src.provider}</p>
                  <p><strong>Frequency:</strong> {src.update_frequency}</p>
                  <p><strong>Records:</strong> {src.row_count.toLocaleString()} rows</p>
                  <p><strong>License:</strong> {src.license}</p>
                </div>
              </div>

              <div className="pt-2 flex items-center justify-between text-[11px]">
                <span className="text-emerald-700 font-semibold flex items-center gap-1">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  <span>{src.reliability_status}</span>
                </span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* CSV Dataset Upload & Schema Normalization Tool */}
      <section className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div>
            <h3 className="text-sm font-bold text-navy-950 flex items-center gap-2">
              <FileSpreadsheet className="w-4 h-4 text-teal-600" />
              <span>Municipal CSV Dataset Ingestion & Column Normalizer</span>
            </h3>
            <p className="text-xs text-slate-500">
              Upload raw ward or weighbridge logs. The engine auto-maps column headers to the central municipal schema.
            </p>
          </div>
        </div>

        <form onSubmit={handleUploadCsv} className="flex flex-col sm:flex-row gap-3 items-center">
          <input
            type="file"
            accept=".csv, .txt"
            onChange={(e) => {
              if (e.target.files && e.target.files[0]) {
                setCsvFile(e.target.files[0]);
                setNormalizationResult(null);
              }
            }}
            className="w-full sm:w-auto text-xs px-3 py-2 rounded-lg border border-slate-200 focus:outline-none file:mr-3 file:py-1 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-slate-100 file:text-slate-700 hover:file:bg-slate-200"
          />

          <button
            type="submit"
            disabled={!csvFile || normalizing}
            className="w-full sm:w-auto px-5 py-2.5 bg-navy-900 hover:bg-navy-950 text-white rounded-lg text-xs font-bold transition flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {normalizing ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Normalizing & Validating Rows...</span>
              </>
            ) : (
              <>
                <Upload className="w-4 h-4" />
                <span>Parse & Normalize CSV</span>
              </>
            )}
          </button>
        </form>

        {/* Normalization Output Table Preview */}
        {normalizationResult && (
          <div className="mt-4 p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-3 animate-in fade-in">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-emerald-800 flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                <span>Successfully Normalized {normalizationResult.total_rows_parsed} Rows</span>
              </span>
              <span className="text-[11px] text-slate-500 font-mono">
                Headers Mapped: {normalizationResult.detected_headers?.join(", ")}
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-[11px] text-slate-600 bg-white rounded-lg border border-slate-200">
                <thead className="bg-slate-100 text-slate-700 font-bold border-b border-slate-200">
                  <tr>
                    <th className="p-2">Location</th>
                    <th className="p-2">Ward</th>
                    <th className="p-2">Zone</th>
                    <th className="p-2">Category</th>
                    <th className="p-2">Weight (kg)</th>
                    <th className="p-2">Vehicle</th>
                    <th className="p-2">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-mono">
                  {normalizationResult.preview_records?.slice(0, 5).map((r: any, idx: number) => (
                    <tr key={idx}>
                      <td className="p-2">{r.location_name}</td>
                      <td className="p-2">Ward {r.ward}</td>
                      <td className="p-2">Zone {r.zone}</td>
                      <td className="p-2 text-teal-700 font-bold">{r.waste_category}</td>
                      <td className="p-2">{r.waste_quantity_kg} kg</td>
                      <td className="p-2">{r.collection_vehicle_id}</td>
                      <td className="p-2 text-emerald-600 font-bold">{r.segregation_status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>
      </div>
    </ProtectedRoute>
  );
}