import Link from "next/link";

export default function Home() {
  return (
    <main className="max-w-4xl mx-auto px-4 py-16">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">📬 Weekly Intel</h1>
        <p className="text-xl text-gray-600">Your AI-powered weekly intelligence digest</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
        <div className="bg-white rounded-xl shadow-sm border p-6">
          <div className="text-3xl mb-3">📡</div>
          <h2 className="text-lg font-semibold mb-2">Multi-Source Ingestion</h2>
          <p className="text-gray-600 text-sm">Substack RSS feeds, Gmail newsletters, and YouTube transcripts unified in one place.</p>
        </div>
        <div className="bg-white rounded-xl shadow-sm border p-6">
          <div className="text-3xl mb-3">🧠</div>
          <h2 className="text-lg font-semibold mb-2">AI-Powered Analysis</h2>
          <p className="text-gray-600 text-sm">Claude extracts key facts, themes, hot takes, and entities. Semantic clustering groups related stories.</p>
        </div>
        <div className="bg-white rounded-xl shadow-sm border p-6">
          <div className="text-3xl mb-3">✉️</div>
          <h2 className="text-lg font-semibold mb-2">Weekly Digest</h2>
          <p className="text-gray-600 text-sm">Beautiful HTML email + Markdown archive, with deduplication across 4 weeks of history.</p>
        </div>
      </div>

      <div className="text-center">
        <Link
          href="/dashboard"
          className="bg-blue-600 text-white px-8 py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors inline-block mr-4"
        >
          Open Dashboard
        </Link>
        <a
          href="https://github.com"
          className="bg-white text-gray-700 border px-8 py-3 rounded-lg font-medium hover:bg-gray-50 transition-colors inline-block"
        >
          View Docs
        </a>
      </div>
    </main>
  );
}
