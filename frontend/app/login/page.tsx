"use client";

import React, { useState, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { 
  Recycle, Mail, Lock, Eye, EyeOff, LogIn, 
  AlertCircle, CheckCircle, ShieldCheck, Sparkles, ArrowRight
} from "lucide-react";

function LoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectUrl = searchParams.get("redirect") || "/";

  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [isSlowResponseNotice, setIsSlowResponseNotice] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    // Guard against duplicate submission
    if (loading) return;

    setErrorMessage("");
    setIsSlowResponseNotice(false);

    const cleanEmail = email.trim();
    if (!cleanEmail || !password) {
      setErrorMessage("Please enter both your email address and password.");
      return;
    }

    setLoading(true);
    const t0 = performance.now();

    // Cold-start notification timer for Render free-tier latency
    const coldStartTimer = setTimeout(() => {
      setIsSlowResponseNotice(true);
    }, 4500);

    try {
      await login(cleanEmail, password, rememberMe);
      clearTimeout(coldStartTimer);
      const elapsed = Math.round(performance.now() - t0);
      console.info(`[Auth Performance] Login succeeded in ${elapsed}ms`);
      router.push(redirectUrl);
    } catch (err: any) {
      clearTimeout(coldStartTimer);
      setIsSlowResponseNotice(false);
      const elapsed = Math.round(performance.now() - t0);
      console.warn(`[Auth Performance] Login failed after ${elapsed}ms:`, err);
      setErrorMessage(
        err.message || "The email or password you entered is incorrect. Please try again."
      );
    } finally {
      clearTimeout(coldStartTimer);
      setLoading(false);
    }
  };

  const fillDemoAccount = (demoEmail: string, demoPass: string) => {
    setEmail(demoEmail);
    setPassword(demoPass);
    setErrorMessage("");
  };

  return (
    <div className="min-h-[80vh] flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        {/* Logo and Brand */}
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-teal-600 text-white shadow-lg shadow-teal-500/30 mb-4">
          <Recycle className="w-9 h-9" />
        </div>
        <h2 className="text-3xl font-extrabold text-navy-950 tracking-tight">
          WasteVision <span className="text-teal-600">AI</span>
        </h2>
        <p className="mt-2 text-sm text-slate-600">
          Sign in to access your waste management dashboard and AI tools.
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-6 shadow-xl shadow-slate-200/50 rounded-2xl border border-slate-200 sm:px-10">
          {errorMessage && (
            <div className="mb-6 bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl p-4 flex items-start space-x-3">
              <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
              <span>{errorMessage}</span>
            </div>
          )}

          {isSlowResponseNotice && (
            <div className="mb-6 bg-amber-50 border border-amber-200 text-amber-800 text-xs rounded-xl p-3.5 flex items-start space-x-2.5 animate-pulse">
              <Sparkles className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold">Waking up cloud service...</span>
                <p className="mt-0.5 text-amber-700">
                  The backend service on Render free-tier spins down after inactivity. Cold starts can take 30–60 seconds on initial wake-up. Subsequent logins will be instant.
                </p>
              </div>
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-5">
            {/* Email Field */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                Email Address
              </label>
              <div className="relative rounded-xl shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <Mail className="w-5 h-5" />
                </div>
                <input
                  type="email"
                  required
                  disabled={loading}
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@chennaiswm.gov.in"
                  className="block w-full pl-10 pr-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 text-sm placeholder-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-teal-500 transition-all disabled:opacity-60"
                />
              </div>
            </div>

            {/* Password Field */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider">
                  Password
                </label>
                <Link
                  href="/forgot-password"
                  className="text-xs font-semibold text-teal-600 hover:text-teal-700"
                >
                  Forgot Password?
                </Link>
              </div>
              <div className="relative rounded-xl shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <Lock className="w-5 h-5" />
                </div>
                <input
                  type={showPassword ? "text" : "password"}
                  required
                  disabled={loading}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="block w-full pl-10 pr-10 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 text-sm placeholder-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-teal-500 transition-all disabled:opacity-60"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-600"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            {/* Remember Me */}
            <div className="flex items-center">
              <input
                id="remember_me"
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                className="h-4 w-4 text-teal-600 focus:ring-teal-500 border-slate-300 rounded"
              />
              <label htmlFor="remember_me" className="ml-2 block text-sm text-slate-600 select-none">
                Remember me for 30 days
              </label>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center py-3 px-4 border border-transparent rounded-xl shadow-md text-sm font-semibold text-white bg-teal-600 hover:bg-teal-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-teal-500 transition-all disabled:opacity-60"
            >
              {loading ? (
                <div className="flex items-center space-x-2">
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Signing in...</span>
                </div>
              ) : (
                <div className="flex items-center space-x-2">
                  <LogIn className="w-4 h-4" />
                  <span>Sign In</span>
                </div>
              )}
            </button>
          </form>

          {/* Registration Link */}
          <div className="mt-6 text-center text-sm text-slate-600">
            Don't have an account?{" "}
            <Link
              href="/register"
              className="font-bold text-teal-600 hover:text-teal-700 hover:underline inline-flex items-center ml-1"
            >
              Create an account
              <ArrowRight className="w-3.5 h-3.5 ml-1" />
            </Link>
          </div>

          {/* Quick Demo Fill Buttons */}
          <div className="mt-8 pt-6 border-t border-slate-100">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3 flex items-center">
              <Sparkles className="w-3.5 h-3.5 text-amber-500 mr-1.5" />
              Quick Fill Demo Personas
            </p>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <button
                type="button"
                onClick={() => fillDemoAccount("admin@chennaiswm.gov.in", "Admin@123")}
                className="p-2 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg text-left text-slate-700 font-medium transition-colors"
              >
                <div className="font-semibold text-navy-900">System Admin</div>
                <div className="text-[10px] text-slate-500 truncate">admin@chennaiswm.gov.in</div>
              </button>
              <button
                type="button"
                onClick={() => fillDemoAccount("ai.lead@chennaiswm.gov.in", "Admin@123")}
                className="p-2 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg text-left text-slate-700 font-medium transition-colors"
              >
                <div className="font-semibold text-navy-900">AI Admin</div>
                <div className="text-[10px] text-slate-500 truncate">ai.lead@chennaiswm.gov.in</div>
              </button>
              <button
                type="button"
                onClick={() => fillDemoAccount("kumar.swm@chennaiswm.gov.in", "Officer@123")}
                className="p-2 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg text-left text-slate-700 font-medium transition-colors"
              >
                <div className="font-semibold text-navy-900">Municipal Officer</div>
                <div className="text-[10px] text-slate-500 truncate">kumar.swm@chennaiswm.gov.in</div>
              </button>
              <button
                type="button"
                onClick={() => fillDemoAccount("priya.chennai@gmail.com", "Citizen@123")}
                className="p-2 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg text-left text-slate-700 font-medium transition-colors"
              >
                <div className="font-semibold text-navy-900">Contributor</div>
                <div className="text-[10px] text-slate-500 truncate">priya.chennai@gmail.com</div>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="w-8 h-8 border-4 border-teal-600 border-t-transparent rounded-full animate-spin" />
      </div>
    }>
      <LoginContent />
    </Suspense>
  );
}