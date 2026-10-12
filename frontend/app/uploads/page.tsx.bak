"use client";

import React, { useState, useEffect, useRef } from "react";
import Image from "next/image";
import Link from "next/link";
import {
  UploadCloud,
  FileImage,
  CheckCircle2,
  AlertCircle,
  Clock,
  Check,
  X,
  Sparkles,
  MapPin,
  Tag,
  FileText,
  RefreshCw,
  Eye,
  Filter,
  ArrowRight,
  ShieldAlert,
  Info
} from "lucide-react";
import { api } from "@/lib/api";

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
  "Other Waste",
  "Unknown"
];

const STATUS_CONFIG: Record<string, { label: string; badgeClass: string; icon: any }> = {
  "PENDING_VERIFICATION": {
    label: "Pending Verification",
    badgeClass: "bg-amber-100 text-amber-900 border-amber-300",
    icon: Clock
  },
  "Approved": {
    label: "Approved",
    badgeClass: "bg-emerald-100 text-emerald-900 border-emerald-300",
    icon: Check
  },
  "Added to Dataset": {
    label: "Added to Dataset",
    badgeClass: "bg-teal-100 text-teal-900 border-teal-300",
    icon: CheckCircle2
  },
  "Used for Training": {
    label: "Used for Training",
    badgeClass: "bg-purple-100 text-purple-900 border-purple-300",
    icon: Sparkles
  },
  "Rejected": {
    label: "Rejected",
    badgeClass: "bg-rose-100 text-rose-900 border-rose-300",
    icon: X
  }
};

export default function UserUploadsPage() {
  // Upload Form State
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [objectLabel, setObjectLabel] = useState("");
  const [category, setCategory] = useState("Unknown");
  const [description, setDescription] = useState("");
  const [locationContext, setLocationContext] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);

  // My Uploads State
  const [uploads, setUploads] = useState<any[]>([]);
  const [statusFilter, setStatusFilter] = useState("All");
  const [isLoadingUploads, setIsLoadingUploads] = useState(true);
  const [previewModalImg, setPreviewModalImg] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadUploads();
  }, [statusFilter]);

  const loadUploads = async () => {
    try {
      setIsLoadingUploads(true);
      const res = await api.getUserUploads(statusFilter === "All" ? undefined : statusFilter);
      setUploads(res.uploads || []);
    } catch (err: any) {
      console.error("Failed to load user uploads:", err);
    } finally {
      setIsLoadingUploads(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setUploadError(null);
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setUploadError(null);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const validateAndSetFile = (file: File) => {
    const validExtensions = ["jpg", "jpeg", "png", "webp"];
    const ext = file.name.split(".").pop()?.toLowerCase() || "";
    
    if (!validExtensions.includes(ext)) {
      setUploadError("Invalid format. Please upload JPG, JPEG, PNG, or WEBP.");
      return;
    }

    if (file.size > 15 * 1024 * 1024) {
      setUploadError(`File is too large (${(file.size / (1024 * 1024)).toFixed(1)}MB). Maximum allowed size is 15MB.`);
      return;
    }

    setSelectedFile(file);
    const objectUrl = URL.createObjectURL(file);
    setPreviewUrl(objectUrl);

    // Auto suggest label from filename if blank
    if (!objectLabel) {
      const cleanName = file.name
        .replace(/\.[^/.]+$/, "")
        .replace(/[-_]/g, " ")
        .replace(/sample|waste|photo|image|\d+/gi, "")
        .trim();
      if (cleanName.length > 2) {
        setObjectLabel(cleanName.charAt(0).toUpperCase() + cleanName.slice(1));
      }
    }
  };

  const handleResetForm = () => {
    setSelectedFile(null);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(null);
    setObjectLabel("");
    setCategory("Unknown");
    setDescription("");
    setLocationContext("");
    setUploadError(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setUploadError("Please select or drop an image file.");
      return;
    }
    if (!objectLabel.trim()) {
      setUploadError("Please provide an object name (e.g., Mobile Phone, Battery, Plastic Bottle).");
      return;
    }

    try {
      setIsUploading(true);
      setUploadError(null);
      setUploadSuccess(null);

      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("object_label", objectLabel.trim());
      formData.append("category", category);
      if (description.trim()) formData.append("description", description.trim());
      if (locationContext.trim()) formData.append("location_context", locationContext.trim());

      const res = await api.uploadWasteImage(formData);
      setUploadSuccess(
        `Image "${res.upload?.original_filename}" uploaded successfully! Initial status set to PENDING_VERIFICATION for Municipal Admin review.`
      );

      handleResetForm();
      loadUploads();
    } catch (err: any) {
      console.error("Upload error:", err);
      setUploadError(err.message || "Failed to upload image. Please try again.");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-teal-50 rounded-xl text-teal-600 border border-teal-200">
              <UploadCloud className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl sm:text-2xl font-extrabold text-navy-950">
                Community Waste Dataset Upload
              </h1>
              <p className="text-xs sm:text-sm text-slate-500 mt-0.5">
                Upload real-world waste photos to expand and train Chennai&apos;s Municipal AI Model, especially for E-Waste, Smartphones, and Batteries.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Link
            href="/admin"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-navy-900 hover:bg-navy-800 text-white rounded-xl text-xs font-bold transition shadow-xs"
          >
            <span>Admin Verification Portal</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>

      {/* Upload Form Section */}
      <div className="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-sm space-y-6">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div>
            <h2 className="text-base font-bold text-navy-950 flex items-center gap-2">
              <FileImage className="w-4 h-4 text-teal-600" />
              <span>Contribute a Waste Image</span>
            </h2>
            <p className="text-xs text-slate-500">
              Images will be verified by municipal AI administrators before inclusion in the training dataset.
            </p>
          </div>
          <span className="text-[11px] font-semibold text-slate-400 bg-slate-50 px-2.5 py-1 rounded-full border border-slate-200">
            JPG, PNG, WEBP up to 15MB
          </span>
        </div>

        {uploadSuccess && (
          <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 text-xs flex items-center justify-between animate-in fade-in">
            <div className="flex items-center gap-2.5">
              <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />
              <div>
                <span className="font-bold block">Upload Staged Successfully!</span>
                <span>{uploadSuccess}</span>
              </div>
            </div>
            <button
              onClick={() => setUploadSuccess(null)}
              className="text-emerald-700 font-bold hover:text-emerald-900 text-xs ml-4"
            >
              Dismiss
            </button>
          </div>
        )}

        {uploadError && (
          <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2.5 animate-in fade-in">
            <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0" />
            <span>{uploadError}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left: Drag & Drop Zone / Image Preview */}
            <div className="lg:col-span-5 flex flex-col">
              <label className="text-xs font-bold text-slate-700 mb-2 block">
                Waste Image *
              </label>

              {previewUrl ? (
                <div className="relative w-full aspect-square rounded-2xl overflow-hidden border-2 border-teal-500 bg-slate-900 flex items-center justify-center group">
                  <img
                    src={previewUrl}
                    alt="Preview"
                    className="w-full h-full object-cover"
                  />
                  <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition flex items-center justify-center gap-3">
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      className="px-3 py-1.5 bg-white text-navy-950 rounded-lg text-xs font-bold shadow-md hover:bg-slate-100 transition"
                    >
                      Replace
                    </button>
                    <button
                      type="button"
                      onClick={handleResetForm}
                      className="px-3 py-1.5 bg-rose-600 text-white rounded-lg text-xs font-bold shadow-md hover:bg-rose-700 transition"
                    >
                      Remove
                    </button>
                  </div>
                </div>
              ) : (
                <div
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                  className="w-full aspect-square rounded-2xl border-2 border-dashed border-slate-300 hover:border-teal-500 bg-slate-50/50 hover:bg-teal-50/20 transition flex flex-col items-center justify-center p-6 text-center cursor-pointer group"
                >
                  <div className="w-14 h-14 rounded-2xl bg-teal-50 group-hover:bg-teal-100 text-teal-600 flex items-center justify-center mb-3 transition shadow-xs">
                    <UploadCloud className="w-7 h-7" />
                  </div>
                  <p className="text-xs sm:text-sm font-bold text-navy-950">
                    Click to browse or drag &amp; drop
                  </p>
                  <p className="text-[11px] text-slate-400 mt-1">
                    Supports JPG, JPEG, PNG, WEBP (Max 15MB)
                  </p>
                  <span className="mt-3 px-3 py-1 bg-white text-teal-700 border border-slate-200 rounded-lg text-xs font-semibold shadow-xs">
                    Select File
                  </span>
                </div>
              )}

              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/jpg,image/png,image/webp"
                onChange={handleFileChange}
                className="hidden"
              />
            </div>

            {/* Right: Metadata Inputs */}
            <div className="lg:col-span-7 space-y-4">
              {/* Object Name */}
              <div>
                <label className="text-xs font-bold text-slate-700 flex items-center gap-1.5 mb-1.5">
                  <Tag className="w-3.5 h-3.5 text-teal-600" />
                  <span>Object Name / Label *</span>
                </label>
                <input
                  type="text"
                  required
                  value={objectLabel}
                  onChange={(e) => setObjectLabel(e.target.value)}
                  placeholder="e.g. Mobile Phone, Broken Charger, PET Bottle, AA Battery"
                  className="w-full px-3.5 py-2.5 text-xs sm:text-sm rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500 bg-white"
                />
                <p className="text-[11px] text-slate-400 mt-1">
                  Examples: Smartphone, Feature phone, Power bank, USB Cable, Cardboard box.
                </p>
              </div>

              {/* Waste Category */}
              <div>
                <label className="text-xs font-bold text-slate-700 flex items-center gap-1.5 mb-1.5">
                  <FileText className="w-3.5 h-3.5 text-teal-600" />
                  <span>Waste Category (Optional if unknown)</span>
                </label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="w-full px-3.5 py-2.5 text-xs sm:text-sm rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500 bg-white"
                >
                  {STANDARD_CATEGORIES.map((cat) => (
                    <option key={cat} value={cat}>
                      {cat}
                    </option>
                  ))}
                </select>
                <p className="text-[11px] text-slate-400 mt-1">
                  Select &quot;Unknown&quot; if you are unsure; municipal administrators will categorize it correctly.
                </p>
              </div>

              {/* Location Context */}
              <div>
                <label className="text-xs font-bold text-slate-700 flex items-center gap-1.5 mb-1.5">
                  <MapPin className="w-3.5 h-3.5 text-teal-600" />
                  <span>Location / Neighborhood Found (Optional)</span>
                </label>
                <input
                  type="text"
                  value={locationContext}
                  onChange={(e) => setLocationContext(e.target.value)}
                  placeholder="e.g. Anna Nagar 2nd Avenue, Besant Nagar Beach, Royapuram MRF"
                  className="w-full px-3.5 py-2.5 text-xs sm:text-sm rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500 bg-white"
                />
              </div>

              {/* Description */}
              <div>
                <label className="text-xs font-bold text-slate-700 flex items-center gap-1.5 mb-1.5">
                  <Info className="w-3.5 h-3.5 text-teal-600" />
                  <span>Description / Condition Notes (Optional)</span>
                </label>
                <textarea
                  rows={3}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="e.g. Discarded phone with shattered LCD screen found in dry waste bin."
                  className="w-full px-3.5 py-2.5 text-xs sm:text-sm rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500 bg-white resize-none"
                />
              </div>

              {/* Submit & Reset Buttons */}
              <div className="flex items-center gap-3 pt-2">
                <button
                  type="submit"
                  disabled={isUploading || !selectedFile}
                  className="flex-1 py-3 bg-teal-600 hover:bg-teal-700 text-white rounded-xl text-xs sm:text-sm font-bold transition flex items-center justify-center gap-2 shadow-sm disabled:opacity-50"
                >
                  {isUploading ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Validating &amp; Staging Upload...</span>
                    </>
                  ) : (
                    <>
                      <UploadCloud className="w-4 h-4" />
                      <span>Submit Waste Image</span>
                    </>
                  )}
                </button>

                <button
                  type="button"
                  onClick={handleResetForm}
                  className="px-4 py-3 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs sm:text-sm font-bold transition"
                >
                  Reset
                </button>
              </div>
            </div>
          </div>
        </form>
      </div>

      {/* My Uploads History Section */}
      <div className="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-sm space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-slate-100">
          <div>
            <h2 className="text-base font-bold text-navy-950 flex items-center gap-2">
              <Clock className="w-4 h-4 text-teal-600" />
              <span>My Uploads History</span>
            </h2>
            <p className="text-xs text-slate-500">
              Track verification progress of your submitted images.
            </p>
          </div>

          {/* Status Filter Tabs */}
          <div className="flex flex-wrap items-center gap-1.5">
            {["All", "PENDING_VERIFICATION", "Added to Dataset", "Used for Training", "Rejected"].map(
              (st) => {
                const label = st === "All" ? "All Statuses" : STATUS_CONFIG[st]?.label || st;
                const active = statusFilter === st;
                return (
                  <button
                    key={st}
                    onClick={() => setStatusFilter(st)}
                    className={`px-3 py-1 rounded-lg text-xs font-bold transition ${
                      active
                        ? "bg-navy-900 text-white shadow-xs"
                        : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                    }`}
                  >
                    {label}
                  </button>
                );
              }
            )}
          </div>
        </div>

        {/* Uploads List Table / Grid */}
        {isLoadingUploads ? (
          <div className="py-16 text-center text-slate-400">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto text-teal-600 mb-2" />
            <span className="text-xs font-semibold">Loading your uploads...</span>
          </div>
        ) : uploads.length === 0 ? (
          <div className="py-16 text-center text-slate-400 space-y-2">
            <FileImage className="w-10 h-10 mx-auto text-slate-300" />
            <p className="text-xs font-bold text-slate-600">No uploads found</p>
            <p className="text-[11px] text-slate-400">
              {statusFilter !== "All"
                ? `No submissions found with status "${statusFilter}".`
                : "Contribute your first waste photo above to help improve municipal waste segregation."}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-200 text-slate-400 uppercase text-[10px] font-bold">
                  <th className="py-3 px-3">Image</th>
                  <th className="py-3 px-3">Object &amp; Category</th>
                  <th className="py-3 px-3">AI Pre-Scan</th>
                  <th className="py-3 px-3">Location Context</th>
                  <th className="py-3 px-3">Date Submitted</th>
                  <th className="py-3 px-3">Status</th>
                  <th className="py-3 px-3 text-right">Preview</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {uploads.map((u) => {
                  const statusInfo = STATUS_CONFIG[u.status] || {
                    label: u.status,
                    badgeClass: "bg-slate-100 text-slate-800 border-slate-200",
                    icon: Clock
                  };
                  const StatusIcon = statusInfo.icon;
                  const displayImgUrl = u.image_url.startsWith("http")
                    ? u.image_url
                    : `${(process.env.NEXT_PUBLIC_API_URL || "https://waste-22.onrender.com/api").replace(/\/api\/?$/, "")}${u.image_url}`;

                  return (
                    <tr key={u.id} className="hover:bg-slate-50 transition">
                      {/* Image Thumbnail */}
                      <td className="py-3 px-3">
                        <div
                          onClick={() => setPreviewModalImg(displayImgUrl)}
                          className="w-14 h-14 rounded-xl overflow-hidden border border-slate-200 bg-slate-100 cursor-pointer relative group flex-shrink-0"
                        >
                          <img
                            src={displayImgUrl}
                            alt={u.object_label}
                            className="w-full h-full object-cover group-hover:scale-105 transition"
                            onError={(e: any) => {
                              e.target.src = "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=150&auto=format&fit=crop";
                            }}
                          />
                          <div className="absolute inset-0 bg-black/30 opacity-0 group-hover:opacity-100 transition flex items-center justify-center text-white">
                            <Eye className="w-4 h-4" />
                          </div>
                        </div>
                      </td>

                      {/* Object & Category */}
                      <td className="py-3 px-3">
                        <span className="font-bold text-navy-950 block text-sm">
                          {u.object_label}
                        </span>
                        <div className="flex items-center gap-1.5 mt-0.5">
                          <span className="text-[11px] text-slate-500">User Tag:</span>
                          <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 text-[10px] font-semibold">
                            {u.category}
                          </span>
                        </div>
                        {u.verified_category && u.verified_category !== u.category && (
                          <span className="text-[10px] text-teal-700 font-semibold block mt-0.5">
                            ✓ Admin corrected to: {u.verified_category}
                          </span>
                        )}
                      </td>

                      {/* AI Pre-Scan */}
                      <td className="py-3 px-3">
                        {u.ai_predicted_label ? (
                          <div className="space-y-0.5">
                            <span className="font-medium text-slate-700 block">
                              {u.ai_predicted_label}
                            </span>
                            <span className="text-[10px] text-slate-400">
                              {u.ai_predicted_category} ({Math.round((u.ai_confidence || 0.85) * 100)}%)
                            </span>
                          </div>
                        ) : (
                          <span className="text-slate-400 text-[11px]">—</span>
                        )}
                      </td>

                      {/* Location */}
                      <td className="py-3 px-3 text-slate-600">
                        {u.location_context ? (
                          <span className="flex items-center gap-1">
                            <MapPin className="w-3 h-3 text-slate-400 flex-shrink-0" />
                            <span>{u.location_context}</span>
                          </span>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>

                      {/* Date */}
                      <td className="py-3 px-3 text-slate-500 text-[11px]">
                        {u.created_at ? u.created_at.substring(0, 10) : "Recently"}
                      </td>

                      {/* Status Badge */}
                      <td className="py-3 px-3">
                        <span
                          className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold border ${statusInfo.badgeClass}`}
                        >
                          <StatusIcon className="w-3 h-3" />
                          <span>{statusInfo.label}</span>
                        </span>
                        {u.status === "Rejected" && u.rejection_reason && (
                          <span className="text-[10px] text-rose-600 block mt-1 max-w-xs line-clamp-1" title={u.rejection_reason}>
                            Reason: {u.rejection_reason}
                          </span>
                        )}
                      </td>

                      {/* Zoom Button */}
                      <td className="py-3 px-3 text-right">
                        <button
                          onClick={() => setPreviewModalImg(displayImgUrl)}
                          className="p-1.5 text-slate-400 hover:text-navy-950 hover:bg-slate-100 rounded-lg transition"
                          title="View Full Resolution"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Full Resolution Preview Modal */}
      {previewModalImg && (
        <div
          onClick={() => setPreviewModalImg(null)}
          className="fixed inset-0 bg-black/80 backdrop-blur-xs z-50 flex items-center justify-center p-4 animate-in fade-in"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="bg-white rounded-2xl max-w-2xl w-full p-4 space-y-3 shadow-2xl relative"
          >
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <span className="text-xs font-bold text-navy-950">Image Full Resolution Preview</span>
              <button
                onClick={() => setPreviewModalImg(null)}
                className="text-slate-400 hover:text-slate-700 text-sm font-bold"
              >
                ✕
              </button>
            </div>
            <div className="relative w-full max-h-[70vh] rounded-xl overflow-hidden bg-slate-900 flex items-center justify-center">
              <img
                src={previewModalImg}
                alt="Enlarged Preview"
                className="max-h-[70vh] w-auto object-contain"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
