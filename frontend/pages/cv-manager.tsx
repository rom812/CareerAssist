import Head from "next/head";
import Layout from "../components/Layout";
import { useUser, useAuth } from "@clerk/nextjs";
import { useState, useEffect, useCallback } from "react";
import { createApiClient, CVVersion, CVProfile, AnalysisJob } from "../lib/api";
import { showToast } from "../components/Toast";
import { Skeleton } from "../components/Skeleton";
import { CVDropzone } from "../components/CVDropzone";

export default function CVManager() {
    const { user, isLoaded: userLoaded } = useUser();
    const { getToken } = useAuth();

    const [cvVersions, setCvVersions] = useState<CVVersion[]>([]);
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(false);
    const [parsing, setParsing] = useState<string | null>(null);

    // Modal state
    const [showModal, setShowModal] = useState(false);
    const [cvText, setCvText] = useState("");
    const [versionName, setVersionName] = useState("My CV");
    const [isPrimary, setIsPrimary] = useState(false);
    
    // Upload tab state
    const [uploadTab, setUploadTab] = useState<"pdf" | "paste">("pdf");
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [uploadProgress, setUploadProgress] = useState(0);
    const [isUploading, setIsUploading] = useState(false);

    // View CV state
    const [selectedCV, setSelectedCV] = useState<CVVersion | null>(null);
    const [showCVDetail, setShowCVDetail] = useState(false);

    // Parse job status polling
    const [parseJobId, setParseJobId] = useState<string | null>(null);

    const loadCVVersions = useCallback(async () => {
        if (!userLoaded || !user) return;

        try {
            const token = await getToken();
            if (!token) return;

            const api = createApiClient(token);
            
            // Ensure user exists in database (creates if first time)
            await api.user.get();
            
            const versions = await api.cvVersions.list();
            setCvVersions(versions);
        } catch (err) {
            console.error("Error loading CV versions:", err);
            showToast("error", "Failed to load CV versions");
        } finally {
            setLoading(false);
        }
    }, [userLoaded, user, getToken]);

    useEffect(() => {
        loadCVVersions();
    }, [loadCVVersions]);

    // Poll for parse job completion
    useEffect(() => {
        if (!parseJobId) return;

        const pollJob = async () => {
            try {
                const token = await getToken();
                if (!token) return;

                const api = createApiClient(token);
                const job = await api.jobs.get(parseJobId);

                if (job.status === "completed") {
                    setParseJobId(null);
                    setParsing(null);
                    showToast("success", "CV parsed successfully!");
                    loadCVVersions();
                } else if (job.status === "failed") {
                    setParseJobId(null);
                    setParsing(null);
                    showToast("error", job.error_message || "CV parsing failed");
                }
            } catch (err) {
                console.error("Error polling job:", err);
            }
        };

        const interval = setInterval(pollJob, 2000);
        return () => clearInterval(interval);
    }, [parseJobId, getToken, loadCVVersions]);

    const handleUploadCV = async () => {
        if (!cvText.trim() || cvText.length < 100) {
            showToast("error", "Please paste your CV text (minimum 100 characters)");
            return;
        }

        setUploading(true);
        try {
            const token = await getToken();
            if (!token) return;

            const api = createApiClient(token);
            const newCV = await api.cvVersions.create({
                raw_text: cvText,
                version_name: versionName || "My CV",
                is_primary: isPrimary,
                file_type: "paste"
            });

            showToast("success", "CV uploaded successfully!");
            resetModal();
            loadCVVersions();

            // Auto-trigger parsing
            const parseResult = await api.analyze.trigger({
                job_type: "cv_parse",
                cv_version_id: newCV.id
            });
            setParsing(newCV.id);
            setParseJobId(parseResult.job_id);
            showToast("info", "Parsing CV with AI...");

        } catch (err) {
            console.error("Error uploading CV:", err);
            showToast("error", err instanceof Error ? err.message : "Failed to upload CV");
        } finally {
            setUploading(false);
        }
    };

    const handleFileSelect = (file: File) => {
        setSelectedFile(file);
    };

    const handleUploadPDF = async () => {
        if (!selectedFile) {
            showToast("error", "Please select a PDF file");
            return;
        }

        setIsUploading(true);
        setUploadProgress(0);

        try {
            const token = await getToken();
            if (!token) return;

            const api = createApiClient(token);
            const result = await api.cvVersions.upload(
                selectedFile,
                versionName || "My CV",
                isPrimary,
                (progress) => setUploadProgress(progress)
            );

            showToast("success", `CV uploaded! Extracted ${result.extracted_length.toLocaleString()} characters.`);
            resetModal();
            loadCVVersions();

            // The upload endpoint auto-triggers parsing
            setParsing(result.cv_version.id);
            setParseJobId(result.job_id);
            showToast("info", "AI is parsing your CV...");

        } catch (err) {
            console.error("Error uploading PDF:", err);
            showToast("error", err instanceof Error ? err.message : "Failed to upload PDF");
        } finally {
            setIsUploading(false);
            setUploadProgress(0);
        }
    };

    const resetModal = () => {
        setShowModal(false);
        setCvText("");
        setVersionName("My CV");
        setIsPrimary(false);
        setSelectedFile(null);
        setUploadProgress(0);
        setUploadTab("pdf");
    };

    const handleDeleteCV = async (cvId: string) => {
        if (!confirm("Are you sure you want to delete this CV version?")) return;

        try {
            const token = await getToken();
            if (!token) return;

            const api = createApiClient(token);
            await api.cvVersions.delete(cvId);
            showToast("success", "CV deleted");
            loadCVVersions();
        } catch (err) {
            console.error("Error deleting CV:", err);
            showToast("error", "Failed to delete CV");
        }
    };

    const handleParseCV = async (cvId: string) => {
        try {
            const token = await getToken();
            if (!token) return;

            const api = createApiClient(token);
            const result = await api.analyze.trigger({
                job_type: "cv_parse",
                cv_version_id: cvId
            });

            setParsing(cvId);
            setParseJobId(result.job_id);
            showToast("info", "Parsing CV with AI...");
        } catch (err) {
            console.error("Error parsing CV:", err);
            showToast("error", "Failed to start CV parsing");
        }
    };

    const handleViewCV = async (cvId: string) => {
        try {
            const token = await getToken();
            if (!token) return;

            const api = createApiClient(token);
            const cv = await api.cvVersions.get(cvId);
            setSelectedCV(cv);
            setShowCVDetail(true);
        } catch (err) {
            console.error("Error loading CV:", err);
            showToast("error", "Failed to load CV details");
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
                <title>CV Manager - CareerAssist</title>
            </Head>
            <Layout>
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                    <div className="flex justify-between items-center mb-8">
                        <h1 className="text-3xl font-bold text-dark">CV Manager</h1>
                        <button
                            onClick={() => setShowModal(true)}
                            className="px-6 py-3 bg-primary text-white rounded-lg hover:bg-blue-600 transition-colors flex items-center gap-2"
                        >
                            <span>+</span> Upload CV
                        </button>
                    </div>

                    {loading ? (
                        <div className="space-y-4">
                            <Skeleton className="h-24 w-full" />
                            <Skeleton className="h-24 w-full" />
                        </div>
                    ) : cvVersions.length === 0 ? (
                        <div className="bg-white rounded-lg shadow p-6">
                            <div className="text-center py-12">
                                <div className="text-6xl mb-4">📄</div>
                                <h2 className="text-xl font-semibold text-gray-700 mb-2">No CVs Uploaded Yet</h2>
                                <p className="text-gray-500 mb-6">
                                    Upload your CV to get started with AI-powered optimization
                                </p>
                                <button
                                    onClick={() => setShowModal(true)}
                                    className="px-6 py-3 bg-primary text-white rounded-lg hover:bg-blue-600 transition-colors"
                                >
                                    Upload CV
                                </button>
                            </div>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {cvVersions.map((cv) => (
                                <div key={cv.id} className="bg-white rounded-lg shadow p-6">
                                    <div className="flex justify-between items-start">
                                        <div className="flex-1">
                                            <div className="flex items-center gap-3">
                                                <h3 className="text-lg font-semibold text-dark">
                                                    {cv.version_name}
                                                </h3>
                                                {cv.is_primary && (
                                                    <span className="px-2 py-1 bg-primary/10 text-primary text-xs rounded-full">
                                                        Primary
                                                    </span>
                                                )}
                                                {cv.parsed_json && (
                                                    <span className="px-2 py-1 bg-green-100 text-green-700 text-xs rounded-full">
                                                        Parsed
                                                    </span>
                                                )}
                                                {parsing === cv.id && (
                                                    <span className="px-2 py-1 bg-yellow-100 text-yellow-700 text-xs rounded-full animate-pulse">
                                                        Parsing...
                                                    </span>
                                                )}
                                            </div>
                                            <p className="text-sm text-gray-500 mt-1">
                                                Uploaded {formatDate(cv.created_at)} • {cv.file_type}
                                            </p>
                                            {cv.parsed_json && (
                                                <div className="mt-2 text-sm text-gray-600">
                                                    <span className="font-medium">{cv.parsed_json.name}</span>
                                                    {cv.parsed_json.skills && (
                                                        <span className="ml-2">
                                                            • {cv.parsed_json.skills.length} skills
                                                        </span>
                                                    )}
                                                    {cv.parsed_json.experience && (
                                                        <span className="ml-2">
                                                            • {cv.parsed_json.experience.length} jobs
                                                        </span>
                                                    )}
                                                </div>
                                            )}
                                            <p className="text-sm text-gray-400 mt-2 line-clamp-2">
                                                {cv.preview || cv.raw_text?.substring(0, 200)}...
                                            </p>
                                        </div>
                                        <div className="flex gap-2 ml-4">
                                            <button
                                                onClick={() => handleViewCV(cv.id)}
                                                className="px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200 transition-colors"
                                            >
                                                View
                                            </button>
                                            {!cv.parsed_json && parsing !== cv.id && (
                                                <button
                                                    onClick={() => handleParseCV(cv.id)}
                                                    className="px-3 py-1.5 text-sm bg-ai-accent text-white rounded hover:bg-purple-700 transition-colors"
                                                >
                                                    Parse with AI
                                                </button>
                                            )}
                                            <button
                                                onClick={() => handleDeleteCV(cv.id)}
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

                    <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-4">
                        <p className="text-sm text-blue-700">
                            <strong>Tip:</strong> Upload different versions of your CV for different job types.
                            Our AI will extract skills, experience, and education to help match you with jobs.
                        </p>
                    </div>
                </div>

                {/* Upload Modal */}
                {showModal && (
                    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                        <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                            <div className="p-6 border-b">
                                <div className="flex justify-between items-start">
                                    <div>
                                        <h2 className="text-xl font-semibold text-dark">Upload CV</h2>
                                        <p className="text-sm text-gray-500 mt-1">
                                            Upload a PDF or paste your CV text. Our AI will analyze and extract key information.
                                        </p>
                                    </div>
                                    <button
                                        onClick={resetModal}
                                        className="text-gray-400 hover:text-gray-600 text-2xl leading-none"
                                    >
                                        ×
                                    </button>
                                </div>
                                
                                {/* Tabs */}
                                <div className="flex gap-1 mt-4 bg-gray-100 p-1 rounded-lg">
                                    <button
                                        onClick={() => setUploadTab("pdf")}
                                        className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
                                            uploadTab === "pdf"
                                                ? "bg-white text-primary shadow-sm"
                                                : "text-gray-600 hover:text-gray-900"
                                        }`}
                                    >
                                        📄 Upload PDF
                                    </button>
                                    <button
                                        onClick={() => setUploadTab("paste")}
                                        className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
                                            uploadTab === "paste"
                                                ? "bg-white text-primary shadow-sm"
                                                : "text-gray-600 hover:text-gray-900"
                                        }`}
                                    >
                                        📝 Paste Text
                                    </button>
                                </div>
                            </div>
                            
                            <div className="p-6 space-y-4">
                                {/* Version Name - Common to both tabs */}
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        Version Name
                                    </label>
                                    <input
                                        type="text"
                                        value={versionName}
                                        onChange={(e) => setVersionName(e.target.value)}
                                        placeholder="e.g., Software Engineer CV"
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                                    />
                                </div>

                                {/* PDF Upload Tab */}
                                {uploadTab === "pdf" && (
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                            CV File
                                        </label>
                                        <CVDropzone
                                            onFileSelect={handleFileSelect}
                                            uploading={isUploading}
                                            uploadProgress={uploadProgress}
                                        />
                                    </div>
                                )}

                                {/* Paste Text Tab */}
                                {uploadTab === "paste" && (
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                            CV Text
                                        </label>
                                        <textarea
                                            value={cvText}
                                            onChange={(e) => setCvText(e.target.value)}
                                            placeholder="Paste your CV text here..."
                                            rows={12}
                                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary resize-none"
                                        />
                                        <p className="text-xs text-gray-500 mt-1">
                                            {cvText.length} characters (minimum 100)
                                        </p>
                                    </div>
                                )}

                                {/* Primary checkbox - Common to both tabs */}
                                <div className="flex items-center gap-2">
                                    <input
                                        type="checkbox"
                                        id="isPrimary"
                                        checked={isPrimary}
                                        onChange={(e) => setIsPrimary(e.target.checked)}
                                        className="rounded border-gray-300"
                                    />
                                    <label htmlFor="isPrimary" className="text-sm text-gray-700">
                                        Set as primary CV
                                    </label>
                                </div>
                            </div>
                            
                            <div className="p-6 border-t flex justify-end gap-3">
                                <button
                                    onClick={resetModal}
                                    disabled={isUploading || uploading}
                                    className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors disabled:opacity-50"
                                >
                                    Cancel
                                </button>
                                
                                {uploadTab === "pdf" ? (
                                    <button
                                        onClick={handleUploadPDF}
                                        disabled={isUploading || !selectedFile}
                                        className={`px-6 py-2 rounded-lg font-medium transition-colors ${
                                            isUploading || !selectedFile
                                                ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                                                : "bg-primary text-white hover:bg-blue-600"
                                        }`}
                                    >
                                        {isUploading ? "Uploading..." : "Upload & Parse"}
                                    </button>
                                ) : (
                                    <button
                                        onClick={handleUploadCV}
                                        disabled={uploading || cvText.length < 100}
                                        className={`px-6 py-2 rounded-lg font-medium transition-colors ${
                                            uploading || cvText.length < 100
                                                ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                                                : "bg-primary text-white hover:bg-blue-600"
                                        }`}
                                    >
                                        {uploading ? "Uploading..." : "Upload & Parse"}
                                    </button>
                                )}
                            </div>
                        </div>
                    </div>
                )}

                {/* CV Detail Modal */}
                {showCVDetail && selectedCV && (
                    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                        <div className="bg-white rounded-xl shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
                            <div className="p-6 border-b flex justify-between items-center">
                                <div>
                                    <h2 className="text-xl font-semibold text-dark">{selectedCV.version_name}</h2>
                                    {selectedCV.parsed_json && (
                                        <p className="text-sm text-gray-500">{selectedCV.parsed_json.name}</p>
                                    )}
                                </div>
                                <button
                                    onClick={() => setShowCVDetail(false)}
                                    className="text-gray-400 hover:text-gray-600 text-2xl"
                                >
                                    ×
                                </button>
                            </div>
                            <div className="p-6">
                                {selectedCV.parsed_json ? (
                                    <CVProfileDisplay profile={selectedCV.parsed_json} />
                                ) : (
                                    <div className="prose max-w-none">
                                        <pre className="whitespace-pre-wrap text-sm text-gray-600 bg-gray-50 p-4 rounded-lg">
                                            {selectedCV.raw_text}
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

// CV Profile Display Component
function CVProfileDisplay({ profile }: { profile: CVProfile }) {
    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="border-b pb-4">
                <h3 className="text-2xl font-bold text-dark">{profile.name}</h3>
                <div className="flex flex-wrap gap-4 mt-2 text-sm text-gray-600">
                    {profile.email && <span>📧 {profile.email}</span>}
                    {profile.phone && <span>📱 {profile.phone}</span>}
                    {profile.location && <span>📍 {profile.location}</span>}
                </div>
                {profile.summary && (
                    <p className="mt-3 text-gray-700">{profile.summary}</p>
                )}
            </div>

            {/* Skills */}
            {profile.skills && profile.skills.length > 0 && (
                <div>
                    <h4 className="text-lg font-semibold text-dark mb-3">Skills</h4>
                    <div className="flex flex-wrap gap-2">
                        {profile.skills.map((skill, idx) => (
                            <span
                                key={idx}
                                className={`px-3 py-1 rounded-full text-sm ${
                                    skill.proficiency === "expert"
                                        ? "bg-green-100 text-green-800"
                                        : skill.proficiency === "proficient"
                                        ? "bg-blue-100 text-blue-800"
                                        : skill.proficiency === "familiar"
                                        ? "bg-yellow-100 text-yellow-800"
                                        : "bg-gray-100 text-gray-800"
                                }`}
                            >
                                {skill.name}
                                {skill.years && <span className="text-xs ml-1">({skill.years}y)</span>}
                            </span>
                        ))}
                    </div>
                </div>
            )}

            {/* Experience */}
            {profile.experience && profile.experience.length > 0 && (
                <div>
                    <h4 className="text-lg font-semibold text-dark mb-3">Experience</h4>
                    <div className="space-y-4">
                        {profile.experience.map((exp, idx) => (
                            <div key={idx} className="border-l-2 border-primary pl-4">
                                <div className="flex justify-between items-start">
                                    <div>
                                        <h5 className="font-semibold text-dark">{exp.role}</h5>
                                        <p className="text-sm text-gray-600">{exp.company}</p>
                                    </div>
                                    <span className="text-xs text-gray-500">
                                        {exp.start_date} - {exp.end_date || "Present"}
                                    </span>
                                </div>
                                {exp.highlights && exp.highlights.length > 0 && (
                                    <ul className="mt-2 text-sm text-gray-700 list-disc list-inside">
                                        {exp.highlights.map((h, i) => (
                                            <li key={i}>{h}</li>
                                        ))}
                                    </ul>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Education */}
            {profile.education && profile.education.length > 0 && (
                <div>
                    <h4 className="text-lg font-semibold text-dark mb-3">Education</h4>
                    <div className="space-y-2">
                        {profile.education.map((edu, idx) => (
                            <div key={idx} className="flex justify-between items-start">
                                <div>
                                    <h5 className="font-medium text-dark">{edu.degree} in {edu.field}</h5>
                                    <p className="text-sm text-gray-600">{edu.institution}</p>
                                </div>
                                {edu.graduation_date && (
                                    <span className="text-xs text-gray-500">{edu.graduation_date}</span>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Certifications */}
            {profile.certifications && profile.certifications.length > 0 && (
                <div>
                    <h4 className="text-lg font-semibold text-dark mb-3">Certifications</h4>
                    <div className="flex flex-wrap gap-2">
                        {profile.certifications.map((cert, idx) => (
                            <span key={idx} className="px-3 py-1 bg-purple-100 text-purple-800 rounded-full text-sm">
                                {cert}
                            </span>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
