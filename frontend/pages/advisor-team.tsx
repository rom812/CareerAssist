import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useAuth } from '@clerk/nextjs';
import Layout from '../components/Layout';
import { createApiClient, AnalysisJob } from '../lib/api';
import Head from 'next/head';

interface Agent {
  icon: string;
  name: string;
  role: string;
  description: string;
  color: string;
  bgColor: string;
}

const agents: Agent[] = [
  {
    icon: '🎯',
    name: 'Orchestrator',
    role: 'Coordinator',
    description: 'Routes career requests to specialist agents and coordinates workflows',
    color: 'text-ai-accent',
    bgColor: 'bg-ai-accent'
  },
  {
    icon: '📄',
    name: 'Extractor',
    role: 'CV & Job Parser',
    description: 'Extracts structured data from CVs and job postings using AI',
    color: 'text-primary',
    bgColor: 'bg-primary'
  },
  {
    icon: '📊',
    name: 'Analyzer',
    role: 'Gap Analysis',
    description: 'Compares CVs to jobs, identifies gaps, and generates rewrites',
    color: 'text-green-600',
    bgColor: 'bg-green-600'
  },
  {
    icon: '📈',
    name: 'Charter',
    role: 'Analytics',
    description: 'Creates application pipeline analytics and visualizations',
    color: 'text-accent',
    bgColor: 'bg-accent'
  },
  {
    icon: '🎤',
    name: 'Interviewer',
    role: 'Interview Coach',
    description: 'Generates tailored interview questions and evaluates answers',
    color: 'text-pink-600',
    bgColor: 'bg-pink-600'
  }
];

export default function AdvisorTeam() {
  const router = useRouter();
  const { getToken } = useAuth();
  const [recentJobs, setRecentJobs] = useState<AnalysisJob[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchJobs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchJobs = async () => {
    try {
      const token = await getToken();
      if (!token) return;

      const api = createApiClient(token);
      const data = await api.jobs.list();
      setRecentJobs(data.jobs.slice(0, 10));
    } catch (error) {
      console.error('Error fetching jobs:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-green-600 bg-green-100';
      case 'failed':
        return 'text-red-600 bg-red-100';
      case 'processing':
        return 'text-blue-600 bg-blue-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getJobTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      cv_parse: 'CV Parse',
      job_parse: 'Job Parse',
      gap_analysis: 'Gap Analysis',
      cv_rewrite: 'CV Rewrite',
      interview_prep: 'Interview Prep',
      full_analysis: 'Full Analysis'
    };
    return labels[type] || type;
  };

  return (
    <>
      <Head>
        <title>AI Agents - CareerAssist</title>
      </Head>
      <Layout>
        <div className="min-h-screen bg-gray-50 py-8">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            {/* Header */}
            <div className="bg-white rounded-lg shadow px-8 py-6 mb-8">
              <h1 className="text-3xl font-bold text-dark mb-2">Your AI Career Advisory Team</h1>
              <p className="text-gray-600">
                Meet your team of specialized AI agents that work together to provide comprehensive career assistance.
                Each agent has a specific role in helping you optimize your job search.
              </p>
            </div>

            {/* Agent Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mb-8">
              {agents.map((agent) => (
                <div
                  key={agent.name}
                  className="bg-white rounded-lg shadow-lg p-6 hover:shadow-xl transition-all duration-300"
                >
                  <div className="text-5xl mb-4">{agent.icon}</div>
                  <h3 className={`text-xl font-semibold mb-1 ${agent.color}`}>
                    {agent.name}
                  </h3>
                  <p className="text-sm text-gray-500 mb-3">{agent.role}</p>
                  <p className="text-gray-600 text-sm">{agent.description}</p>
                </div>
              ))}
            </div>

            {/* How It Works */}
            <div className="bg-white rounded-lg shadow px-8 py-6 mb-8">
              <h2 className="text-2xl font-semibold text-dark mb-6">How the Agents Work Together</h2>
              <div className="relative">
                {/* Flow diagram */}
                <div className="flex flex-col md:flex-row items-center justify-between gap-4">
                  <div className="flex flex-col items-center text-center p-4">
                    <div className="text-3xl mb-2">📝</div>
                    <div className="font-medium">You Upload</div>
                    <div className="text-sm text-gray-500">CV + Job Posting</div>
                  </div>
                  <div className="text-2xl text-gray-400">→</div>
                  <div className="flex flex-col items-center text-center p-4 bg-ai-accent/10 rounded-lg">
                    <div className="text-3xl mb-2">🎯</div>
                    <div className="font-medium">Orchestrator</div>
                    <div className="text-sm text-gray-500">Routes Request</div>
                  </div>
                  <div className="text-2xl text-gray-400">→</div>
                  <div className="flex flex-col items-center text-center p-4 bg-primary/10 rounded-lg">
                    <div className="text-3xl mb-2">📄</div>
                    <div className="font-medium">Extractor</div>
                    <div className="text-sm text-gray-500">Parses Documents</div>
                  </div>
                  <div className="text-2xl text-gray-400">→</div>
                  <div className="flex flex-col items-center text-center p-4 bg-green-100 rounded-lg">
                    <div className="text-3xl mb-2">📊</div>
                    <div className="font-medium">Analyzer</div>
                    <div className="text-sm text-gray-500">Gap Analysis + Rewrite</div>
                  </div>
                  <div className="text-2xl text-gray-400">→</div>
                  <div className="flex flex-col items-center text-center p-4 bg-pink-100 rounded-lg">
                    <div className="text-3xl mb-2">🎤</div>
                    <div className="font-medium">Interviewer</div>
                    <div className="text-sm text-gray-500">Interview Prep</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Recent Jobs */}
            <div className="bg-white rounded-lg shadow px-8 py-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-semibold text-dark">Recent Agent Activity</h2>
                <button
                  onClick={() => router.push('/job-board')}
                  className="px-6 py-3 bg-ai-accent text-white rounded-lg hover:bg-purple-700 transition-colors font-medium"
                >
                  Start New Analysis
                </button>
              </div>

              {loading ? (
                <div className="text-center py-8 text-gray-500">Loading...</div>
              ) : recentJobs.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-gray-500 mb-4">No agent activity yet.</p>
                  <p className="text-sm text-gray-400">
                    Upload a CV and add a job posting to see your agents in action!
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {recentJobs.map((job) => (
                    <div
                      key={job.id}
                      className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                    >
                      <div className="flex-1">
                        <div className="flex items-center gap-3">
                          <span className="text-sm font-medium text-gray-900">
                            {getJobTypeLabel(job.job_type)}
                          </span>
                          <span className={`text-xs px-2 py-1 rounded-full ${getStatusColor(job.status)}`}>
                            {job.status}
                          </span>
                          {job.status === 'processing' && (
                            <div className="flex gap-1">
                              <div className="w-2 h-2 bg-blue-600 rounded-full animate-pulse" />
                              <div className="w-2 h-2 bg-blue-600 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }} />
                              <div className="w-2 h-2 bg-blue-600 rounded-full animate-pulse" style={{ animationDelay: '0.4s' }} />
                            </div>
                          )}
                        </div>
                        <p className="text-xs text-gray-500 mt-1">
                          {formatDate(job.created_at)}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        {job.progress_percentage > 0 && job.status === 'processing' && (
                          <div className="w-24 bg-gray-200 rounded-full h-2">
                            <div
                              className="bg-blue-600 h-2 rounded-full transition-all"
                              style={{ width: `${job.progress_percentage}%` }}
                            />
                          </div>
                        )}
                        {job.status === 'completed' && (
                          <button
                            onClick={() => router.push('/analysis')}
                            className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-blue-600 text-sm font-medium"
                          >
                            View Results
                          </button>
                        )}
                        {job.status === 'failed' && job.error_message && (
                          <span className="text-xs text-red-600 max-w-xs truncate">
                            {job.error_message}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Agent Capabilities */}
            <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-gradient-to-br from-primary/10 to-ai-accent/10 rounded-lg p-6">
                <h3 className="font-semibold text-dark mb-3">What the Agents Can Do</h3>
                <ul className="space-y-2 text-sm text-gray-700">
                  <li className="flex items-center gap-2">
                    <span className="text-green-500">✓</span>
                    Parse and extract structured data from any CV format
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="text-green-500">✓</span>
                    Analyze job postings for key requirements and ATS keywords
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="text-green-500">✓</span>
                    Score your fit for specific roles (0-100)
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="text-green-500">✓</span>
                    Identify skill gaps with actionable recommendations
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="text-green-500">✓</span>
                    Rewrite CV bullets for specific job applications
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="text-green-500">✓</span>
                    Generate tailored interview questions
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="text-green-500">✓</span>
                    Create cover letters optimized for each role
                  </li>
                </ul>
              </div>
              <div className="bg-gradient-to-br from-green-100 to-blue-100 rounded-lg p-6">
                <h3 className="font-semibold text-dark mb-3">Powered by Advanced AI</h3>
                <p className="text-sm text-gray-700 mb-4">
                  CareerAssist uses a multi-agent architecture where specialized AI agents
                  collaborate to provide comprehensive career assistance.
                </p>
                <div className="space-y-2 text-sm text-gray-600">
                  <div className="flex items-center gap-2">
                    <span className="text-blue-500">🤖</span>
                    Built on AWS Bedrock with Claude
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-blue-500">⚡</span>
                    OpenAI Agents SDK for orchestration
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-blue-500">🔒</span>
                    Enterprise-grade security
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-blue-500">📊</span>
                    Vector search for intelligent matching
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </Layout>
    </>
  );
}
