import { useUser, useAuth } from "@clerk/nextjs";
import { useEffect, useState, useCallback } from "react";
import Layout from "../components/Layout";
import { Skeleton, SkeletonCard } from "../components/Skeleton";
import { showToast } from "../components/Toast";
import { createApiClient, DashboardStats, AnalysisJob } from "../lib/api";
import Head from "next/head";
import Link from "next/link";

export default function Dashboard() {
  const { user, isLoaded: userLoaded } = useUser();
  const { getToken } = useAuth();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [pendingJobs, setPendingJobs] = useState<AnalysisJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    if (!userLoaded || !user) return;

    try {
      const token = await getToken();
      if (!token) {
        setError("Not authenticated");
        setLoading(false);
        return;
      }

      const api = createApiClient(token);
      
      // Ensure user exists in database (creates if first time)
      await api.user.get();
      
      // Get dashboard stats
      const dashboardStats = await api.dashboard.getStats();
      setStats(dashboardStats);

      // Get pending jobs
      const jobsData = await api.jobs.list();
      const pending = jobsData.jobs.filter(j => j.status === "pending" || j.status === "processing");
      setPendingJobs(pending);

    } catch (err) {
      console.error("Error loading data:", err);
      setError(err instanceof Error ? err.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  }, [userLoaded, user, getToken]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Poll for pending jobs
  useEffect(() => {
    if (pendingJobs.length === 0) return;

    const poll = setInterval(async () => {
      try {
        const token = await getToken();
        if (!token) return;

        const api = createApiClient(token);
        const jobsData = await api.jobs.list();
        const pending = jobsData.jobs.filter(j => j.status === "pending" || j.status === "processing");
        setPendingJobs(pending);

        // Refresh stats if jobs completed
        if (pending.length < pendingJobs.length) {
          const newStats = await api.dashboard.getStats();
          setStats(newStats);
        }
      } catch (err) {
        console.error("Error polling jobs:", err);
      }
    }, 3000);

    return () => clearInterval(poll);
  }, [pendingJobs.length, getToken]);

  const getScoreColor = (score: number | null) => {
    if (score === null) return "text-gray-400";
    if (score >= 80) return "text-green-600";
    if (score >= 60) return "text-yellow-600";
    if (score >= 40) return "text-orange-600";
    return "text-red-600";
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    });
  };

  return (
    <>
      <Head>
        <title>Dashboard - CareerAssist AI Career Advisor</title>
      </Head>
      <Layout>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <h1 className="text-3xl font-bold text-dark mb-8">Dashboard</h1>

          {loading ? (
            <div className="space-y-8">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="bg-white rounded-lg shadow p-6">
                    <Skeleton className="h-4 w-3/4 mx-auto mb-3" />
                    <Skeleton className="h-8 w-1/2 mx-auto" />
                  </div>
                ))}
              </div>
              <SkeletonCard />
            </div>
          ) : error ? (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-red-600">{error}</p>
            </div>
          ) : (
            <>
              {/* Stats Cards */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
                <div className="bg-white rounded-lg shadow p-6 text-center">
                  <h3 className="text-sm font-medium text-gray-500 mb-3">CVs Uploaded</h3>
                  <p className="text-3xl font-bold text-primary">{stats?.cv_count || 0}</p>
                  <Link href="/cv-manager" className="text-sm text-primary hover:underline mt-2 inline-block">
                    Manage CVs →
                  </Link>
                </div>

                <div className="bg-white rounded-lg shadow p-6 text-center">
                  <h3 className="text-sm font-medium text-gray-500 mb-3">Jobs Saved</h3>
                  <p className="text-3xl font-bold text-dark">{stats?.job_count || 0}</p>
                  <Link href="/job-board" className="text-sm text-primary hover:underline mt-2 inline-block">
                    View Jobs →
                  </Link>
                </div>

                <div className="bg-white rounded-lg shadow p-6 text-center">
                  <h3 className="text-sm font-medium text-gray-500 mb-3">Analyses Run</h3>
                  <p className="text-3xl font-bold text-ai-accent">{stats?.analysis_count || 0}</p>
                  <Link href="/analysis" className="text-sm text-primary hover:underline mt-2 inline-block">
                    View Results →
                  </Link>
                </div>

                <div className="bg-white rounded-lg shadow p-6 text-center">
                  <h3 className="text-sm font-medium text-gray-500 mb-3">Avg Fit Score</h3>
                  <p className={`text-3xl font-bold ${getScoreColor(stats?.avg_fit_score ?? null)}`}>
                    {stats?.avg_fit_score !== null ? `${stats.avg_fit_score}%` : "—"}
                  </p>
                </div>
              </div>

              {/* Pending Jobs */}
              {pendingJobs.length > 0 && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-8">
                  <h3 className="font-semibold text-yellow-800 mb-2">Processing...</h3>
                  <div className="space-y-2">
                    {pendingJobs.map((job) => (
                      <div key={job.id} className="flex items-center gap-3">
                        <div className="animate-spin h-4 w-4 border-2 border-yellow-600 border-t-transparent rounded-full" />
                        <span className="text-sm text-yellow-700">
                          {job.job_type.replace(/_/g, " ")} - {job.status}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Quick Actions */}
              <div className="bg-white rounded-lg shadow p-6 mb-8">
                <h2 className="text-xl font-semibold text-dark mb-4">Quick Actions</h2>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <Link
                    href="/cv-manager"
                    className="flex items-center gap-4 p-4 border rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    <div className="text-3xl">📄</div>
                    <div>
                      <h3 className="font-medium text-dark">Upload CV</h3>
                      <p className="text-sm text-gray-500">Add a new CV version</p>
                    </div>
                  </Link>
                  <Link
                    href="/job-board"
                    className="flex items-center gap-4 p-4 border rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    <div className="text-3xl">💼</div>
                    <div>
                      <h3 className="font-medium text-dark">Add Job</h3>
                      <p className="text-sm text-gray-500">Paste a job posting</p>
                    </div>
                  </Link>
                  <Link
                    href="/analysis"
                    className="flex items-center gap-4 p-4 border rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    <div className="text-3xl">📊</div>
                    <div>
                      <h3 className="font-medium text-dark">View Analyses</h3>
                      <p className="text-sm text-gray-500">See gap analyses & interview prep</p>
                    </div>
                  </Link>
                </div>
              </div>

              {/* Recent Analyses */}
              <div className="bg-white rounded-lg shadow p-6 mb-8">
                <div className="flex justify-between items-center mb-4">
                  <h2 className="text-xl font-semibold text-dark">Recent Analyses</h2>
                  {stats && stats.recent_analyses.length > 0 && (
                    <Link href="/analysis" className="text-sm text-primary hover:underline">
                      View all →
                    </Link>
                  )}
                </div>
                {stats && stats.recent_analyses.length > 0 ? (
                  <div className="space-y-3">
                    {stats.recent_analyses.map((analysis) => (
                      <Link
                        key={analysis.id}
                        href="/analysis"
                        className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50 transition-colors"
                      >
                        <div>
                          <h4 className="font-medium text-dark">{analysis.role_title}</h4>
                          <p className="text-sm text-gray-500">{analysis.company_name}</p>
                        </div>
                        <div className="text-right">
                          <div className={`text-lg font-bold ${getScoreColor(analysis.fit_score)}`}>
                            {analysis.fit_score}%
                          </div>
                          <div className="text-xs text-gray-400">
                            ATS: {analysis.ats_score}%
                          </div>
                        </div>
                      </Link>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-500">
                    <p>No analyses yet.</p>
                    <p className="text-sm mt-1">
                      Upload a CV and add a job posting to get started!
                    </p>
                  </div>
                )}
              </div>

              {/* Getting Started Guide (if no data) */}
              {stats && stats.cv_count === 0 && stats.job_count === 0 && (
                <div className="bg-gradient-to-r from-primary/10 to-ai-accent/10 rounded-lg p-6">
                  <h2 className="text-xl font-semibold text-dark mb-4">Getting Started</h2>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div className="flex gap-4">
                      <div className="flex-shrink-0 w-8 h-8 bg-primary text-white rounded-full flex items-center justify-center font-bold">
                        1
                      </div>
                      <div>
                        <h3 className="font-medium text-dark">Upload Your CV</h3>
                        <p className="text-sm text-gray-600">
                          Paste your CV text and let our AI parse your skills and experience.
                        </p>
                      </div>
                    </div>
                    <div className="flex gap-4">
                      <div className="flex-shrink-0 w-8 h-8 bg-ai-accent text-white rounded-full flex items-center justify-center font-bold">
                        2
                      </div>
                      <div>
                        <h3 className="font-medium text-dark">Add Job Postings</h3>
                        <p className="text-sm text-gray-600">
                          Paste job descriptions to save and analyze for fit.
                        </p>
                      </div>
                    </div>
                    <div className="flex gap-4">
                      <div className="flex-shrink-0 w-8 h-8 bg-success text-white rounded-full flex items-center justify-center font-bold">
                        3
                      </div>
                      <div>
                        <h3 className="font-medium text-dark">Run Analysis</h3>
                        <p className="text-sm text-gray-600">
                          Get gap analysis, CV rewrites, and interview prep!
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </Layout>
    </>
  );
}
