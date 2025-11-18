#!/usr/bin/env python3
"""
Rechtliche Seiten mit ECHTEN Daten von SBS Deutschland
"""

from pathlib import Path

# ============================================
# IMPRESSUM
# ============================================
IMPRESSUM_HTML = '''<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <title>Impressum – SBS Deutschland</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="icon" href="/static/favicon.ico">
  <style>
    :root {
      --sbs-bg: #f5f6f8;
      --sbs-white: #ffffff;
      --sbs-dark: #003856;
      --sbs-accent: #ffb400;
      --sbs-text: #17212b;
      --sbs-muted: #6b7280;
    }
    
    * { box-sizing: border-box; margin: 0; padding: 0; }
    
    body {
      font-family: system-ui, sans-serif;
      background: var(--sbs-bg);
      color: var(--sbs-text);
      line-height: 1.7;
    }
    
    .container {
      max-width: 900px;
      margin: 0 auto;
      padding: 40px 24px 80px;
    }
    
    h1 {
      font-size: 2.2rem;
      color: var(--sbs-dark);
      margin-bottom: 12px;
      font-weight: 700;
    }
    
    h2 {
      font-size: 1.4rem;
      color: var(--sbs-dark);
      margin: 36px 0 14px;
      font-weight: 600;
    }
    
    p, address {
      margin-bottom: 18px;
      font-style: normal;
      font-size: 1rem;
    }
    
    strong {
      color: var(--sbs-dark);
      font-weight: 600;
    }
    
    a {
      color: var(--sbs-accent);
      text-decoration: none;
    }
    
    a:hover {
      text-decoration: underline;
    }
    
    .back-link {
      display: inline-block;
      margin-bottom: 24px;
      color: var(--sbs-muted);
      font-size: 0.95rem;
      transition: color 0.2s;
    }
    
    .back-link:hover {
      color: var(--sbs-dark);
    }
  </style>
</head>
<body>

<div class="container">
  <a href="/sbshomepage/" class="back-link">← Zurück zur Startseite</a>
  
  <h1>Impressum</h1>
  
  <h2>Angaben gemäß § 5 TMG</h2>
  <address>
    <strong>SBS Deutschland GmbH & Co. KG</strong><br>
    In der Dell 19<br>
    69469 Weinheim<br>
    Deutschland
  </address>
  
  <h2>Vertreten durch</h2>
  <p>
    Geschäftsführer: Andreas Schenk
  </p>
  
  <h2>Kontakt</h2>
  <p>
    <strong>Telefon:</strong> +49 6201 80 6109<br>
    <strong>E-Mail:</strong> <a href="mailto:info@sbsdeutschland.com">info@sbsdeutschland.com</a><br>
    <strong>Website:</strong> <a href="https://www.sbsdeutschland.com">www.sbsdeutschland.com</a>
  </p>
  
  <p>
    <strong>Geschäftszeiten:</strong><br>
    Montag bis Freitag: 9:00 – 18:00 Uhr
  </p>
  
  <h2>Registereintrag</h2>
  <p>
    <strong>Eintragung im Handelsregister:</strong><br>
    Registergericht: Amtsgericht Mannheim<br>
    Registernummer: HRA 706204
  </p>
  
  <h2>Umsatzsteuer-ID</h2>
  <p>
    Umsatzsteuer-Identifikationsnummer gemäß § 27a Umsatzsteuergesetz:<br>
    <em>Auf Anfrage erhältlich</em>
  </p>
  
  <h2>Berufsbezeichnung und berufsrechtliche Regelungen</h2>
  <p>
    Dienstleistungen im Bereich KI-Rechnungsverarbeitung, IT-Consulting, 
    Quality & Risk Management, SAP-Consulting sowie Metrologie und PMO.
  </p>
  
  <h2>EU-Streitschlichtung</h2>
  <p>
    Die Europäische Kommission stellt eine Plattform zur Online-Streitbeilegung (OS) bereit:<br>
    <a href="https://ec.europa.eu/consumers/odr" target="_blank" rel="noopener">https://ec.europa.eu/consumers/odr</a>
  </p>
  <p>
    Unsere E-Mail-Adresse finden Sie oben im Impressum.
  </p>
  
  <h2>Verbraucher­streit­beilegung / Universal­schlichtungs­stelle</h2>
  <p>
    Wir sind nicht bereit oder verpflichtet, an Streitbeilegungsverfahren vor einer 
    Verbraucherschlichtungsstelle teilzunehmen.
  </p>
  
  <h2>Haftung für Inhalte</h2>
  <p>
    Als Diensteanbieter sind wir gemäß § 7 Abs.1 TMG für eigene Inhalte auf diesen Seiten nach 
    den allgemeinen Gesetzen verantwortlich. Nach §§ 8 bis 10 TMG sind wir als Diensteanbieter 
    jedoch nicht verpflichtet, übermittelte oder gespeicherte fremde Informationen zu überwachen 
    oder nach Umständen zu forschen, die auf eine rechtswidrige Tätigkeit hinweisen.
  </p>
  
  <h2>Haftung für Links</h2>
  <p>
    Unser Angebot enthält Links zu externen Websites Dritter, auf deren Inhalte wir keinen 
    Einfluss haben. Deshalb können wir für diese fremden Inhalte auch keine Gewähr übernehmen. 
    Für die Inhalte der verlinkten Seiten ist stets der jeweilige Anbieter oder Betreiber der 
    Seiten verantwortlich.
  </p>
  
  <h2>Urheberrecht</h2>
  <p>
    Die durch die Seitenbetreiber erstellten Inhalte und Werke auf diesen Seiten unterliegen 
    dem deutschen Urheberrecht. Die Vervielfältigung, Bearbeitung, Verbreitung und jede Art der 
    Verwertung außerhalb der Grenzen des Urheberrechtes bedürfen der schriftlichen Zustimmung 
    des jeweiligen Autors bzw. Erstellers.
  </p>
</div>

</body>
</html>'''

# ============================================
# AGB
# ============================================
AGB_HTML = '''<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <title>AGB – SBS Deutschland</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="icon" href="/static/favicon.ico">
  <style>
    :root {
      --sbs-bg: #f5f6f8;
      --sbs-white: #ffffff;
      --sbs-dark: #003856;
      --sbs-accent: #ffb400;
      --sbs-text: #17212b;
      --sbs-muted: #6b7280;
    }
    
    * { box-sizing: border-box; margin: 0; padding: 0; }
    
    body {
      font-family: system-ui, sans-serif;
      background: var(--sbs-bg);
      color: var(--sbs-text);
      line-height: 1.7;
    }
    
    .container {
      max-width: 900px;
      margin: 0 auto;
      padding: 40px 24px 80px;
    }
    
    h1 {
      font-size: 2.2rem;
      color: var(--sbs-dark);
      margin-bottom: 12px;
      font-weight: 700;
    }
    
    h2 {
      font-size: 1.4rem;
      color: var(--sbs-dark);
      margin: 36px 0 14px;
      font-weight: 600;
    }
    
    h3 {
      font-size: 1.15rem;
      color: var(--sbs-dark);
      margin: 26px 0 12px;
      font-weight: 600;
    }
    
    p, ul {
      margin-bottom: 18px;
      font-size: 1rem;
    }
    
    ul {
      padding-left: 28px;
    }
    
    li {
      margin-bottom: 8px;
    }
    
    strong {
      color: var(--sbs-dark);
      font-weight: 600;
    }
    
    a {
      color: var(--sbs-accent);
      text-decoration: none;
    }
    
    a:hover {
      text-decoration: underline;
    }
    
    .back-link {
      display: inline-block;
      margin-bottom: 24px;
      color: var(--sbs-muted);
      font-size: 0.95rem;
    }
  </style>
</head>
<body>

<div class="container">
  <a href="/sbshomepage/" class="back-link">← Zurück zur Startseite</a>
  
  <h1>Allgemeine Geschäftsbedingungen (AGB)</h1>
  
  <p><strong>Stand: November 2025</strong></p>
  
  <p>
    Für alle Geschäftsbeziehungen zwischen der SBS Deutschland GmbH & Co. KG 
    (nachfolgend "Auftragnehmer") und ihren Auftraggebern (nachfolgend "Auftraggeber") 
    gelten ausschließlich die nachfolgenden Allgemeinen Geschäftsbedingungen.
  </p>
  
  <h2>§ 1 Geltungsbereich</h2>
  <p>
    Diese Allgemeinen Geschäftsbedingungen gelten für alle Verträge über die Erbringung von 
    Dienstleistungen im Bereich:
  </p>
  <ul>
    <li>KI-Rechnungsverarbeitung</li>
    <li>IT-Consulting und Softwareentwicklung</li>
    <li>Quality & Risk Management</li>
    <li>SAP-Consulting und Reporting</li>
    <li>Metrologie und Projektmanagement-Office (PMO)</li>
  </ul>
  <p>
    Entgegenstehende oder abweichende Bedingungen des Auftraggebers werden nur dann Vertragsbestandteil, 
    wenn der Auftragnehmer diesen ausdrücklich schriftlich zugestimmt hat.
  </p>
  
  <h2>§ 2 Vertragsschluss</h2>
  <p>
    Angebote des Auftragnehmers sind freibleibend und unverbindlich, sofern sie nicht ausdrücklich 
    als verbindlich gekennzeichnet sind. Der Vertrag kommt durch schriftliche Auftragsbestätigung 
    des Auftragnehmers oder durch Beginn der Leistungserbringung zustande.
  </p>
  
  <h2>§ 3 Leistungsumfang</h2>
  <p>
    Der Umfang der zu erbringenden Leistungen ergibt sich aus der Leistungsbeschreibung im 
    jeweiligen Angebot bzw. Vertrag. Änderungen und Ergänzungen des Leistungsumfangs bedürfen 
    der Schriftform und werden gesondert vergütet.
  </p>
  
  <h2>§ 4 Mitwirkungspflichten des Auftraggebers</h2>
  <p>
    Der Auftraggeber verpflichtet sich:
  </p>
  <ul>
    <li>Alle für die Leistungserbringung erforderlichen Informationen, Daten und Unterlagen 
    rechtzeitig zur Verfügung zu stellen</li>
    <li>Ansprechpartner zu benennen und verfügbar zu halten</li>
    <li>Erforderliche Zugänge zu Systemen und Räumlichkeiten bereitzustellen</li>
    <li>Entscheidungen zeitnah zu treffen</li>
  </ul>
  <p>
    Verzögerungen durch fehlende oder unzureichende Mitwirkung gehen zu Lasten des Auftraggebers 
    und berechtigen den Auftragnehmer zur Anpassung von Terminen und Vergütung.
  </p>
  
  <h2>§ 5 Vergütung und Zahlungsbedingungen</h2>
  <p>
    Die Vergütung richtet sich nach der jeweiligen Vereinbarung (Festpreis, Stunden- oder Tagessatz). 
    Sofern nicht anders vereinbart:
  </p>
  <ul>
    <li>Rechnungen sind innerhalb von 14 Tagen nach Rechnungsdatum ohne Abzug zur Zahlung fällig</li>
    <li>Bei Zahlungsverzug gelten die gesetzlichen Verzugszinsen</li>
    <li>Alle Preise verstehen sich zuzüglich der gesetzlichen Umsatzsteuer</li>
  </ul>
  
  <h2>§ 6 Vertraulichkeit</h2>
  <p>
    Beide Parteien verpflichten sich zur Vertraulichkeit über alle im Rahmen der Zusammenarbeit 
    bekannt gewordenen Informationen, insbesondere Geschäfts- und Betriebsgeheimnisse. Diese 
    Verpflichtung besteht auch nach Beendigung des Vertragsverhältnisses fort.
  </p>
  
  <h2>§ 7 Datenschutz</h2>
  <p>
    Die Verarbeitung personenbezogener Daten erfolgt gemäß den Bestimmungen der 
    Datenschutz-Grundverordnung (DSGVO) und des Bundesdatenschutzgesetzes (BDSG). 
    Details regelt unsere separate <a href="/sbshomepage/datenschutz.html">Datenschutzerklärung</a>.
  </p>
  
  <h2>§ 8 Gewährleistung</h2>
  <p>
    Der Auftragnehmer erbringt seine Leistungen mit der im Verkehr erforderlichen Sorgfalt und 
    unter Einhaltung anerkannter Regeln der Technik. Bei Mängeln ist dem Auftragnehmer zunächst 
    innerhalb angemessener Frist Gelegenheit zur Nachbesserung zu geben.
  </p>
  <p>
    Die Gewährleistungsfrist beträgt 12 Monate ab Abnahme, soweit nicht gesetzlich längere Fristen 
    vorgeschrieben sind.
  </p>
  
  <h2>§ 9 Haftung</h2>
  <p>
    Der Auftragnehmer haftet unbeschränkt:
  </p>
  <ul>
    <li>Bei Vorsatz und grober Fahrlässigkeit</li>
    <li>Bei Verletzung von Leben, Körper oder Gesundheit</li>
    <li>Nach den Vorschriften des Produkthaftungsgesetzes</li>
    <li>Im Umfang einer übernommenen Garantie</li>
  </ul>
  <p>
    Bei leichter Fahrlässigkeit haftet der Auftragnehmer nur bei Verletzung wesentlicher 
    Vertragspflichten (Kardinalpflichten). In diesem Fall ist die Haftung der Höhe nach auf den 
    vertragstypischen, vorhersehbaren Schaden begrenzt.
  </p>
  
  <h2>§ 10 Urheberrechte und Nutzungsrechte</h2>
  <p>
    Alle vom Auftragnehmer erstellten Arbeitsergebnisse (Dokumentationen, Software, Konzepte etc.) 
    bleiben bis zur vollständigen Bezahlung Eigentum des Auftragnehmers. Nach vollständiger Zahlung 
    erhält der Auftraggeber die vereinbarten Nutzungsrechte.
  </p>
  
  <h2>§ 11 Laufzeit und Kündigung</h2>
  <p>
    Die Vertragslaufzeit und Kündigungsfristen ergeben sich aus der jeweiligen Vereinbarung. 
    Projektbezogene Verträge enden mit Abschluss des Projekts. Dauerschuldverhältnisse können 
    mit einer Frist von 3 Monaten zum Quartalsende gekündigt werden, sofern nichts anderes 
    vereinbart wurde.
  </p>
  <p>
    Das Recht zur außerordentlichen Kündigung aus wichtigem Grund bleibt unberührt.
  </p>
  
  <h2>§ 12 Abtretung und Aufrechnung</h2>
  <p>
    Die Abtretung von Rechten und Pflichten aus diesem Vertrag bedarf der vorherigen schriftlichen 
    Zustimmung der anderen Partei. Der Auftraggeber kann nur mit unbestrittenen oder rechtskräftig 
    festgestellten Forderungen aufrechnen.
  </p>
  
  <h2>§ 13 Salvatorische Klausel</h2>
  <p>
    Sollten einzelne Bestimmungen dieser AGB unwirksam sein oder werden, bleibt die Wirksamkeit 
    der übrigen Bestimmungen hiervon unberührt. Die Parteien verpflichten sich, anstelle der 
    unwirksamen Bestimmung eine rechtlich zulässige Regelung zu treffen, die dem wirtschaftlichen 
    Zweck der unwirksamen Bestimmung am nächsten kommt.
  </p>
  
  <h2>§ 14 Anwendbares Recht und Gerichtsstand</h2>
  <p>
    Für alle Rechtsbeziehungen zwischen dem Auftragnehmer und dem Auftraggeber gilt ausschließlich 
    das Recht der Bundesrepublik Deutschland unter Ausschluss des UN-Kaufrechts.
  </p>
  <p>
    Gerichtsstand für alle Streitigkeiten aus diesem Vertrag ist Mannheim, sofern der Auftraggeber 
    Kaufmann, juristische Person des öffentlichen Rechts oder öffentlich-rechtliches Sondervermögen ist.
  </p>
  
  <p style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
    <strong>Kontakt bei Fragen:</strong><br>
    SBS Deutschland GmbH & Co. KG<br>
    In der Dell 19, 69469 Weinheim<br>
    Telefon: +49 6201 80 6109<br>
    E-Mail: <a href="mailto:info@sbsdeutschland.com">info@sbsdeutschland.com</a>
  </p>
</div>

</body>
</html>'''

# ============================================
# DATENSCHUTZ (wird in nächster Nachricht fortgesetzt wegen Länge)
# ============================================
DATENSCHUTZ_HTML = '''<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <title>Datenschutzerklärung – SBS Deutschland</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="icon" href="/static/favicon.ico">
  <style>
    :root {
      --sbs-bg: #f5f6f8;
      --sbs-white: #ffffff;
      --sbs-dark: #003856;
      --sbs-accent: #ffb400;
      --sbs-text: #17212b;
      --sbs-muted: #6b7280;
    }
    
    * { box-sizing: border-box; margin: 0; padding: 0; }
    
    body {
      font-family: system-ui, sans-serif;
      background: var(--sbs-bg);
      color: var(--sbs-text);
      line-height: 1.7;
    }
    
    .container {
      max-width: 900px;
      margin: 0 auto;
      padding: 40px 24px 80px;
    }
    
    h1 {
      font-size: 2.2rem;
      color: var(--sbs-dark);
      margin-bottom: 12px;
      font-weight: 700;
    }
    
    h2 {
      font-size: 1.4rem;
      color: var(--sbs-dark);
      margin: 36px 0 14px;
      font-weight: 600;
    }
    
    h3 {
      font-size: 1.15rem;
      color: var(--sbs-dark);
      margin: 26px 0 12px;
      font-weight: 600;
    }
    
    p, ul {
      margin-bottom: 18px;
      font-size: 1rem;
    }
    
    ul {
      padding-left: 28px;
    }
    
    li {
      margin-bottom: 8px;
    }
    
    strong {
      color: var(--sbs-dark);
      font-weight: 600;
    }
    
    a {
      color: var(--sbs-accent);
      text-decoration: none;
    }
    
    a:hover {
      text-decoration: underline;
    }
    
    .back-link {
      display: inline-block;
      margin-bottom: 24px;
      color: var(--sbs-muted);
      font-size: 0.95rem;
    }
    
    .info-box {
      background: rgba(255, 180, 0, 0.1);
      border-left: 4px solid var(--sbs-accent);
      padding: 16px;
      margin: 24px 0;
      border-radius: 6px;
    }
  </style>
</head>
<body>

<div class="container">
  <a href="/sbshomepage/" class="back-link">← Zurück zur Startseite</a>
  
  <h1>Datenschutzerklärung</h1>
  
  <p><strong>Stand: November 2025</strong></p>
  
  <div class="info-box">
    <p style="margin: 0;">
      <strong>Zusammenfassung:</strong> Wir nehmen den Schutz Ihrer persönlichen Daten sehr ernst 
      und behandeln Ihre personenbezogenen Daten vertraulich und entsprechend der gesetzlichen 
      Datenschutzvorschriften sowie dieser Datenschutzerklärung.
    </p>
  </div>
  
  <h2>1. Verantwortlicher</h2>
  <p>
    Verantwortlich für die Datenverarbeitung auf dieser Website ist:
  </p>
  <address>
    <strong>SBS Deutschland GmbH & Co. KG</strong><br>
    In der Dell 19<br>
    69469 Weinheim<br>
    Deutschland<br><br>
    <strong>Telefon:</strong> +49 6201 80 6109<br>
    <strong>E-Mail:</strong> <a href="mailto:info@sbsdeutschland.com">info@sbsdeutschland.com</a><br>
    <strong>Website:</strong> <a href="https://www.sbsdeutschland.com">www.sbsdeutschland.com</a>
  </address>
  
  <p style="margin-top: 16px;">
    <strong>Geschäftsführer:</strong> Andreas Schenk<br>
    <strong>Datenschutzanfragen:</strong> <a href="mailto:info@sbsdeutschland.com">info@sbsdeutschland.com</a>
  </p>
  
  <h2>2. Allgemeines zur Datenverarbeitung</h2>
  
  <h3>2.1 Umfang der Verarbeitung personenbezogener Daten</h3>
  <p>
    Wir erheben und verwenden personenbezogene Daten unserer Nutzer grundsätzlich nur, soweit 
    dies zur Bereitstellung einer funktionsfähigen Website sowie unserer Inhalte und Leistungen 
    erforderlich ist. Die Erhebung und Verwendung personenbezogener Daten unserer Nutzer erfolgt 
    regelmäßig nur nach Einwilligung des Nutzers.
  </p>
  
  <h3>2.2 Rechtsgrundlage für die Verarbeitung personenbezogener Daten</h3>
  <p>
    Soweit wir für Verarbeitungsvorgänge personenbezogener Daten eine Einwilligung der betroffenen 
    Person einholen, dient Art. 6 Abs. 1 lit. a EU-Datenschutzgrundverordnung (DSGVO) als Rechtsgrundlage.
  </p>
  <p>
    Bei der Verarbeitung von personenbezogenen Daten, die zur Erfüllung eines Vertrages, dessen 
    Vertragspartei die betroffene Person ist, erforderlich ist, dient Art. 6 Abs. 1 lit. b DSGVO 
    als Rechtsgrundlage.
  </p>
  <p>
    Soweit eine Verarbeitung personenbezogener Daten zur Erfüllung einer rechtlichen Verpflichtung 
    erforderlich ist, dient Art. 6 Abs. 1 lit. c DSGVO als Rechtsgrundlage.
  </p>
  <p>
    Ist die Verarbeitung zur Wahrung eines berechtigten Interesses unseres Unternehmens oder eines 
    Dritten erforderlich und überwiegen die Interessen, Grundrechte und Grundfreiheiten des Betroffenen 
    das erstgenannte Interesse nicht, so dient Art. 6 Abs. 1 lit. f DSGVO als Rechtsgrundlage für die 
    Verarbeitung.
  </p>
  
  <h3>2.3 Datenlöschung und Speicherdauer</h3>
  <p>
    Die personenbezogenen Daten der betroffenen Person werden gelöscht oder gesperrt, sobald der Zweck 
    der Speicherung entfällt. Eine Speicherung kann darüber hinaus erfolgen, wenn dies durch den 
    europäischen oder nationalen Gesetzgeber in unionsrechtlichen Verordnungen, Gesetzen oder sonstigen 
    Vorschriften vorgesehen wurde. Eine Sperrung oder Löschung der Daten erfolgt auch dann, wenn eine 
    durch die genannten Normen vorgeschriebene Speicherfrist abläuft, es sei denn, dass eine 
    Erforderlichkeit zur weiteren Speicherung der Daten für einen Vertragsabschluss oder eine 
    Vertragserfüllung besteht.
  </p>
  
  <h2>3. Bereitstellung der Website und Erstellung von Logfiles</h2>
  
  <h3>3.1 Beschreibung und Umfang der Datenverarbeitung</h3>
  <p>
    Bei jedem Aufruf unserer Internetseite erfasst unser System automatisiert Daten und Informationen 
    vom Computersystem des aufrufenden Rechners. Folgende Daten werden hierbei erhoben:
  </p>
  <ul>
    <li>IP-Adresse des Nutzers</li>
    <li>Datum und Uhrzeit des Zugriffs</li>
    <li>Aufgerufene Seite / Referrer URL</li>
    <li>Browsertyp und Browserversion</li>
    <li>Verwendetes Betriebssystem</li>
    <li>Hostname des zugreifenden Rechners</li>
  </ul>
  <p>
    Die Daten werden in den Logfiles unseres Systems gespeichert. Eine Speicherung dieser Daten zusammen 
    mit anderen personenbezogenen Daten des Nutzers findet nicht statt.
  </p>
  
  <h3>3.2 Rechtsgrundlage</h3>
  <p>
    Rechtsgrundlage für die vorübergehende Speicherung der Daten und der Logfiles ist Art. 6 Abs. 1 lit. f 
    DSGVO (berechtigtes Interesse).
  </p>
  
  <h3>3.3 Zweck der Datenverarbeitung</h3>
  <p>
    Die vorübergehende Speicherung der IP-Adresse durch das System ist notwendig, um eine Auslieferung 
    der Website an den Rechner des Nutzers zu ermöglichen. Hierfür muss die IP-Adresse des Nutzers für 
    die Dauer der Sitzung gespeichert bleiben. Die Speicherung in Logfiles erfolgt, um die 
    Funktionsfähigkeit der Website sicherzustellen. Zudem dienen uns die Daten zur Optimierung der 
    Website und zur Sicherstellung der Sicherheit unserer informationstechnischen Systeme.
  </p>
  
  <h3>3.4 Dauer der Speicherung</h3>
  <p>
    Die Daten werden gelöscht, sobald sie für die Erreichung des Zweckes ihrer Erhebung nicht mehr 
    erforderlich sind. Im Falle der Erfassung der Daten zur Bereitstellung der Website ist dies der Fall, 
    wenn die jeweilige Sitzung beendet ist. Im Falle der Speicherung der Daten in Logfiles ist dies nach 
    spätestens sieben Tagen der Fall.
  </p>
  
  <h2>4. Verwendung von Cookies und Local Storage</h2>
  
  <h3>4.1 Beschreibung und Umfang der Datenverarbeitung</h3>
  <p>
    Unsere Website verwendet technisch notwendige Cookies und Local Storage. Cookies sind Textdateien, 
    die im Internetbrowser bzw. vom Internetbrowser auf dem Computersystem des Nutzers gespeichert werden. 
    Local Storage funktioniert ähnlich, speichert jedoch Daten im Browser des Nutzers.
  </p>
  <p>
    Wir verwenden:
  </p>
  <ul>
    <li><strong>Session-Cookies:</strong> Zur Verwaltung der Benutzersitzung</li>
    <li><strong>Local Storage:</strong> Zur Speicherung der Dark-Mode-Einstellung</li>
  </ul>
  
  <h3>4.2 Rechtsgrundlage</h3>
  <p>
    Die Rechtsgrundlage für die Verarbeitung personenbezogener Daten unter Verwendung technisch 
    notwendiger Cookies ist Art. 6 Abs. 1 lit. f DSGVO (berechtigtes Interesse an der Funktionsfähigkeit 
    der Website).
  </p>
  
  <h3>4.3 Widerspruchs- und Beseitigungsmöglichkeit</h3>
  <p>
    Cookies und Local Storage können jederzeit über die Einstellungen des Browsers gelöscht werden. 
    Bitte beachten Sie, dass die Website dann möglicherweise nicht mehr vollständig funktioniert.
  </p>
  
  <h2>5. KI-Rechnungsverarbeitung</h2>
  
  <h3>5.1 Beschreibung und Umfang</h3>
  <p>
    Bei Nutzung unserer KI-Rechnungsverarbeitungs-Dienste verarbeiten wir:
  </p>
  <ul>
    <li>Hochgeladene PDF-Dateien und Bilddateien</li>
    <li>Extrahierte Rechnungsdaten (Rechnungsnummer, Beträge, Lieferantendaten, etc.)</li>
    <li>Verarbeitungsprotokolle und Metadaten</li>
    <li>Exportdateien (DATEV, CSV, Excel)</li>
  </ul>
  
  <h3>5.2 Rechtsgrundlage</h3>
  <p>
    Rechtsgrundlage ist Art. 6 Abs. 1 lit. b DSGVO (Vertragserfüllung) in Verbindung mit Art. 28 DSGVO 
    (Auftragsverarbeitung), sofern die Verarbeitung im Auftrag eines Kunden erfolgt.
  </p>
  
  <h3>5.3 Speicherdauer</h3>
  <p>
    Die hochgeladenen Dateien und verarbeiteten Daten werden nach Abschluss der Verarbeitung und 
    erfolgtem Export gelöscht, sofern keine gesetzlichen Aufbewahrungspflichten bestehen oder eine 
    längere Speicherung vertraglich vereinbart wurde.
  </p>
  
  <h3>5.4 Hosting und Serverstandort</h3>
  <p>
    Unsere Dienste werden ausschließlich in Deutschland gehostet. Alle Datenverarbeitungen erfolgen 
    DSGVO-konform innerhalb der EU. Es findet keine Übermittlung in Drittländer statt.
  </p>
  
  <h2>6. Kontaktformular und E-Mail-Kontakt</h2>
  
  <h3>6.1 Beschreibung und Umfang</h3>
  <p>
    Bei Kontaktaufnahme per E-Mail oder über ein Kontaktformular werden die übermittelten Daten 
    (Name, E-Mail-Adresse, Telefonnummer, Nachricht) gespeichert.
  </p>
  
  <h3>6.2 Rechtsgrundlage</h3>
  <p>
    Rechtsgrundlage ist Art. 6 Abs. 1 lit. b DSGVO (Anfragenbearbeitung im Rahmen vorvertraglicher 
    Maßnahmen) bzw. Art. 6 Abs. 1 lit. f DSGVO (berechtigtes Interesse an der Beantwortung von Anfragen).
  </p>
  
  <h3>6.3 Dauer der Speicherung</h3>
  <p>
    Die Daten werden gelöscht, sobald sie für die Erreichung des Zweckes ihrer Erhebung nicht mehr 
    erforderlich sind. Für die personenbezogenen Daten aus der Eingabemaske des Kontaktformulars und 
    diejenigen, die per E-Mail übersandt wurden, ist dies dann der Fall, wenn die jeweilige Konversation 
    mit dem Nutzer beendet ist.
  </p>
  
  <h2>7. SSL/TLS-Verschlüsselung</h2>
  <p>
    Diese Website nutzt aus Sicherheitsgründen und zum Schutz der Übertragung vertraulicher Inhalte, 
    wie zum Beispiel Anfragen, die Sie an uns als Seitenbetreiber senden, eine SSL/TLS-Verschlüsselung. 
    Eine verschlüsselte Verbindung erkennen Sie daran, dass die Adresszeile des Browsers von "http://" 
    auf "https://" wechselt und an dem Schloss-Symbol in Ihrer Browserzeile.
  </p>
  
  <h2>8. Ihre Rechte als betroffene Person</h2>
  <p>
    Werden personenbezogene Daten von Ihnen verarbeitet, sind Sie Betroffener i.S.d. DSGVO und es stehen 
    Ihnen folgende Rechte gegenüber dem Verantwortlichen zu:
  </p>
  
  <h3>8.1 Auskunftsrecht (Art. 15 DSGVO)</h3>
  <p>
    Sie können von uns eine Bestätigung darüber verlangen, ob personenbezogene Daten, die Sie betreffen, 
    von uns verarbeitet werden.
  </p>
  
  <h3>8.2 Recht auf Berichtigung (Art. 16 DSGVO)</h3>
  <p>
    Sie haben ein Recht auf Berichtigung und/oder Vervollständigung gegenüber dem Verantwortlichen, sofern 
    die verarbeiteten personenbezogenen Daten, die Sie betreffen, unrichtig oder unvollständig sind.
  </p>
  
  <h3>8.3 Recht auf Löschung (Art. 17 DSGVO)</h3>
  <p>
    Sie haben das Recht, von uns zu verlangen, dass die Sie betreffenden personenbezogenen Daten 
    unverzüglich gelöscht werden.
  </p>
  
  <h3>8.4 Recht auf Einschränkung der Verarbeitung (Art. 18 DSGVO)</h3>
  <p>
    Sie haben das Recht, von uns die Einschränkung der Verarbeitung zu verlangen.
  </p>
  
  <h3>8.5 Recht auf Datenübertragbarkeit (Art. 20 DSGVO)</h3>
  <p>
    Sie haben das Recht, die Sie betreffenden personenbezogenen Daten, die Sie uns bereitgestellt haben, 
    in einem strukturierten, gängigen und maschinenlesbaren Format zu erhalten.
  </p>
  
  <h3>8.6 Widerspruchsrecht (Art. 21 DSGVO)</h3>
  <p>
    Sie haben das Recht, aus Gründen, die sich aus Ihrer besonderen Situation ergeben, jederzeit gegen 
    die Verarbeitung der Sie betreffenden personenbezogenen Daten, die aufgrund von Art. 6 Abs. 1 lit. f 
    DSGVO erfolgt, Widerspruch einzulegen.
  </p>
  
  <h3>8.7 Recht auf Widerruf der datenschutzrechtlichen Einwilligungserklärung (Art. 7 Abs. 3 DSGVO)</h3>
  <p>
    Sie haben das Recht, Ihre datenschutzrechtliche Einwilligungserklärung jederzeit zu widerrufen. 
    Durch den Widerruf der Einwilligung wird die Rechtmäßigkeit der aufgrund der Einwilligung bis zum 
    Widerruf erfolgten Verarbeitung nicht berührt.
  </p>
  
  <h3>8.8 Recht auf Beschwerde bei einer Aufsichtsbehörde (Art. 77 DSGVO)</h3>
  <p>
    Unbeschadet eines anderweitigen verwaltungsrechtlichen oder gerichtlichen Rechtsbehelfs steht Ihnen 
    das Recht auf Beschwerde bei einer Aufsichtsbehörde zu.
  </p>
  <p>
    <strong>Zuständige Aufsichtsbehörde:</strong><br>
    Der Landesbeauftragte für den Datenschutz und die Informationsfreiheit Baden-Württemberg<br>
    Königstraße 10a<br>
    70173 Stuttgart<br>
    Telefon: 0711/61 55 41-0<br>
    E-Mail: poststelle@lfdi.bwl.de
  </p>
  
  <h2>9. Ausübung Ihrer Rechte</h2>
  <p>
    Zur Ausübung Ihrer Rechte oder bei Fragen zum Datenschutz wenden Sie sich bitte an:
  </p>
  <p>
    <strong>SBS Deutschland GmbH & Co. KG</strong><br>
    z.Hd. Datenschutz<br>
    In der Dell 19<br>
    69469 Weinheim<br>
    E-Mail: <a href="mailto:info@sbsdeutschland.com">info@sbsdeutschland.com</a><br>
    Telefon: +49 6201 80 6109
  </p>
  
  <h2>10. Änderungen der Datenschutzerklärung</h2>
  <p>
    Wir behalten uns vor, diese Datenschutzerklärung anzupassen, damit sie stets den aktuellen rechtlichen 
    Anforderungen entspricht oder um Änderungen unserer Leistungen in der Datenschutzerklärung umzusetzen. 
    Für Ihren erneuten Besuch gilt dann die neue Datenschutzerklärung. Der Stand wird jeweils oben in der 
    Erklärung angegeben.
  </p>
  
  <div class="info-box" style="margin-top: 40px;">
    <p style="margin: 0;">
      <strong>Bei Fragen kontaktieren Sie uns gerne:</strong><br>
      E-Mail: <a href="mailto:info@sbsdeutschland.com">info@sbsdeutschland.com</a><br>
      Telefon: +49 6201 80 6109<br>
      Geschäftszeiten: Mo–Fr, 9:00 – 18:00 Uhr
    </p>
  </div>
</div>

</body>
</html>'''

def save_files():
    """Speichert alle 3 Dateien"""
    base = Path('/var/www/invoice-app/web/sbshomepage')
    
    files = {
        'impressum.html': IMPRESSUM_HTML,
        'agb.html': AGB_HTML,
        'datenschutz.html': DATENSCHUTZ_HTML,
    }
    
    for filename, content in files.items():
        filepath = base / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Erstellt: {filename}")

def main():
    print("=" * 70)
    print("📋 RECHTLICHE SEITEN MIT ECHTEN DATEN")
    print("=" * 70)
    print()
    print("Daten:")
    print("  ✅ Firma: SBS Deutschland GmbH & Co. KG")
    print("  ✅ Adresse: In der Dell 19, 69469 Weinheim")
    print("  ✅ Handelsregister: HRA 706204, Amtsgericht Mannheim")
    print("  ✅ Geschäftsführer: Andreas Schenk")
    print("  ✅ Telefon: +49 6201 80 6109")
    print("  ✅ E-Mail: info@sbsdeutschland.com")
    print("  ✅ Öffnungszeiten: Mo–Fr, 9:00 – 18:00 Uhr")
    print()
    print("=" * 70)
    print()
    
    save_files()
    
    print()
    print("=" * 70)
    print("✅ ALLE SEITEN ERSTELLT!")
    print("=" * 70)
    print()
    print("📄 Erstellt:")
    print("  • /sbshomepage/impressum.html")
    print("  • /sbshomepage/agb.html")
    print("  • /sbshomepage/datenschutz.html")
    print()
    print("🧪 JETZT TESTEN:")
    print("  https://sbsdeutschland.com/sbshomepage/impressum.html")
    print("  https://sbsdeutschland.com/sbshomepage/agb.html")
    print("  https://sbsdeutschland.com/sbshomepage/datenschutz.html")
    print()
    print("💡 HINWEIS:")
    print("  USt-ID wurde als 'Auf Anfrage erhältlich' eingetragen.")
    print("  Falls vorhanden, bitte nachträglich ergänzen!")
    print()

if __name__ == '__main__':
    main()
