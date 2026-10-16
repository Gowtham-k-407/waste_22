"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import {
  Truck,
  MapPin,
  RefreshCw,
  X,
  Clock,
  AlertTriangle,
  CheckCircle2,
  Compass,
  ShieldCheck,
  Radio,
  ExternalLink
} from "lucide-react";
import { api } from "@/lib/api";

interface AssignedTruckMiniMapModalProps {
  isOpen: boolean;
  onClose: () => void;
  wardNumber?: number;
  initialTruckData?: any;
}

interface TruckTelemetry {
  assigned: boolean;
  vehicle_code?: string;
  vehicle_type?: string;
  status: string;
  current_fill_pct?: number;
  latitude?: number | null;
  longitude?: number | null;
  last_ping?: string | null;
  assigned_ward_id?: number;
  assigned_ward_number?: number;
  data_mode: "live" | "simulated" | "stale" | "unavailable";
  is_stale: boolean;
  message?: string;
}

export function AssignedTruckMiniMapModal({
  isOpen,
  onClose,
  wardNumber,
  initialTruckData,
}: AssignedTruckMiniMapModalProps) {
  const [truck, setTruck] = useState<TruckTelemetry | null>(initialTruckData || null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);
  const markerRef = useRef<any>(null);
  const pollingTimerRef = useRef<NodeJS.Timeout | null>(null);
  const inFlightRef = useRef(false);

  // Fetch latest telemetry for assigned truck
  const fetchTelemetry = useCallback(async (isInitial = false) => {
    if (inFlightRef.current) return;
    inFlightRef.current = true;
    if (isInitial) setLoading(true);

    try {
      const data: TruckTelemetry = await api.getAssignedTruckLocation();
      setTruck(data);
      setLastUpdated(new Date());
      setError(null);
    } catch (err: any) {
      console.error("Failed to fetch assigned truck telemetry:", err);
      setError(err?.message || "Failed to reach vehicle telemetry service.");
    } finally {
      inFlightRef.current = false;
      if (isInitial) setLoading(false);
    }
  }, []);

  // Handle ESC key to close modal
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  // Initial fetch and polling loop while open
  useEffect(() => {
    if (!isOpen) {
      if (pollingTimerRef.current) {
        clearInterval(pollingTimerRef.current);
        pollingTimerRef.current = null;
      }
      return;
    }

    fetchTelemetry(true);

    // Poll every 8 seconds while modal is open
    pollingTimerRef.current = setInterval(() => {
      fetchTelemetry(false);
    }, 8000);

    return () => {
      if (pollingTimerRef.current) {
        clearInterval(pollingTimerRef.current);
        pollingTimerRef.current = null;
      }
    };
  }, [isOpen, fetchTelemetry]);

  // Initialize or update Leaflet interactive map
  useEffect(() => {
    if (!isOpen || !mapContainerRef.current) return;

    let isMounted = true;

    // Only initialize map if we have valid coordinates
    const hasValidCoords =
      truck?.latitude != null &&
      truck?.longitude != null &&
      !isNaN(truck.latitude) &&
      !isNaN(truck.longitude) &&
      truck.latitude >= -90 &&
      truck.latitude <= 90 &&
      truck.longitude >= -180 &&
      truck.longitude <= 180;

    if (!hasValidCoords) {
      // If map exists and coords became invalid, clean up
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
        markerRef.current = null;
      }
      return;
    }

    const lat = truck.latitude as number;
    const lng = truck.longitude as number;

    const setupMap = async () => {
      try {
        const L = (await import("leaflet")).default;

        if (!isMounted || !mapContainerRef.current) return;

        if (!mapInstanceRef.current) {
          // Create map
          const map = L.map(mapContainerRef.current, {
            center: [lat, lng],
            zoom: 15,
            minZoom: 11,
            maxZoom: 18,
            zoomControl: true,
            attributionControl: true,
          });

          L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            attribution:
              '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors | GCC Municipal GIS',
            maxZoom: 19,
          }).addTo(map);

          // Custom Truck Marker Icon
          const truckIconHtml = `
            <div style="
              position: relative;
              width: 38px;
              height: 38px;
              display: flex;
              align-items: center;
              justify-content: center;
            ">
              <span style="
                position: absolute;
                width: 38px;
                height: 38px;
                border-radius: 50%;
                background-color: ${truck.is_stale ? "#f59e0b" : "#0284c7"};
                opacity: 0.35;
                animation: ping 1.8s cubic-bezier(0, 0, 0.2, 1) infinite;
              "></span>
              <div style="
                width: 32px;
                height: 32px;
                border-radius: 10px;
                background-color: ${truck.is_stale ? "#d97706" : "#0369a1"};
                color: white;
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: 0 4px 10px rgba(0,0,0,0.3);
                border: 2px solid white;
              ">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M14 18V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v11a1 1 0 0 0 1 1h2"/>
                  <path d="M15 18H9"/>
                  <path d="M19 18h2a1 1 0 0 0 1-1v-3.65a1 1 0 0 0-.22-.624l-3.48-4.35A1 1 0 0 0 17.52 8H14"/>
                  <circle cx="17" cy="18" r="2"/>
                  <circle cx="7" cy="18" r="2"/>
                </svg>
              </div>
            </div>
          `;

          const customIcon = L.divIcon({
            html: truckIconHtml,
            className: "assigned-truck-marker",
            iconSize: [38, 38],
            iconAnchor: [19, 19],
            popupAnchor: [0, -20],
          });

          const marker = L.marker([lat, lng], { icon: customIcon }).addTo(map);

          marker.bindPopup(`
            <div style="font-family: inherit; font-size: 11px; padding: 2px;">
              <strong style="color: #0f172a; font-size: 12px; display: block; margin-bottom: 3px;">
                ${truck.vehicle_code || "Assigned Truck"}
              </strong>
              <div style="color: #475569; margin-bottom: 2px;">Status: <strong>${truck.status}</strong></div>
              <div style="color: #64748b; font-size: 10px;">Ward: ${truck.assigned_ward_number || "—"}</div>
            </div>
          `);

          markerRef.current = marker;
          mapInstanceRef.current = map;

          // Force a leaflet resize recalculation after modal renders
          setTimeout(() => {
            if (mapInstanceRef.current) {
              mapInstanceRef.current.invalidateSize();
            }
          }, 200);
        } else {
          // Smoothly update marker location without recreating the map
          const map = mapInstanceRef.current;
          if (markerRef.current) {
            markerRef.current.setLatLng([lat, lng]);
          }
          map.panTo([lat, lng], { animate: true, duration: 0.8 });
        }
      } catch (e) {
        console.error("Leaflet map initialization error:", e);
      }
    };

    setupMap();

    return () => {
      isMounted = false;
    };
  }, [isOpen, truck?.latitude, truck?.longitude, truck?.is_stale, truck?.status, truck?.vehicle_code, truck?.assigned_ward_number]);

  // Cleanup map instance on modal close or unmount
  useEffect(() => {
    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
        markerRef.current = null;
      }
    };
  }, []);

  const handleManualRefresh = () => {
    fetchTelemetry(false);
  };

  const handleRecenter = () => {
    if (mapInstanceRef.current && truck?.latitude && truck?.longitude) {
      mapInstanceRef.current.setView([truck.latitude, truck.longitude], 15, { animate: true });
    }
  };

  if (!isOpen) return null;

  const dataMode = truck?.data_mode || "unavailable";
  const hasCoordinates =
    truck?.latitude != null &&
    truck?.longitude != null &&
    !isNaN(truck.latitude) &&
    !isNaN(truck.longitude);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5 bg-slate-950/70 backdrop-blur-sm animate-in fade-in duration-200"
      role="dialog"
      aria-modal="true"
      aria-labelledby="mini-map-title"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-3xl shadow-2xl border border-slate-200 w-full max-w-2xl overflow-hidden flex flex-col max-h-[92vh] animate-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="p-4 sm:p-5 bg-slate-900 text-white flex items-center justify-between border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-sky-500/20 text-sky-400 border border-sky-400/30 flex items-center justify-center flex-shrink-0">
              <Truck className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 id="mini-map-title" className="text-base sm:text-lg font-black tracking-tight text-white">
                  Assigned Collection Truck
                </h2>
                <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-sky-500/20 text-sky-300 border border-sky-400/30 font-mono">
                  Ward {truck?.assigned_ward_number || wardNumber || "Verified"}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Official GCC Municipal Waste Collection Vehicle Live GPS Telemetry
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleManualRefresh}
              disabled={loading}
              className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-xl transition disabled:opacity-50"
              title="Refresh Telemetry"
              aria-label="Refresh GPS Telemetry"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-sky-400" : ""}`} />
            </button>
            <button
              onClick={onClose}
              className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-xl transition"
              title="Close Map (Esc)"
              aria-label="Close Map"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Telemetry Status Strip */}
        <div className="px-4 py-3 bg-slate-50 border-b border-slate-200 flex flex-wrap items-center justify-between gap-2.5 text-xs">
          <div className="flex items-center gap-2">
            {/* Classification Badge */}
            {dataMode === "live" && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                Live GPS Stream
              </span>
            )}

            {dataMode === "simulated" && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold bg-sky-100 text-sky-800 border border-sky-300">
                <Radio className="w-3 h-3 text-sky-600" />
                Simulated Telemetry
              </span>
            )}

            {dataMode === "stale" && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold bg-amber-100 text-amber-900 border border-amber-300">
                <AlertTriangle className="w-3 h-3 text-amber-700" />
                Last Known Location (Stale)
              </span>
            )}

            {dataMode === "unavailable" && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold bg-slate-200 text-slate-700 border border-slate-300">
                <AlertTriangle className="w-3 h-3 text-slate-500" />
                Telemetry Unavailable
              </span>
            )}

            {/* Vehicle Identifier */}
            {truck?.vehicle_code && (
              <span className="font-mono font-bold text-slate-800 bg-white px-2 py-0.5 rounded-lg border border-slate-200 text-[11px]">
                {truck.vehicle_code}
              </span>
            )}

            {truck?.status && (
              <span className="text-slate-600 font-semibold capitalize">
                • {truck.status.replace(/_/g, " ")}
              </span>
            )}
          </div>

          {/* Actual Timestamp */}
          <div className="flex items-center gap-1.5 text-slate-500 text-[11px]">
            <Clock className="w-3.5 h-3.5 text-slate-400" />
            <span>Signal Timestamp:</span>
            <strong className="text-slate-700 font-medium">
              {truck?.last_ping ? new Date(truck.last_ping).toLocaleTimeString() : "No Ping"}
            </strong>
          </div>
        </div>

        {/* Modal Body & Interactive Map */}
        <div className="relative flex-1 min-h-[350px] sm:min-h-[420px] bg-slate-100 flex flex-col">
          {error && (
            <div className="m-3 p-3 bg-rose-50 border border-rose-200 text-rose-800 rounded-xl text-xs flex items-center justify-between">
              <span>{error}</span>
              <button
                onClick={() => setError(null)}
                className="text-rose-500 font-bold ml-2 hover:underline"
              >
                Dismiss
              </button>
            </div>
          )}

          {hasCoordinates ? (
            <div className="relative w-full h-[350px] sm:h-[420px]">
              {/* Map Canvas Container */}
              <div
                ref={mapContainerRef}
                className="w-full h-full z-10"
                style={{ minHeight: "350px" }}
              />

              {/* Floating Quick Action: Re-center on Truck */}
              <button
                onClick={handleRecenter}
                className="absolute bottom-4 right-4 z-20 px-3 py-1.5 bg-white/95 hover:bg-white text-slate-800 rounded-xl text-xs font-bold shadow-md border border-slate-200 flex items-center gap-1.5 backdrop-blur-sm transition"
                title="Center on Truck"
              >
                <Compass className="w-3.5 h-3.5 text-sky-600" />
                <span>Re-center Truck</span>
              </button>

              {/* Stale Warning Overlay Banner if stale */}
              {truck?.is_stale && (
                <div className="absolute top-3 left-3 right-3 z-20 bg-amber-500/90 text-slate-950 px-3.5 py-2 rounded-xl text-xs font-bold backdrop-blur-sm shadow-md border border-amber-600/30 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                  <span>
                    GPS signal has not updated in over 15 minutes. Displaying the vehicle's last recorded location.
                  </span>
                </div>
              )}
            </div>
          ) : (
            /* Honest Unavailable State when coordinates are not available */
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center space-y-3">
              <div className="w-14 h-14 rounded-2xl bg-slate-200 text-slate-500 flex items-center justify-center">
                <Truck className="w-7 h-7" />
              </div>
              <div className="max-w-md space-y-1">
                <h3 className="text-sm font-bold text-slate-800">
                  {truck?.assigned ? "GPS Signal Currently Unavailable" : "No Truck Assigned"}
                </h3>
                <p className="text-xs text-slate-500 leading-relaxed">
                  {truck?.message ||
                    `No active GPS coordinates are currently transmitting for Ward ${
                      truck?.assigned_ward_number || wardNumber || "Verified Area"
                    }. The vehicle may be offline, undergoing depot maintenance, or outside operational shift hours.`}
                </p>
              </div>
              <button
                onClick={handleManualRefresh}
                className="px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-800 rounded-xl text-xs font-bold transition flex items-center gap-1.5 shadow-sm"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Retry Telemetry Check</span>
              </button>
            </div>
          )}
        </div>

        {/* Modal Footer / Telemetry Details */}
        <div className="p-4 bg-white border-t border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-4 text-slate-600">
            {truck?.vehicle_type && (
              <div>
                <span className="text-slate-400 text-[10px] block uppercase font-bold">Vehicle Type</span>
                <span className="font-semibold text-slate-800">{truck.vehicle_type}</span>
              </div>
            )}
            {hasCoordinates && (
              <div>
                <span className="text-slate-400 text-[10px] block uppercase font-bold">Coordinates</span>
                <span className="font-mono font-semibold text-slate-800">
                  {truck.latitude?.toFixed(4)}, {truck.longitude?.toFixed(4)}
                </span>
              </div>
            )}
            {truck?.current_fill_pct != null && (
              <div>
                <span className="text-slate-400 text-[10px] block uppercase font-bold">Bin Compactor Fill</span>
                <span className="font-bold text-teal-700">{truck.current_fill_pct}%</span>
              </div>
            )}
          </div>

          <div className="flex items-center gap-2 self-end sm:self-center">
            {lastUpdated && (
              <span className="text-[10px] text-slate-400">
                Poll updated {lastUpdated.toLocaleTimeString()}
              </span>
            )}
            <button
              onClick={onClose}
              className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-xl text-xs transition"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
