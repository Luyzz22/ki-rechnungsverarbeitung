'use client';

import Link from 'next/link';

const categories = [
  { name: 'Alle', count: 3 },
  { name: 'Finance Intelligence', count: 2 },
  { name: 'Vergleich', count: 1 },
];

const featuredPost = {
  title: 'E-Rechnung Pflicht 2025: Was Unternehmen jetzt tun müssen',
  excerpt: 'Seit dem 1. Januar 2025 gilt die E-Rechnungspflicht für alle B2B-Transaktionen. Dieser Leitfaden zeigt Fristen, Formate und wie KI-Automatisierung 85% Zeitersparnis bringt.',
  slug: 'e-rechnung-pflicht-2025-was-unternehmen-jetzt-tun-muessen',
  category: 'Finance Intelligence',
  author: 'Luis Schenk',
  date: '15. Feb 2026',
  readTime: '12 Min',
};

const posts = [
  {
    title: 'KI-Rechnungsverarbeitung im Mittelstand: SAP Concur vs. Basware vs. SBS Nexus',
    excerpt: 'Der komplette Vergleich der drei relevantesten Plattformen — mit Fokus auf DATEV-Integration, Kosten und Implementierungsdauer.',
    slug: 'ki-rechnungsverarbeitung-mittelstand-vergleich',
    category: 'Vergleich',
    date: '15. Feb 2026',
    readTime: '15 Min',
  },
  {
    title: 'Warum DATEV-Automatisierung 2026 kein Luxus mehr ist',
    excerpt: 'Der deutsche Mittelstand verarbeitet Millionen Rechnungen pro Jahr manuell. Mit KI-gestützter Automatisierung lässt sich die Buchhaltungszeit um 70% reduzieren.',
    slug: 'warum-datev-automatisierung-2026',
    category: 'Finance Intelligence',
    date: '28. Jan 2026',
    readTime: '8 Min',
  },
];

export default function BlogPage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950">
      {/* SEO Meta */}
      <head>
        <title>Blog | SBS Nexus – KI-Automatisierung für den deutschen Mittelstand</title>
        <meta name="description" content="Praxis-Wissen zu KI-Automatisierung, DATEV-Integration, E-Rechnung und Enterprise-Software für den deutschen Mittelstand. Von SBS Deutschland." />
        <link rel="canonical" href="https://www.sbsnexus.de/blog" />
      </head>

      {/* Header */}
      <header className="border-b border-slate-800/50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex justify-between items-center">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-8 h-8 bg-orange-500 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">SBS</span>
            </div>
            <span className="text-white font-semibold">SBS Nexus</span>
          </Link>
          <nav className="hidden md:flex items-center gap-6">
            <Link href="/#modules" className="text-slate-400 hover:text-white text-sm">Module</Link>
            <Link href="/pricing" className="text-slate-400 hover:text-white text-sm">Pricing</Link>
            <Link href="/blog" className="text-white text-sm font-medium">Blog</Link>
            <Link href="/about" className="text-slate-400 hover:text-white text-sm">Über uns</Link>
            <Link 
              href="https://calendly.com/ki-sbsdeutschland/sbs-nexus-30-minuten-discovery-call"
              className="bg-orange-500 hover:bg-orange-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition"
            >
              Demo buchen
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section className="py-16 px-6 text-center">
        <div className="max-w-3xl mx-auto">
          <h1 className="text-4xl md:text-5xl font-bold text-white mb-4">
            SBS Nexus Blog
          </h1>
          <p className="text-xl text-slate-400">
            Praxis-Wissen zu KI-Automatisierung, DATEV-Workflows und Enterprise-Software 
            für den deutschen Mittelstand.
          </p>
        </div>
      </section>

      {/* Categories */}
      <section className="px-6 pb-8">
        <div className="max-w-6xl mx-auto">
          <div className="flex flex-wrap gap-2 justify-center">
            {categories.map((cat, idx) => (
              <button
                key={idx}
                className={`px-4 py-2 rounded-full text-sm transition ${
                  idx === 0
                    ? 'bg-orange-500 text-white'
                    : 'bg-slate-800/50 text-slate-400 hover:bg-slate-700 hover:text-white'
                }`}
              >
                {cat.name}
                <span className="ml-2 text-xs opacity-60">({cat.count})</span>
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* Featured Post */}
      <section className="px-6 pb-12">
        <div className="max-w-6xl mx-auto">
          <Link href={`/blog/${featuredPost.slug}`}>
            <div className="bg-gradient-to-r from-orange-500/20 to-slate-800/50 rounded-2xl p-8 md:p-12 border border-orange-500/30 hover:border-orange-500/50 transition">
              <div className="flex flex-wrap gap-3 mb-4">
                <span className="bg-orange-500 text-white text-xs px-3 py-1 rounded-full font-medium">
                  Featured
                </span>
                <span className="bg-slate-700 text-slate-300 text-xs px-3 py-1 rounded-full">
                  {featuredPost.category}
                </span>
              </div>
              <h2 className="text-2xl md:text-3xl font-bold text-white mb-4">
                {featuredPost.title}
              </h2>
              <p className="text-slate-300 text-lg mb-6 max-w-3xl">
                {featuredPost.excerpt}
              </p>
              <div className="flex items-center gap-4 text-sm text-slate-400">
                <span>{featuredPost.author}</span>
                <span>·</span>
                <span>{featuredPost.date}</span>
                <span>·</span>
                <span>{featuredPost.readTime} Lesezeit</span>
              </div>
            </div>
          </Link>
        </div>
      </section>

      {/* Post Grid */}
      <section className="px-6 pb-20">
        <div className="max-w-6xl mx-auto">
          <div className="grid md:grid-cols-2 lg:grid-cols-2 gap-6">
            {posts.map((post, idx) => (
              <Link key={idx} href={`/blog/${post.slug}`}>
                <article className="bg-slate-800/30 rounded-xl p-6 border border-slate-700/50 hover:border-slate-600 transition h-full flex flex-col">
                  <div className="flex items-center gap-2 mb-4">
                    <span className="bg-slate-700 text-slate-300 text-xs px-2 py-1 rounded">
                      {post.category}
                    </span>
                    <span className="text-slate-500 text-xs">{post.readTime}</span>
                  </div>
                  <h3 className="text-lg font-semibold text-white mb-3 flex-grow">
                    {post.title}
                  </h3>
                  <p className="text-slate-400 text-sm mb-4">
                    {post.excerpt}
                  </p>
                  <div className="text-slate-500 text-xs">
                    {post.date}
                  </div>
                </article>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* Newsletter CTA */}
      <section className="px-6 pb-20">
        <div className="max-w-3xl mx-auto">
          <div className="bg-slate-800/50 rounded-2xl p-8 md:p-12 text-center border border-slate-700/50">
            <h2 className="text-2xl font-bold text-white mb-4">
              Mittelstand-Insights direkt ins Postfach
            </h2>
            <p className="text-slate-400 mb-6">
              Einmal im Monat: Praxis-Tipps zu KI-Automatisierung, DATEV-Workflows und SAP-Integration. Kein Spam.
            </p>
            <form className="flex flex-col sm:flex-row gap-3 max-w-md mx-auto">
              <input
                type="email"
                placeholder="ihre@email.de"
                className="flex-grow px-4 py-3 rounded-lg bg-slate-900 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:border-orange-500"
              />
              <button
                type="submit"
                className="bg-orange-500 hover:bg-orange-600 text-white px-6 py-3 rounded-lg font-medium transition whitespace-nowrap"
              >
                Abonnieren
              </button>
            </form>
            <p className="text-slate-500 text-xs mt-4">
              Mit der Anmeldung akzeptieren Sie unsere <Link href="/datenschutz" className="text-orange-400 hover:underline">Datenschutzerklärung</Link>.
            </p>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-800/50 py-8 px-6">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-4">
          <p className="text-slate-500 text-sm">
            © 2026 SBS Deutschland GmbH · Weinheim · Alle Rechte vorbehalten.
          </p>
          <div className="flex gap-6">
            <Link href="/blog" className="text-white text-sm">Blog</Link>
            <Link href="/security" className="text-slate-500 hover:text-white text-sm">Security</Link>
            <Link href="/about" className="text-slate-500 hover:text-white text-sm">Über uns</Link>
            <Link href="/datenschutz" className="text-slate-500 hover:text-white text-sm">Datenschutz</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
