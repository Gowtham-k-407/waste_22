const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "https://waste-22.onrender.com/api";

export async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  
  // Attach token if present in browser
  const headers: Record<string, string> = {
    ...(options?.headers as Record<string, string> || {}),
  };

  if (typeof window !== "undefined") {
    const token = localStorage.getItem("wastevision_token");
    if (token && !headers["Authorization"]) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }

  try {
    const res = await fetch(url, {
      ...options,
      headers,
      cache: "no-store",
    });

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}));
      throw new Error(errorData.user_message || errorData.detail || `Request failed with status ${res.status}`);
    }

    return await res.json();
  } catch (err: any) {
    console.error(`Error fetching ${endpoint}:`, err);
    throw err;
  }
}

export const api = {
  // Authentication & User Profile
  login: (data: { email: string; password: string; remember_me?: boolean }) =>
    fetchApi<any>("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),

  register: (data: { email: string; password: string; full_name: string; organization?: string; city?: string }) =>
    fetchApi<any>("/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),

  forgotPassword: (email: string) =>
    fetchApi<any>("/auth/forgot-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    }),

  resetPassword: (data: { token: string; new_password: string }) =>
    fetchApi<any>("/auth/reset-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),

  getCurrentUser: () => fetchApi<any>("/auth/me"),

  updateProfile: (data: { full_name?: string; organization?: string; city?: string }) =>
    fetchApi<any>("/auth/profile", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),

  changePassword: (data: { current_password: string; new_password: string }) =>
    fetchApi<any>("/auth/change-password", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),

  getProfileStats: () => fetchApi<any>("/auth/profile-stats"),

  getRoles: () => fetchApi<any[]>("/auth/roles"),

  switchRole: (role: string) =>
    fetchApi<any>("/auth/switch-role", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role }),
    }),

  // Dashboard & KPIs
  getDashboardSummary: () => fetchApi<any>("/dashboard/summary"),
  
  // Wards
  getWards: (zoneId?: number, sortBy?: string) => {
    const params = new URLSearchParams();
    if (zoneId) params.append("zone_id", zoneId.toString());
    if (sortBy) params.append("sort_by", sortBy);
    return fetchApi<any[]>(`/wards/?${params.toString()}`);
  },
  getWardRankings: () => fetchApi<any[]>("/wards/rankings"),
  getWardByNumber: (wardNumber: number) => fetchApi<any>(`/wards/${wardNumber}`),

  // Waste & Composition
  getWasteCategories: () => fetchApi<any[]>("/waste/categories"),
  getCompositionTrends: () => fetchApi<any>("/waste/composition-trends"),

  // Facilities
  getPlants: (status?: string) => {
    const params = status ? `?status=${status}` : "";
    return fetchApi<any[]>(`/plants/${params}`);
  },
  updatePlantStatus: (plantId: number, status: string, currentInput?: number) =>
    fetchApi<any>(`/plants/${plantId}/status?status=${status}${currentInput !== undefined ? `&current_input=${currentInput}` : ""}`, {
      method: "PUT",
    }),

  // Vehicles
  getVehicles: () => fetchApi<any[]>("/vehicles/"),

  // Detections
  getRecentDetections: (vehicleCode?: string, limit: number = 30) => {
    const params = new URLSearchParams();
    if (vehicleCode) params.append("vehicle_code", vehicleCode);
    params.append("limit", limit.toString());
    return fetchApi<any[]>(`/detections/?${params.toString()}`);
  },
  simulateTruckScan: (formData: FormData) =>
    fetchApi<any>("/detections/simulate-truck-scan", {
      method: "POST",
      body: formData,
    }),
  liveDetect: (formData: FormData) =>
    fetchApi<any>("/detections/live-detect", {
      method: "POST",
      body: formData,
    }),

  // Community Contributions
  getContributions: (limit: number = 50) => fetchApi<any[]>(`/contributions/?limit=${limit}`),
  getContributionStats: () => fetchApi<any>("/contributions/stats"),
  uploadAndPredict: (formData: FormData) =>
    fetchApi<any>("/contributions/upload-and-predict", {
      method: "POST",
      body: formData,
    }),
  confirmAndSubmit: (formData: FormData) =>
    fetchApi<any>("/contributions/confirm-and-submit", {
      method: "POST",
      body: formData,
    }),

  // Personal AI Memory ("My Waste AI Memory")
  getMemoryItems: () => fetchApi<any[]>("/memory/"),
  addMemoryItem: (formData: FormData) =>
    fetchApi<any>("/memory/add", {
      method: "POST",
      body: formData,
    }),
  deleteMemoryItem: (refId: number) =>
    fetchApi<any>(`/memory/${refId}`, {
      method: "DELETE",
    }),
  updateMemoryItem: (refId: number, data: { confirmed_item?: string; confirmed_waste_category?: string; notes?: string }) =>
    fetchApi<any>(`/memory/${refId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
  searchMemoryMatch: (formData: FormData) =>
    fetchApi<any>("/memory/search-match", {
      method: "POST",
      body: formData,
    }),
  getMemoryStats: () => fetchApi<any>("/memory/stats"),

  // Continuous Training & Models
  getTrainingStatus: () => fetchApi<any>("/ai-training/status"),
  getClassDistribution: () => fetchApi<any>("/ai-training/class-distribution"),
  getConfusionMatrix: () => fetchApi<any>("/ai-training/confusion-matrix"),
  triggerRetraining: (force: boolean = false) => {
    const fd = new FormData();
    fd.append("force", force.toString());
    return fetchApi<any>("/ai-training/trigger-retraining", {
      method: "POST",
      body: fd,
    });
  },
  getModels: () => fetchApi<any[]>("/models/"),
  getModelComparison: () => fetchApi<any>("/models/comparison"),
  deployModel: (candidateVersion: string) => {
    const fd = new FormData();
    fd.append("candidate_version", candidateVersion);
    return fetchApi<any>("/models/deploy", {
      method: "POST",
      body: fd,
    });
  },
  rollbackModel: (targetVersion?: string) => {
    const fd = new FormData();
    if (targetVersion) fd.append("target_version", targetVersion);
    return fetchApi<any>("/models/rollback", {
      method: "POST",
      body: fd,
    });
  },

  // Datasets
  getDatasetSources: () => fetchApi<any[]>("/datasets/catalog"),
  uploadCsv: (formData: FormData) =>
    fetchApi<any>("/datasets/upload-csv", {
      method: "POST",
      body: formData,
    }),

  // Optimization
  getRecommendations: () => fetchApi<any[]>("/optimization/recommendations"),

  // Alerts
  getAlerts: (priority?: string) => {
    const params = priority ? `?priority=${priority}` : "";
    return fetchApi<any[]>(`/alerts/${params}`);
  },
  resolveAlert: (alertId: number) =>
    fetchApi<any>(`/alerts/${alertId}/resolve`, {
      method: "POST",
    }),

  // Environmental
  getEnvironmentalSummary: () => fetchApi<any>("/environmental/summary"),

  // Simulation
  getSimulationStatus: () => fetchApi<any>("/simulation/status"),
  toggleSimulation: () => fetchApi<any>("/simulation/toggle", { method: "POST" }),

  // User Dataset Uploads
  uploadWasteImage: (formData: FormData) =>
    fetchApi<any>("/uploads/", {
      method: "POST",
      body: formData,
    }),
  getUserUploads: (statusFilter?: string) => {
    const q = statusFilter ? `?status_filter=${encodeURIComponent(statusFilter)}` : "";
    return fetchApi<any>(`/uploads/${q}`);
  },
  getUploadDetail: (id: number) => fetchApi<any>(`/uploads/${id}`),

  // Admin Portal & Verification
  adminLogin: (data: { email: string; password: string }) =>
    fetchApi<any>("/admin/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
  getAdminOverview: () => fetchApi<any>("/admin/overview"),
  getAdminUploads: (statusFilter?: string, limit: number = 100, offset: number = 0) => {
    const params = new URLSearchParams();
    if (statusFilter && statusFilter !== "All") params.append("status_filter", statusFilter);
    params.append("limit", limit.toString());
    params.append("offset", offset.toString());
    return fetchApi<any>(`/admin/uploads?${params.toString()}`);
  },
  approveAdminUpload: (id: number, data: { verified_category?: string; verified_label?: string; admin_notes?: string }) =>
    fetchApi<any>(`/admin/uploads/${id}/approve`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
  rejectAdminUpload: (id: number, data: { rejection_reason: string; admin_notes?: string }) =>
    fetchApi<any>(`/admin/uploads/${id}/reject`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
  updateAdminUpload: (id: number, data: any) =>
    fetchApi<any>(`/admin/uploads/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
  batchApproveAdminUploads: (upload_ids: number[]) =>
    fetchApi<any>("/admin/uploads/batch-approve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ upload_ids }),
    }),
  batchRejectAdminUploads: (upload_ids: number[], rejection_reason: string) =>
    fetchApi<any>("/admin/uploads/batch-reject", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ upload_ids, rejection_reason }),
    }),

  // Admin Verified Dataset
  getVerifiedDataset: (category?: string, search?: string, limit: number = 100, offset: number = 0) => {
    const params = new URLSearchParams();
    if (category && category !== "All") params.append("category", category);
    if (search) params.append("search", search);
    params.append("limit", limit.toString());
    params.append("offset", offset.toString());
    return fetchApi<any>(`/admin/dataset?${params.toString()}`);
  },
  updateDatasetImage: (id: number, data: any) =>
    fetchApi<any>(`/admin/dataset/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
  deleteDatasetImage: (id: number) =>
    fetchApi<any>(`/admin/dataset/${id}`, {
      method: "DELETE",
    }),
  exportDataset: (format: "json" | "csv" = "json") =>
    fetchApi<any>(`/admin/dataset/export?format=${format}`),

  // Real Model Training
  startAdminTraining: (config?: { candidate_version?: string; total_epochs?: number; batch_size?: number; learning_rate?: number }) =>
    fetchApi<any>("/admin/train-model", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config || {}),
    }),
  getAdminTrainingStatus: () => fetchApi<any>("/admin/training-status"),

  // Model Versions & Deployment
  getAdminModels: () => fetchApi<any>("/admin/models"),
  activateAdminModel: (id: number) =>
    fetchApi<any>(`/admin/models/${id}/activate`, {
      method: "POST",
    }),
  rollbackAdminModel: (id: number) =>
    fetchApi<any>(`/admin/models/${id}/rollback`, {
      method: "POST",
    }),
  getActiveAdminModel: () => fetchApi<any>("/admin/models/active"),

  // Direct Live Webcam Detection using Active Model
  detectWebcamFrame: (formData: FormData) =>
    fetchApi<any>("/detect", {
      method: "POST",
      body: formData,
    }),
};