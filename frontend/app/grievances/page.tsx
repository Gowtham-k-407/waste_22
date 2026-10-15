"use client";

import React, { useEffect, useState } from "react";
import { 
  FileText, 
  AlertCircle, 
  PlusCircle, 
  CheckCircle2, 
  Clock, 
  ArrowUpRight, 
  Send, 
  RotateCcw, 
  MapPin, 
  Building2, 
  ShieldAlert,
  ChevronRight,
  Filter,
  Search,
  MessageSquare,
  ShieldCheck,
  HelpCircle,
  X
} from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

interface GrievanceItem {
  id: number;
  complaint_code: string;
  tracking_number: string;
  category: string;
  description: string;
  location_address: string;
  ward_id: number;
  status: string;
  priority: string;
  assigned_department: string;
  assigned_authority?: string;
  current_escalation_tier: number;
  can_escalate: boolean;
  photo_evidence_url?: string;
  resolution_notes?: string;
  resolution_evidence_url?: string;
  created_at: string;
  resolved_at?: string;
  estimated_sla_hours: number;
}

const CATEGORIES = [
  { value: "missed_collection", label: "Missed Waste Collection" },
  { value: "overflowing_bin", label: "Overflowing Public Garbage Bin" },
  { value: "illegal_dumping", label: "Illegal Dumping / Vacant Plot Litter" },
  { value: "drainage_blockage", label: "Drainage Blockage / Sewage Stagnation" },
  { value: "drainage_leakage", label: "Drainage Leakage" },
  { value: "street_cleaning", label: "Street Sweeping / Cleaning Needed" },
  { value: "damaged_bin", label: "Damaged / Broken GCC Dustbin" },
  { value: "public_sanitation_hazard", label: "Public Health / Sanitation Hazard" },
  { value: "other", label: "Other Civic Cleanliness Issue" },
];

const ESCALATION_TIERS = [
  { tier: 0, title: "Ward Sanitary Inspector", department: "Ward Sanitation Office" },
  { tier: 1, title: "Assistant Engineer / Zonal Officer", department: "Zonal Health & Sanitation Wing" },
  { tier: 2, title: "Municipal Health Officer", department: "GCC Public Health Directorate" },
  { tier: 3, title: "Municipal Commissioner Executive Cell", department: "Commissioner Executive Grievance Cell" },
];

export default function GrievancesPage() {
  const { user, isAuthenticated } = useAuth();
  const [complaints, setComplaints] = useState<GrievanceItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal states
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedComplaint, setSelectedComplaint] = useState<any | null>(null);
  const [showDetailModal, setShowDetailModal] = useState(false);

  // Form states for creation
  const [category, setCategory] = useState("missed_collection");
  const [description, setDescription] = useState("");
  const [locationAddress, setLocationAddress] = useState("");
  const [wardId, setWardId] = useState<number>(user?.assigned_ward || 102);
  const [photoUrl, setPhotoUrl] = useState("");
  const [priority, setPriority] = useState("Medium");
  const [submitting, setSubmitting] = useState(false);

  // Follow-up and Escalation states
  const [followUpMsg, setFollowUpMsg] = useState("");
  const [escalationReason, setEscalationReason] = useState("");
  const [reopenReason, setReopenReason] = useState("");
  const [actionLoading, setActionLoading] = useState(false);

  // Staff resolution form
  const [staffStatus, setStaffStatus] = useState("in_progress");
  const [staffNotes, setStaffNotes] = useState("");
  const [resolutionPhoto, setResolutionPhoto] = useState("");

  const isStaffOrAdmin = user && !["public", "contributor"].includes(user.role);

  const loadComplaints = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.getComplaints();
      setComplaints(res.complaints || []);
    } catch (err: any) {
      setError(err.message || "Failed to load sanitation grievances.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isAuthenticated) {
      loadComplaints();
    } else {
      setLoading(false);
    }
  }, [isAuthenticated]);

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (description.length < 10) {
      alert("Please provide at least 10 characters in the issue description.");
      return;
    }
    try {
      setSubmitting(true);
      await api.submitComplaint({
        category,
        description,
        location_address: locationAddress,
        ward_id: Number(wardId),
        photo_evidence_url: photoUrl || undefined,
        priority,
      });
      setShowCreateModal(false);
      setDescription("");
      setLocationAddress("");
      setPhotoUrl("");
      loadComplaints();
    } catch (err: any) {
      alert(err.message || "Failed to register grievance.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleOpenDetail = async (complaintId: number | string) => {
    try {
      setActionLoading(true);
      const res = await api.getComplaintDetail(complaintId);
      setSelectedComplaint(res);
      setShowDetailModal(true);
    } catch (err: any) {
      alert(err.message || "Unable to fetch grievance details.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleAddFollowUp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedComplaint || !followUpMsg.trim()) return;
    try {
      setActionLoading(true);
      await api.addComplaintFollowUp(selectedComplaint.complaint.id, {
        message: followUpMsg.trim(),
      });
      setFollowUpMsg("");
      handleOpenDetail(selectedComplaint.complaint.id);
      loadComplaints();
    } catch (err: any) {
      alert(err.message || "Failed to add follow-up note.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleEscalate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedComplaint || escalationReason.length < 10) {
      alert("Please provide at least 10 characters explaining the reason for escalation.");
      return;
    }
    try {
      setActionLoading(true);
      await api.escalateComplaint(selectedComplaint.complaint.id, {
        reason: escalationReason.trim(),
      });
      setEscalationReason("");
      alert("Grievance has been escalated to the next municipal authority.");
      handleOpenDetail(selectedComplaint.complaint.id);
      loadComplaints();
    } catch (err: any) {
      alert(err.message || "Failed to escalate grievance.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleReopen = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedComplaint || reopenReason.length < 5) {
      alert("Please provide a reason for reopening this grievance.");
      return;
    }
    try {
      setActionLoading(true);
      await api.reopenComplaint(selectedComplaint.complaint.id, reopenReason.trim());
      setReopenReason("");
      alert("Grievance has been reopened for supervisor reinspection.");
      handleOpenDetail(selectedComplaint.complaint.id);
      loadComplaints();
    } catch (err: any) {
      alert(err.message || "Failed to reopen grievance.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleStaffStatusUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedComplaint) return;
    try {
      setActionLoading(true);
      await api.updateComplaintStatus(selectedComplaint.complaint.id, {
        status: staffStatus,
        officer_notes: staffNotes,
        resolution_evidence_url: resolutionPhoto || undefined,
      });
      alert(`Grievance status updated to '${staffStatus}'.`);
      setStaffNotes("");
      setResolutionPhoto("");
      handleOpenDetail(selectedComplaint.complaint.id);
      loadComplaints();
    } catch (err: any) {
      alert(err.message || "Failed to update grievance status.");
    } finally {
      setActionLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case "resolved":
      case "closed":
        return "bg-emerald-100 text-emerald-800 border-emerald-300";
      case "in_progress":
      case "assigned":
        return "bg-sky-100 text-sky-800 border-sky-300";
      case "escalated":
        return "bg-amber-100 text-amber-900 border-amber-300";
      case "reopened":
        return "bg-purple-100 text-purple-800 border-purple-300";
      default:
        return "bg-slate-100 text-slate-700 border-slate-300";
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="max-w-2xl mx-auto my-12 p-8 bg-white rounded-2xl border border-slate-200 shadow-sm text-center">
        <Building2 className="w-12 h-12 text-teal-600 mx-auto mb-3" />
        <h2 className="text-xl font-bold text-slate-800">GCC Citizen Grievance Redressal</h2>
        <p className="text-sm text-slate-600 mt-2">
          Please sign in to file public sanitation complaints, track status history, and escalate overdue issues.
        </p>
        <a
          href="/login"
          className="mt-5 inline-block px-6 py-2.5 bg-teal-600 hover:bg-teal-700 text-white text-sm font-semibold rounded-xl shadow-sm transition"
        >
          Sign In to Report / Track Issues
        </a>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-navy-950 via-navy-900 to-teal-950 text-white rounded-2xl p-6 shadow-sm border border-navy-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded-full bg-teal-500/20 border border-teal-500/30 text-teal-300 text-xs font-semibold mb-2">
            <Building2 className="w-3.5 h-3.5" />
            <span>Greater Chennai Corporation • Solid Waste Management</span>
          </div>
          <h1 className="text-2xl font-bold">Public Sanitation Grievance Redressal</h1>
          <p className="text-slate-300 text-xs sm:text-sm mt-1 max-w-2xl">
            {isStaffOrAdmin
              ? "Operational municipal grievance tracking across assigned wards and zones."
              : `Track and escalate civic cleanliness issues reported for your neighborhood in Ward ${user?.assigned_ward || 102}.`}
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold rounded-xl shadow-sm transition shrink-0"
        >
          <PlusCircle className="w-4 h-4" />
          <span>Report Sanitation Issue</span>
        </button>
      </div>

      {/* Main List */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <FileText className="w-5 h-5 text-teal-600" />
            <h2 className="text-sm font-bold text-slate-800">
              {isStaffOrAdmin ? "Assigned Municipal Grievances" : "My Reported Sanitation Issues"}
            </h2>
          </div>
          <span className="text-xs text-slate-500">{complaints.length} Records</span>
        </div>

        {loading ? (
          <div className="p-8 text-center text-slate-400 text-sm">Loading grievances...</div>
        ) : complaints.length === 0 ? (
          <div className="p-12 text-center space-y-3">
            <CheckCircle2 className="w-12 h-12 text-slate-300 mx-auto" />
            <p className="text-sm font-medium text-slate-700">No grievances on record.</p>
            <p className="text-xs text-slate-500 max-w-md mx-auto">
              If you observe missed garbage collection, overflowing public bins, or sanitation blockages in your area, please file a report.
            </p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="mt-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition"
            >
              Report Your First Issue
            </button>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {complaints.map((item) => (
              <div
                key={item.id}
                onClick={() => handleOpenDetail(item.id)}
                className="p-4 hover:bg-slate-50 transition cursor-pointer flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3"
              >
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="font-mono text-xs font-bold text-teal-800">{item.complaint_code}</span>
                    <span className={`px-2 py-0.5 text-[10px] font-bold rounded-full border uppercase ${getStatusBadge(item.status)}`}>
                      {item.status.replace("_", " ")}
                    </span>
                    {item.current_escalation_tier > 0 && (
                      <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-amber-50 text-amber-800 border border-amber-300">
                        Tier {item.current_escalation_tier} Escalated
                      </span>
                    )}
                  </div>
                  <h4 className="text-xs font-bold text-slate-800">{item.category.replace(/_/g, " ").toUpperCase()}</h4>
                  <p className="text-xs text-slate-600 line-clamp-1">{item.description}</p>
                  <div className="flex items-center space-x-4 text-[11px] text-slate-400 pt-0.5">
                    <span className="flex items-center"><MapPin className="w-3 h-3 mr-1 text-slate-400" /> Ward {item.ward_id} • {item.location_address}</span>
                    <span className="flex items-center"><Clock className="w-3 h-3 mr-1 text-slate-400" /> SLA: {item.estimated_sla_hours}h</span>
                  </div>
                </div>

                <div className="flex items-center space-x-3 shrink-0">
                  <div className="text-right hidden sm:block">
                    <p className="text-[11px] font-medium text-slate-600">{item.assigned_department}</p>
                    <p className="text-[10px] text-slate-400">{item.assigned_authority || "Ward Sanitary Inspector"}</p>
                  </div>
                  <ChevronRight className="w-4 h-4 text-slate-400" />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* CREATE MODAL */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl border border-slate-200 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-sm font-bold text-slate-900">Report Sanitation & Cleanliness Issue</h3>
              <button onClick={() => setShowCreateModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Issue Category *</label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500"
                >
                  {CATEGORIES.map((cat) => (
                    <option key={cat.value} value={cat.value}>{cat.label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Location Address *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. 2nd Main Road near community park, Anna Nagar"
                  value={locationAddress}
                  onChange={(e) => setLocationAddress(e.target.value)}
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Ward Number (1-200)</label>
                  <input
                    type="number"
                    min={1}
                    max={200}
                    value={wardId}
                    onChange={(e) => setWardId(Number(e.target.value))}
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Priority Level</label>
                  <select
                    value={priority}
                    onChange={(e) => setPriority(e.target.value)}
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500"
                  >
                    <option value="Low">Low (Standard Collection)</option>
                    <option value="Medium">Medium (Attention Required)</option>
                    <option value="High">High (Severe Overflow / Hazard)</option>
                    <option value="Critical">Critical (Blocked Drainage / Health Risk)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Detailed Description * (min 10 characters)</label>
                <textarea
                  required
                  rows={3}
                  placeholder="Describe the issue, estimated volume, and public impact..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Photo Evidence URL (Optional)</label>
                <input
                  type="url"
                  placeholder="https://example.com/photo.jpg"
                  value={photoUrl}
                  onChange={(e) => setPhotoUrl(e.target.value)}
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500"
                />
              </div>

              <div className="flex items-center justify-end space-x-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-5 py-2 text-xs font-bold text-white bg-teal-600 hover:bg-teal-700 rounded-lg shadow-sm disabled:opacity-50"
                >
                  {submitting ? "Submitting..." : "Submit Report"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* DETAIL MODAL */}
      {showDetailModal && selectedComplaint && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-xl border border-slate-200 space-y-6 max-h-[90vh] overflow-y-auto">
            <div className="flex items-start justify-between pb-3 border-b border-slate-100">
              <div>
                <div className="flex items-center space-x-2">
                  <span className="font-mono text-sm font-extrabold text-teal-800">
                    {selectedComplaint.complaint.complaint_code}
                  </span>
                  <span className={`px-2 py-0.5 text-xs font-bold rounded-full border uppercase ${getStatusBadge(selectedComplaint.complaint.status)}`}>
                    {selectedComplaint.complaint.status}
                  </span>
                </div>
                <h3 className="text-base font-bold text-slate-900 mt-1">
                  {selectedComplaint.complaint.category.replace(/_/g, " ").toUpperCase()}
                </h3>
              </div>
              <button onClick={() => setShowDetailModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Overview Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-50 p-3.5 rounded-xl text-xs">
              <div>
                <span className="text-slate-400 block text-[10px] uppercase">Ward / Location</span>
                <span className="font-bold text-slate-800">Ward {selectedComplaint.complaint.ward_id}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase">Assigned Authority</span>
                <span className="font-bold text-slate-800">{selectedComplaint.complaint.assigned_authority || "Sanitary Inspector"}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase">Escalation Tier</span>
                <span className="font-bold text-amber-700">Tier {selectedComplaint.complaint.current_escalation_tier} of 3</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase">SLA Target</span>
                <span className="font-bold text-slate-800">{selectedComplaint.complaint.estimated_sla_hours} Hours</span>
              </div>
            </div>

            <div>
              <h4 className="text-xs font-bold text-slate-700 uppercase mb-1">Description</h4>
              <p className="text-xs text-slate-600 bg-slate-50 p-3 rounded-lg border border-slate-100">
                {selectedComplaint.complaint.description}
              </p>
            </div>

            {selectedComplaint.complaint.resolution_notes && (
              <div className="bg-emerald-50 border border-emerald-200 p-3.5 rounded-xl space-y-1">
                <h4 className="text-xs font-bold text-emerald-900 flex items-center">
                  <CheckCircle2 className="w-4 h-4 mr-1 text-emerald-600" />
                  Official Municipal Remediation Notes
                </h4>
                <p className="text-xs text-emerald-800 leading-relaxed">
                  {selectedComplaint.complaint.resolution_notes}
                </p>
              </div>
            )}

            {/* Timeline */}
            <div>
              <h4 className="text-xs font-bold text-slate-800 uppercase mb-2">History & Follow-ups</h4>
              <div className="space-y-2 border-l-2 border-teal-200 pl-3 ml-2">
                {selectedComplaint.timeline && selectedComplaint.timeline.length > 0 ? (
                  selectedComplaint.timeline.map((entry: any) => (
                    <div key={entry.id} className="text-xs space-y-0.5">
                      <div className="flex items-center space-x-2">
                        <span className="font-bold text-slate-700">{entry.author_name}</span>
                        <span className="text-[10px] text-slate-400 uppercase">({entry.author_role})</span>
                      </div>
                      <p className="text-slate-600">{entry.message}</p>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-slate-400">No follow-up notes yet.</p>
                )}
              </div>
            </div>

            {/* Citizen Actions: Follow-up & Escalation */}
            {!isStaffOrAdmin && (
              <div className="space-y-4 pt-3 border-t border-slate-100">
                {/* Follow-up input */}
                <form onSubmit={handleAddFollowUp} className="flex gap-2">
                  <input
                    type="text"
                    required
                    placeholder="Add follow-up notes or additional details..."
                    value={followUpMsg}
                    onChange={(e) => setFollowUpMsg(e.target.value)}
                    className="flex-1 px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500"
                  />
                  <button
                    type="submit"
                    disabled={actionLoading || !followUpMsg.trim()}
                    className="px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white text-xs font-bold rounded-lg shrink-0 disabled:opacity-50"
                  >
                    Send Note
                  </button>
                </form>

                {/* Escalation Section */}
                {selectedComplaint.complaint.can_escalate && (
                  <div className="bg-amber-50 border border-amber-200 p-4 rounded-xl space-y-2">
                    <div className="flex items-start space-x-2">
                      <ShieldAlert className="w-4 h-4 text-amber-700 mt-0.5 shrink-0" />
                      <div>
                        <h5 className="text-xs font-bold text-amber-900">
                          Escalate to Higher Municipal Authority
                        </h5>
                        <p className="text-[11px] text-amber-800">
                          Next Tier: <span className="font-semibold">{ESCALATION_TIERS[selectedComplaint.complaint.current_escalation_tier + 1]?.title || "Higher Authority"}</span> ({ESCALATION_TIERS[selectedComplaint.complaint.current_escalation_tier + 1]?.department})
                        </p>
                      </div>
                    </div>
                    <form onSubmit={handleEscalate} className="flex gap-2 pt-1">
                      <input
                        type="text"
                        required
                        placeholder="Reason for escalation (e.g. SLA elapsed without inspection)..."
                        value={escalationReason}
                        onChange={(e) => setEscalationReason(e.target.value)}
                        className="flex-1 px-3 py-1.5 text-xs border border-amber-300 rounded-lg focus:ring-2 focus:ring-amber-500"
                      />
                      <button
                        type="submit"
                        disabled={actionLoading || escalationReason.length < 10}
                        className="px-4 py-1.5 bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold rounded-lg shrink-0 disabled:opacity-50"
                      >
                        Escalate
                      </button>
                    </form>
                  </div>
                )}

                {/* Reopen if resolved */}
                {["resolved", "closed"].includes(selectedComplaint.complaint.status.toLowerCase()) && (
                  <form onSubmit={handleReopen} className="bg-purple-50 border border-purple-200 p-3 rounded-xl flex gap-2 items-center">
                    <input
                      type="text"
                      required
                      placeholder="Reason for reopening (e.g. garbage was not cleared properly)..."
                      value={reopenReason}
                      onChange={(e) => setReopenReason(e.target.value)}
                      className="flex-1 px-3 py-1.5 text-xs border border-purple-300 rounded-lg focus:ring-2 focus:ring-purple-500"
                    />
                    <button
                      type="submit"
                      disabled={actionLoading || reopenReason.length < 5}
                      className="px-4 py-1.5 bg-purple-600 hover:bg-purple-700 text-white text-xs font-bold rounded-lg shrink-0 disabled:opacity-50"
                    >
                      Reopen Grievance
                    </button>
                  </form>
                )}
              </div>
            )}

            {/* Municipal Staff Resolution Workflow */}
            {isStaffOrAdmin && (
              <form onSubmit={handleStaffStatusUpdate} className="bg-slate-50 border border-slate-200 p-4 rounded-xl space-y-3 pt-3 border-t">
                <h5 className="text-xs font-bold text-slate-800 uppercase flex items-center">
                  <ShieldCheck className="w-4 h-4 mr-1 text-teal-600" />
                  Municipal Redressal Action
                </h5>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-700 mb-1">Set Lifecycle Status</label>
                    <select
                      value={staffStatus}
                      onChange={(e) => setStaffStatus(e.target.value)}
                      className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-lg"
                    >
                      <option value="in_progress">In Progress (Inspecting / Team Dispatched)</option>
                      <option value="resolved">Resolved (Remediation Completed)</option>
                      <option value="closed">Closed (Verified by Supervisor)</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-700 mb-1">Resolution Photo URL</label>
                    <input
                      type="url"
                      placeholder="https://example.com/clean.jpg"
                      value={resolutionPhoto}
                      onChange={(e) => setResolutionPhoto(e.target.value)}
                      className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-lg"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 mb-1">Remediation Notes</label>
                  <textarea
                    rows={2}
                    placeholder="Enter remediation action taken, worker name, and date..."
                    value={staffNotes}
                    onChange={(e) => setStaffNotes(e.target.value)}
                    className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-lg"
                  />
                </div>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-2 bg-teal-700 hover:bg-teal-800 text-white text-xs font-bold rounded-lg transition disabled:opacity-50"
                >
                  Commit Status Update
                </button>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
