import { useUser, UserButton, Protect } from "@clerk/nextjs";
import Link from "next/link";
import { useRouter } from "next/router";
import { ReactNode } from "react";
import PageTransition from "./PageTransition";

interface LayoutProps {
  children: ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const { user } = useUser();
  const router = useRouter();

  // Helper to determine if a link is active
  const isActive = (path: string) => router.pathname === path;

  return (
    <Protect fallback={
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <p className="text-gray-600">Redirecting to sign in...</p>
        </div>
      </div>
    }>
      <div className="min-h-screen bg-gray-50 flex flex-col">
        {/* Navigation */}
        <nav className="bg-white shadow-sm border-b">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              {/* Logo and Brand */}
              <div className="flex items-center gap-8">
                <Link href="/dashboard" className="flex items-center">
                  <h1 className="text-xl font-bold text-dark">
                    CareerAssist <span className="text-primary">AI Career Advisor</span>
                  </h1>
                </Link>

                {/* Navigation Links */}
                <div className="hidden md:flex items-center gap-6">
                  <Link
                    href="/dashboard"
                    className={`text-sm font-medium transition-colors ${isActive("/dashboard")
                        ? "text-primary"
                        : "text-gray-600 hover:text-primary"
                      }`}
                  >
                    Dashboard
                  </Link>
                  <Link
                    href="/cv-manager"
                    className={`text-sm font-medium transition-colors ${isActive("/cv-manager")
                        ? "text-primary"
                        : "text-gray-600 hover:text-primary"
                      }`}
                  >
                    CV Manager
                  </Link>
                  <Link
                    href="/job-board"
                    className={`text-sm font-medium transition-colors ${isActive("/job-board")
                        ? "text-primary"
                        : "text-gray-600 hover:text-primary"
                      }`}
                  >
                    Job Board
                  </Link>
                  <Link
                    href="/analysis"
                    className={`text-sm font-medium transition-colors ${isActive("/analysis")
                        ? "text-primary"
                        : "text-gray-600 hover:text-primary"
                      }`}
                  >
                    Analysis
                  </Link>
                  <Link
                    href="/market-insights"
                    className={`text-sm font-medium transition-colors ${isActive("/market-insights")
                        ? "text-primary"
                        : "text-gray-600 hover:text-primary"
                      }`}
                  >
                    Market Insights
                  </Link>
                  <Link
                    href="/advisor-team"
                    className={`text-sm font-medium transition-colors ${isActive("/advisor-team")
                        ? "text-primary"
                        : "text-gray-600 hover:text-primary"
                      }`}
                  >
                    AI Agents
                  </Link>
                </div>
              </div>

              {/* User Section */}
              <div className="flex items-center gap-4">
                <span className="hidden sm:inline text-sm text-gray-600">
                  {user?.firstName || user?.emailAddresses[0]?.emailAddress}
                </span>
                <UserButton afterSignOutUrl="/" />
              </div>
            </div>

            {/* Mobile Navigation */}
            <div className="md:hidden flex items-center gap-4 pb-3">
              <Link
                href="/dashboard"
                className={`text-sm font-medium transition-colors ${isActive("/dashboard")
                    ? "text-primary"
                    : "text-gray-600 hover:text-primary"
                  }`}
              >
                Dashboard
              </Link>
              <Link
                href="/cv-manager"
                className={`text-sm font-medium transition-colors ${isActive("/cv-manager")
                    ? "text-primary"
                    : "text-gray-600 hover:text-primary"
                  }`}
              >
                CV Manager
              </Link>
              <Link
                href="/job-board"
                className={`text-sm font-medium transition-colors ${isActive("/job-board")
                    ? "text-primary"
                    : "text-gray-600 hover:text-primary"
                  }`}
              >
                Job Board
              </Link>
              <Link
                href="/analysis"
                className={`text-sm font-medium transition-colors ${isActive("/analysis")
                    ? "text-primary"
                    : "text-gray-600 hover:text-primary"
                  }`}
              >
                Analysis
              </Link>
              <Link
                href="/market-insights"
                className={`text-sm font-medium transition-colors ${isActive("/market-insights")
                    ? "text-primary"
                    : "text-gray-600 hover:text-primary"
                  }`}
              >
                Insights
              </Link>
              <Link
                href="/advisor-team"
                className={`text-sm font-medium transition-colors ${isActive("/advisor-team")
                    ? "text-primary"
                    : "text-gray-600 hover:text-primary"
                  }`}
              >
                AI Agents
              </Link>
            </div>
          </div>
        </nav>

        {/* Main Content */}
        <main className="flex-1">
          <PageTransition>
            {children}
          </PageTransition>
        </main>

        {/* Footer */}
        <footer className="bg-white border-t mt-auto">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <p className="text-sm text-gray-700 font-medium mb-2">
                About CareerAssist
              </p>
              <p className="text-xs text-gray-600">
                CareerAssist uses AI to help you optimize your CV, track job applications, and prepare for interviews.
                This is a learning tool and should be used alongside professional career advice.
              </p>
            </div>
            <div className="mt-4 pt-4 border-t border-gray-200">
              <p className="text-xs text-gray-500 text-center">
                © 2025 CareerAssist AI Career Advisor. Powered by AI agents and built with care.
              </p>
            </div>
          </div>
        </footer>
      </div>
    </Protect>
  );
}