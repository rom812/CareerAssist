import Head from "next/head";
import Layout from "../components/Layout";
import { useUser, useAuth } from "@clerk/nextjs";
import { useState, useEffect, useCallback } from "react";
import { createApiClient, ResearchFinding, MarketInsightsSummary } from "../lib/api";
import { showToast } from "../components/Toast";
import { Skeleton } from "../components/Skeleton";

// Category configuration
const CATEGORIES = [
    { id: "all", label: "All Insights", icon: "📊" },
    { id: "role_trend", label: "Trending Roles", icon: "💼" },
    { id: "skill_demand", label: "Skills in Demand", icon: "🚀" },
    { id: "salary_insight", label: "Salary Insights", icon: "💰" },
    { id: "industry_news", label: "Industry News", icon: "📰" },
] as const;

type CategoryId = typeof CATEGORIES[number]["id"];

export default function MarketInsights() {
    const { user, isLoaded: userLoaded } = useUser();
    const { getToken } = useAuth();

    const [findings, setFindings] = useState<ResearchFinding[]>([]);
    const [summary, setSummary] = useState<MarketInsightsSummary | null>(null);
    const [loading, setLoading] = useState(true);
    const [selectedCategory, setSelectedCategory] = useState<CategoryId>("all");
    const [selectedFinding, setSelectedFinding] = useState<ResearchFinding | null>(null);

    const loadData = useCallback(async () => {
        if (!userLoaded || !user) return;

        try {
            const token = await getToken();
            if (!token) return;

            const api = createApiClient(token);

            // Load summary and findings in parallel
            const [summaryData, findingsData] = await Promise.all([
                api.researchFindings.getSummary(),
                api.researchFindings.list({
                    category: selectedCategory === "all" ? undefined : selectedCategory,
                    limit: 20,
                }),
            ]);

            setSummary(summaryData);
            setFindings(findingsData.findings);
        } catch (err) {
            console.error("Error loading market insights:", err);
            showToast("error", "Failed to load market insights");
        } finally {
            setLoading(false);
        }
    }, [userLoaded, user, getToken, selectedCategory]);

    useEffect(() => {
        loadData();
    }, [loadData]);

    // Reload when category changes
    const handleCategoryChange = async (category: CategoryId) => {
        setSelectedCategory(category);
        setLoading(true);

        try {
            const token = await getToken();
            if (!token) return;

            const api = createApiClient(token);
            const findingsData = await api.researchFindings.list({
                category: category === "all" ? undefined : category,
                limit: 20,
            });
            setFindings(findingsData.findings);
        } catch (err) {
            console.error("Error loading findings:", err);
            showToast("error", "Failed to load findings");
        } finally {
            setLoading(false);
        }
    };

    const formatDate = (dateStr: string) => {
        return new Date(dateStr).toLocaleDateString("en-US", {
            year: "numeric",
            month: "short",
            day: "numeric",
        });
    };

    const formatTimeAgo = (dateStr: string) => {
        const date = new Date(dateStr);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
        const diffDays = Math.floor(diffHours / 24);

        if (diffHours < 1) return "Just now";
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;
        return formatDate(dateStr);
    };

    const getCategoryIcon = (category: string) => {
        const cat = CATEGORIES.find((c) => c.id === category);
        return cat?.icon || "📄";
    };

    const getCategoryLabel = (category: string) => {
        const cat = CATEGORIES.find((c) => c.id === category);
        return cat?.label || category;
    };

    const getCategoryColor = (category: string) => {
        switch (category) {
            case "role_trend":
                return "bg-blue-100 text-blue-800";
            case "skill_demand":
                return "bg-green-100 text-green-800";
            case "salary_insight":
                return "bg-yellow-100 text-yellow-800";
            case "industry_news":
                return "bg-purple-100 text-purple-800";
            default:
                return "bg-gray-100 text-gray-800";
        }
    };

    return (
        <>
            <Head>
                <title>Market Insights - CareerAssist</title>
            </Head>
            <Layout>
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                    {/* Header */}
                    <div className="mb-8">
                        <h1 className="text-3xl font-bold text-dark">Market Insights</h1>
                        <p className="text-gray-600 mt-2">
                            AI-researched career trends, job market data, and industry insights updated regularly
                        </p>
                    </div>

                    {loading && !summary ? (
                        <div className="space-y-4">
                            <Skeleton className="h-24 w-full" />
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                <Skeleton className="h-48 w-full" />
                                <Skeleton className="h-48 w-full" />
                                <Skeleton className="h-48 w-full" />
                            </div>
                        </div>
                    ) : findings.length === 0 && !summary?.total_findings ? (
                        <div className="bg-white rounded-lg shadow p-6">
                            <div className="text-center py-12">
                                <div className="text-6xl mb-4">🔍</div>
                                <h2 className="text-xl font-semibold text-gray-700 mb-2">
                                    No Market Insights Yet
                                </h2>
                                <p className="text-gray-500 mb-6 max-w-md mx-auto">
                                    Our AI researcher is gathering the latest job market trends.
                                    Check back soon for trending roles, in-demand skills, and salary insights!
                                </p>
                                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 max-w-md mx-auto">
                                    <p className="text-sm text-blue-700">
                                        <strong>Tip:</strong> Market insights are updated every 2 hours by our AI researcher agent.
                                    </p>
                                </div>
                            </div>
                        </div>
                    ) : (
                        <>
                            {/* Summary Stats */}
                            {summary && summary.total_findings > 0 && (
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                                    <div className="bg-white rounded-lg shadow p-4 text-center">
                                        <div className="text-3xl font-bold text-primary">
                                            {summary.total_findings}
                                        </div>
                                        <div className="text-sm text-gray-500">Total Insights</div>
                                    </div>
                                    <div className="bg-white rounded-lg shadow p-4 text-center">
                                        <div className="text-3xl font-bold text-blue-600">
                                            {summary.by_category?.role_trend || 0}
                                        </div>
                                        <div className="text-sm text-gray-500">Trending Roles</div>
                                    </div>
                                    <div className="bg-white rounded-lg shadow p-4 text-center">
                                        <div className="text-3xl font-bold text-green-600">
                                            {summary.by_category?.skill_demand || 0}
                                        </div>
                                        <div className="text-sm text-gray-500">Skills Tracked</div>
                                    </div>
                                    <div className="bg-white rounded-lg shadow p-4 text-center">
                                        <div className="text-3xl font-bold text-yellow-600">
                                            {summary.by_category?.salary_insight || 0}
                                        </div>
                                        <div className="text-sm text-gray-500">Salary Reports</div>
                                    </div>
                                </div>
                            )}

                            {/* Category Tabs */}
                            <div className="bg-white rounded-lg shadow mb-6">
                                <div className="border-b overflow-x-auto">
                                    <div className="flex">
                                        {CATEGORIES.map((category) => (
                                            <button
                                                key={category.id}
                                                onClick={() => handleCategoryChange(category.id)}
                                                className={`px-6 py-4 font-medium transition-colors whitespace-nowrap flex items-center gap-2 ${
                                                    selectedCategory === category.id
                                                        ? "text-primary border-b-2 border-primary"
                                                        : "text-gray-500 hover:text-gray-700"
                                                }`}
                                            >
                                                <span>{category.icon}</span>
                                                <span>{category.label}</span>
                                                {summary?.by_category?.[category.id as keyof typeof summary.by_category] !== undefined && (
                                                    <span className="ml-1 text-xs bg-gray-100 px-2 py-0.5 rounded-full">
                                                        {category.id === "all"
                                                            ? summary.total_findings
                                                            : summary.by_category[category.id as keyof typeof summary.by_category] || 0}
                                                    </span>
                                                )}
                                            </button>
                                        ))}
                                    </div>
                                </div>

                                {/* Findings Grid */}
                                <div className="p-6">
                                    {loading ? (
                                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                            <Skeleton className="h-48 w-full" />
                                            <Skeleton className="h-48 w-full" />
                                            <Skeleton className="h-48 w-full" />
                                        </div>
                                    ) : findings.length === 0 ? (
                                        <div className="text-center py-8 text-gray-500">
                                            <p>No insights in this category yet.</p>
                                        </div>
                                    ) : (
                                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                            {findings.map((finding) => (
                                                <FindingCard
                                                    key={finding.id}
                                                    finding={finding}
                                                    onClick={() => setSelectedFinding(finding)}
                                                    getCategoryColor={getCategoryColor}
                                                    getCategoryIcon={getCategoryIcon}
                                                    formatTimeAgo={formatTimeAgo}
                                                />
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* Info Banner */}
                            <div className="bg-gradient-to-r from-primary/10 to-ai-accent/10 rounded-lg p-4">
                                <p className="text-sm text-gray-700">
                                    <strong>About Market Insights:</strong> Our AI researcher agent browses
                                    LinkedIn, Indeed, Glassdoor, and other sources to gather the latest job
                                    market trends. Insights are updated every 2 hours.
                                </p>
                            </div>
                        </>
                    )}

                    {/* Finding Detail Modal */}
                    {selectedFinding && (
                        <FindingDetailModal
                            finding={selectedFinding}
                            onClose={() => setSelectedFinding(null)}
                            getCategoryColor={getCategoryColor}
                            getCategoryLabel={getCategoryLabel}
                            formatDate={formatDate}
                        />
                    )}
                </div>
            </Layout>
        </>
    );
}

// Finding Card Component
function FindingCard({
    finding,
    onClick,
    getCategoryColor,
    getCategoryIcon,
    formatTimeAgo,
}: {
    finding: ResearchFinding;
    onClick: () => void;
    getCategoryColor: (category: string) => string;
    getCategoryIcon: (category: string) => string;
    formatTimeAgo: (date: string) => string;
}) {
    return (
        <button
            onClick={onClick}
            className="bg-gray-50 rounded-lg p-4 text-left hover:bg-gray-100 transition-colors border border-gray-200 flex flex-col h-full"
        >
            <div className="flex items-start justify-between mb-2">
                <span
                    className={`text-xs px-2 py-1 rounded-full ${getCategoryColor(
                        finding.category
                    )}`}
                >
                    {getCategoryIcon(finding.category)} {finding.category.replace("_", " ")}
                </span>
                {finding.is_featured && (
                    <span className="text-yellow-500" title="Featured">
                        ⭐
                    </span>
                )}
            </div>
            <h3 className="font-semibold text-dark mb-2 line-clamp-2">{finding.title}</h3>
            <p className="text-sm text-gray-600 mb-3 line-clamp-3 flex-grow">
                {finding.summary}
            </p>
            <div className="flex items-center justify-between text-xs text-gray-400 mt-auto">
                <span>{formatTimeAgo(finding.created_at)}</span>
                <span className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-green-500"></span>
                    {finding.relevance_score}% relevant
                </span>
            </div>
        </button>
    );
}

// Finding Detail Modal Component
function FindingDetailModal({
    finding,
    onClose,
    getCategoryColor,
    getCategoryLabel,
    formatDate,
}: {
    finding: ResearchFinding;
    onClose: () => void;
    getCategoryColor: (category: string) => string;
    getCategoryLabel: (category: string) => string;
    formatDate: (date: string) => string;
}) {
    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                <div className="p-6 border-b flex justify-between items-start">
                    <div>
                        <div className="flex items-center gap-2 mb-2">
                            <span
                                className={`text-xs px-2 py-1 rounded-full ${getCategoryColor(
                                    finding.category
                                )}`}
                            >
                                {getCategoryLabel(finding.category)}
                            </span>
                            {finding.is_featured && (
                                <span className="text-xs px-2 py-1 bg-yellow-100 text-yellow-800 rounded-full">
                                    ⭐ Featured
                                </span>
                            )}
                        </div>
                        <h2 className="text-xl font-semibold text-dark">{finding.title}</h2>
                        <p className="text-sm text-gray-500 mt-1">
                            {finding.topic} • {formatDate(finding.created_at)}
                        </p>
                    </div>
                    <button
                        onClick={onClose}
                        className="text-gray-400 hover:text-gray-600 text-2xl"
                    >
                        ×
                    </button>
                </div>
                <div className="p-6">
                    {/* Summary */}
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
                        <h4 className="font-medium text-blue-800 mb-1">Summary</h4>
                        <p className="text-blue-700">{finding.summary}</p>
                    </div>

                    {/* Full Content */}
                    <div className="prose max-w-none">
                        <h4 className="font-medium text-gray-800 mb-2">Details</h4>
                        <div className="text-gray-700 whitespace-pre-wrap">{finding.content}</div>
                    </div>

                    {/* Metadata */}
                    <div className="mt-6 pt-4 border-t flex items-center justify-between text-sm text-gray-500">
                        <div className="flex items-center gap-4">
                            <span>Relevance: {finding.relevance_score}%</span>
                            {finding.source_url && (
                                <a
                                    href={finding.source_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-primary hover:underline"
                                >
                                    View Source →
                                </a>
                            )}
                        </div>
                        <span>Updated: {formatDate(finding.updated_at)}</span>
                    </div>
                </div>
            </div>
        </div>
    );
}
