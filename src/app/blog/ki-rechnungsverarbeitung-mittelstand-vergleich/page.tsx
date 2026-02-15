'use client';

import Link from 'next/link';

export default function BlogPostKIVergleich() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950">
      {/* SEO Meta */}
      <head>
        <title>KI-Rechnungsverarbeitung im Mittelstand: SAP Concur vs. Basware vs. SBS Nexus | SBS Nexus</title>
        <meta name="description" content="Vergleich der führenden KI-Lösungen für Rechnungsverarbeitung im deutschen Mittelstand. SAP Concur, Basware und SBS Nexus im direkten Vergleich: Kosten, DATEV-Integration, Implementierungsdauer." />
        <meta name="keywords" content="KI Rechnungsverarbeitung Vergleich, SAP Concur Alternative, Basware Alternative, Rechnungsverarbeitung Mittelstand, DATEV Automatisierung, Invoice Processing KI" />
        <meta property="og:title" content="KI-Rechnungsverarbeitung im Mittelstand: Der komplette Vergleich 2026" />
        <meta property="og:description" content="SAP Concur vs. Basware vs. SBS Nexus: Welche KI-Lösung passt zum deutschen Mittelstand?" />
        <meta property="og:type" content="article" />
        <meta property="og:url" content="https://www.sbsnexus.de/blog/ki-rechnungsverarbeitung-mittelstand-vergleich" />
        <link rel="canonical" href="https://www.sbsnexus.de/blog/ki-rechnungsverarbeitung-mittelstand-vergleich" />
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify({
          "@context": "https://schema.org",
          "@type": "Article",
          "headline": "KI-Rechnungsverarbeitung im Mittelstand: SAP Concur vs. Basware vs. SBS Nexus",
          "author": { "@type": "Person", "name": "Luis Schenk" },
          "publisher": { "@type": "Organization", "name": "SBS Deutschland GmbH" },
          "datePublished": "2026-02-15",
          "dateModified": "2026-02-15",
          "description": "Umfassender Vergleich der führenden KI-Lösungen für Rechnungsverarbeitung im deutschen Mittelstand."
        })}} />
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

      {/* Article */}
      <article className="py-12 px-6">
        <div className="max-w-3xl mx-auto">
          {/* Breadcrumb */}
          <nav className="flex items-center gap-2 text-sm text-slate-400 mb-8">
            <Link href="/blog" className="hover:text-white">Blog</Link>
            <span>/</span>
            <span className="text-slate-500">Vergleich</span>
          </nav>

          {/* Header */}
          <header className="mb-12">
            <div className="flex items-center gap-3 mb-4">
              <span className="bg-blue-500/20 text-blue-400 text-xs px-3 py-1 rounded-full">
                Vergleich
              </span>
              <span className="text-slate-500 text-sm">15 Min Lesezeit</span>
            </div>
            <h1 className="text-3xl md:text-4xl font-bold text-white mb-6 leading-tight">
              KI-Rechnungsverarbeitung im Mittelstand: SAP Concur vs. Basware vs. SBS Nexus
            </h1>
            <p className="text-xl text-slate-400 mb-8">
              Welche KI-Lösung passt zum deutschen Mittelstand? Wir vergleichen die drei relevantesten 
              Plattformen für automatisierte Rechnungsverarbeitung — mit Fokus auf DATEV-Integration, 
              Implementierungsdauer, Kosten und Datensicherheit.
            </p>
            <div className="flex items-center gap-4 text-sm text-slate-400">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 bg-slate-700 rounded-full flex items-center justify-center text-xs text-white font-medium">LS</div>
                <span>Luis Schenk</span>
              </div>
              <span>·</span>
              <span>15. Februar 2026</span>
              <span>·</span>
              <span>Aktualisiert</span>
            </div>
          </header>

          {/* Quick Summary Box */}
          <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700/50 mb-12">
            <h2 className="text-white font-semibold mb-4">Zusammenfassung auf einen Blick</h2>
            <div className="grid md:grid-cols-3 gap-4 text-sm">
              <div className="bg-slate-900/50 rounded-lg p-4">
                <p className="text-slate-400 mb-1">SAP Concur</p>
                <p className="text-white font-medium">Enterprise-Standard</p>
                <p className="text-slate-400 text-xs mt-1">Ab 5.000 €/Monat · 3–6 Monate Setup</p>
              </div>
              <div className="bg-slate-900/50 rounded-lg p-4">
                <p className="text-slate-400 mb-1">Basware</p>
                <p className="text-white font-medium">Procurement-fokussiert</p>
                <p className="text-slate-400 text-xs mt-1">Ab 3.000 €/Monat · 2–4 Monate Setup</p>
              </div>
              <div className="bg-slate-900/50 rounded-lg p-4 border border-orange-500/30">
                <p className="text-orange-400 mb-1">SBS Nexus</p>
                <p className="text-white font-medium">Mittelstand-nativ</p>
                <p className="text-slate-400 text-xs mt-1">Ab 1.990 €/Monat · 2 Wochen Setup</p>
              </div>
            </div>
          </div>

          {/* Article Content */}
          <div className="prose prose-invert max-w-none">
            
            {/* Intro */}
            <section className="mb-12">
              <h2 className="text-2xl font-bold text-white mb-4">Warum dieser Vergleich?</h2>
              <p className="text-slate-300 leading-relaxed mb-4">
                Die E-Rechnungspflicht zwingt deutsche Unternehmen zum Handeln. Der Markt für 
                KI-gestützte Rechnungsverarbeitung wächst entsprechend. Doch nicht jede Lösung 
                passt zum Mittelstand: Manche sind für Konzerne konzipiert, andere decken den 
                deutschen Markt nur als Nebenprodukt ab.
              </p>
              <p className="text-slate-300 leading-relaxed mb-4">
                Dieser Vergleich fokussiert auf die drei Kriterien, die für mittelständische 
                Unternehmen mit 50–500 Mitarbeitern entscheidend sind: Passt die Lösung zu 
                meinem DATEV-Workflow? Kann ich sie schnell einführen? Und bleiben meine Daten 
                in Deutschland?
              </p>
            </section>

            {/* Main Comparison Table */}
            <section className="mb-12">
              <h2 className="text-2xl font-bold text-white mb-6">Der vollständige Vergleich</h2>
              
              <div className="overflow-x-auto my-6">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-700">
                      <th className="text-left py-3 px-4 text-slate-400 font-medium">Kriterium</th>
                      <th className="text-left py-3 px-4 text-slate-400 font-medium">SAP Concur</th>
                      <th className="text-left py-3 px-4 text-slate-400 font-medium">Basware</th>
                      <th className="text-left py-3 px-4 text-orange-400 font-medium">SBS Nexus</th>
                    </tr>
                  </thead>
                  <tbody className="text-slate-300">
                    <tr className="border-b border-slate-800">
                      <td className="py-3 px-4 font-medium text-white">Zielgruppe</td>
                      <td className="py-3 px-4">Enterprise 500+ MA</td>
                      <td className="py-3 px-4">Enterprise 500+ MA</td>
                      <td className="py-3 px-4 text-orange-300">Mittelstand 50–500 MA</td>
                    </tr>
                    <tr className="border-b border-slate-800">
                      <td className="py-3 px-4 font-medium text-white">Monatliche Kosten</td>
                      <td className="py-3 px-4">5.000–8.000 €</td>
                      <td className="py-3 px-4">3.000–6.000 €</td>
                      <td className="py-3 px-4 text-orange-300">Ab 1.990 €</td>
                    </tr>
                    <tr className="border-b border-slate-800">
                      <td className="py-3 px-4 font-medium text-white">Implementierung</td>
                      <td className="py-3 px-4">3–6 Monate</td>
                      <td className="py-3 px-4">2–4 Monate</td>
                      <td className="py-3 px-4 text-orange-300">2 Wochen</td>
                    </tr>
                    <tr className="border-b border-slate-800">
                      <td className="py-3 px-4 font-medium text-white">DATEV-Integration</td>
                      <td className="py-3 px-4 text-yellow-400">Über Drittanbieter</td>
                      <td className="py-3 px-4 text-yellow-400">Eingeschränkt</td>
                      <td className="py-3 px-4 text-green-400">Nativ (SKR03/04)</td>
                    </tr>
                    <tr className="border-b border-slate-800">
                      <td className="py-3 px-4 font-medium text-white">Serverstandort</td>
                      <td className="py-3 px-4 text-red-400">USA / EU gemischt</td>
                      <td className="py-3 px-4 text-yellow-400">EU (Finnland)</td>
                      <td className="py-3 px-4 text-green-400">100% Frankfurt</td>
                    </tr>
                    <tr className="border-b border-slate-800">
                      <td className="py-3 px-4 font-medium text-white">KI-Erkennungsrate</td>
                      <td className="py-3 px-4">~85%</td>
                      <td className="py-3 px-4">~80%</td>
                      <td className="py-3 px-4 text-orange-300">~95%</td>
                    </tr>
                    <tr className="border-b border-slate-800">
                      <td className="py-3 px-4 font-medium text-white">Kontierung</td>
                      <td className="py-3 px-4">Manuell / Regeln</td>
                      <td className="py-3 px-4">Regelbasiert</td>
                      <td className="py-3 px-4 text-orange-300">KI-automatisch</td>
                    </tr>
                    <tr className="border-b border-slate-800">
                      <td className="py-3 px-4 font-medium text-white">Zusätzliche Module</td>
                      <td className="py-3 px-4">Reisekosten, Spesen</td>
                      <td className="py-3 px-4">Procurement, AP</td>
                      <td className="py-3 px-4 text-orange-300">Vertragsanalyse, Hydraulik-Doku</td>
                    </tr>
                    <tr className="border-b border-slate-800">
                      <td className="py-3 px-4 font-medium text-white">Support</td>
                      <td className="py-3 px-4">Ticket-System (EN)</td>
                      <td className="py-3 px-4">Ticket-System (EN)</td>
                      <td className="py-3 px-4 text-orange-300">Persönlich (DE)</td>
                    </tr>
                    <tr className="border-b border-slate-800">
                      <td className="py-3 px-4 font-medium text-white">Vendor Lock-in</td>
                      <td className="py-3 px-4 text-red-400">Hoch (SAP-Ökosystem)</td>
                      <td className="py-3 px-4 text-yellow-400">Mittel</td>
                      <td className="py-3 px-4 text-green-400">Kein (Self-hosted möglich)</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </section>

            {/* SAP Concur Deep Dive */}
            <section className="mb-12">
              <h2 className="text-2xl font-bold text-white mb-4">SAP Concur: Der Enterprise-Platzhirsch</h2>
              <p className="text-slate-300 leading-relaxed mb-4">
                SAP Concur ist Teil des SAP-Ökosystems und damit die natürliche Wahl für Unternehmen, 
                die bereits SAP S/4HANA oder SAP Business One nutzen. Die Stärke liegt in der tiefen 
                Integration mit SAP-Modulen wie FI/CO und MM. Für den deutschen Mittelstand gibt es 
                jedoch einige Einschränkungen.
              </p>
              <div className="grid md:grid-cols-2 gap-4 my-6">
                <div className="bg-green-500/10 rounded-lg p-4 border border-green-500/20">
                  <p className="text-green-400 text-sm font-semibold mb-2">Stärken</p>
                  <p className="text-slate-300 text-sm">Tiefe SAP-Integration, globaler Standard für Reisekosten, bewährte Enterprise-Infrastruktur, umfangreiche Compliance-Features für Konzerne</p>
                </div>
                <div className="bg-red-500/10 rounded-lg p-4 border border-red-500/20">
                  <p className="text-red-400 text-sm font-semibold mb-2">Schwächen für den Mittelstand</p>
                  <p className="text-slate-300 text-sm">Hohe Kosten (oft 5.000+ €/Monat), lange Implementierung (3–6 Monate), DATEV nur über Drittanbieter, Daten teilweise auf US-Servern, Support nur auf Englisch</p>
                </div>
              </div>
              <p className="text-slate-300 leading-relaxed">
                Fazit: SAP Concur ist die richtige Wahl für Konzerne mit bestehendem SAP-Stack. Für 
                mittelständische Unternehmen ohne SAP-Infrastruktur ist die Lösung oft überdimensioniert 
                und zu teuer.
              </p>
            </section>

            {/* Basware Deep Dive */}
            <section className="mb-12">
              <h2 className="text-2xl font-bold text-white mb-4">Basware: Der Procurement-Spezialist</h2>
              <p className="text-slate-300 leading-relaxed mb-4">
                Basware aus Finnland positioniert sich als führende Plattform für Purchase-to-Pay-Prozesse. 
                Die Stärke liegt in der automatisierten Beschaffung und im Rechnungseingang — besonders 
                für Unternehmen mit komplexen Beschaffungsketten.
              </p>
              <div className="grid md:grid-cols-2 gap-4 my-6">
                <div className="bg-green-500/10 rounded-lg p-4 border border-green-500/20">
                  <p className="text-green-400 text-sm font-semibold mb-2">Stärken</p>
                  <p className="text-slate-300 text-sm">Starke Procurement-Funktionen, EU-Serverstandort (Finnland), gute Erkennungsraten bei strukturierten Rechnungen, E-Invoicing-Netzwerk</p>
                </div>
                <div className="bg-red-500/10 rounded-lg p-4 border border-red-500/20">
                  <p className="text-red-400 text-sm font-semibold mb-2">Schwächen für den Mittelstand</p>
                  <p className="text-slate-300 text-sm">Eingeschränkte DATEV-Integration, kein deutscher Serverstandort, Fokus auf Procurement statt Buchhaltung, englischsprachiger Support, höhere Komplexität als nötig</p>
                </div>
              </div>
              <p className="text-slate-300 leading-relaxed">
                Fazit: Basware eignet sich für Unternehmen mit komplexer Beschaffung und internationalem 
                Lieferantennetzwerk. Die fehlende native DATEV-Integration macht die Lösung für den 
                klassischen deutschen Mittelstand weniger attraktiv.
              </p>
            </section>

            {/* SBS Nexus Deep Dive */}
            <section className="mb-12">
              <h2 className="text-2xl font-bold text-white mb-4">SBS Nexus: Gebaut für den deutschen Mittelstand</h2>
              <p className="text-slate-300 leading-relaxed mb-4">
                SBS Nexus wurde von Anfang an für die Anforderungen des deutschen Mittelstands entwickelt. 
                Die Plattform kombiniert KI-gestützte Rechnungsverarbeitung mit nativer DATEV-Integration 
                und erweitert das Spektrum um Vertragsanalyse und industrielle Dokumentation.
              </p>
              <div className="grid md:grid-cols-2 gap-4 my-6">
                <div className="bg-green-500/10 rounded-lg p-4 border border-green-500/20">
                  <p className="text-green-400 text-sm font-semibold mb-2">Stärken</p>
                  <p className="text-slate-300 text-sm">Native DATEV-Integration (SKR03/04), 100% deutsche Server (Frankfurt), 2 Wochen Go-Live, persönlicher deutscher Support, 3 KI-Module (Rechnungen, Verträge, Hydraulik-Doku), kein Vendor Lock-in</p>
                </div>
                <div className="bg-yellow-500/10 rounded-lg p-4 border border-yellow-500/20">
                  <p className="text-yellow-400 text-sm font-semibold mb-2">Zu beachten</p>
                  <p className="text-slate-300 text-sm">Jüngerer Anbieter als SAP/Basware, optimiert für DACH-Markt (noch kein globales Netzwerk), SAP-Integration in Entwicklung</p>
                </div>
              </div>

              <div className="bg-orange-500/10 border border-orange-500/30 rounded-lg p-5 my-6">
                <p className="text-orange-300 text-sm font-medium mb-1">Besonderheit: 3 KI-Module in einer Plattform</p>
                <p className="text-slate-200">
                  Anders als SAP Concur und Basware bietet SBS Nexus neben der Rechnungsverarbeitung auch 
                  KI-Vertragsanalyse (Risiko-Erkennung, Fristen-Management) und HydraulikDoc AI 
                  (multimodale technische Dokumentation) — alles auf einer Plattform, einem Login, einem Vertrag.
                </p>
              </div>
            </section>

            {/* Decision Matrix */}
            <section className="mb-12">
              <h2 className="text-2xl font-bold text-white mb-4">Entscheidungshilfe: Welche Lösung passt zu Ihnen?</h2>
              
              <div className="space-y-4 my-6">
                <div className="bg-slate-800/30 rounded-lg p-5 border border-slate-700/50">
                  <h3 className="text-white font-semibold mb-2">Wählen Sie SAP Concur, wenn...</h3>
                  <p className="text-slate-300 text-sm leading-relaxed">
                    Sie bereits SAP S/4HANA nutzen, mehr als 500 Mitarbeiter haben, globale Reisekosten- und 
                    Spesenabrechnung benötigen und ein Budget von 5.000+ € pro Monat für die Rechnungsverarbeitung 
                    einplanen können.
                  </p>
                </div>
                <div className="bg-slate-800/30 rounded-lg p-5 border border-slate-700/50">
                  <h3 className="text-white font-semibold mb-2">Wählen Sie Basware, wenn...</h3>
                  <p className="text-slate-300 text-sm leading-relaxed">
                    Ihr Schwerpunkt auf Procurement und Purchase-to-Pay liegt, Sie ein internationales 
                    Lieferantennetzwerk managen und DATEV-Integration für Sie zweitrangig ist.
                  </p>
                </div>
                <div className="bg-slate-800/30 rounded-lg p-5 border border-orange-500/30">
                  <h3 className="text-orange-400 font-semibold mb-2">Wählen Sie SBS Nexus, wenn...</h3>
                  <p className="text-slate-300 text-sm leading-relaxed">
                    Sie 50–500 Mitarbeiter haben, DATEV Ihr zentrales Buchhaltungssystem ist, Sie eine 
                    schnelle Einführung (Wochen statt Monate) brauchen, deutsche Datensouveränität 
                    Priorität hat und Sie neben Rechnungen auch Verträge und technische Dokumentation 
                    automatisieren möchten.
                  </p>
                </div>
              </div>
            </section>

            {/* TCO Comparison */}
            <section className="mb-12">
              <h2 className="text-2xl font-bold text-white mb-4">Total Cost of Ownership: 3-Jahres-Vergleich</h2>
              <p className="text-slate-300 leading-relaxed mb-4">
                Der Kaufpreis ist nur ein Teil der Gesamtkosten. Implementierung, Beratung, Schulung und 
                laufender Support summieren sich — besonders bei Enterprise-Lösungen.
              </p>
              
              <div className="overflow-x-auto my-6">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-700">
                      <th className="text-left py-3 px-4 text-slate-400 font-medium">Kostenposition</th>
                      <th className="text-left py-3 px-4 text-slate-400 font-medium">SAP Concur</th>
                      <th className="text-left py-3 px-4 text-slate-400 font-medium">Basware</th>
                      <th className="text-left py-3 px-4 text-orange-400 font-medium">SBS Nexus</th>
                    </tr>
                  </thead>
                  <tbody className="text-slate-300">
                    <tr className="border-b border-slate-800">
                      <td className="py-3 px-4">Setup & Implementierung</td>
                      <td className="py-3 px-4">25.000–50.000 €</td>
                      <td className="py-3 px-4">15.000–30.000 €</td>
                      <td className="py-3 px-4 text-orange-300">2.990 €</td>
                    </tr>
                    <tr className="border-b border-slate-800">
                      <td className="py-3 px-4">Laufende Kosten (36 Monate)</td>
                      <td className="py-3 px-4">180.000–288.000 €</td>
                      <td className="py-3 px-4">108.000–216.000 €</td>
                      <td className="py-3 px-4 text-orange-300">71.640 €</td>
                    </tr>
                    <tr className="border-b border-slate-800">
                      <td className="py-3 px-4">Externe Beratung</td>
                      <td className="py-3 px-4">20.000–40.000 €</td>
                      <td className="py-3 px-4">10.000–20.000 €</td>
                      <td className="py-3 px-4 text-orange-300">0 €</td>
                    </tr>
                    <tr className="border-b border-slate-800">
                      <td className="py-3 px-4">DATEV-Adapter (falls nötig)</td>
                      <td className="py-3 px-4">5.000–10.000 €</td>
                      <td className="py-3 px-4">5.000–8.000 €</td>
                      <td className="py-3 px-4 text-green-400">Inklusive</td>
                    </tr>
                    <tr className="border-b border-slate-700 font-semibold">
                      <td className="py-3 px-4 text-white">TCO 3 Jahre (gesamt)</td>
                      <td className="py-3 px-4 text-white">230.000–388.000 €</td>
                      <td className="py-3 px-4 text-white">138.000–274.000 €</td>
                      <td className="py-3 px-4 text-orange-400">74.630 €</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div className="bg-orange-500/10 border border-orange-500/30 rounded-lg p-5 my-6">
                <p className="text-orange-300 text-sm font-medium mb-1">Rechenbeispiel</p>
                <p className="text-slate-200">
                  Ein Unternehmen mit 200 Mitarbeitern und 500 Rechnungen/Monat spart mit SBS Nexus 
                  im 3-Jahres-Vergleich zwischen 63.000 € und 313.000 € gegenüber SAP Concur — 
                  bei schnellerem Go-Live und nativer DATEV-Integration.
                </p>
              </div>
            </section>

            {/* Conclusion / CTA */}
            <section className="mb-12">
              <h2 className="text-2xl font-bold text-white mb-4">Fazit</h2>
              <p className="text-slate-300 leading-relaxed mb-4">
                Die Wahl der richtigen Lösung hängt von drei Faktoren ab: Unternehmensgröße, bestehende 
                IT-Landschaft und Budget. SAP Concur und Basware sind bewährte Enterprise-Lösungen — 
                aber für den deutschen Mittelstand oft überdimensioniert, zu teuer und ohne native 
                DATEV-Anbindung.
              </p>
              <p className="text-slate-300 leading-relaxed mb-6">
                SBS Nexus schließt genau diese Lücke: Enterprise-Grade KI-Automatisierung zum 
                Mittelstandspreis, mit nativer DATEV-Integration, deutschen Servern und einem 
                Go-Live in 2 Wochen statt 6 Monaten.
              </p>

              <div className="bg-gradient-to-r from-orange-500/20 to-slate-800/50 rounded-xl p-8 border border-orange-500/30 text-center">
                <h3 className="text-xl font-bold text-white mb-3">
                  Vergleich live erleben
                </h3>
                <p className="text-slate-300 mb-6">
                  In 30 Minuten zeigen wir Ihnen den Unterschied — mit Ihren echten Rechnungen. 
                  Kein Sales-Pitch, sondern ein echter Vergleich.
                </p>
                <Link 
                  href="https://calendly.com/ki-sbsdeutschland/sbs-nexus-30-minuten-discovery-call"
                  className="inline-block bg-orange-500 hover:bg-orange-600 text-white px-8 py-3 rounded-lg font-medium transition"
                >
                  Kostenlose Demo buchen
                </Link>
              </div>
            </section>
          </div>

          {/* Author Bio */}
          <div className="border-t border-slate-800 pt-8 mt-12">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-slate-700 rounded-full flex items-center justify-center text-white font-medium">LS</div>
              <div>
                <p className="text-white font-semibold">Luis Schenk</p>
                <p className="text-slate-400 text-sm">
                  Gründer von SBS Deutschland. Baut Enterprise-KI-Lösungen für den deutschen Mittelstand — 
                  DSGVO-konform, DATEV-nativ, 100% Made in Germany.
                </p>
              </div>
            </div>
          </div>

          {/* Related Posts */}
          <div className="border-t border-slate-800 pt-12 mt-12">
            <h2 className="text-xl font-bold text-white mb-6">Weiterlesen</h2>
            <div className="grid md:grid-cols-2 gap-4">
              {[
                { title: 'E-Rechnung Pflicht 2025: Was Unternehmen jetzt tun müssen', category: 'Finance Intelligence', slug: 'e-rechnung-pflicht-2025-was-unternehmen-jetzt-tun-muessen' },
                { title: 'Warum DATEV-Automatisierung 2026 kein Luxus mehr ist', category: 'Finance Intelligence', slug: 'warum-datev-automatisierung-2026' },
              ].map((post, idx) => (
                <Link key={idx} href={`/blog/${post.slug}`} className="bg-slate-800/30 rounded-lg p-5 border border-slate-700/50 hover:border-slate-600 transition">
                  <span className="text-xs text-orange-400 mb-2 block">{post.category}</span>
                  <h3 className="text-white font-medium">{post.title}</h3>
                </Link>
              ))}
            </div>
          </div>
        </div>
      </article>

      {/* Footer */}
      <footer className="border-t border-slate-800/50 py-8 px-6 mt-12">
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
