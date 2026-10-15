"use client";

import React from "react";
import { ProtectedRoute } from "@/components/ProtectedRoute";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <ProtectedRoute
      allowedRoles={[
        "system_admin",
        "ai_admin",
        "municipal_officer",
        "municipal_commissioner",
        "solid_waste_management_officer"
      ]}
      requiredPermissionTitle="Access to the Municipal Admin & AI Retraining Portal requires Administrator or Executive Officer privileges."
    >
      {children}
    </ProtectedRoute>
  );
}
