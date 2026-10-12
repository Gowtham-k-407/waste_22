"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Layers,
  Search,
  Filter,
  Download,
  Trash2,
  Edit,
  Eye,
  RefreshCw,
  Sparkles,
  MapPin,
  CheckCircle2,
  ArrowRight,
  ShieldCheck,
  FolderOpen
} from "lucide-react";
import { api } from "@/lib/api";
import { AdminNav } from "@/components/AdminNav";

const CATEGORY_COLORS: Record<string, string> = {
  "E-Waste": "bg-purple-100 text-purple-800 border-purple-300",
  "Mobile Phone": "bg-indigo-100 text-indigo-800 border-indigo-300",
  "Battery": "bg-violet-100 text-violet-800 border-violet-300",
  "Electronic Components": "bg-purple-50 text-purple-900 border-purple-200",
  "Plastic": "bg-blue-100 text-blue-800 border-blue-300",
  "Paper": "bg-amber-100 text-amber-800 border-amber-300",
  "Metal": "bg-slate-200 text-slate-800 border-slate-400",
  "Glass": "bg-cyan-100 text-cyan-800 border-cyan-300",
  "Organic Waste": "bg-emerald-100 text-emerald-800 border-emerald-300",
  "Other Waste": "bg-slate-100 text-slate-700 border-slate-300",
};

export default function VerifiedDatasetPage() {
  const [datasetImages, setDatasetImages] = useState<any[]>([]);
  const [categoryCounts, setCategoryCounts] = useState<Record<string, number>>({});
  const [totalCount, setTotalCount] = useState(0);
  const [activeCategory, setActiveCategory] = useState("All");
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);

  // Edit Modal State
  const [editingItem, setEditingItem] = useState<any>(null);
  const [editCategory, setEditCategory] = useState("");
  const [editLabel, setEditLabel] = useState("");
  const [editSplit, setEditSplit] = useState("train");

  // Zoom Modal
  const [zoomedImage, setZoomedImage] = useState<string | null>(null);

  useEffect(() => {
    loadDataset();
  }, [activeCategory]);

  const loadDataset = async () => {
    try {
      setLoading(true);
      const res = await api.getVerifiedDataset(activeCategory, searchQuery);
      setDatasetImages(res.dataset_images || []);
      setCategoryCounts(res.category_counts || {});
      setTotalCount(res.total_dataset_count || 0);
    } catch (err: any) {
      console.error("Failed to load dataset:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadDataset();
  };

  const handleOpenEdit = (item: any) => {
    setEditingItem(item);
    setEditCategory(item.waste_category);
    setEditLabel(item.object_label);
    setEditSplit(item.split || "train");
  };

  const handleSaveEdit = async () => {
    if (!editingItem) return;
    try {
      await api.updateDatasetImage(editingItem.id, {
        waste_category: editCategory,
        object_label: editLabel,
        split: editSplit,
      });
      setEditingItem(null);
      loadDataset();
    } catch (err: any) {
      alert(err.message || "Failed to update dataset image.");
    }
  };

  const handleDeleteItem = async (id: number) => {
    if (!confirm("Are you sure you want to remove this verified image from the AI training dataset?")) return;
    try {
      await api.deleteDatasetImage(id);
      loadDataset();
    } catch (err: any) {
      alert(err.message || "Failed to delete image.");
    }
  };

  const handleExport = (format: "json" | "csv") => {
    const url = `${(process.env.NEXT_PUBLIC_API_URL || "https://waste-22.onrender.com/api").replace(/\/$/, "")}/admin/dataset/export?format=${format}`;
    window.open(url, "_blank");
  };

  const categoriesList = [
    "All",
    "Plastic",
    "Paper",
    "Metal",
    "Glass",
    "Organic Waste",
    "E-Waste",
    "Battery",
    "Mobile Phone",
    "Electronic Components",
    "Other Waste"
  ];

  return (
    <div className="max-w-7xl mx-auto space-y-8 pb-12">
      {/* Header & Sub-Nav */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-navy-950 flex items-center gap-2.5">
              <Layers className="w-7 h-7 text-teal-600" />
              <span>Verified Municipal Training Dataset</span>
            </h1>
            <p className="text-xs sm:text-sm text-slate-500 mt-1">
              Curated, verified solid waste image repository utilized by the YOLOv8 vision engine and smart collection trucks across Chennai.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => handleExport("json")}
              className="px-3 py-1.5 bg-white hover:bg-slate-50 text-slate-700 rounded-xl text-xs font-bold transition flex items-center gap-1.5 border border-slate-300 shadow-xs"
            >
              <Download className="w-3.5 h-3.5 text-slate-500" />
              <span>Export JSON</span>
            </button>
            <button
              onClick={() => handleExport("csv")}
              className="px-3 py-1.5 bg-navy-900 hover:bg-navy-800 text-white rounded-xl text-xs font-bold transition flex items-center gap-1.5 shadow-xs"
            >
              <Download className="w-3.5 h-3.5 text-teal-400" />
              <span>Export CSV</span>
            </button>
          </div>
        </div>

        <AdminNav />
      </div>

      {/* Category Breakdown Badges */}
      <section className="bg-white rounded-2xl p-5 border border-slate-200 shadow-xs space-y-3">
        <span className="text-xs font-bold text-navy-950 flex items-center gap-1.5">
          <FolderOpen className="w-4 h-4 text-teal-600" />
          <span>Category Distribution Breakdown ({totalCount} verified samples)</span>
        </span>

        <div className="flex flex-wrap gap-2">
          {categoriesList.map((cat) => {
            const count = cat === "All" ? totalCount : categoryCounts[cat] || 0;
            const isActive = activeCategory === cat;
            return (
              <button
                key={cat}
                onClick={() => setActiveCategory(cat)}
                className={`px-3 py-1.5 rounded-xl text-xs font-bold transition flex items-center gap-2 ${
                  isActive
                    ? "bg-teal-600 text-white shadow-sm"
                    : "bg-slate-50 text-slate-700 hover:bg-slate-100 border border-slate-200"
                }`}
              >
                <span>{cat}</span>
                <span
                  className={`px-2 py-0.2 rounded-full text-[10px] font-extrabold ${
                    isActive ? "bg-teal-800 text-teal-100" : "bg-slate-200 text-slate-800"
                  }`}
                >
                  {count}
                </span>
              </button>
            );
          })}
        </div>
      </section>

      {/* Search & Filter Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <form onSubmit={handleSearchSubmit} className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by object label, neighborhood, notes..."
            className="w-full pl-9 pr-4 py-2.5 bg-white rounded-xl border border-slate-300 text-xs focus:outline-none focus:ring-2 focus:ring-teal-500 shadow-xs"
          />
        </form>

        <div className="flex items-center gap-2">
          <Link
            href="/admin/model-training"
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-teal-600 hover:bg-teal-700 text-white rounded-xl text-xs font-bold transition shadow-xs"
          >
            <Sparkles className="w-4 h-4" />
            <span>Retrain Model with this Dataset &rarr;</span>
          </Link>
        </div>
      </div>

      {/* Dataset Images Grid */}
      {loading ? (
        <div className="py-24 text-center text-slate-400">
          <RefreshCw className="w-6 h-6 animate-spin mx-auto text-teal-600 mb-2" />
          <span className="text-xs font-semibold">Loading verified images...</span>
        </div>
      ) : datasetImages.length === 0 ? (
        <div className="bg-white rounded-2xl p-12 text-center border border-slate-200 text-slate-400 space-y-2">
          <Layers className="w-12 h-12 mx-auto text-slate-300" />
          <p className="text-sm font-bold text-navy-950">No verified images found</p>
          <p className="text-xs text-slate-400">
            {activeCategory !== "All"
              ? `No images found in category "${activeCategory}".`
              : "No verified dataset images matching your query."}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {datasetImages.map((img) => {
            const displayImgUrl = img.image_url.startsWith("http")
              ? img.image_url
              : `${(process.env.NEXT_PUBLIC_API_URL || "https://waste-22.onrender.com/api").replace(/\/api\/?$/, "")}${img.image_url}`;
            const badgeClass = CATEGORY_COLORS[img.waste_category] || "bg-slate-100 text-slate-700 border-slate-300";

            return (
              <div
                key={img.id}
                className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-xs hover:shadow-md transition flex flex-col justify-between group"
              >
                {/* Image Viewport */}
                <div
                  onClick={() => setZoomedImage(displayImgUrl)}
                  className="relative aspect-video w-full bg-slate-900 overflow-hidden cursor-pointer"
                >
                  <img
                    src={displayImgUrl}
                    alt={img.object_label}
                    className="w-full h-full object-cover group-hover:scale-105 transition duration-300"
                    onError={(e: any) => {
                      e.target.src =
                        "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=300&auto=format&fit=crop";
                    }}
                  />
                  <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition flex items-center justify-center text-white gap-2">
                    <Eye className="w-5 h-5" />
                    <span className="text-xs font-bold">Inspect</span>
                  </div>

                  {/* Split Tag (Train / Val / Test) */}
                  <span className="absolute top-2 left-2 px-2 py-0.5 rounded-md bg-navy-950/80 text-teal-300 text-[10px] font-mono uppercase font-bold backdrop-blur-xs">
                    {img.split}
                  </span>
                </div>

                {/* Content */}
                <div className="p-4 space-y-2 flex-1 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between gap-1 mb-1">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${badgeClass}`}>
                        {img.waste_category}
                      </span>
                      <span className="text-[10px] text-slate-400 font-mono">
                        {img.dataset_code}
                      </span>
                    </div>

                    <h3 className="font-extrabold text-navy-950 text-sm truncate" title={img.object_label}>
                      {img.object_label}
                    </h3>

                    {img.location_context && (
                      <span className="flex items-center gap-1 text-[11px] text-slate-500 mt-1 truncate">
                        <MapPin className="w-3 h-3 text-slate-400 flex-shrink-0" />
                        <span>{img.location_context}</span>
                      </span>
                    )}

                    {img.description && (
                      <p className="text-[11px] text-slate-400 line-clamp-2 mt-1">
                        {img.description}
                      </p>
                    )}
                  </div>

                  {/* Card Actions */}
                  <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
                    <span className="text-[10px] text-slate-400">
                      {img.verified_at ? img.verified_at.substring(0, 10) : "Verified"}
                    </span>

                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handleOpenEdit(img)}
                        className="p-1.5 text-slate-500 hover:text-teal-600 hover:bg-teal-50 rounded-lg transition"
                        title="Edit label or category"
                      >
                        <Edit className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => handleDeleteItem(img.id)}
                        className="p-1.5 text-slate-500 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition"
                        title="Remove from dataset"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Edit Category / Label Modal */}
      {editingItem && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-xs z-50 flex items-center justify-center p-4 animate-in fade-in">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl border border-slate-200">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <h3 className="text-sm font-bold text-navy-950 flex items-center gap-2">
                <Edit className="w-4 h-4 text-teal-600" />
                <span>Edit Dataset Image Annotations</span>
              </h3>
              <button
                onClick={() => setEditingItem(null)}
                className="text-slate-400 hover:text-slate-600 font-bold"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">
                  Waste Category
                </label>
                <select
                  value={editCategory}
                  onChange={(e) => setEditCategory(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500"
                >
                  {categoriesList
                    .filter((c) => c !== "All")
                    .map((cat) => (
                      <option key={cat} value={cat}>
                        {cat}
                      </option>
                    ))}
                </select>
              </div>

              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">
                  Object Name / Specific Item
                </label>
                <input
                  type="text"
                  value={editLabel}
                  onChange={(e) => setEditLabel(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">
                  Dataset Split
                </label>
                <select
                  value={editSplit}
                  onChange={(e) => setEditSplit(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500"
                >
                  <option value="train">Train (70%)</option>
                  <option value="val">Validation (15%)</option>
                  <option value="test">Test (15%)</option>
                </select>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
              <button
                onClick={() => setEditingItem(null)}
                className="px-4 py-2 text-xs font-bold text-slate-600 hover:bg-slate-100 rounded-lg transition"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveEdit}
                className="px-5 py-2 bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold rounded-lg transition shadow-sm"
              >
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Zoom Modal */}
      {zoomedImage && (
        <div
          onClick={() => setZoomedImage(null)}
          className="fixed inset-0 bg-black/80 backdrop-blur-xs z-50 flex items-center justify-center p-4 animate-in fade-in cursor-zoom-out"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="bg-white rounded-2xl max-w-3xl w-full p-4 space-y-3 shadow-2xl relative"
          >
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <span className="text-xs font-bold text-navy-950">Verified Dataset Inspection</span>
              <button
                onClick={() => setZoomedImage(null)}
                className="text-slate-400 hover:text-slate-700 font-bold text-sm"
              >
                ✕
              </button>
            </div>
            <div className="relative w-full max-h-[75vh] rounded-xl overflow-hidden bg-slate-950 flex items-center justify-center">
              <img
                src={zoomedImage}
                alt="Enlarged Review"
                className="max-h-[75vh] w-auto object-contain"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
