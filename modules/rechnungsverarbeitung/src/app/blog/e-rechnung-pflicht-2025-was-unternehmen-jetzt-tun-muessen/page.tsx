'use client';

import Link from 'next/link';
import Head from 'next/head';

export default function BlogPostERechnung() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950">
      {/* SEO Meta */}
      <head>
        <title>E-Rechnung Pflicht 2025: Was Unternehmen jetzt tun müssen | SBS Nexus</title>
        <meta name="description" content="Die E-Rechnungspflicht 2025 betrifft alle B2B-Unternehmen in Deutschland. Erfahren Sie, welche Formate gelten, welche Fristen laufen und wie KI-Automatisierung 85% Zeitersparnis bringt." />
        <meta name="keywords" content="E-Rechnung Pflicht 2025, E-Rechnung Deutschland, XRechnung, ZUGFeRD, Rechnungsverarbeitung automatisieren, DATEV Export, KI Buchhaltung" />
        <meta property="og:title" content="E-Rechnung Pflicht 2025: Was Unternehmen jetzt tun müssen" />
        <meta property="og:description" content="Kompletter Leitfaden zur E-Rechnungspflicht: Fristen, Formate, Umsetzung und wie KI-Automatisierung den Umstieg vereinfacht." />
        <meta property="og:type" content="article" />
        <meta property="og:url" content="https://www.sbsnexus.de/blog/e-rechnung-pflicht-2025-was-unternehmen-jetzt-tun-muessen" />
        <link rel="canonical" href="https://www.sbsnexus.de/blog/e-rechnung-pflicht-2025-was-unternehmen-jetzt-tun-muessen" />
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify({
          "@context": "https://schema.org",
          "@type": "Article",
          "headline": "E-Rechnung Pflicht 2025: Was Unternehmen jetzt tun müssen",
          "author": { "@type": "Person", "name": "Luis Schenk" },
          "publisher": { "@type": "Organization", "name": "SBS Deutschland GmbH" },
          "datePublished": "2026-02-15",
          "dateModified": "2026-02-15",
          "description": "Kompletter Leitfaden zur E-Rechnungspflicht 2025 für den deutschen Mittelstand.",
          "mainEntityOfPage": "https://www.sbsnexus.de/blog/e-rechnung-pflicht-2025-was-unternehmen-jetzt-tun-muessen"
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
            <span className="text-slate-500">Finance Intelligence</span>
          </nav>

          {/* Header */}
          <header className="mb-12">
            <div className="flex items-center gap-3 mb-4">
              <span className="bg-orange-500/20 text-orange-400 text-xs px-3 py-1 rounded-full">
                Finance Intelligence
              </span>
              <span className="text-slate-500 text-sm">12 Min Lesezeit</span>
            </div>
            <h1 className="text-3xl md:text-4xl font-bold text-white mb-6 leading-tight">
              E-Rechnung Pflicht 2025: Was Unternehmen jetzt tun müssen
            </h1>
            <p className="text-xl text-slate-400 mb-8">
              Seit dem 1. Januar 2025 gilt die E-Rechnungspflicht für alle B2B-Transaktionen in Deutschland. 
              Viele Unternehmen verarbeiten ihre Rechnungen immer noch manuell — mit 12–15 Minuten pro Beleg. 
              Dieser Leitfaden zeigt, was sich ändert und wie KI-Automatisierung den Umstieg vereinfacht.
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

          {/* Table of Contents */}
          <div className="bg-slate-800/30 rounded-xl p-6 border border-slate-700/50 mb-12">
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4">Inhalt</h2>
            <nav className="space-y-2 text-sm">
              <a href="#was-aendert-sich" className="block text-slate-400 hover:text-orange-400 transition">1. Was ändert sich ab 2025?</a>
              <a href="#formate" className="block text-slate-400 hover:text-orange-400 transition">2. XRechnung vs. ZUGFeRD: Welches Format?</a>
              <a href="#fristen" className="block text-slate-400 hover:text-orange-400 transition">3. Übergangsfristen und Deadlines</a>
              <a href="#herausforderungen" className="block text-slate-400 hover:text-orange-400 transition">4. Die 5 größten Herausforderungen für den Mittelstand</a>
              <a href="#ki-automatisierung" className="block text-slate-400 hover:text-orange-400 transition">5. Wie KI-Automatisierung 85% Zeitersparnis bringt</a>
              <a href="#datev" className="block text-slate-400 hover:text-orange-400 transition">6. DATEV-Integration: Der schnellste Weg</a>
              <a href="#checkliste" className="block text-slate-400 hover:text-orange-400 transition">7. Checkliste: In 5 Schritten E-Rechnungs-ready</a>
            </nav>
          </div>

          {/* Article Content */}
          <div className="prose prose-invert max-w-none">
            
            {/* Section 1 */}
            <section id="was-aendert-sich" className="mb-12">
              <h2 className="text-2xl font-bold text-white mb-4">1. Was ändert sich ab 2025?</h2>
              <p className="text-slate-300 leading-relaxed mb-4">
                Mit dem Wachstumschancengesetz hat der Bundestag die verpflichtende E-Rechnung im B2B-Bereich 
                beschlossen. Ab dem 1. Januar 2025 müssen alle inländischen B2B-Unternehmen in der Lage sein, 
                elektronische Rechnungen zu empfangen. Die Pflicht zum Versand folgt gestaffelt.
              </p>
              <p className="text-slate-300 leading-relaxed mb-4">
                Das bedeutet konkret: Eine PDF-Rechnung per E-Mail gilt nicht mehr als elektronische Rechnung im 
                Sinne des Gesetzes. Gefordert werden strukturierte Datenformate, die maschinell ausgelesen werden 
                können — allen voran XRechnung und ZUGFeRD 2.x.
              </p>
              <div className="bg-orange-500/10 border border-orange-500/30 rounded-lg p-5 my-6">
                <p className="text-orange-300 text-sm font-medium mb-1">Kernaussage</p>
                <p className="text-slate-200">
                  PDF-Rechnungen per E-Mail sind ab 2025 keine E-Rechnungen mehr. Gefordert werden maschinenlesbare 
                  Formate wie XRechnung oder ZUGFeRD 2.x nach EN 16931.
                </p>
              </div>
            </section>

            {/* Section 2 */}
            <section id="formate" className="mb-12">
              <h2 className="text-2xl font-bold text-white mb-4">2. XRechnung vs. ZUGFeRD: Welches Format?</h2>
              <p className="text-slate-300 leading-relaxed mb-4">
                Beide Formate erfüllen die europäische Norm EN 16931 und sind damit gesetzeskonform. Der Unterschied 
                liegt im Aufbau: XRechnung ist ein reines XML-Format — optimal für vollautomatische Verarbeitung. 
                ZUGFeRD 2.x kombiniert eine PDF-Datei mit eingebettetem XML — dadurch ist die Rechnung sowohl 
                menschenlesbar als auch maschinenlesbar.
              </p>
              
              <div className="overflow-x-auto my-6">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-700">
                      <th className="text-left py-3 px-4 text-slate-400 font-medium">Kriterium</th>
                      <th className="text-left py-3 px-4 text-slate-400 font-medium">XRechnung</th>
                      <th className="text-left py-3 px-4 text-slate-400 font-medium">ZUGFeRD 2.x</th>
                    </tr>
                  </thead>
                  <tbody className="text-slate-300">
                    <tr className="border-b border-slate-800">
                      <td className="py-3 px-4">Format</td>
                      <td className="py-3 px-4">Reines XML</td>
                      <td className="py-3 px-4">PDF + eingebettetes XML</td>
                    </tr>
                    <tr className="border-b border-slate-800">
                      <td className="py-3 px-4">Menschenlesbar</td>
                      <td className="py-3 px-4 text-red-400">Nein</td>
                      <td className="py-3 px-4 text-green-400">Ja</td>
                    </tr>
                    <tr className="border-b border-slate-800">
                      <td className="py-3 px-4">Maschinenlesbar</td>
                      <td className="py-3 px-4 text-green-400">Ja</td>
                      <td className="py-3 px-4 text-green-400">Ja</td>
                    </tr>
                    <tr className="border-b border-slate-800">
                      <td className="py-3 px-4">DATEV-kompatibel</td>
                      <td className="py-3 px-4 text-green-400">Ja</td>
                      <td className="py-3 px-4 text-green-400">Ja</td>
                    </tr>
                    <tr className="border-b border-slate-800">
                      <td className="py-3 px-4">Empfehlung Mittelstand</td>
                      <td className="py-3 px-4">Behörden, öffentliche Aufträge</td>
                      <td className="py-3 px-4 text-orange-400 font-medium">Universell einsetzbar</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <p className="text-slate-300 leading-relaxed">
                Für die meisten mittelständischen Unternehmen ist ZUGFeRD 2.x die pragmatischere Wahl: 
                Geschäftspartner können die Rechnung weiterhin als PDF lesen, während die strukturierten Daten 
                automatisch in Buchhaltungssysteme wie DATEV importiert werden können.
              </p>
            </section>

            {/* Section 3 */}
            <section id="fristen" className="mb-12">
              <h2 className="text-2xl font-bold text-white mb-4">3. Übergangsfristen und Deadlines</h2>
              <p className="text-slate-300 leading-relaxed mb-4">
                Der Gesetzgeber hat gestaffelte Übergangsfristen vorgesehen, um Unternehmen Zeit für die 
                technische Umstellung zu geben.
              </p>
              
              <div className="space-y-4 my-6">
                <div className="bg-slate-800/50 rounded-lg p-5 border-l-4 border-green-500">
                  <p className="text-green-400 text-sm font-semibold mb-1">Ab 1. Januar 2025</p>
                  <p className="text-slate-300">Empfangspflicht: Alle B2B-Unternehmen müssen E-Rechnungen empfangen und verarbeiten können.</p>
                </div>
                <div className="bg-slate-800/50 rounded-lg p-5 border-l-4 border-yellow-500">
                  <p className="text-yellow-400 text-sm font-semibold mb-1">Bis 31. Dezember 2026</p>
                  <p className="text-slate-300">Übergangszeit: Papier- und PDF-Rechnungen dürfen noch versendet werden, wenn der Empfänger zustimmt.</p>
                </div>
                <div className="bg-slate-800/50 rounded-lg p-5 border-l-4 border-orange-500">
                  <p className="text-orange-400 text-sm font-semibold mb-1">Bis 31. Dezember 2027</p>
                  <p className="text-slate-300">Erweiterte Frist für Unternehmen mit weniger als 800.000 EUR Vorjahresumsatz.</p>
                </div>
                <div className="bg-slate-800/50 rounded-lg p-5 border-l-4 border-red-500">
                  <p className="text-red-400 text-sm font-semibold mb-1">Ab 1. Januar 2028</p>
                  <p className="text-slate-300">Vollständige Pflicht: Alle B2B-Rechnungen müssen als E-Rechnung versendet werden.</p>
                </div>
              </div>

              <div className="bg-orange-500/10 border border-orange-500/30 rounded-lg p-5 my-6">
                <p className="text-orange-300 text-sm font-medium mb-1">Praxis-Tipp</p>
                <p className="text-slate-200">
                  Warten Sie nicht bis 2028. Unternehmen, die jetzt automatisieren, haben zwei Jahre Vorsprung 
                  bei der Prozessoptimierung — und sparen ab Tag 1 Zeit und Geld.
                </p>
              </div>
            </section>

            {/* Section 4 */}
            <section id="herausforderungen" className="mb-12">
              <h2 className="text-2xl font-bold text-white mb-4">4. Die 5 größten Herausforderungen für den Mittelstand</h2>
              
              <div className="space-y-6 my-6">
                <div className="bg-slate-800/30 rounded-lg p-5 border border-slate-700/50">
                  <h3 className="text-white font-semibold mb-2">Herausforderung 1: Manuelle Prozesse</h3>
                  <p className="text-slate-300 text-sm leading-relaxed">
                    Viele Unternehmen erfassen Rechnungsdaten noch manuell in Excel oder direkt in DATEV. Bei 500 
                    eingehenden Rechnungen pro Monat und 12–15 Minuten pro Rechnung bedeutet das 100–125 
                    Arbeitsstunden — die Kapazität von mehr als einem halben FTE nur für Dateneingabe.
                  </p>
                </div>
                <div className="bg-slate-800/30 rounded-lg p-5 border border-slate-700/50">
                  <h3 className="text-white font-semibold mb-2">Herausforderung 2: Verschiedene Eingangsformate</h3>
                  <p className="text-slate-300 text-sm leading-relaxed">
                    Rechnungen kommen als PDF per E-Mail, als Scan, als Foto vom Außendienst oder als strukturierte 
                    XML-Datei. Diese Formatvielfalt erfordert unterschiedliche Verarbeitungswege — oder eine 
                    intelligente Lösung, die alle Formate automatisch erkennt.
                  </p>
                </div>
                <div className="bg-slate-800/30 rounded-lg p-5 border border-slate-700/50">
                  <h3 className="text-white font-semibold mb-2">Herausforderung 3: DATEV-Kompatibilität</h3>
                  <p className="text-slate-300 text-sm leading-relaxed">
                    90% der deutschen Steuerberater arbeiten mit DATEV. Die Rechnungsdaten müssen im korrekten 
                    Format (SKR03 oder SKR04) mit den richtigen Kontierungen exportiert werden — ein fehleranfälliger 
                    Schritt, der bei manueller Bearbeitung regelmäßig zu Korrekturen führt.
                  </p>
                </div>
                <div className="bg-slate-800/30 rounded-lg p-5 border border-slate-700/50">
                  <h3 className="text-white font-semibold mb-2">Herausforderung 4: Fehlerquote und Compliance</h3>
                  <p className="text-slate-300 text-sm leading-relaxed">
                    Manuelle Dateneingabe produziert typischerweise 2–5% Fehler. Bei Steuerprüfungen können 
                    fehlerhafte Buchungen zu Nachzahlungen, Zinsen und im schlimmsten Fall zu Compliance-Verstößen führen.
                  </p>
                </div>
                <div className="bg-slate-800/30 rounded-lg p-5 border border-slate-700/50">
                  <h3 className="text-white font-semibold mb-2">Herausforderung 5: Datensicherheit</h3>
                  <p className="text-slate-300 text-sm leading-relaxed">
                    Rechnungen enthalten sensible Geschäftsdaten. Viele Cloud-Lösungen verarbeiten diese Daten 
                    auf US-Servern — ein Problem unter DSGVO. Deutsche Unternehmen brauchen Lösungen mit 
                    Datenverarbeitung in Deutschland.
                  </p>
                </div>
              </div>
            </section>

            {/* Section 5 */}
            <section id="ki-automatisierung" className="mb-12">
              <h2 className="text-2xl font-bold text-white mb-4">5. Wie KI-Automatisierung 85% Zeitersparnis bringt</h2>
              <p className="text-slate-300 leading-relaxed mb-4">
                Moderne KI-Systeme erkennen Rechnungsdaten nicht durch starre Regelwerke, sondern durch 
                intelligente Dokumentenanalyse. Das funktioniert formatunabhängig — egal ob PDF, Scan, Foto 
                oder strukturiertes XML.
              </p>
              
              <div className="bg-gradient-to-r from-slate-800/50 to-orange-500/10 rounded-xl p-6 border border-slate-700/50 my-6">
                <h3 className="text-white font-semibold mb-4">Vorher vs. Nachher: Rechnungsverarbeitung</h3>
                <div className="grid md:grid-cols-2 gap-6">
                  <div>
                    <p className="text-red-400 text-sm font-semibold mb-3">Manueller Prozess</p>
                    <div className="space-y-2 text-slate-300 text-sm">
                      <p>12–15 Minuten pro Rechnung</p>
                      <p>2–5% Fehlerquote</p>
                      <p>DATEV-Export manuell (wöchentlich)</p>
                      <p>Keine automatische Kontierung</p>
                      <p>125 Stunden/Monat bei 500 Rechnungen</p>
                    </div>
                  </div>
                  <div>
                    <p className="text-green-400 text-sm font-semibold mb-3">KI-automatisiert</p>
                    <div className="space-y-2 text-slate-300 text-sm">
                      <p>Unter 3 Sekunden pro Rechnung</p>
                      <p>Unter 0,5% Fehlerquote</p>
                      <p>DATEV-Export automatisch (täglich)</p>
                      <p>Automatische SKR03/04-Kontierung</p>
                      <p>18 Stunden/Monat bei 500 Rechnungen</p>
                    </div>
                  </div>
                </div>
              </div>

              <p className="text-slate-300 leading-relaxed mb-4">
                Der Ablauf ist denkbar einfach: Rechnung hochladen oder per E-Mail weiterleiten — die KI 
                extrahiert Lieferant, Rechnungsnummer, Positionen, Beträge und Umsatzsteuer. Anschließend wird 
                automatisch die passende Kontierung vorgeschlagen und der DATEV-Export erstellt. Die 
                Sachbearbeiterin prüft nur noch das Ergebnis und gibt frei.
              </p>
            </section>

            {/* Section 6 */}
            <section id="datev" className="mb-12">
              <h2 className="text-2xl font-bold text-white mb-4">6. DATEV-Integration: Der schnellste Weg</h2>
              <p className="text-slate-300 leading-relaxed mb-4">
                Für den deutschen Mittelstand ist die DATEV-Kompatibilität entscheidend. Eine 
                KI-Rechnungsverarbeitung, die nicht nahtlos mit DATEV funktioniert, schafft nur ein weiteres 
                Silo statt echter Automatisierung.
              </p>
              <p className="text-slate-300 leading-relaxed mb-4">
                Die wichtigsten Anforderungen an eine DATEV-kompatible Lösung: Export im CSV- oder 
                XML-Format nach DATEV-Standard, Unterstützung von SKR03 und SKR04, automatische Zuordnung 
                zu Sachkonten und Kostenstellen, Belegbilder als DATEV-konforme Anhänge, und 
                Schnittstelle zu DATEV Unternehmen online oder DATEV Connect.
              </p>
              
              <div className="bg-orange-500/10 border border-orange-500/30 rounded-lg p-5 my-6">
                <p className="text-orange-300 text-sm font-medium mb-1">SBS Nexus</p>
                <p className="text-slate-200">
                  SBS Nexus bietet native DATEV-Integration mit automatischer SKR03/04-Kontierung und 
                  Export — bei 100% deutscher Datenverarbeitung (Frankfurt). In 2 Wochen live, ohne 
                  6-monatiges Einführungsprojekt.
                </p>
                <Link 
                  href="https://calendly.com/ki-sbsdeutschland/sbs-nexus-30-minuten-discovery-call"
                  className="inline-block mt-3 bg-orange-500 hover:bg-orange-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition"
                >
                  Kostenlose Demo buchen
                </Link>
              </div>
            </section>

            {/* Section 7 - Checklist */}
            <section id="checkliste" className="mb-12">
              <h2 className="text-2xl font-bold text-white mb-4">7. Checkliste: In 5 Schritten E-Rechnungs-ready</h2>
              
              <div className="space-y-4 my-6">
                {[
                  { step: '01', title: 'Ist-Zustand analysieren', desc: 'Wie viele Rechnungen verarbeiten Sie monatlich? Wie hoch ist der manuelle Aufwand? Welche Formate kommen rein?' },
                  { step: '02', title: 'Formate klären', desc: 'Prüfen Sie, ob Ihre Lieferanten bereits XRechnung oder ZUGFeRD unterstützen. Informieren Sie Ihre Geschäftspartner über die neuen Anforderungen.' },
                  { step: '03', title: 'DATEV-Workflow prüfen', desc: 'Klären Sie mit Ihrem Steuerberater den gewünschten Exportprozess: CSV, XML oder DATEV Connect Online? Welcher Kontenrahmen wird genutzt?' },
                  { step: '04', title: 'Automatisierungslösung evaluieren', desc: 'Vergleichen Sie Lösungen anhand von: Erkennungsgenauigkeit, DATEV-Kompatibilität, Datensicherheit (Serverstandort), Implementierungsdauer und Kosten.' },
                  { step: '05', title: 'Pilotphase starten', desc: 'Beginnen Sie mit einem Teilbereich (z.B. Eingangsrechnungen eines Standorts). Messen Sie Zeitersparnis und Fehlerquote vor und nach der Umstellung.' },
                ].map((item, idx) => (
                  <div key={idx} className="flex gap-4 bg-slate-800/30 rounded-lg p-5 border border-slate-700/50">
                    <div className="text-orange-500 font-bold text-lg min-w-[32px]">{item.step}</div>
                    <div>
                      <h3 className="text-white font-semibold mb-1">{item.title}</h3>
                      <p className="text-slate-300 text-sm leading-relaxed">{item.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            {/* Conclusion / CTA */}
            <section className="mb-12">
              <h2 className="text-2xl font-bold text-white mb-4">Fazit: Jetzt handeln, 2028 profitieren</h2>
              <p className="text-slate-300 leading-relaxed mb-4">
                Die E-Rechnungspflicht ist kein optionales IT-Projekt — sie wird für alle B2B-Unternehmen 
                verbindlich. Wer jetzt automatisiert, spart nicht nur 85% Zeit bei der Rechnungsverarbeitung, 
                sondern reduziert Fehler, verbessert die Compliance und entlastet die Buchhaltung für 
                wertschöpfendere Aufgaben.
              </p>
              <p className="text-slate-300 leading-relaxed mb-6">
                Der schnellste Weg: Eine KI-Lösung mit nativer DATEV-Integration, die in Wochen statt 
                Monaten live geht — und dabei DSGVO-konform in Deutschland betrieben wird.
              </p>

              <div className="bg-gradient-to-r from-orange-500/20 to-slate-800/50 rounded-xl p-8 border border-orange-500/30 text-center">
                <h3 className="text-xl font-bold text-white mb-3">
                  Bereit für die E-Rechnungspflicht?
                </h3>
                <p className="text-slate-300 mb-6">
                  In 30 Minuten zeigen wir Ihnen, wie SBS Nexus Ihre Rechnungen in unter 3 Sekunden 
                  verarbeitet — mit Ihren echten Dokumenten.
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
                { title: 'Warum DATEV-Automatisierung 2026 kein Luxus mehr ist', category: 'Finance Intelligence', slug: 'warum-datev-automatisierung-2026' },
                { title: 'KI-Rechnungsverarbeitung im Mittelstand: Der komplette Vergleich', category: 'Vergleich', slug: 'ki-rechnungsverarbeitung-mittelstand-vergleich' },
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
