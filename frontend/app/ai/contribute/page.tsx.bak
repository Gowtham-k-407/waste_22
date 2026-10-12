"use client";

import React, { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { 
  UploadCloud, 
  Camera, 
  Video, 
  VideoOff, 
  CheckCircle2, 
  AlertCircle, 
  AlertTriangle, 
  Sparkles, 
  ShieldCheck, 
  Award, 
  RefreshCw, 
  MapPin, 
  Tag, 
  FileText, 
  Clock, 
  ArrowRight,
  Eye,
  Info,
  Check
} from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

const WASTE_CATEGORIES = [
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

export default function ContributeToImproveAIPage() {
  const { user, isAuthenticated } = useAuth();

  // Mode: "upload" or "camera"
  const [inputMode, setInputMode] = useState<"upload" | "camera">("upload");

  // Image & Preview
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  // Form inputs
  const [objectName, setObjectName] = useState("");
  const [category, setCategory] = useState("E-Waste");
  const [description, setDescription] = useState("");
  const [locationContext, setLocationContext] = useState("");
  const [contributorName, setContributorName] = useState("");

  // UI state
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<any>(null);

  // WebCam state
  const [cameraActive, setCameraActive] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Recent Uploads History
  const [recentUploads, setRecentUploads] = useState<any[]>([]);
  const [loadingRecent, setLoadingRecent] = useState(false);

  useEffect(() => {
    if (user?.full_name) {
      setContributorName(user.full_name);
    } else if (user?.username) {
      setContributorName(user.username);
    } else {
      setContributorName("Citizen Contributor");
    }
    loadRecentUploads();

    return () => {
      stopCamera();
    };
  }, [user]);

  const loadRecentUploads = async () => {
    try {
      setLoadingRecent(true);
      const res = await api.getUserUploads();
      setRecentUploads((res.uploads || []).slice(0, 5));
    } catch (e) {
      console.error("Could not load recent uploads", e);
    } finally {
      setLoadingRecent(false);
    }
  };

  const startCamera = async () => {
    setCameraError(null);
    try {
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: "environment" },
        });
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.play().catch(() => {});
        }
        setCameraActive(true);
      } else {
        setCameraError("Camera device is not supported in this browser. Please use the file upload option.");
      }
    } catch (err: any) {
      console.error("Camera access error:", err);
      setCameraError(
        err.name === "NotAllowedError"
          ? "Camera permission denied. Please allow camera access in your browser settings to take photos."
          : "Could not access the camera device. Please ensure no other application is using it."
      );
      setCameraActive(false);
    }
  };

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setCameraActive(false);
  };

  const snapPhoto = async () => {
    if (!videoRef.current) return;
    const video = videoRef.current;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.92));
    if (!blob) return;

    const file = new File([blob], `waste_camera_${Date.now()}.jpg`, { type: "image/jpeg" });
    processSelectedFile(file);
    stopCamera();
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setUploadError(null);
    if (e.target.files && e.target.files[0]) {
      processSelectedFile(e.target.files[0]);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setUploadError(null);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processSelectedFile(e.dataTransfer.files[0]);
    }
  };

  const processSelectedFile = (file: File) => {
    setUploadError(null);
    setUploadSuccess(null);

    // Validate extension
    const validExtensions = ["jpg", "jpeg", "png", "webp"];
    const ext = file.name.split(".").pop()?.toLowerCase() || "";
    if (!validExtensions.includes(ext)) {
      setUploadError("Unsupported image format. Allowed formats are JPG, JPEG, PNG, and WEBP.");
      return;
    }

    // Validate size (max 15MB)
    if (file.size > 15 * 1024 * 1024) {
      setUploadError(`File is too large (${(file.size / (1024 * 1024)).toFixed(1)}MB). The maximum allowed size is 15MB.`);
      return;
    }

    setSelectedFile(file);
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);

    // If objectName is empty, attempt intelligent prefill from filename
    if (!objectName) {
      const cleanName = file.name
        .replace(/\.[^/.]+$/, "")
        .replace(/[-_]/g, " ")
        .replace(/image|photo|waste|sample|img|\d+/gi, "")
        .trim();
      if (cleanName.length > 2) {
        setObjectName(cleanName.charAt(0).toUpperCase() + cleanName.slice(1));
      }
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(null);
    setObjectName("");
    setCategory("E-Waste");
    setDescription("");
    setLocationContext("");
    setUploadError(null);
    setUploadSuccess(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
    if (inputMode === "camera") {
      startCamera();
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!selectedFile) {
      setUploadError("Please select or capture a waste image before submitting.");
      return;
    }

    if (!objectName.trim()) {
      setUploadError("Please enter an object name (e.g. Mobile Phone, Battery, Plastic Bottle).");
      return;
    }

    try {
      setIsUploading(true);
      setUploadError(null);
      setUploadSuccess(null);

      // Build real multipart/form-data request
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("image", selectedFile); // support both field names
      formData.append("object_label", objectName.trim());
      formData.append("objectName", objectName.trim());
      formData.append("category", category);
      if (description.trim()) {
        formData.append("description", description.trim());
      }
      if (locationContext.trim()) {
        formData.append("location_context", locationContext.trim());
      }

      // Send to real backend API: POST /api/uploads
      const response = await api.uploadWasteImage(formData);

      if (response && response.success) {
        setUploadSuccess(response);
        // Refresh recent uploads list
        loadRecentUploads();
      } else {
        throw new Error(response?.message || "Server did not acknowledge upload.");
      }
    } catch (err: any) {
      console.error("Contribution upload error:", err);
      setUploadError(
        err.message || "Failed to upload image. Please check your network connection and try again."
      );
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-8 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-teal-50 border border-teal-200 text-teal-800 text-xs font-bold mb-2">
            <Sparkles className="w-3.5 h-3.5 text-teal-600" />
            <span>Continuous AI Improvement Pipeline • Citizen AI</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-navy-950">
            Contribute to Improve AI
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1 max-w-2xl">
            Upload waste photos to train and improve Chennai&apos;s municipal AI detection models. All submissions are staged with status <strong className="text-amber-700">PENDING_VERIFICATION</strong> and reviewed by municipal administrators before entering the training dataset.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link
            href="/admin"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-navy-900 hover:bg-navy-800 text-white rounded-xl text-xs font-bold transition shadow-xs"
          >
            <ShieldCheck className="w-3.5 h-3.5 text-teal-400" />
            <span>Admin Verification Queue</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>

      {/* Main Contribution Box */}
      <div className="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-sm space-y-6">
        {/* Step Progression Bar */}
        <div className="grid grid-cols-4 gap-2 text-center text-[11px] font-bold border-b border-slate-100 pb-4">
          <div className={`p-2 rounded-lg ${!selectedFile ? "bg-teal-50 text-teal-900 font-extrabold" : "text-slate-400"}`}>
            1. Select Image
          </div>
          <div className={`p-2 rounded-lg ${selectedFile && !uploadSuccess ? "bg-teal-50 text-teal-900 font-extrabold" : "text-slate-400"}`}>
            2. Enter Details
          </div>
          <div className={`p-2 rounded-lg ${isUploading ? "bg-purple-50 text-purple-900 animate-pulse font-extrabold" : "text-slate-400"}`}>
            3. Upload to API
          </div>
          <div className={`p-2 rounded-lg ${uploadSuccess ? "bg-emerald-50 text-emerald-900 font-extrabold" : "text-slate-400"}`}>
            4. Pending Review
          </div>
        </div>

        {/* Error Alert */}
        {uploadError && (
          <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-900 text-xs flex items-center justify-between animate-in fade-in">
            <div className="flex items-center gap-2.5">
              <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0" />
              <span className="font-semibold">{uploadError}</span>
            </div>
            <button
              type="button"
              onClick={() => setUploadError(null)}
              className="text-xs text-rose-700 underline font-bold"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Success Alert */}
        {uploadSuccess ? (
          <div className="p-6 rounded-2xl bg-emerald-50 border border-emerald-200 text-center space-y-4 animate-in zoom-in-95">
            <div className="w-14 h-14 rounded-full bg-emerald-600 text-white flex items-center justify-center mx-auto shadow-md">
              <Check className="w-7 h-7" />
            </div>

            <div className="space-y-1">
              <h3 className="text-lg font-black text-emerald-950">
                Image Uploaded Successfully!
              </h3>
              <p className="text-xs text-emerald-800 max-w-md mx-auto">
                {uploadSuccess.message || "Your contribution has been staged and is now waiting for administrative verification."}
              </p>
            </div>

            {/* Upload Metadata Preview */}
            <div className="p-4 bg-white rounded-xl border border-emerald-200 text-left text-xs max-w-lg mx-auto flex items-center gap-4">
              {uploadSuccess.upload?.imageUrl && (
                <div className="w-16 h-16 rounded-lg overflow-hidden bg-slate-100 flex-shrink-0 border border-slate-200">
                  <img
                    src={uploadSuccess.upload.imageUrl.startsWith("http") ? uploadSuccess.upload.imageUrl : `${(process.env.NEXT_PUBLIC_API_URL || "https://waste-22.onrender.com/api").replace(/\/api\/?$/, "")}${uploadSuccess.upload.imageUrl}`}
                    alt="Uploaded waste"
                    className="w-full h-full object-cover"
                  />
                </div>
              )}
              <div className="space-y-1 flex-1">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-navy-950 text-sm">
                    {uploadSuccess.upload?.objectName || uploadSuccess.upload?.object_label || objectName}
                  </span>
                  <span className="px-2 py-0.5 rounded-full bg-amber-100 text-amber-900 border border-amber-300 text-[10px] font-extrabold uppercase">
                    {uploadSuccess.upload?.status || "PENDING_VERIFICATION"}
                  </span>
                </div>
                <div className="text-[11px] text-slate-500">
                  Category: <strong className="text-navy-950">{uploadSuccess.upload?.category || category}</strong>
                </div>
                <div className="text-[10px] text-slate-400">
                  Upload ID: {uploadSuccess.upload?.upload_id || uploadSuccess.upload?.id}
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
              <button
                type="button"
                onClick={handleReset}
                className="px-5 py-2.5 bg-teal-600 hover:bg-teal-700 text-white rounded-xl text-xs font-bold transition shadow-sm"
              >
                Contribute Another Photo
              </button>
              <Link
                href="/admin"
                className="px-5 py-2.5 bg-navy-900 hover:bg-navy-950 text-white rounded-xl text-xs font-bold transition shadow-sm inline-flex items-center gap-1.5"
              >
                <span>View in Admin Dashboard</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Mode Selection Tabs (Upload vs Camera) */}
            <div className="flex justify-center">
              <div className="inline-flex p-1 bg-slate-100 rounded-xl text-xs font-bold">
                <button
                  type="button"
                  onClick={() => {
                    setInputMode("upload");
                    stopCamera();
                  }}
                  className={`px-4 py-2 rounded-lg transition flex items-center gap-1.5 ${
                    inputMode === "upload"
                      ? "bg-white text-navy-950 shadow-xs"
                      : "text-slate-600 hover:text-navy-900"
                  }`}
                >
                  <UploadCloud className="w-4 h-4 text-teal-600" />
                  <span>Choose Image File</span>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setInputMode("camera");
                    startCamera();
                  }}
                  className={`px-4 py-2 rounded-lg transition flex items-center gap-1.5 ${
                    inputMode === "camera"
                      ? "bg-white text-navy-950 shadow-xs"
                      : "text-slate-600 hover:text-navy-900"
                  }`}
                >
                  <Camera className="w-4 h-4 text-teal-600" />
                  <span>Use Camera / WebCam</span>
                </button>
              </div>
            </div>

            {/* Main Form Grid: Preview on Left, Metadata on Right */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
              {/* Left Column: File Dropzone OR WebCam Viewport */}
              <div className="lg:col-span-5 space-y-3">
                <label className="text-xs font-bold text-slate-700 block">
                  Waste Image *
                </label>

                {previewUrl ? (
                  <div className="relative w-full aspect-square rounded-2xl overflow-hidden border-2 border-teal-500 bg-slate-900 flex items-center justify-center group shadow-xs">
                    <img
                      src={previewUrl}
                      alt="Selected waste preview"
                      className="w-full h-full object-cover"
                    />
                    <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition flex items-center justify-center gap-3">
                      <button
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        className="px-3 py-1.5 bg-white text-navy-950 rounded-lg text-xs font-bold shadow-md hover:bg-slate-100 transition"
                      >
                        Change Photo
                      </button>
                      <button
                        type="button"
                        onClick={handleReset}
                        className="px-3 py-1.5 bg-rose-600 text-white rounded-lg text-xs font-bold shadow-md hover:bg-rose-700 transition"
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                ) : inputMode === "camera" ? (
                  <div className="relative w-full aspect-square rounded-2xl overflow-hidden bg-slate-950 border border-slate-800 flex flex-col items-center justify-center shadow-inner">
                    <video
                      ref={videoRef}
                      playsInline
                      muted
                      className={`w-full h-full object-cover ${cameraActive ? "block" : "hidden"}`}
                    />

                    {!cameraActive ? (
                      <div className="text-center p-6 space-y-3 text-slate-400">
                        <div className="w-12 h-12 rounded-full bg-slate-800 text-slate-400 flex items-center justify-center mx-auto">
                          <Camera className="w-6 h-6" />
                        </div>
                        <div>
                          <p className="text-xs font-bold text-white">Camera Offline</p>
                          <p className="text-[11px] text-slate-400 mt-1 max-w-xs mx-auto">
                            Click below to start your webcam or switch to file upload.
                          </p>
                        </div>
                        <button
                          type="button"
                          onClick={startCamera}
                          className="px-4 py-2 bg-teal-600 hover:bg-teal-500 text-white rounded-xl text-xs font-bold transition shadow-sm inline-flex items-center gap-1.5"
                        >
                          <Video className="w-4 h-4" />
                          <span>Activate Camera</span>
                        </button>
                      </div>
                    ) : (
                      <div className="absolute bottom-4 inset-x-0 flex justify-center z-10">
                        <button
                          type="button"
                          onClick={snapPhoto}
                          className="px-5 py-2.5 bg-teal-600 hover:bg-teal-500 text-white font-extrabold text-xs rounded-full shadow-lg border-2 border-white flex items-center gap-2 transition transform hover:scale-105"
                        >
                          <Camera className="w-4 h-4" />
                          <span>Snap Photo</span>
                        </button>
                      </div>
                    )}
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
                      Click to choose or drag &amp; drop
                    </p>
                    <p className="text-[11px] text-slate-400 mt-1">
                      JPG, JPEG, PNG, WEBP (Max 15MB)
                    </p>
                    <span className="mt-3 px-3 py-1 bg-white text-teal-700 border border-slate-200 rounded-lg text-xs font-semibold shadow-xs">
                      Browse File
                    </span>
                  </div>
                )}

                {cameraError && (
                  <div className="p-3 rounded-lg bg-amber-50 border border-amber-200 text-amber-900 text-xs flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0" />
                    <span>{cameraError}</span>
                  </div>
                )}

                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/jpeg,image/jpg,image/png,image/webp"
                  onChange={handleFileInputChange}
                  className="hidden"
                />
              </div>

              {/* Right Column: Metadata Form Fields */}
              <div className="lg:col-span-7 space-y-4">
                {/* Object Name */}
                <div>
                  <label className="text-xs font-bold text-slate-700 flex items-center gap-1.5 mb-1.5">
                    <Tag className="w-3.5 h-3.5 text-teal-600" />
                    <span>Object Name / Item Label *</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={objectName}
                    onChange={(e) => setObjectName(e.target.value)}
                    placeholder="e.g. Mobile Phone, Charger Adapter, Battery, PET Bottle"
                    className="w-full px-3.5 py-2.5 text-xs sm:text-sm rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500 bg-white"
                  />
                  <p className="text-[11px] text-slate-400 mt-1">
                    Please name the specific object shown in your photo.
                  </p>
                </div>

                {/* Waste Category */}
                <div>
                  <label className="text-xs font-bold text-slate-700 flex items-center gap-1.5 mb-1.5">
                    <FileText className="w-3.5 h-3.5 text-teal-600" />
                    <span>Waste Category *</span>
                  </label>
                  <select
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    className="w-full px-3.5 py-2.5 text-xs sm:text-sm rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500 bg-white"
                  >
                    {WASTE_CATEGORIES.map((cat) => (
                      <option key={cat} value={cat}>
                        {cat}
                      </option>
                    ))}
                  </select>
                  <p className="text-[11px] text-slate-400 mt-1">
                    Select &quot;E-Waste&quot; for phones, electronics, chargers, and circuit boards.
                  </p>
                </div>

                {/* Location Context */}
                <div>
                  <label className="text-xs font-bold text-slate-700 flex items-center gap-1.5 mb-1.5">
                    <MapPin className="w-3.5 h-3.5 text-teal-600" />
                    <span>Found Location / Neighborhood (Optional)</span>
                  </label>
                  <input
                    type="text"
                    value={locationContext}
                    onChange={(e) => setLocationContext(e.target.value)}
                    placeholder="e.g. Anna Nagar 2nd Avenue, Besant Nagar Beach, Royapuram Hub"
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
                    rows={2}
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="e.g. Defunct smartphone with shattered screen found in electronic collection bin."
                    className="w-full px-3.5 py-2.5 text-xs sm:text-sm rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500 bg-white resize-none"
                  />
                </div>

                {/* Contributor Info */}
                <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs flex items-center justify-between text-slate-600">
                  <span>Contributing as: <strong>{contributorName}</strong></span>
                  <span className="text-[10px] text-teal-700 font-semibold">
                    {isAuthenticated ? "Authenticated Citizen" : "Guest Contributor"}
                  </span>
                </div>

                {/* Submit Button */}
                <div className="flex items-center gap-3 pt-2">
                  <button
                    type="submit"
                    disabled={isUploading || !selectedFile}
                    className="flex-1 py-3 bg-teal-600 hover:bg-teal-700 text-white rounded-xl text-xs sm:text-sm font-bold transition flex items-center justify-center gap-2 shadow-sm disabled:opacity-50"
                  >
                    {isUploading ? (
                      <>
                        <RefreshCw className="w-4 h-4 animate-spin" />
                        <span>Uploading to Municipal AI Server...</span>
                      </>
                    ) : (
                      <>
                        <UploadCloud className="w-4 h-4" />
                        <span>Submit for AI Training (+10 Eco Points)</span>
                      </>
                    )}
                  </button>

                  <button
                    type="button"
                    onClick={handleReset}
                    className="px-4 py-3 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs sm:text-sm font-bold transition"
                  >
                    Reset
                  </button>
                </div>
              </div>
            </div>
          </form>
        )}
      </div>

      {/* Safety & Quality Safeguards Info */}
      <div className="p-4 rounded-2xl bg-slate-100 border border-slate-200 text-xs text-slate-600 space-y-1">
        <span className="font-bold text-slate-800 flex items-center gap-1.5">
          <ShieldCheck className="w-4 h-4 text-teal-600" />
          <span>Automated Verification &amp; Dataset Safety Gate</span>
        </span>
        <p>
          Submitted images undergo automated resolution checks, blur filtering, and visual feature extraction. Images are queued with status <strong className="text-amber-800 font-bold">PENDING_VERIFICATION</strong> and reviewed by municipal AI administrators before entering the active YOLO training dataset.
        </p>
      </div>

      {/* Recent Submissions History */}
      {recentUploads.length > 0 && (
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <h2 className="text-sm font-bold text-navy-950 flex items-center gap-2">
              <Clock className="w-4 h-4 text-teal-600" />
              <span>Recent Contributions</span>
            </h2>
            <Link href="/uploads" className="text-xs font-bold text-teal-600 hover:underline">
              View All &rarr;
            </Link>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            {recentUploads.map((u) => {
              const displayUrl = u.image_url.startsWith("http")
                ? u.image_url
                : `${(process.env.NEXT_PUBLIC_API_URL || "https://waste-22.onrender.com/api").replace(/\/api\/?$/, "")}${u.image_url}`;
              return (
                <div
                  key={u.id}
                  className="p-3 bg-slate-50 rounded-xl border border-slate-200 flex items-center gap-3 text-xs"
                >
                  <div className="w-12 h-12 rounded-lg overflow-hidden bg-slate-200 flex-shrink-0">
                    <img
                      src={displayUrl}
                      alt={u.object_label}
                      className="w-full h-full object-cover"
                      onError={(e: any) => {
                        e.target.src = "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=150&auto=format&fit=crop";
                      }}
                    />
                  </div>
                  <div className="space-y-0.5 flex-1 min-w-0">
                    <span className="font-bold text-navy-950 block truncate">
                      {u.object_label}
                    </span>
                    <span className="text-[10px] text-slate-500 block truncate">
                      {u.category}
                    </span>
                    <span
                      className={`inline-block px-2 py-0.2 rounded-full text-[9px] font-bold border ${
                        u.status === "PENDING_VERIFICATION"
                          ? "bg-amber-100 text-amber-900 border-amber-300"
                          : u.status === "Added to Dataset" || u.status === "Approved"
                          ? "bg-emerald-100 text-emerald-900 border-emerald-300"
                          : u.status === "Used for Training"
                          ? "bg-purple-100 text-purple-900 border-purple-300"
                          : "bg-rose-100 text-rose-900 border-rose-300"
                      }`}
                    >
                      {u.status === "PENDING_VERIFICATION" ? "Pending" : u.status}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}