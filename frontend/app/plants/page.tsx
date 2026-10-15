"use client";

import React, { useEffect, useState } from "react";
import { 
  Factory, 
  MapPin, 
  Phone, 
  CheckCircle2, 
  AlertTriangle, 
  Wrench, 
  BarChart, 
  Search,
  Filter,
  ShieldCheck,
  Edit2
} from "lucide-react";
import { api } from "@/lib/api";
import { DataProvenanceBadge } from "@/components/DataProvenanceBadge";
import { ProtectedRoute } from "@/components/ProtectedRoute";

const PLANT_ROLES = [
  "system_admin",
  "waste_processing_plant_operator",
  "plant_operator",
  "environmental_engineer",
  "municipal_commissioner",
  "municipal_officer",
  "ai_admin"
];

export default function SegregationPlantsPage() {
  return (
    <ProtectedRoute allowedRoles={PLANT_ROLES} requiredPermissionTitle="Segregation Facility Operations">
      <SegregationPlantsContent />
    </ProtectedRoute>
  );
}

function SegregationPlantsContent() {
  const [plants, setPlants] = useState<any[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [search, setSearch] = useState("");
  const [selectedPlant, setSelectedPlant] = useState<any>(null);
  const [newInput, setNewInput] = useState<string>("");
  const [newStatus, setNewStatus] = useState<string>("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadPlants() {
      try {
        setLoading(true);
        const data = await api.getPlants();
        setPlants(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadPlants();
  }, []);

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPlant) return;
    try {
      await api.updatePlantStatus(
        selectedPlant.id,
        newStatus || selectedPlant.status,
        newInput ? parseFloat(newInput) : undefined
      );
      const updated = await api.getPlants();
      setPlants(updated);
      setSelectedPlant(null);
    } catch (err) {
      console.error(err);
    }
  };

  const filteredPlants = plants.filter((p) => {
    const matchesStatus = statusFilter === "all" || p.status === statusFilter;
    const matchesSearch =
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      p.facility_type.toLowerCase().includes(search.toLowerCase()) ||
      p.operator_name.toLowerCase().includes(search.toLowerCase());
    return matchesStatus && matchesSearch;
  });

  const totalCapacity = plants.reduce((acc, p) => acc + p.capacity_tpd, 0);
  const totalInput = plants.reduce((acc, p) => acc + p.current_input_tpd, 0);
  const avgUtil = totalCapacity > 0 ? Math.round((totalInput / totalCapacity) * 100) : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl sm:text-2xl font-extrabold text-navy-950">
              Waste Segregation & Recycling Facilities Directory
            </h1>
            <DataProvenanceBadge
              provenance={{
                source: "Greater Chennai Corporation Solid Waste Registry & Plant Weighbridges",
                dataset_name: "Metropolitan Waste Processing Infrastructure Master Register",
                last_updated: "07 September 2026",
                data_type: "HISTORICAL DATA",
                reliability: "Verified Municipal Infrastructure Register",
              }}
              metricTitle="Plant Infrastructure Directory"
            />
          </div>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Operational status, daily processing capacities, real-time input utilization, and accepted waste fractions across 12 Chennai recycling facilities.
          </p>
        </div>
      </div>

      {/* Aggregate Plant KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm">
          <span className="text-xs font-semibold text-slate-500">Total Processing Capacity</span>
          <p className="text-2xl font-extrabold text-navy-950 mt-1">
            {totalCapacity.toLocaleString()} <span className="text-xs font-normal">TPD</span>
          </p>
          <span className="text-[11px] text-slate-500">Combined rated capacity</span>
        </div>

        <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm">
          <span className="text-xs font-semibold text-slate-500">Current Daily Input</span>
          <p className="text-2xl font-extrabold text-teal-700 mt-1">
            {Math.round(totalInput).toLocaleString()} <span className="text-xs font-normal">TPD</span>
          </p>
          <span className="text-[11px] text-slate-500">Weighbridge incoming flow</span>
        </div>

        <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm">
          <span className="text-xs font-semibold text-slate-500">Overall Capacity Utilization</span>
          <p className="text-2xl font-extrabold text-navy-900 mt-1">
            {avgUtil}%
          </p>
          <span className="text-[11px] text-emerald-600 font-medium">Optimal Operating Band</span>
        </div>

        <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm">
          <span className="text-xs font-semibold text-slate-500">Active Facilities</span>
          <p className="text-2xl font-extrabold text-emerald-700 mt-1">
            {plants.filter(p => p.status === "active").length} <span className="text-xs font-normal text-slate-500">/ {plants.length}</span>
          </p>
          <span className="text-[11px] text-amber-600 font-medium">{plants.filter(p => p.status === "maintenance").length} under scheduled maintenance</span>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-white p-3.5 rounded-xl border border-slate-200 shadow-sm">
        <div className="relative w-full sm:w-72">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search facility name, type, operator..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-1 focus:ring-teal-500"
          />
        </div>

        <div className="flex items-center gap-1.5 w-full sm:w-auto overflow-x-auto text-xs">
          {["all", "active", "maintenance", "inactive"].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1.5 rounded-lg font-semibold capitalize transition ${
                statusFilter === st
                  ? "bg-navy-900 text-white shadow-sm"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Facilities Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {filteredPlants.map((plant) => {
          const isOverloaded = plant.utilization_pct > 85;
          const isMaint = plant.status === "maintenance";

          return (
            <div
              key={plant.id}
              className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm hover:border-teal-300 transition space-y-4 flex flex-col justify-between"
            >
              <div className="space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
                      {plant.facility_type}
                    </span>
                    <h3 className="text-sm font-extrabold text-navy-950 mt-1">
                      {plant.name}
                    </h3>
                  </div>

                  <span
                    className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                      plant.status === "active"
                        ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                        : plant.status === "maintenance"
                        ? "bg-amber-50 text-amber-700 border border-amber-200"
                        : "bg-slate-100 text-slate-600 border border-slate-200"
                    }`}
                  >
                    {plant.status}
                  </span>
                </div>

                {/* Capacity Utilization Progress */}
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-500 font-medium">Capacity Utilization:</span>
                    <span className={`font-extrabold ${isOverloaded ? "text-rose-600" : "text-emerald-700"}`}>
                      {plant.utilization_pct}%
                    </span>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                    <div
                      className={`h-2 rounded-full transition-all duration-300 ${
                        isOverloaded ? "bg-rose-500" : isMaint ? "bg-amber-500" : "bg-teal-600"
                      }`}
                      style={{ width: `${Math.min(100, plant.utilization_pct)}%` }}
                    ></div>
                  </div>
                  <div className="flex justify-between text-[11px] text-slate-400 pt-0.5">
                    <span>Input: {plant.current_input_tpd} TPD</span>
                    <span>Max: {plant.capacity_tpd} TPD</span>
                  </div>
                </div>

                {/* Accepted Waste Streams */}
                <div className="space-y-1">
                  <span className="text-[11px] font-semibold text-slate-500 block">Accepted Waste Streams:</span>
                  <div className="flex flex-wrap gap-1">
                    {plant.accepted_categories.split(',').map((c: string, idx: number) => (
                      <span key={idx} className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 text-[10px] font-medium">
                        {c.trim()}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Operator Details */}
                <div className="text-[11px] text-slate-500 space-y-1 border-t border-slate-100 pt-2">
                  <p><strong>Operator:</strong> {plant.operator_name}</p>
                  <p className="flex items-center gap-1">
                    <Phone className="w-3 h-3 text-slate-400" />
                    <span>{plant.contact_phone}</span>
                  </p>
                  <p className="truncate text-slate-400">{plant.address}</p>
                </div>
              </div>

              {/* Plant Operator Action Button */}
              <div className="pt-3 border-t border-slate-100 flex justify-end">
                <button
                  onClick={() => {
                    setSelectedPlant(plant);
                    setNewStatus(plant.status);
                    setNewInput(plant.current_input_tpd.toString());
                  }}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold transition"
                >
                  <Edit2 className="w-3 h-3" />
                  <span>Update Input / Status</span>
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Operator Update Modal */}
      {selectedPlant && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl max-w-md w-full p-6 shadow-2xl border border-slate-200 space-y-4">
            <h3 className="text-base font-bold text-navy-950">
              Update Plant: {selectedPlant.name}
            </h3>
            <p className="text-xs text-slate-500">
              Adjust live daily weighbridge throughput and operational status.
            </p>

            <form onSubmit={handleUpdate} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-700 font-semibold mb-1">
                  Current Input (Tons Per Day)
                </label>
                <input
                  type="number"
                  step="0.1"
                  value={newInput}
                  onChange={(e) => setNewInput(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 focus:outline-none focus:ring-1 focus:ring-teal-500 text-xs"
                />
              </div>

              <div>
                <label className="block text-slate-700 font-semibold mb-1">
                  Facility Operational Status
                </label>
                <select
                  value={newStatus}
                  onChange={(e) => setNewStatus(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 focus:outline-none focus:ring-1 focus:ring-teal-500 text-xs bg-white"
                >
                  <option value="active">Active</option>
                  <option value="maintenance">Maintenance</option>
                  <option value="inactive">Inactive</option>
                </select>
              </div>

              <div className="flex justify-end gap-2 pt-3">
                <button
                  type="button"
                  onClick={() => setSelectedPlant(null)}
                  className="px-3 py-1.5 bg-slate-100 text-slate-600 rounded-lg font-medium hover:bg-slate-200 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 bg-teal-600 text-white rounded-lg font-bold hover:bg-teal-700 transition"
                >
                  Save Changes
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}