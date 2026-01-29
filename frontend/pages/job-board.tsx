import Head from "next/head";
import Layout from "../components/Layout";
import { useUser, useAuth } from "@clerk/nextjs";
import { useState, useEffect, useCallback } from "react";
import { createApiClient, JobPosting, CVVersion, GapAnalysis, JobProfile, DiscoveredJob, DiscoveredJobsSummary } from "../lib/api";
import { showToast } from "../components/Toast";
import { Skeleton } from "../components/Skeleton";
import Link from "next/link";

export default function JobBoard() {
    const { user, isLoaded: userLoaded } = useUser();
    const { getToken } = useAuth();

    const [jobPostings, setJobPostings] = useState<JobPosting[]>([]);
    const [cvVersions, setCvVersions] = useState<CVVersion[]>([]);
    const [discoveredJobs, setDiscoveredJobs] = useState<DiscoveredJob[]>([]);
    const [discoveredSummary, setDiscoveredSummary] = useState<DiscoveredJobsSummary | null>(null);
    const [loading, setLoading] = useState(true);
    const [loadingDiscovered, setLoadingDiscovered] = useState(true);
    const [uploading, setUploading] = useState(false);
    const [savingJobId, setSavingJobId] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<'my-jobs' | 'discover'>('my-jobs');

    // Modal state
    const [showModal, setShowModal] = useState(false);
    const [jobText, setJobText] = useState("");
    const [companyName, setCompanyName] = useState("");
    const [roleTitle, setRoleTitle] = useState("");
    const [jobUrl, setJobUrl] = useState("");
    const [location, setLocation] = useState("");
    const [remotePolicy, setRemotePolicy] = useState("");

    // Analysis modal state
    const [showAnalysisModal, setShowAnalysisModal] = useState(false);
    const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
    const [selectedCvId, setSelectedCvId] = useState<string>("");
    const [analyzing, setAnalyzing] = useState(false);
    const [analysisJobId, setAnalysisJobId] = useState<string | null>(null);

    // View job state
    const [selectedJob, setSelectedJob] = useState<JobPosting | null>(null);
    const [showJobDetail, setShowJobDetail] = useState(false);

    const loadData = useCallback(async () => {
        if (!userLoaded || !user) return;

        try {
            const token = await getToken();
            if (!token) return;

            const api = createApiClient(token);
            
            // Ensure user exists in database (creates if first time)
            await api.user.get();
            
            const [jobs, cvs] = await Promise.all([
                api.jobPostings.list(),
                api.cvVersions.list()
            ]);
            setJobPostings(jobs);
            setCvVersions(cvs);

            // Set default CV if available
            const primaryCv = cvs.find(cv => cv.is_primary);
            if (primaryCv) {
                setSelectedCvId(primaryCv.id);
            } else if (cvs.length > 0) {
                setSelectedCvId(cvs[0].id);
            }
        } catch (err) {
            console.error("Error loading data:", err);
            showToast("error", "Failed to load data");
        } finally {
            setLoading(false);
        }
    }, [userLoaded, user, getToken]);

    const loadDiscoveredJobs = useCallback(async () => {
        try {
            const token = await getToken();
            if (!token) return;

            const api = createApiClient(token);
            const [jobsResponse, summary] = await Promise.all([
                api.discoveredJobs.list({ limit: 20 }),
                api.discoveredJobs.getSummary()
            ]);
            setDiscoveredJobs(jobsResponse.jobs);
            setDiscoveredSummary(summary);
        } catch (err) {
            console.error("Error loading discovered jobs:", err);
            // Don't show error toast - discovered jobs are optional
        } finally {
            setLoadingDiscovered(false);
        }
    }, [getToken]);

    useEffect(() => {
        loadData();
    }, [loadData]);

    useEffect(() => {
        // Load discovered jobs when tab changes to discover, or on initial load
        if (activeTab === 'discover' || !loadingDiscovered) {
            loadDiscoveredJobs();
        }
    }, [activeTab, loadDiscoveredJobs, loadingDiscovered]);

    // Poll for analysis job completion
    useEffect(() => {
        if (!analysisJobId) return;

        const pollJob = async () => {
            try {
                const token = await getToken();
                if (!token) return;

                const api = createApiClient(token);
                const job = await api.jobs.get(analysisJobId);

                if (job.status === "completed") {
                    setAnalysisJobId(null);
                    setAnalyzing(false);
                    showToast("success", "Analysis complete!");
                    loadData();
                    setShowAnalysisModal(false);
                    // Navigate to analysis page
                    window.location.href = "/analysis";
                } else if (job.status === "failed") {
                    setAnalysisJobId(null);
                    setAnalyzing(false);
                    showToast("error", job.error_message || "Analysis failed");
                }
            } catch (err) {
                console.error("Error polling job:", err);
            }
        };

        const interval = setInterval(pollJob, 2000);
        return () => clearInterval(interval);
    }, [analysisJobId, getToken, loadData]);

    const handleAddJob = async () => {
        if (!jobText.trim() || jobText.length < 50) {
            showToast("error", "Please paste the job posting text (minimum 50 characters)");
            return;
        }

        setUploading(true);
        try {
            const token = await getToken();
            if (!token) return;

            const api = createApiClient(token);
            const newJob = await api.jobPostings.create({
                raw_text: jobText,
                company_name: companyName || undefined,
                role_title: roleTitle || undefined,
                url: jobUrl || undefined,
                location: location || undefined,
                remote_policy: remotePolicy || undefined
            });

            showToast("success", "Job posting saved!");
            setShowModal(false);
            setJobText("");
            setCompanyName("");
            setRoleTitle("");
            setJobUrl("");
            setLocation("");
            setRemotePolicy("");
            loadData();

            // Auto-trigger parsing
            await api.analyze.trigger({
                job_type: "job_parse",
                job_posting_id: newJob.id
            });
            showToast("info", "Parsing job posting with AI...");

        } catch (err) {
            console.error("Error adding job:", err);
            showToast("error", err instanceof Error ? err.message : "Failed to add job");
        } finally {
            setUploading(false);
        }
    };

    const handleDeleteJob = async (jobId: string) => {
        if (!confirm("Are you sure you want to delete this job posting?")) return;

        try {
            const token = await getToken();
            if (!token) return;

            const api = createApiClient(token);
            await api.jobPostings.delete(jobId);
            showToast("success", "Job deleted");
            loadData();
        } catch (err) {
            console.error("Error deleting job:", err);
            showToast("error", "Failed to delete job");
        }
    };

    const handleStartAnalysis = (jobId: string) => {
        setSelectedJobId(jobId);
        setShowAnalysisModal(true);
    };

    const handleRunAnalysis = async () => {
        if (!selectedJobId || !selectedCvId) {
            showToast("error", "Please select a CV for comparison");
            return;
        }

        setAnalyzing(true);
        try {
            const token = await getToken();
            if (!token) return;

            const api = createApiClient(token);
            const result = await api.analyze.trigger({
                job_type: "full_analysis",
                cv_version_id: selectedCvId,
                job_posting_id: selectedJobId
            });

            setAnalysisJobId(result.job_id);
            showToast("info", "Running full analysis... This may take a minute.");
        } catch (err) {
            console.error("Error running analysis:", err);
            showToast("error", "Failed to start analysis");
            setAnalyzing(false);
        }
    };

    const handleViewJob = async (jobId: string) => {
        try {
            const token = await getToken();
            if (!token) return;

            const api = createApiClient(token);
            const job = await api.jobPostings.get(jobId);
            setSelectedJob(job);
            setShowJobDetail(true);
        } catch (err) {
            console.error("Error loading job:", err);
            showToast("error", "Failed to load job details");
        }
    };

    const handleSaveDiscoveredJob = async (jobId: string) => {
        setSavingJobId(jobId);
        try {
            const token = await getToken();
            if (!token) return;

            const api = createApiClient(token);
            const result = await api.discoveredJobs.save(jobId);
            
            if (result.success) {
                showToast("success", result.message);
                // Refresh the user's job postings
                loadData();
                // Switch to My Jobs tab
                setActiveTab('my-jobs');
            } else {
                showToast("info", result.message);
            }
        } catch (err) {
            console.error("Error saving discovered job:", err);
            showToast("error", err instanceof Error ? err.message : "Failed to save job");
        } finally {
            setSavingJobId(null);
        }
    };

    const formatDate = (dateStr: string) => {
        return new Date(dateStr).toLocaleDateString("en-US", {
            year: "numeric",
            month: "short",
            day: "numeric"
        });
    };

    return (
        <>
            <Head>
                <title>Job Board - CareerAssist</title>
            </Head>
            <Layout>
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                    <div className="flex justify-between items-center mb-6">
                        <h1 className="text-3xl font-bold text-dark">Job Board</h1>
                        {activeTab === 'my-jobs' && (
                            <button
                                onClick={() => setShowModal(true)}
                                className="px-6 py-3 bg-primary text-white rounded-lg hover:bg-blue-600 transition-colors flex items-center gap-2"
                            >
                                <span>+</span> Add Job Posting
                            </button>
                        )}
                    </div>

                    {/* Tab Navigation */}
                    <div className="flex border-b border-gray-200 mb-6">
                        <button
                            onClick={() => setActiveTab('my-jobs')}
                            className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                                activeTab === 'my-jobs'
                                    ? 'border-primary text-primary'
                                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                            }`}
                        >
                            My Saved Jobs ({jobPostings.length})
                        </button>
                        <button
                            onClick={() => setActiveTab('discover')}
                            className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
                                activeTab === 'discover'
                                    ? 'border-primary text-primary'
                                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                            }`}
                        >
                            <span>Discover New Jobs</span>
                            {discoveredSummary && discoveredSummary.total_jobs > 0 && (
                                <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded-full">
                                    {discoveredSummary.total_jobs}
                                </span>
                            )}
                        </button>
                    </div>

                    {cvVersions.length === 0 && activeTab === 'my-jobs' && (
                        <div className="mb-6 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                            <p className="text-sm text-yellow-700">
                                <strong>Note:</strong> You haven't uploaded a CV yet.{" "}
                                <Link href="/cv-manager" className="text-primary hover:underline">
                                    Upload your CV first
                                </Link>{" "}
                                to run job fit analysis.
                            </p>
                        </div>
                    )}

                    {/* My Jobs Tab */}
                    {activeTab === 'my-jobs' && (
                        <>
                            {loading ? (
                                <div className="space-y-4">
                                    <Skeleton className="h-32 w-full" />
                                    <Skeleton className="h-32 w-full" />
                                </div>
                            ) : jobPostings.length === 0 ? (
                                <div className="bg-white rounded-lg shadow p-6">
                                    <div className="text-center py-12">
                                        <div className="text-6xl mb-4">💼</div>
                                        <h2 className="text-xl font-semibold text-gray-700 mb-2">No Jobs Saved Yet</h2>
                                        <p className="text-gray-500 mb-6">
                                            Save job postings to analyze fit and track your applications
                                        </p>
                                        <div className="flex justify-center gap-4">
                                            <button
                                                onClick={() => setShowModal(true)}
                                                className="px-6 py-3 bg-primary text-white rounded-lg hover:bg-blue-600 transition-colors"
                                            >
                                                Add Job Posting
                                            </button>
                                            <button
                                                onClick={() => setActiveTab('discover')}
                                                className="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                                            >
                                                Discover AI-Found Jobs
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            ) : (
                                <div className="grid gap-4">
                                    {jobPostings.map((job) => (
                                        <div key={job.id} className="bg-white rounded-lg shadow p-6">
                                            <div className="flex justify-between items-start">
                                                <div className="flex-1">
                                                    <div className="flex items-center gap-3">
                                                        <h3 className="text-lg font-semibold text-dark">
                                                            {job.role_title || "Job Posting"}
                                                        </h3>
                                                        {job.parsed_json && (
                                                            <span className="px-2 py-1 bg-green-100 text-green-700 text-xs rounded-full">
                                                                Parsed
                                                            </span>
                                                        )}
                                                    </div>
                                                    {job.company_name && (
                                                        <p className="text-gray-600 font-medium">{job.company_name}</p>
                                                    )}
                                                    <div className="flex flex-wrap gap-3 mt-2 text-sm text-gray-500">
                                                        {job.location && <span>📍 {job.location}</span>}
                                                        {job.remote_policy && <span>🏠 {job.remote_policy}</span>}
                                                        <span>📅 Added {formatDate(job.created_at)}</span>
                                                    </div>
                                                    {job.parsed_json && (
                                                        <div className="mt-2 flex flex-wrap gap-2">
                                                            {job.parsed_json.ats_keywords?.slice(0, 5).map((keyword, idx) => (
                                                                <span
                                                                    key={idx}
                                                                    className="px-2 py-1 bg-blue-50 text-blue-700 text-xs rounded"
                                                                >
                                                                    {keyword}
                                                                </span>
                                                            ))}
                                                            {job.parsed_json.ats_keywords && job.parsed_json.ats_keywords.length > 5 && (
                                                                <span className="text-xs text-gray-400">
                                                                    +{job.parsed_json.ats_keywords.length - 5} more
                                                                </span>
                                                            )}
                                                        </div>
                                                    )}
                                                    <p className="text-sm text-gray-400 mt-2 line-clamp-2">
                                                        {job.preview || job.raw_text?.substring(0, 200)}...
                                                    </p>
                                                </div>
                                                <div className="flex flex-col gap-2 ml-4">
                                                    <button
                                                        onClick={() => handleViewJob(job.id)}
                                                        className="px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200 transition-colors"
                                                    >
                                                        View
                                                    </button>
                                                    {cvVersions.length > 0 && (
                                                        <button
                                                            onClick={() => handleStartAnalysis(job.id)}
                                                            className="px-3 py-1.5 text-sm bg-ai-accent text-white rounded hover:bg-purple-700 transition-colors"
                                                        >
                                                            Analyze Fit
                                                        </button>
                                                    )}
                                                    <button
                                                        onClick={() => handleDeleteJob(job.id)}
                                                        className="px-3 py-1.5 text-sm bg-red-100 text-red-700 rounded hover:bg-red-200 transition-colors"
                                                    >
                                                        Delete
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}

                            <div className="mt-8 bg-green-50 border border-green-200 rounded-lg p-4">
                                <p className="text-sm text-green-700">
                                    <strong>Tip:</strong> Paste job descriptions to get AI analysis of how well your CV matches,
                                    identify skill gaps, and get suggestions for tailoring your application.
                                </p>
                            </div>
                        </>
                    )}

                    {/* Discover Jobs Tab */}
                    {activeTab === 'discover' && (
                        <>
                            {/* Summary Header */}
                            {discoveredSummary && discoveredSummary.total_jobs > 0 && (
                                <div className="mb-6 bg-gradient-to-r from-green-50 to-blue-50 border border-green-200 rounded-lg p-4">
                                    <div className="flex items-center justify-between">
                                        <div>
                                            <h3 className="font-semibold text-gray-800">
                                                AI-Discovered Jobs
                                            </h3>
                                            <p className="text-sm text-gray-600">
                                                {discoveredSummary.total_jobs} jobs found from{' '}
                                                {Object.keys(discoveredSummary.by_source).join(' & ')}
                                            </p>
                                        </div>
                                        {discoveredSummary.last_discovered && (
                                            <div className="text-right">
                                                <p className="text-xs text-gray-500">Last updated</p>
                                                <p className="text-sm text-gray-700">
                                                    {formatDate(discoveredSummary.last_discovered)}
                                                </p>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )}

                            {loadingDiscovered ? (
                                <div className="space-y-4">
                                    <Skeleton className="h-32 w-full" />
                                    <Skeleton className="h-32 w-full" />
                                    <Skeleton className="h-32 w-full" />
                                </div>
                            ) : discoveredJobs.length === 0 ? (
                                <div className="bg-white rounded-lg shadow p-6">
                                    <div className="text-center py-12">
                                        <div className="text-6xl mb-4">🔍</div>
                                        <h2 className="text-xl font-semibold text-gray-700 mb-2">No Discovered Jobs Yet</h2>
                                        <p className="text-gray-500 mb-2">
                                            Our AI researcher automatically discovers relevant jobs from Indeed and Glassdoor.
                                        </p>
                                        <p className="text-sm text-gray-400">
                                            New jobs are discovered every 5 hours. Check back soon!
                                        </p>
                                    </div>
                                </div>
                            ) : (
                                <div className="grid gap-4">
                                    {discoveredJobs.map((job) => (
                                        <div key={job.id} className="bg-white rounded-lg shadow p-6 border-l-4 border-green-400">
                                            <div className="flex justify-between items-start">
                                                <div className="flex-1">
                                                    <div className="flex items-center gap-3">
                                                        <h3 className="text-lg font-semibold text-dark">
                                                            {job.role_title}
                                                        </h3>
                                                        <span className={`px-2 py-1 text-xs rounded-full ${
                                                            job.source === 'indeed' 
                                                                ? 'bg-blue-100 text-blue-700' 
                                                                : 'bg-green-100 text-green-700'
                                                        }`}>
                                                            {job.source.charAt(0).toUpperCase() + job.source.slice(1)}
                                                        </span>
                                                    </div>
                                                    {job.company_name && (
                                                        <p className="text-gray-600 font-medium">{job.company_name}</p>
                                                    )}
                                                    <div className="flex flex-wrap gap-3 mt-2 text-sm text-gray-500">
                                                        {job.location && <span>📍 {job.location}</span>}
                                                        {job.remote_policy && job.remote_policy !== 'unknown' && (
                                                            <span>🏠 {job.remote_policy}</span>
                                                        )}
                                                        {(job.salary_min || job.salary_max) && (
                                                            <span>
                                                                💰 {job.salary_currency || '$'}
                                                                {job.salary_min?.toLocaleString()}
                                                                {job.salary_max ? ` - ${job.salary_max.toLocaleString()}` : '+'}
                                                            </span>
                                                        )}
                                                        <span>📅 Found {formatDate(job.discovered_at)}</span>
                                                    </div>
                                                    {job.description_text && (
                                                        <p className="text-sm text-gray-400 mt-2 line-clamp-2">
                                                            {job.description_text.substring(0, 200)}...
                                                        </p>
                                                    )}
                                                </div>
                                                <div className="flex flex-col gap-2 ml-4">
                                                    {job.source_url && (
                                                        <a
                                                            href={job.source_url}
                                                            target="_blank"
                                                            rel="noopener noreferrer"
                                                            className="px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200 transition-colors text-center"
                                                        >
                                                            View Original
                                                        </a>
                                                    )}
                                                    <button
                                                        onClick={() => handleSaveDiscoveredJob(job.id)}
                                                        disabled={savingJobId === job.id}
                                                        className={`px-3 py-1.5 text-sm rounded transition-colors ${
                                                            savingJobId === job.id
                                                                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                                                                : 'bg-primary text-white hover:bg-blue-600'
                                                        }`}
                                                    >
                                                        {savingJobId === job.id ? 'Saving...' : 'Save to My Jobs'}
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}

                            <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-4">
                                <p className="text-sm text-blue-700">
                                    <strong>How it works:</strong> Our AI researcher automatically browses Indeed and Glassdoor 
                                    every 5 hours to find relevant software engineering and data science jobs. 
                                    Save jobs to your board to run fit analysis with your CV.
                                </p>
                            </div>
                        </>
                    )}
                </div>

                {/* Add Job Modal */}
                {showModal && (
                    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                        <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                            <div className="p-6 border-b">
                                <h2 className="text-xl font-semibold text-dark">Add Job Posting</h2>
                                <p className="text-sm text-gray-500 mt-1">
                                    Paste the job description below. Our AI will extract key requirements.
                                </p>
                            </div>
                            <div className="p-6 space-y-4">
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                            Company Name
                                        </label>
                                        <input
                                            type="text"
                                            value={companyName}
                                            onChange={(e) => setCompanyName(e.target.value)}
                                            placeholder="e.g., Google"
                                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                            Role Title
                                        </label>
                                        <input
                                            type="text"
                                            value={roleTitle}
                                            onChange={(e) => setRoleTitle(e.target.value)}
                                            placeholder="e.g., Senior Software Engineer"
                                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                                        />
                                    </div>
                                </div>
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                            Location
                                        </label>
                                        <input
                                            type="text"
                                            value={location}
                                            onChange={(e) => setLocation(e.target.value)}
                                            placeholder="e.g., San Francisco, CA"
                                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                            Remote Policy
                                        </label>
                                        <select
                                            value={remotePolicy}
                                            onChange={(e) => setRemotePolicy(e.target.value)}
                                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                                        >
                                            <option value="">Select...</option>
                                            <option value="onsite">On-site</option>
                                            <option value="hybrid">Hybrid</option>
                                            <option value="remote">Remote</option>
                                        </select>
                                    </div>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        Job URL (optional)
                                    </label>
                                    <input
                                        type="url"
                                        value={jobUrl}
                                        onChange={(e) => setJobUrl(e.target.value)}
                                        placeholder="https://..."
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        Job Description *
                                    </label>
                                    <textarea
                                        value={jobText}
                                        onChange={(e) => setJobText(e.target.value)}
                                        placeholder="Paste the full job description here..."
                                        rows={10}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary resize-none"
                                    />
                                    <p className="text-xs text-gray-500 mt-1">
                                        {jobText.length} characters (minimum 50)
                                    </p>
                                </div>
                            </div>
                            <div className="p-6 border-t flex justify-end gap-3">
                                <button
                                    onClick={() => setShowModal(false)}
                                    className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleAddJob}
                                    disabled={uploading || jobText.length < 50}
                                    className={`px-6 py-2 rounded-lg font-medium transition-colors ${
                                        uploading || jobText.length < 50
                                            ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                                            : "bg-primary text-white hover:bg-blue-600"
                                    }`}
                                >
                                    {uploading ? "Saving..." : "Save & Parse"}
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {/* Analysis Modal */}
                {showAnalysisModal && (
                    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                        <div className="bg-white rounded-xl shadow-xl max-w-md w-full">
                            <div className="p-6 border-b">
                                <h2 className="text-xl font-semibold text-dark">Run Gap Analysis</h2>
                                <p className="text-sm text-gray-500 mt-1">
                                    Select a CV to compare against this job posting.
                                </p>
                            </div>
                            <div className="p-6">
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Select CV Version
                                </label>
                                <select
                                    value={selectedCvId}
                                    onChange={(e) => setSelectedCvId(e.target.value)}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                                >
                                    <option value="">Select a CV...</option>
                                    {cvVersions.map((cv) => (
                                        <option key={cv.id} value={cv.id}>
                                            {cv.version_name} {cv.is_primary ? "(Primary)" : ""}
                                        </option>
                                    ))}
                                </select>
                                <p className="text-xs text-gray-500 mt-2">
                                    This will analyze your CV against the job requirements and generate:
                                </p>
                                <ul className="text-xs text-gray-500 mt-1 list-disc list-inside">
                                    <li>Fit score and ATS compatibility</li>
                                    <li>Skills gaps and recommendations</li>
                                    <li>Tailored CV rewrite suggestions</li>
                                    <li>Interview preparation questions</li>
                                </ul>
                            </div>
                            <div className="p-6 border-t flex justify-end gap-3">
                                <button
                                    onClick={() => setShowAnalysisModal(false)}
                                    disabled={analyzing}
                                    className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleRunAnalysis}
                                    disabled={analyzing || !selectedCvId}
                                    className={`px-6 py-2 rounded-lg font-medium transition-colors ${
                                        analyzing || !selectedCvId
                                            ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                                            : "bg-ai-accent text-white hover:bg-purple-700"
                                    }`}
                                >
                                    {analyzing ? "Analyzing..." : "Run Full Analysis"}
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {/* Job Detail Modal */}
                {showJobDetail && selectedJob && (
                    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                        <div className="bg-white rounded-xl shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
                            <div className="p-6 border-b flex justify-between items-center">
                                <div>
                                    <h2 className="text-xl font-semibold text-dark">
                                        {selectedJob.role_title || "Job Posting"}
                                    </h2>
                                    {selectedJob.company_name && (
                                        <p className="text-gray-600">{selectedJob.company_name}</p>
                                    )}
                                </div>
                                <button
                                    onClick={() => setShowJobDetail(false)}
                                    className="text-gray-400 hover:text-gray-600 text-2xl"
                                >
                                    ×
                                </button>
                            </div>
                            <div className="p-6">
                                {selectedJob.parsed_json ? (
                                    <JobProfileDisplay profile={selectedJob.parsed_json} />
                                ) : (
                                    <div className="prose max-w-none">
                                        <pre className="whitespace-pre-wrap text-sm text-gray-600 bg-gray-50 p-4 rounded-lg">
                                            {selectedJob.raw_text}
                                        </pre>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                )}
            </Layout>
        </>
    );
}

// Job Profile Display Component
function JobProfileDisplay({ profile }: { profile: JobProfile }) {
    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="border-b pb-4">
                <h3 className="text-2xl font-bold text-dark">{profile.role_title}</h3>
                <p className="text-lg text-gray-600">{profile.company}</p>
                <div className="flex flex-wrap gap-4 mt-2 text-sm text-gray-500">
                    {profile.location && <span>📍 {profile.location}</span>}
                    {profile.remote_policy && <span>🏠 {profile.remote_policy}</span>}
                    {profile.seniority && <span>📊 {profile.seniority}</span>}
                    {profile.salary_min && profile.salary_max && (
                        <span>
                            💰 {profile.salary_currency} {profile.salary_min.toLocaleString()} - {profile.salary_max.toLocaleString()}
                        </span>
                    )}
                </div>
            </div>

            {/* Must Have Requirements */}
            {profile.must_have && profile.must_have.length > 0 && (
                <div>
                    <h4 className="text-lg font-semibold text-dark mb-3 flex items-center gap-2">
                        <span className="text-red-500">*</span> Must Have Requirements
                    </h4>
                    <ul className="space-y-2">
                        {profile.must_have.map((req, idx) => (
                            <li key={idx} className="flex items-start gap-2">
                                <span className="text-red-500 mt-1">•</span>
                                <div>
                                    <span className="text-gray-700">{req.text}</span>
                                    {req.years_required && (
                                        <span className="ml-2 text-xs text-gray-500">
                                            ({req.years_required}+ years)
                                        </span>
                                    )}
                                </div>
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {/* Nice to Have */}
            {profile.nice_to_have && profile.nice_to_have.length > 0 && (
                <div>
                    <h4 className="text-lg font-semibold text-dark mb-3">Nice to Have</h4>
                    <ul className="space-y-2">
                        {profile.nice_to_have.map((req, idx) => (
                            <li key={idx} className="flex items-start gap-2">
                                <span className="text-green-500 mt-1">•</span>
                                <span className="text-gray-700">{req.text}</span>
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {/* Responsibilities */}
            {profile.responsibilities && profile.responsibilities.length > 0 && (
                <div>
                    <h4 className="text-lg font-semibold text-dark mb-3">Responsibilities</h4>
                    <ul className="space-y-2">
                        {profile.responsibilities.map((resp, idx) => (
                            <li key={idx} className="flex items-start gap-2">
                                <span className="text-primary mt-1">•</span>
                                <span className="text-gray-700">{resp}</span>
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {/* ATS Keywords */}
            {profile.ats_keywords && profile.ats_keywords.length > 0 && (
                <div>
                    <h4 className="text-lg font-semibold text-dark mb-3">Key Skills / ATS Keywords</h4>
                    <div className="flex flex-wrap gap-2">
                        {profile.ats_keywords.map((keyword, idx) => (
                            <span
                                key={idx}
                                className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm"
                            >
                                {keyword}
                            </span>
                        ))}
                    </div>
                </div>
            )}

            {/* Benefits */}
            {profile.benefits && profile.benefits.length > 0 && (
                <div>
                    <h4 className="text-lg font-semibold text-dark mb-3">Benefits</h4>
                    <div className="flex flex-wrap gap-2">
                        {profile.benefits.map((benefit, idx) => (
                            <span
                                key={idx}
                                className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm"
                            >
                                {benefit}
                            </span>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
