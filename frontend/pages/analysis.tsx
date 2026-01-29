import Head from "next/head";
import Layout from "../components/Layout";
import { useUser, useAuth } from "@clerk/nextjs";
import { useState, useEffect, useCallback } from "react";
import { createApiClient, GapAnalysis, AnalysisJob, GapItem, InterviewQuestion } from "../lib/api";
import { showToast } from "../components/Toast";
import { Skeleton } from "../components/Skeleton";

export default function Analysis() {
    const { user, isLoaded: userLoaded } = useUser();
    const { getToken } = useAuth();

    const [analyses, setAnalyses] = useState<GapAnalysis[]>([]);
    const [recentJobs, setRecentJobs] = useState<AnalysisJob[]>([]);
    const [loading, setLoading] = useState(true);

    // Selected analysis
    const [selectedAnalysis, setSelectedAnalysis] = useState<GapAnalysis | null>(null);
    const [selectedJob, setSelectedJob] = useState<AnalysisJob | null>(null);

    // Tab state
    const [activeTab, setActiveTab] = useState<"gap" | "rewrite" | "interview">("gap");

    const loadData = useCallback(async () => {
        if (!userLoaded || !user) return;

        try {
            const token = await getToken();
            if (!token) return;

            const api = createApiClient(token);
            
            // Ensure user exists in database (creates if first time)
            await api.user.get();
            
            const [analysisData, jobsData] = await Promise.all([
                api.gapAnalyses.list(),
                api.jobs.list()
            ]);
            
            setAnalyses(analysisData);
            
            // Filter to completed full_analysis jobs
            const completedJobs = jobsData.jobs
                .filter(j => j.status === "completed" && j.job_type === "full_analysis")
                .slice(0, 10);
            setRecentJobs(completedJobs);

            // Auto-select most recent if available
            if (completedJobs.length > 0) {
                const mostRecent = completedJobs[0];
                const fullJob = await api.jobs.get(mostRecent.id);
                setSelectedJob(fullJob);
            }
        } catch (err) {
            console.error("Error loading data:", err);
            showToast("error", "Failed to load analysis data");
        } finally {
            setLoading(false);
        }
    }, [userLoaded, user, getToken]);

    useEffect(() => {
        loadData();
    }, [loadData]);

    const handleSelectJob = async (jobId: string) => {
        try {
            const token = await getToken();
            if (!token) return;

            const api = createApiClient(token);
            const job = await api.jobs.get(jobId);
            setSelectedJob(job);
            setActiveTab("gap");
        } catch (err) {
            console.error("Error loading job:", err);
            showToast("error", "Failed to load analysis");
        }
    };

    const formatDate = (dateStr: string) => {
        return new Date(dateStr).toLocaleDateString("en-US", {
            year: "numeric",
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit"
        });
    };

    const getSeverityColor = (severity: string) => {
        switch (severity) {
            case "critical": return "bg-red-100 text-red-800 border-red-200";
            case "high": return "bg-orange-100 text-orange-800 border-orange-200";
            case "medium": return "bg-yellow-100 text-yellow-800 border-yellow-200";
            case "low": return "bg-green-100 text-green-800 border-green-200";
            default: return "bg-gray-100 text-gray-800 border-gray-200";
        }
    };

    const getScoreColor = (score: number) => {
        if (score >= 80) return "text-green-600";
        if (score >= 60) return "text-yellow-600";
        if (score >= 40) return "text-orange-600";
        return "text-red-600";
    };

    return (
        <>
            <Head>
                <title>Analysis Results - CareerAssist</title>
            </Head>
            <Layout>
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                    <h1 className="text-3xl font-bold text-dark mb-8">Analysis Results</h1>

                    {loading ? (
                        <div className="space-y-4">
                            <Skeleton className="h-32 w-full" />
                            <Skeleton className="h-64 w-full" />
                        </div>
                    ) : recentJobs.length === 0 ? (
                        <div className="bg-white rounded-lg shadow p-6">
                            <div className="text-center py-12">
                                <div className="text-6xl mb-4">📊</div>
                                <h2 className="text-xl font-semibold text-gray-700 mb-2">No Analyses Yet</h2>
                                <p className="text-gray-500 mb-6">
                                    Run a gap analysis from the Job Board to see results here
                                </p>
                                <a
                                    href="/job-board"
                                    className="px-6 py-3 bg-primary text-white rounded-lg hover:bg-blue-600 transition-colors inline-block"
                                >
                                    Go to Job Board
                                </a>
                            </div>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                            {/* Sidebar - Recent Analyses */}
                            <div className="lg:col-span-1">
                                <div className="bg-white rounded-lg shadow p-4">
                                    <h3 className="font-semibold text-dark mb-4">Recent Analyses</h3>
                                    <div className="space-y-2">
                                        {recentJobs.map((job) => (
                                            <button
                                                key={job.id}
                                                onClick={() => handleSelectJob(job.id)}
                                                className={`w-full text-left p-3 rounded-lg transition-colors ${
                                                    selectedJob?.id === job.id
                                                        ? "bg-primary/10 border border-primary"
                                                        : "bg-gray-50 hover:bg-gray-100"
                                                }`}
                                            >
                                                <div className="text-sm font-medium text-dark truncate">
                                                    {job.analyzer_payload?.gap_analysis?.company || "Analysis"}
                                                </div>
                                                <div className="text-xs text-gray-500">
                                                    {formatDate(job.created_at)}
                                                </div>
                                                {job.analyzer_payload?.gap_analysis?.fit_score && (
                                                    <div className={`text-sm font-bold mt-1 ${getScoreColor(job.analyzer_payload.gap_analysis.fit_score as number)}`}>
                                                        Fit: {job.analyzer_payload.gap_analysis.fit_score as number}%
                                                    </div>
                                                )}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            </div>

                            {/* Main Content */}
                            <div className="lg:col-span-3">
                                {selectedJob ? (
                                    <div className="bg-white rounded-lg shadow">
                                        {/* Tabs */}
                                        <div className="border-b">
                                            <div className="flex">
                                                <button
                                                    onClick={() => setActiveTab("gap")}
                                                    className={`px-6 py-4 font-medium transition-colors ${
                                                        activeTab === "gap"
                                                            ? "text-primary border-b-2 border-primary"
                                                            : "text-gray-500 hover:text-gray-700"
                                                    }`}
                                                >
                                                    Gap Analysis
                                                </button>
                                                <button
                                                    onClick={() => setActiveTab("rewrite")}
                                                    className={`px-6 py-4 font-medium transition-colors ${
                                                        activeTab === "rewrite"
                                                            ? "text-primary border-b-2 border-primary"
                                                            : "text-gray-500 hover:text-gray-700"
                                                    }`}
                                                >
                                                    CV Rewrite
                                                </button>
                                                <button
                                                    onClick={() => setActiveTab("interview")}
                                                    className={`px-6 py-4 font-medium transition-colors ${
                                                        activeTab === "interview"
                                                            ? "text-primary border-b-2 border-primary"
                                                            : "text-gray-500 hover:text-gray-700"
                                                    }`}
                                                >
                                                    Interview Prep
                                                </button>
                                            </div>
                                        </div>

                                        {/* Tab Content */}
                                        <div className="p-6">
                                            {activeTab === "gap" && (
                                                <GapAnalysisTab job={selectedJob} getScoreColor={getScoreColor} getSeverityColor={getSeverityColor} />
                                            )}
                                            {activeTab === "rewrite" && (
                                                <CVRewriteTab job={selectedJob} />
                                            )}
                                            {activeTab === "interview" && (
                                                <InterviewPrepTab job={selectedJob} />
                                            )}
                                        </div>
                                    </div>
                                ) : (
                                    <div className="bg-white rounded-lg shadow p-6 text-center text-gray-500">
                                        Select an analysis from the sidebar
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            </Layout>
        </>
    );
}

// Gap Analysis Tab Component
function GapAnalysisTab({ job, getScoreColor, getSeverityColor }: { 
    job: AnalysisJob; 
    getScoreColor: (score: number) => string;
    getSeverityColor: (severity: string) => string;
}) {
    const gapAnalysis = job.analyzer_payload?.gap_analysis as any;
    
    if (!gapAnalysis) {
        return <div className="text-gray-500">No gap analysis data available</div>;
    }

    return (
        <div className="space-y-6">
            {/* Scores */}
            <div className="grid grid-cols-2 gap-4">
                <div className="bg-gray-50 rounded-lg p-4 text-center">
                    <div className="text-sm text-gray-500 mb-1">Fit Score</div>
                    <div className={`text-4xl font-bold ${getScoreColor(gapAnalysis.fit_score || 0)}`}>
                        {gapAnalysis.fit_score || 0}%
                    </div>
                </div>
                <div className="bg-gray-50 rounded-lg p-4 text-center">
                    <div className="text-sm text-gray-500 mb-1">ATS Score</div>
                    <div className={`text-4xl font-bold ${getScoreColor(gapAnalysis.ats_score || 0)}`}>
                        {gapAnalysis.ats_score || 0}%
                    </div>
                </div>
            </div>

            {/* Summary */}
            {gapAnalysis.summary && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <h4 className="font-semibold text-blue-800 mb-2">Summary</h4>
                    <p className="text-blue-700">{gapAnalysis.summary}</p>
                </div>
            )}

            {/* Strengths */}
            {gapAnalysis.strengths && gapAnalysis.strengths.length > 0 && (
                <div>
                    <h4 className="font-semibold text-dark mb-3 flex items-center gap-2">
                        <span className="text-green-500">✓</span> Strengths
                    </h4>
                    <ul className="space-y-2">
                        {gapAnalysis.strengths.map((strength: string, idx: number) => (
                            <li key={idx} className="flex items-start gap-2 text-gray-700">
                                <span className="text-green-500 mt-1">•</span>
                                {strength}
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {/* Gaps */}
            {gapAnalysis.gaps && gapAnalysis.gaps.length > 0 && (
                <div>
                    <h4 className="font-semibold text-dark mb-3 flex items-center gap-2">
                        <span className="text-orange-500">!</span> Gaps to Address
                    </h4>
                    <div className="space-y-3">
                        {gapAnalysis.gaps.map((gap: GapItem, idx: number) => (
                            <div key={idx} className={`border rounded-lg p-4 ${getSeverityColor(gap.severity)}`}>
                                <div className="flex justify-between items-start mb-2">
                                    <span className="font-medium">{gap.requirement}</span>
                                    <span className={`text-xs px-2 py-1 rounded-full ${getSeverityColor(gap.severity)}`}>
                                        {gap.severity}
                                    </span>
                                </div>
                                <p className="text-sm mb-2">{gap.missing_element}</p>
                                <p className="text-sm text-gray-600">
                                    <strong>Recommendation:</strong> {gap.recommendation}
                                </p>
                                {gap.estimated_time && (
                                    <p className="text-xs text-gray-500 mt-1">
                                        Est. time to address: {gap.estimated_time}
                                    </p>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Action Items */}
            {gapAnalysis.action_items && gapAnalysis.action_items.length > 0 && (
                <div>
                    <h4 className="font-semibold text-dark mb-3">Action Items</h4>
                    <ol className="space-y-2">
                        {gapAnalysis.action_items.map((item: string, idx: number) => (
                            <li key={idx} className="flex items-start gap-3">
                                <span className="flex-shrink-0 w-6 h-6 bg-primary text-white rounded-full flex items-center justify-center text-sm">
                                    {idx + 1}
                                </span>
                                <span className="text-gray-700">{item}</span>
                            </li>
                        ))}
                    </ol>
                </div>
            )}

            {/* Missing Keywords */}
            {gapAnalysis.keywords_missing && gapAnalysis.keywords_missing.length > 0 && (
                <div>
                    <h4 className="font-semibold text-dark mb-3">Missing ATS Keywords</h4>
                    <div className="flex flex-wrap gap-2">
                        {gapAnalysis.keywords_missing.map((keyword: string, idx: number) => (
                            <span key={idx} className="px-3 py-1 bg-red-100 text-red-700 rounded-full text-sm">
                                {keyword}
                            </span>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

// CV Rewrite Tab Component
function CVRewriteTab({ job }: { job: AnalysisJob }) {
    const cvRewrite = job.analyzer_payload?.cv_rewrite || job.summary_payload;
    const cvRewriteError = (job.analyzer_payload as any)?.cv_rewrite_error;
    
    if (!cvRewrite) {
        if (cvRewriteError) {
            return (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                    <h4 className="font-semibold text-red-800 mb-2">CV Rewrite Failed</h4>
                    <p className="text-red-700">{cvRewriteError}</p>
                    <p className="text-sm text-red-600 mt-2">
                        Please try running the analysis again. If the problem persists, check your CV and job posting for any formatting issues.
                    </p>
                </div>
            );
        }
        return <div className="text-gray-500">No CV rewrite data available</div>;
    }

    return (
        <div className="space-y-6">
            {/* Rewritten Summary */}
            {(cvRewrite as any).rewritten_summary && (
                <div>
                    <h4 className="font-semibold text-dark mb-3">Optimized Professional Summary</h4>
                    <div className="bg-gray-50 rounded-lg p-4 text-gray-700">
                        {(cvRewrite as any).rewritten_summary}
                    </div>
                    <button
                        onClick={() => navigator.clipboard.writeText((cvRewrite as any).rewritten_summary)}
                        className="mt-2 text-sm text-primary hover:underline"
                    >
                        Copy to clipboard
                    </button>
                </div>
            )}

            {/* Rewritten Bullets */}
            {(cvRewrite as any).rewritten_bullets && (cvRewrite as any).rewritten_bullets.length > 0 && (
                <div>
                    <h4 className="font-semibold text-dark mb-3">Improved Experience Bullets</h4>
                    <div className="space-y-4">
                        {(cvRewrite as any).rewritten_bullets.map((bullet: any, idx: number) => (
                            <div key={idx} className="border rounded-lg p-4">
                                {bullet.original && (
                                    <div className="mb-2">
                                        <span className="text-xs text-gray-500">Original:</span>
                                        <p className="text-sm text-gray-500 line-through">{bullet.original}</p>
                                    </div>
                                )}
                                <div>
                                    <span className="text-xs text-green-600">Improved:</span>
                                    <p className="text-gray-700">{bullet.improved || bullet}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Skills to Highlight */}
            {(cvRewrite as any).skills_to_highlight && (cvRewrite as any).skills_to_highlight.length > 0 && (
                <div>
                    <h4 className="font-semibold text-dark mb-3">Skills to Highlight</h4>
                    <div className="flex flex-wrap gap-2">
                        {(cvRewrite as any).skills_to_highlight.map((skill: string, idx: number) => (
                            <span key={idx} className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm">
                                {skill}
                            </span>
                        ))}
                    </div>
                </div>
            )}

            {/* Cover Letter */}
            {(cvRewrite as any).cover_letter && (
                <div>
                    <h4 className="font-semibold text-dark mb-3">Generated Cover Letter</h4>
                    <div className="bg-gray-50 rounded-lg p-4">
                        <pre className="whitespace-pre-wrap text-sm text-gray-700 font-sans">
                            {(cvRewrite as any).cover_letter}
                        </pre>
                    </div>
                    <button
                        onClick={() => navigator.clipboard.writeText((cvRewrite as any).cover_letter)}
                        className="mt-2 text-sm text-primary hover:underline"
                    >
                        Copy to clipboard
                    </button>
                </div>
            )}

            {/* LinkedIn Summary */}
            {(cvRewrite as any).linkedin_summary && (
                <div>
                    <h4 className="font-semibold text-dark mb-3">LinkedIn Summary</h4>
                    <div className="bg-blue-50 rounded-lg p-4 text-gray-700">
                        {(cvRewrite as any).linkedin_summary}
                    </div>
                    <button
                        onClick={() => navigator.clipboard.writeText((cvRewrite as any).linkedin_summary)}
                        className="mt-2 text-sm text-primary hover:underline"
                    >
                        Copy to clipboard
                    </button>
                </div>
            )}
        </div>
    );
}

// Interview Prep Tab Component
function InterviewPrepTab({ job }: { job: AnalysisJob }) {
    const interviewData = job.interviewer_payload?.interview_pack || job.interviewer_payload;
    
    if (!interviewData) {
        return <div className="text-gray-500">No interview prep data available</div>;
    }

    const [expandedQuestion, setExpandedQuestion] = useState<string | null>(null);

    const getDifficultyColor = (difficulty: string) => {
        switch (difficulty) {
            case "easy": return "bg-green-100 text-green-700";
            case "medium": return "bg-yellow-100 text-yellow-700";
            case "hard": return "bg-red-100 text-red-700";
            default: return "bg-gray-100 text-gray-700";
        }
    };

    const getTypeIcon = (type: string) => {
        switch (type) {
            case "behavioral": return "🗣️";
            case "technical": return "💻";
            case "situational": return "🎯";
            case "motivation": return "💡";
            default: return "❓";
        }
    };

    return (
        <div className="space-y-6">
            {/* Focus Areas */}
            {(interviewData as any).focus_areas && (interviewData as any).focus_areas.length > 0 && (
                <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
                    <h4 className="font-semibold text-purple-800 mb-2">Key Focus Areas</h4>
                    <ul className="list-disc list-inside text-purple-700">
                        {(interviewData as any).focus_areas.map((area: string, idx: number) => (
                            <li key={idx}>{area}</li>
                        ))}
                    </ul>
                </div>
            )}

            {/* Company Tips */}
            {(interviewData as any).company_specific_tips && (interviewData as any).company_specific_tips.length > 0 && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <h4 className="font-semibold text-blue-800 mb-2">Company-Specific Tips</h4>
                    <ul className="list-disc list-inside text-blue-700">
                        {(interviewData as any).company_specific_tips.map((tip: string, idx: number) => (
                            <li key={idx}>{tip}</li>
                        ))}
                    </ul>
                </div>
            )}

            {/* Questions */}
            {(interviewData as any).questions && (interviewData as any).questions.length > 0 && (
                <div>
                    <h4 className="font-semibold text-dark mb-3">
                        Practice Questions ({(interviewData as any).questions.length})
                    </h4>
                    <div className="space-y-3">
                        {(interviewData as any).questions.map((q: InterviewQuestion, idx: number) => (
                            <div key={q.id || idx} className="border rounded-lg overflow-hidden">
                                <button
                                    onClick={() => setExpandedQuestion(expandedQuestion === q.id ? null : q.id)}
                                    className="w-full p-4 text-left flex items-start justify-between hover:bg-gray-50"
                                >
                                    <div className="flex-1">
                                        <div className="flex items-center gap-2 mb-1">
                                            <span className="text-lg">{getTypeIcon(q.type)}</span>
                                            <span className={`text-xs px-2 py-0.5 rounded ${getDifficultyColor(q.difficulty)}`}>
                                                {q.difficulty}
                                            </span>
                                            <span className="text-xs text-gray-500">{q.type}</span>
                                        </div>
                                        <p className="font-medium text-dark">{q.question}</p>
                                    </div>
                                    <span className="text-gray-400 ml-2">
                                        {expandedQuestion === q.id ? "−" : "+"}
                                    </span>
                                </button>
                                {expandedQuestion === q.id && (
                                    <div className="px-4 pb-4 border-t bg-gray-50">
                                        <div className="mt-3 space-y-3">
                                            {q.what_theyre_testing && (
                                                <div>
                                                    <span className="text-xs font-semibold text-gray-500">What they're testing:</span>
                                                    <p className="text-sm text-gray-700">{q.what_theyre_testing}</p>
                                                </div>
                                            )}
                                            {q.sample_answer_outline && (
                                                <div>
                                                    <span className="text-xs font-semibold text-gray-500">Answer outline:</span>
                                                    <p className="text-sm text-gray-700">{q.sample_answer_outline}</p>
                                                </div>
                                            )}
                                            {q.follow_up_questions && q.follow_up_questions.length > 0 && (
                                                <div>
                                                    <span className="text-xs font-semibold text-gray-500">Possible follow-ups:</span>
                                                    <ul className="text-sm text-gray-700 list-disc list-inside">
                                                        {q.follow_up_questions.map((fu, i) => (
                                                            <li key={i}>{fu}</li>
                                                        ))}
                                                    </ul>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* General Tips */}
            {(interviewData as any).general_tips && (interviewData as any).general_tips.length > 0 && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                    <h4 className="font-semibold text-green-800 mb-2">General Tips</h4>
                    <ul className="list-disc list-inside text-green-700">
                        {(interviewData as any).general_tips.map((tip: string, idx: number) => (
                            <li key={idx}>{tip}</li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
}
