"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "./api";

export interface User {
  id: number;
  username: string;
  email: string;
  full_name: string;
  role: "public" | "contributor" | "municipal_officer" | "plant_operator" | "ai_admin" | "system_admin";
  organization?: string;
  city?: string;
  profile_image?: string;
  is_active: boolean;
  contribution_points: number;
  badges: string;
  assigned_ward?: number;
  created_at: string;
  updated_at?: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string, rememberMe?: boolean) => Promise<void>;
  register: (data: { email: string; password: string; full_name: string; organization?: string; city?: string }) => Promise<void>;
  logout: () => void;
  updateProfile: (data: { full_name?: string; organization?: string; city?: string }) => Promise<User>;
  switchRole: (newRole: string) => Promise<void>;
  restoreSession: () => Promise<void>;
  refreshUser: () => Promise<void>;
  hasRole: (allowedRoles: string | string[]) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  // Load user and token from localStorage on mount
  useEffect(() => {
    const initAuth = async () => {
      try {
        const storedToken = localStorage.getItem("wastevision_token");
        const storedUser = localStorage.getItem("wastevision_user");

        if (storedToken && storedUser) {
          setToken(storedToken);
          setUser(JSON.parse(storedUser));
          // Silently refresh current user in background
          try {
            const currentUser = await api.getCurrentUser();
            if (currentUser) {
              setUser(currentUser);
              localStorage.setItem("wastevision_user", JSON.stringify(currentUser));
            }
          } catch (e) {
            console.warn("Could not silently refresh user session:", e);
          }
        }
      } catch (err) {
        console.error("Failed to initialize auth state:", err);
      } finally {
        setLoading(false);
      }
    };

    initAuth();
  }, []);

  const login = async (email: string, password: string, rememberMe: boolean = false) => {
    const response = await api.login({ email, password, remember_me: rememberMe });
    const { access_token, user: loggedInUser } = response;

    setToken(access_token);
    setUser(loggedInUser);

    localStorage.setItem("wastevision_token", access_token);
    localStorage.setItem("wastevision_user", JSON.stringify(loggedInUser));
  };

  const register = async (data: { email: string; password: string; full_name: string; organization?: string; city?: string }) => {
    const response = await api.register(data);
    const { access_token, user: newUser } = response;

    setToken(access_token);
    setUser(newUser);

    localStorage.setItem("wastevision_token", access_token);
    localStorage.setItem("wastevision_user", JSON.stringify(newUser));
  };

  const logout = () => {
    localStorage.removeItem("wastevision_token");
    localStorage.removeItem("wastevision_user");
    setToken(null);
    setUser(null);
    router.push("/login");
  };

  const updateProfile = async (data: { full_name?: string; organization?: string; city?: string }) => {
    const updated = await api.updateProfile(data);
    setUser(updated);
    localStorage.setItem("wastevision_user", JSON.stringify(updated));
    return updated;
  };

  const switchRole = async (newRole: string): Promise<void> => {
    try {
      const resp = await api.switchRole(newRole);
      if (resp && resp.user) {
        setUser(resp.user);
        localStorage.setItem("wastevision_user", JSON.stringify(resp.user));
        if (resp.access_token) {
          setToken(resp.access_token);
          localStorage.setItem("wastevision_token", resp.access_token);
        }
      }
    } catch (e: any) {
      console.error("Failed to switch role on server:", e);
      // Never mutate local state when the server rejects authorization
      throw e;
    }
  };

  const restoreSession = async (): Promise<void> => {
    try {
      const resp = await api.restoreSession();
      if (resp && resp.user) {
        setUser(resp.user);
        localStorage.setItem("wastevision_user", JSON.stringify(resp.user));
        if (resp.access_token) {
          setToken(resp.access_token);
          localStorage.setItem("wastevision_token", resp.access_token);
        }
      }
    } catch (e: any) {
      console.error("Failed to restore session on server:", e);
      throw e;
    }
  };

  const refreshUser = async () => {
    try {
      const currentUser = await api.getCurrentUser();
      if (currentUser) {
        setUser(currentUser);
        localStorage.setItem("wastevision_user", JSON.stringify(currentUser));
      }
    } catch (e) {
      console.error("Failed to refresh user:", e);
    }
  };

  const hasRole = (allowedRoles: string | string[]): boolean => {
    if (!user) return false;
    // System admin has access to all municipal operations
    if (user.role === "system_admin") return true;

    if (Array.isArray(allowedRoles)) {
      return allowedRoles.includes(user.role);
    }
    return user.role === allowedRoles;
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        isAuthenticated: !!user,
        login,
        register,
        logout,
        updateProfile,
        switchRole,
        restoreSession,
        refreshUser,
        hasRole,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}