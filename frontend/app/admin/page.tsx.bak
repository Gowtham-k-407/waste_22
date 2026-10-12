"use client";

import React, { useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import {
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Check,
  X,
  RefreshCw,
  Eye,
  Filter,
  Layers,
  Cpu,
  BookmarkCheck,
  Sparkles,
  MapPin,
  Tag,
  FileText,
  Search,
  ExternalLink,
  Edit3,
  Sliders,
  CheckSquare,
  Square,
  ChevronRight
} from "lucide-react";
import { api } from "@/lib/api";
import { AdminNav } from "@/components/AdminNav";

const STANDARD_CATEGORIES = [
  "E-Waste",
  "Mobile Phone",
  "Battery",
  "Electronic Components",
  "Plastic",
  "Paper",
  "Metal",
  "Glass",
  "Organic Waste",
  "Other Waste"
];

const REJECTION_REASONS = [
  "Blurry or low resolution photo",
  "Poor lighting or heavily obscured item",
  "Duplicate submission already in dataset",
  "Irrelevant or unidentifiable object",
  "Inappropriate or non-waste content"
];

export default function AdminDashboardPage() {
  const [overview, setOverview] = useState<any>(null);
  const [uploads, setUploads] = useState<any[]>([]);
  const [statusFilter, setStatusFilter] = useState("PENDING_VERIFICATION");
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [bannerMsg, setBannerMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Selection for Batch Actions
  const [selectedIds, setSelectedIds] = useState<number[]>([]);

  // Approval Modal with Category/Label Correction
  const [approvingUpload, setApprovingUpload] = useState<any>(null);
  const [approveCategory, setApproveCategory] = useState("");
  const [approveLabel, setApproveLabel] = useState("");
  const [approveNotes, setApproveNotes] = useState("");

  // Rejection Modal
  const [rejectingUpload, setRejectingUpload] = useState<any>(null);
  const [rejectReason, setRejectReason] = useState(REJECTION_REASONS[0]);
  const [rejectNotes, setRejectNotes] = useState("");

  // Batch Reject Modal
  const [showBatchRejectModal, setShowBatchRejectModal] = useState(false);
  const [batchRejectReason, setBatchRejectReason] = useState(REJECTION_REASONS[0]);

  // Image Zoom Modal
  const [zoomedImage, setZoomedImage] = useState<string | null>(null);

  useEffect(() => {
    loadDashboardData();
  }, [statusFilter]);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const [overviewRes, uploadsRes] = await Promise.all([
        api.getAdminOverview(),
        api.getAdminUploads(statusFilter),
      ]);
      setOverview(overviewRes.metrics || {});
      setUploads(uploadsRes.uploads || []);
      setSelectedIds([]);
    } catch (err: any) {
      console.error("Failed to load admin data", err);
      // Auto-fallback: if unauthenticated, authenticate as demo admin
      if (err.message && (err.message.includes("401") || err.message.includes("Admin authentication required"))) {
        await handleQuickAdminLogin();
      }
    } finally {
      setLoading(false);
    }
  };

  const handleQuickAdminLogin = async () => {
    try {
      const res = await api.adminLogin({
        email: "ai.lead@chennaiswm.gov.in",
        password: "Admin@123",
      });
      if (res.access_token) {
        localStorage.setItem("wastevision_token", res.access_token);
        localStorage.setItem("wastevision_user", JSON.stringify(res.user));
        localStorage.setItem("user_role", res.user.role);
        setBannerMsg({ type: "success", text: "Signed in as Lead AI Administrator (Dr. Ananya Natarajan)." });
        // Reload dashboard
        const [overviewRes, uploadsRes] = await Promise.all([
          api.getAdminOverview(),
          api.getAdminUploads(statusFilter),
        ]);
        setOverview(overviewRes.metrics || {});
        setUploads(uploadsRes.uploads || []);
      }
    } catch (e: any) {
      console.error("Quick admin login failed:", e);
    }
  };

  // Selection Toggles
  const handleToggleSelect = (id: number) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const handleSelectAll = () => {
    if (selectedIds.length === uploads.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(uploads.map((u) => u.id));
    }
  };

  // Open Approval Dialog (Prefilled with suggested labels or user labels)
  const openApproveModal = (u: any) => {
    setApprovingUpload(u);
    // If user labeled it mobile phone or battery, standardize to E-Waste
    let suggestedCat = u.ai_predicted_category || u.category;
    if (suggestedCat === "Unknown" || !suggestedCat) suggestedCat = "E-Waste";
    setApproveCategory(suggestedCat);
    setApproveLabel(u.ai_predicted_label || u.object_label);
    setApproveNotes(`Verified and added to dataset by Municipal AI Admin.`);
  };

  const handleConfirmApproval = async () => {
    if (!approvingUpload) return;
    try {
      setActionLoading(true);
      await api.approveAdminUpload(approvingUpload.id, {
        verified_category: approveCategory,
        verified_label: approveLabel,
        admin_notes: approveNotes,
      });
      setBannerMsg({
        type: "success",
        text: `Successfully approved "${approveLabel}" and added to verified ${approveCategory} dataset!`,
      });
      setApprovingUpload(null);
      loadDashboardData();
    } catch (err: any) {
      alert(err.message || "Failed to approve upload.");
    } finally {
      setActionLoading(false);
    }
  };

  // Open Rejection Dialog
  const openRejectModal = (u: any) => {
    setRejectingUpload(u);
    setRejectReason(REJECTION_REASONS[0]);
    setRejectNotes("");
  };

  const handleConfirmRejection = async () => {
    if (!rejectingUpload) return;
    try {
      setActionLoading(true);
      await api.rejectAdminUpload(rejectingUpload.id, {
        rejection_reason: rejectReason,
        admin_notes: rejectNotes,
      });
      setBannerMsg({
        type: "success",
        text: `Upload marked as rejected (${rejectReason}).`,
      });
      setRejectingUpload(null);
      loadDashboardData();
    } catch (err: any) {
      alert(err.message || "Failed to reject upload.");
    } finally {
      setActionLoading(false);
    }
  };

  // Batch Approve
  const handleBatchApprove = async () => {
    if (selectedIds.length === 0) return;
    if (!confirm(`Approve all ${selectedIds.length} selected images to the verified dataset?`)) return;
    try {
      setActionLoading(true);
      await api.batchApproveAdminUploads(selectedIds);
      setBannerMsg({
        type: "success",
        text: `Batch approved ${selectedIds.length} images to verified training dataset!`,
      });
      loadDashboardData();
    } catch (err: any) {
      alert(err.message || "Batch approval failed.");
    } finally {
      setActionLoading(false);
    }
  };

  // Batch Reject
  const handleConfirmBatchReject = async () => {
    if (selectedIds.length === 0) return;
    try {
      setActionLoading(true);
      await api.batchRejectAdminUploads(selectedIds, batchRejectReason);
      setBannerMsg({
        type: "success",
        text: `Batch rejected ${selectedIds.length} images.`,
      });
      setShowBatchRejectModal(false);
      loadDashboardData();
    } catch (err: any) {
      alert(err.message || "Batch rejection failed.");
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-8 pb-12">
      {/* Header & Sub-Nav */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-navy-950 flex items-center gap-2.5">
              <ShieldCheck className="w-7 h-7 text-teal-600" />
              <span>Municipal AI Administrator Dashboard</span>
            </h1>
            <p className="text-xs sm:text-sm text-slate-500 mt-1">
              Verify citizen waste submissions, curate standardized datasets, retrain YOLO models, and promote production weights for Greater Chennai Corporation.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleQuickAdminLogin}
              className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-bold transition flex items-center gap-1.5 border border-slate-300"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Refresh Admin Session</span>
            </button>
          </div>
        </div>

        <AdminNav pendingCount={overview?.pending_verification_count} />
      </div>

      {/* Notification Banner */}
      {bannerMsg && (
        <div
          className={`p-4 rounded-xl text-xs flex items-center justify-between animate-in fade-in ${
            bannerMsg.type === "success"
              ? "bg-emerald-50 border border-emerald-200 text-emerald-900"
              : "bg-rose-50 border border-rose-200 text-rose-900"
          }`}
        >
          <div className="flex items-center gap-2">
            {bannerMsg.type === "success" ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
            ) : (
              <AlertTriangle className="w-4 h-4 text-rose-600 flex-shrink-0" />
            )}
            <span className="font-semibold">{bannerMsg.text}</span>
          </div>
          <button
            onClick={() => setBannerMsg(null)}
            className="text-xs underline font-bold"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* 8 Overview KPI Metrics Cards */}
      <section className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
        {/* 1. Total User Uploads */}
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between space-y-1">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
            Total Uploads
          </span>
          <span className="text-2xl font-black text-navy-950">
            {overview?.total_user_uploads ?? "—"}
          </span>
          <span className="text-[10px] text-slate-500">Citizen submissions</span>
        </div>

        {/* 2. Pending Verification */}
        <div className="bg-amber-50/60 p-4 rounded-2xl border border-amber-200 shadow-xs flex flex-col justify-between space-y-1">
          <span className="text-[10px] font-bold text-amber-800 uppercase tracking-wider flex items-center gap-1">
            <Clock className="w-3 h-3 text-amber-600" />
            <span>Pending</span>
          </span>
          <span className="text-2xl font-black text-amber-950">
            {overview?.pending_verification_count ?? "—"}
          </span>
          <span className="text-[10px] text-amber-700 font-semibold">Requires review</span>
        </div>

        {/* 3. Approved Images */}
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between space-y-1">
          <span className="text-[10px] font-bold text-emerald-700 uppercase tracking-wider flex items-center gap-1">
            <Check className="w-3 h-3 text-emerald-600" />
            <span>Approved</span>
          </span>
          <span className="text-2xl font-black text-emerald-950">
            {overview?.approved_images_count ?? "—"}
          </span>
          <span className="text-[10px] text-emerald-700">Validated items</span>
        </div>

        {/* 4. Rejected Images */}
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between space-y-1">
          <span className="text-[10px] font-bold text-rose-700 uppercase tracking-wider flex items-center gap-1">
            <X className="w-3 h-3 text-rose-600" />
            <span>Rejected</span>
          </span>
          <span className="text-2xl font-black text-rose-950">
            {overview?.rejected_images_count ?? "—"}
          </span>
          <span className="text-[10px] text-rose-600">Low quality/blurry</span>
        </div>

        {/* 5. Total Dataset Images */}
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between space-y-1">
          <span className="text-[10px] font-bold text-teal-700 uppercase tracking-wider flex items-center gap-1">
            <Layers className="w-3 h-3 text-teal-600" />
            <span>Dataset Total</span>
          </span>
          <span className="text-2xl font-black text-navy-950">
            {overview?.total_dataset_images ?? "—"}
          </span>
          <Link href="/admin/dataset" className="text-[10px] text-teal-600 font-bold hover:underline">
            View dataset &rarr;
          </Link>
        </div>

        {/* 6. AI Models Trained */}
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between space-y-1">
          <span className="text-[10px] font-bold text-purple-700 uppercase tracking-wider flex items-center gap-1">
            <Cpu className="w-3 h-3 text-purple-600" />
            <span>Models Trained</span>
          </span>
          <span className="text-2xl font-black text-purple-950">
            {overview?.ai_models_trained_count ?? "—"}
          </span>
          <Link href="/admin/models" className="text-[10px] text-purple-600 font-bold hover:underline">
            Registry &rarr;
          </Link>
        </div>

        {/* 7. Active Model Version */}
        <div className="bg-teal-50/50 p-4 rounded-2xl border border-teal-200 shadow-xs flex flex-col justify-between space-y-1">
          <span className="text-[10px] font-bold text-teal-800 uppercase tracking-wider flex items-center gap-1">
            <BookmarkCheck className="w-3 h-3 text-teal-600" />
            <span>Active Model</span>
          </span>
          <span className="text-xl font-black text-teal-950 truncate" title={overview?.active_model_name}>
            {overview?.active_model_version ?? "v2.1"}
          </span>
          <span className="text-[10px] text-teal-700 font-semibold">
            {overview?.active_model_accuracy ? `${Math.round(overview.active_model_accuracy * 100)}% Accuracy` : "In Production"}
          </span>
        </div>

        {/* 8. Last Training Date */}
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between space-y-1">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
            Last Training
          </span>
          <span className="text-sm font-black text-navy-950 truncate mt-1">
            {overview?.last_training_date ?? "Recent"}
          </span>
          <Link href="/admin/model-training" className="text-[10px] text-teal-600 font-bold hover:underline">
            Retrain AI &rarr;
          </Link>
        </div>
      </section>

      {/* Image Verification Queue Section */}
      <section className="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-sm space-y-6">
        {/* Controls bar */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-slate-100">
          <div>
            <h2 className="text-base font-bold text-navy-950 flex items-center gap-2">
              <CheckSquare className="w-4 h-4 text-teal-600" />
              <span>Image Verification Queue</span>
            </h2>
            <p className="text-xs text-slate-500">
              Inspect citizen uploads, correct erroneous tags (e.g. Mobile Phone as Plastic &rarr; E-Waste), and approve into the official training dataset.
            </p>
          </div>

          {/* Status Filter Tabs & Batch Actions */}
          <div className="flex flex-wrap items-center gap-2">
            {["PENDING_VERIFICATION", "Added to Dataset", "Rejected", "All"].map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`px-3 py-1.5 rounded-xl text-xs font-bold transition ${
                  statusFilter === st
                    ? "bg-navy-900 text-white shadow-xs"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                {st === "PENDING_VERIFICATION"
                  ? "Pending Review"
                  : st === "Added to Dataset"
                  ? "Approved in Dataset"
                  : st}
              </button>
            ))}

            {selectedIds.length > 0 && (
              <div className="flex items-center gap-1.5 ml-2 pl-2 border-l border-slate-300">
                <button
                  onClick={handleBatchApprove}
                  disabled={actionLoading}
                  className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold transition shadow-xs flex items-center gap-1"
                >
                  <Check className="w-3.5 h-3.5" />
                  <span>Approve ({selectedIds.length})</span>
                </button>
                <button
                  onClick={() => setShowBatchRejectModal(true)}
                  disabled={actionLoading}
                  className="px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-bold transition shadow-xs flex items-center gap-1"
                >
                  <X className="w-3.5 h-3.5" />
                  <span>Reject ({selectedIds.length})</span>
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Uploads Queue Table */}
        {loading ? (
          <div className="py-20 text-center text-slate-400">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto text-teal-600 mb-2" />
            <span className="text-xs font-semibold">Loading verification queue...</span>
          </div>
        ) : uploads.length === 0 ? (
          <div className="py-20 text-center text-slate-400 space-y-2">
            <CheckCircle2 className="w-10 h-10 mx-auto text-emerald-500" />
            <p className="text-sm font-bold text-navy-950">Verification Queue is Clear!</p>
            <p className="text-xs text-slate-400">
              {statusFilter === "PENDING_VERIFICATION"
                ? "No pending waste images awaiting review. All contributions have been processed."
                : `No records found under filter "${statusFilter}".`}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-200 text-slate-400 uppercase text-[10px] font-bold">
                  <th className="py-3 px-3 w-10">
                    <button
                      onClick={handleSelectAll}
                      className="text-slate-500 hover:text-navy-950"
                    >
                      {selectedIds.length === uploads.length && uploads.length > 0 ? (
                        <CheckSquare className="w-4 h-4 text-teal-600" />
                      ) : (
                        <Square className="w-4 h-4" />
                      )}
                    </button>
                  </th>
                  <th className="py-3 px-3">Image Preview</th>
                  <th className="py-3 px-3">Citizen Submission</th>
                  <th className="py-3 px-3">AI Pre-Scan Hint</th>
                  <th className="py-3 px-3">Location &amp; Notes</th>
                  <th className="py-3 px-3">Status</th>
                  <th className="py-3 px-3 text-right">Verification Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {uploads.map((u) => {
                  const isSelected = selectedIds.includes(u.id);
                  const displayImgUrl = u.image_url.startsWith("http")
                    ? u.image_url
                    : `${(process.env.NEXT_PUBLIC_API_URL || "https://waste-22.onrender.com/api").replace(/\/api\/?$/, "")}${u.image_url}`;

                  return (
                    <tr
                      key={u.id}
                      className={`hover:bg-slate-50 transition ${
                        isSelected ? "bg-teal-50/30" : ""
                      }`}
                    >
                      {/* Checkbox */}
                      <td className="py-3 px-3">
                        <button
                          onClick={() => handleToggleSelect(u.id)}
                          className="text-slate-400 hover:text-navy-950"
                        >
                          {isSelected ? (
                            <CheckSquare className="w-4 h-4 text-teal-600" />
                          ) : (
                            <Square className="w-4 h-4" />
                          )}
                        </button>
                      </td>

                      {/* Image Preview with Zoom */}
                      <td className="py-3 px-3">
                        <div
                          onClick={() => setZoomedImage(displayImgUrl)}
                          className="w-16 h-16 rounded-xl overflow-hidden border border-slate-200 bg-slate-100 cursor-pointer relative group flex-shrink-0"
                          title="Click to zoom preview"
                        >
                          <img
                            src={displayImgUrl}
                            alt={u.object_label}
                            className="w-full h-full object-cover group-hover:scale-110 transition"
                            onError={(e: any) => {
                              e.target.src =
                                "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=150&auto=format&fit=crop";
                            }}
                          />
                          <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition flex items-center justify-center text-white">
                            <Eye className="w-4 h-4" />
                          </div>
                        </div>
                      </td>

                      {/* Citizen Submission Info */}
                      <td className="py-3 px-3 space-y-1">
                        <span className="font-bold text-navy-950 text-sm block">
                          {u.object_label}
                        </span>
                        <div className="flex items-center gap-1 text-[11px] text-slate-500">
                          <span>User Category:</span>
                          <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 font-semibold text-[10px]">
                            {u.category}
                          </span>
                        </div>
                        <span className="text-[10px] text-slate-400 block">
                          By: {u.user_name} • {u.created_at ? u.created_at.substring(0, 10) : "Recent"}
                        </span>
                      </td>

                      {/* AI Pre-Scan Hint */}
                      <td className="py-3 px-3">
                        {u.ai_predicted_label ? (
                          <div className="p-2 rounded-xl bg-slate-50 border border-slate-200 max-w-xs space-y-0.5">
                            <div className="flex items-center justify-between text-[11px]">
                              <span className="font-bold text-navy-950">
                                {u.ai_predicted_label}
                              </span>
                              <span className="font-extrabold text-teal-700">
                                {Math.round((u.ai_confidence || 0.85) * 100)}%
                              </span>
                            </div>
                            <span className="text-[10px] text-purple-700 font-semibold block">
                              AI Tag: {u.ai_predicted_category}
                            </span>
                          </div>
                        ) : (
                          <span className="text-slate-400 text-[11px]">No automated scan</span>
                        )}
                      </td>

                      {/* Location & Notes */}
                      <td className="py-3 px-3 max-w-xs">
                        {u.location_context && (
                          <span className="flex items-center gap-1 text-slate-600 text-[11px] mb-0.5">
                            <MapPin className="w-3 h-3 text-slate-400 flex-shrink-0" />
                            <span className="truncate">{u.location_context}</span>
                          </span>
                        )}
                        {u.description && (
                          <p className="text-[11px] text-slate-500 italic line-clamp-2" title={u.description}>
                            &ldquo;{u.description}&rdquo;
                          </p>
                        )}
                        {u.verified_category && (
                          <span className="text-[10px] text-teal-700 font-bold block mt-1">
                            ✓ Verified as: {u.verified_category} / {u.verified_label}
                          </span>
                        )}
                      </td>

                      {/* Status */}
                      <td className="py-3 px-3">
                        <span
                          className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold border ${
                            u.status === "PENDING_VERIFICATION"
                              ? "bg-amber-100 text-amber-900 border-amber-300"
                              : u.status === "Added to Dataset" || u.status === "Approved"
                              ? "bg-emerald-100 text-emerald-900 border-emerald-300"
                              : u.status === "Used for Training"
                              ? "bg-purple-100 text-purple-900 border-purple-300"
                              : "bg-rose-100 text-rose-900 border-rose-300"
                          }`}
                        >
                          {u.status === "PENDING_VERIFICATION" && <Clock className="w-2.5 h-2.5" />}
                          {u.status === "Added to Dataset" && <CheckCircle2 className="w-2.5 h-2.5" />}
                          {u.status === "Used for Training" && <Sparkles className="w-2.5 h-2.5" />}
                          {u.status === "Rejected" && <X className="w-2.5 h-2.5" />}
                          <span>{u.status === "PENDING_VERIFICATION" ? "Pending Review" : u.status}</span>
                        </span>
                        {u.rejection_reason && (
                          <span className="text-[10px] text-rose-600 block mt-1 line-clamp-1" title={u.rejection_reason}>
                            {u.rejection_reason}
                          </span>
                        )}
                      </td>

                      {/* Verification Actions */}
                      <td className="py-3 px-3 text-right">
                        <div className="inline-flex items-center gap-1.5 justify-end">
                          <button
                            onClick={() => openApproveModal(u)}
                            className="px-2.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold transition flex items-center gap-1 shadow-xs"
                            title="Approve and add to dataset"
                          >
                            <Check className="w-3.5 h-3.5" />
                            <span>Approve</span>
                          </button>

                          <button
                            onClick={() => openRejectModal(u)}
                            className="px-2.5 py-1.5 bg-slate-100 hover:bg-rose-100 text-slate-700 hover:text-rose-700 rounded-lg text-xs font-bold transition flex items-center gap-1 border border-slate-200"
                            title="Reject image"
                          >
                            <X className="w-3.5 h-3.5" />
                            <span>Reject</span>
                          </button>

                          <button
                            onClick={() => setZoomedImage(displayImgUrl)}
                            className="p-1.5 text-slate-400 hover:text-navy-950 hover:bg-slate-100 rounded-lg transition"
                            title="Zoom Preview"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Approve Modal (Allows Category & Label Correction) */}
      {approvingUpload && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-xs z-50 flex items-center justify-center p-4 animate-in fade-in">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 space-y-5 border border-slate-200 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                <h3 className="text-base font-bold text-navy-950">
                  Approve Image &amp; Add to Training Dataset
                </h3>
              </div>
              <button
                onClick={() => setApprovingUpload(null)}
                className="text-slate-400 hover:text-slate-600 font-bold"
              >
                ✕
              </button>
            </div>

            {/* Thumbnail + Details */}
            <div className="flex items-start gap-4 p-3 bg-slate-50 rounded-xl border border-slate-200">
              <div className="w-20 h-20 rounded-lg overflow-hidden bg-slate-900 flex-shrink-0">
                <img
                  src={
                    approvingUpload.image_url.startsWith("http")
                      ? approvingUpload.image_url
                      : `${(process.env.NEXT_PUBLIC_API_URL || "https://waste-22.onrender.com/api").replace(/\/api\/?$/, "")}${approvingUpload.image_url}`
                  }
                  alt={approvingUpload.object_label}
                  className="w-full h-full object-cover"
                />
              </div>
              <div className="space-y-1 text-xs">
                <span className="font-bold text-navy-950 block text-sm">
                  {approvingUpload.object_label}
                </span>
                <span className="text-slate-500 block">
                  User Category: <strong className="text-navy-950">{approvingUpload.category}</strong>
                </span>
                {approvingUpload.location_context && (
                  <span className="text-slate-500 block">
                    Found at: {approvingUpload.location_context}
                  </span>
                )}
              </div>
            </div>

            {/* Form to Correct Category / Label */}
            <div className="space-y-4">
              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">
                  Standardized Waste Category (Admin Correctable) *
                </label>
                <select
                  value={approveCategory}
                  onChange={(e) => setApproveCategory(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                >
                  {STANDARD_CATEGORIES.map((cat) => (
                    <option key={cat} value={cat}>
                      {cat}
                    </option>
                  ))}
                </select>
                <p className="text-[11px] text-slate-400 mt-1">
                  Example: If user marked a smartphone as &quot;Plastic&quot;, change to &quot;E-Waste&quot; or &quot;Mobile Phone&quot;.
                </p>
              </div>

              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">
                  Standardized Object Name *
                </label>
                <input
                  type="text"
                  required
                  value={approveLabel}
                  onChange={(e) => setApproveLabel(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">
                  Admin Verification Notes
                </label>
                <input
                  type="text"
                  value={approveNotes}
                  onChange={(e) => setApproveNotes(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
              <button
                onClick={() => setApprovingUpload(null)}
                className="px-4 py-2 text-xs font-bold text-slate-600 hover:bg-slate-100 rounded-lg transition"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmApproval}
                disabled={actionLoading}
                className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold transition shadow-sm flex items-center gap-1.5"
              >
                {actionLoading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
                <span>Confirm &amp; Add to Dataset</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Reject Modal */}
      {rejectingUpload && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-xs z-50 flex items-center justify-center p-4 animate-in fade-in">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 space-y-5 border border-slate-200 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-rose-600" />
                <h3 className="text-base font-bold text-navy-950">
                  Reject Waste Submission
                </h3>
              </div>
              <button
                onClick={() => setRejectingUpload(null)}
                className="text-slate-400 hover:text-slate-600 font-bold"
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-slate-600">
              Please specify the primary reason for rejecting this image submission.
            </p>

            <div className="space-y-4">
              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">
                  Rejection Reason *
                </label>
                <select
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-rose-500"
                >
                  {REJECTION_REASONS.map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">
                  Additional Admin Feedback (Optional)
                </label>
                <textarea
                  rows={2}
                  value={rejectNotes}
                  onChange={(e) => setRejectNotes(e.target.value)}
                  placeholder="e.g. Image is completely out of focus with dark shadows."
                  className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-rose-500 resize-none"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
              <button
                onClick={() => setRejectingUpload(null)}
                className="px-4 py-2 text-xs font-bold text-slate-600 hover:bg-slate-100 rounded-lg transition"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmRejection}
                disabled={actionLoading}
                className="px-5 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-bold transition shadow-sm flex items-center gap-1.5"
              >
                {actionLoading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <X className="w-3.5 h-3.5" />}
                <span>Reject Image</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Batch Reject Modal */}
      {showBatchRejectModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-xs z-50 flex items-center justify-center p-4 animate-in fade-in">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 space-y-5 border border-slate-200 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-rose-600" />
                <h3 className="text-base font-bold text-navy-950">
                  Batch Reject {selectedIds.length} Images
                </h3>
              </div>
              <button
                onClick={() => setShowBatchRejectModal(false)}
                className="text-slate-400 hover:text-slate-600 font-bold"
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-slate-600">
              Select the reason to apply to all {selectedIds.length} selected images:
            </p>

            <div>
              <select
                value={batchRejectReason}
                onChange={(e) => setBatchRejectReason(e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-rose-500"
              >
                {REJECTION_REASONS.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
              <button
                onClick={() => setShowBatchRejectModal(false)}
                className="px-4 py-2 text-xs font-bold text-slate-600 hover:bg-slate-100 rounded-lg transition"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmBatchReject}
                disabled={actionLoading}
                className="px-5 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-bold transition shadow-sm flex items-center gap-1.5"
              >
                <span>Reject All {selectedIds.length}</span>
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
              <span className="text-xs font-bold text-navy-950">High Resolution Inspection</span>
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
                alt="Zoomed Review"
                className="max-h-[75vh] w-auto object-contain"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}