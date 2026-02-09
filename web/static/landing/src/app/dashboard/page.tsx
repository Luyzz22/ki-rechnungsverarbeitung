"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

// Stats Card Component
function StatCard({ 
  title, 
  value, 
  icon, 
  trend, 
  color 
}: { 
  title: string; 
  value: string | number; 
  icon: string; 
  trend?: string;
  color: string;
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 hover:shadow-lg transition-shadow">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-500">{title}</p>
          <p className={`text-3xl font-bold mt-1 ${color}`}>{value}</p>
          {trend && (
            <p className="text-sm text-green-600 mt-1 flex items-center gap-1">
              <span>↑</span> {trend}
            </p>
          )}
        </div>
        <div className="text-4xl">{icon}</div>
      </div>
    </div>
  );
}

// Product Card Component
function ProductCard({
  name,
  description,
  icon,
  usage,
  limit,
  color,
  href,
  status
}: {
  name: string;
  description: string;
  icon: string;
  usage: number;
  limit: number;
  color: string;
  href: string;
  status: "active" | "inactive";
}) {
  const percentage = Math.round((usage / limit) * 100);
  const barColor = percentage > 80 ? "bg-red-500" : percentage > 60 ? "bg-yellow-500" : color;
  
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 hover:shadow-lg transition-all hover:border-blue-300">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <span className="text-3xl">{icon}</span>
          <div>
            <h3 className="font-semibold text-gray-900">{name}</h3>
            <p className="text-sm text-gray-500">{description}</p>
          </div>
        </div>
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
          status === "active" ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-600"
        }`}>
          {status === "active" ? "Aktiv" : "Inaktiv"}
        </span>
      </div>
      
      <div className="mb-4">
        <div className="flex justify-between text-sm mb-1">
          <span className="text-gray-600">Nutzung</span>
          <span className="font-medium">{usage} / {limit}</span>
        </div>
        <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
          <div 
            className={`h-full ${barColor} rounded-full transition-all`}
            style={{ width: `${Math.min(percentage, 100)}%` }}
          />
        </div>
      </div>
      
      <Link 
        href={href}
        className={`block w-full text-center py-2 px-4 rounded-lg font-medium transition-colors ${color} text-white hover:opacity-90`}
      >
        Öffnen →
      </Link>
    </div>
  );
}

// Activity Item Component
function ActivityItem({
  icon,
  title,
  description,
  time,
  type
}: {
  icon: string;
  title: string;
  description: string;
  time: string;
  type: "invoice" | "contract" | "hydraulik" | "system";
}) {
  const colors = {
    invoice: "bg-cyan-100 text-cyan-700",
    contract: "bg-purple-100 text-purple-700",
    hydraulik: "bg-orange-100 text-orange-700",
    system: "bg-gray-100 text-gray-700"
  };
  
  return (
    <div className="flex items-start gap-4 py-3 border-b border-gray-100 last:border-0">
      <div className={`p-2 rounded-lg ${colors[type]}`}>
        <span className="text-lg">{icon}</span>
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-medium text-gray-900 truncate">{title}</p>
        <p className="text-sm text-gray-500 truncate">{description}</p>
      </div>
      <span className="text-xs text-gray-400 whitespace-nowrap">{time}</span>
    </div>
  );
}

export default function DashboardPage() {
  const [stats, setStats] = useState({
    invoicesTotal: 127,
    contractsTotal: 45,
    videoDiagnoses: 12,
    successRate: 98.5
  });
  
  const [activities, setActivities] = useState([
    {
      icon: "📄",
      title: "Rechnung #2024-087 verarbeitet",
      description: "Bosch Rexroth AG · €4.250,00",
      time: "vor 2 Min",
      type: "invoice" as const
    },
    {
      icon: "📝",
      title: "Vertrag analysiert",
      description: "NDA mit Siemens AG",
      time: "vor 15 Min",
      type: "contract" as const
    },
    {
      icon: "🎬",
      title: "Video-Diagnose abgeschlossen",
      description: "Hydraulikpumpe HYD-4500 · Kavitation erkannt",
      time: "vor 1 Std",
      type: "hydraulik" as const
    },
    {
      icon: "✅",
      title: "System-Update",
      description: "Gemini 2.5 Pro erfolgreich integriert",
      time: "vor 3 Std",
      type: "system" as const
    },
    {
      icon: "📄",
      title: "Rechnung #2024-086 verarbeitet",
      description: "Festo SE & Co. KG · €1.890,00",
      time: "vor 4 Std",
      type: "invoice" as const
    }
  ]);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-gradient-to-r from-slate-900 to-slate-800 text-white">
        <div className="max-w-7xl mx-auto px-6 py-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold">Willkommen zurück, Luis! 👋</h1>
              <p className="text-slate-300 mt-1">
                Ihre SBS Produkte und Aktivitäten auf einen Blick.
              </p>
            </div>
            <div className="flex items-center gap-4">
              <span className="bg-green-500/20 text-green-300 px-3 py-1 rounded-full text-sm font-medium">
                ● Alle Systeme online
              </span>
              <div className="w-10 h-10 bg-blue-600 rounded-full flex items-center justify-center font-bold">
                LS
              </div>
            </div>
          </div>
        </div>
      </header>
      
      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <StatCard
            title="Rechnungen verarbeitet"
            value={stats.invoicesTotal}
            icon="📄"
            trend="12% diesen Monat"
            color="text-cyan-600"
          />
          <StatCard
            title="Verträge analysiert"
            value={stats.contractsTotal}
            icon="📝"
            trend="8% diesen Monat"
            color="text-purple-600"
          />
          <StatCard
            title="Video-Diagnosen"
            value={stats.videoDiagnoses}
            icon="🎬"
            trend="Neu!"
            color="text-orange-600"
          />
          <StatCard
            title="Erfolgsrate"
            value={`${stats.successRate}%`}
            icon="✅"
            color="text-green-600"
          />
        </div>
        
        {/* Products + Activity Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Products */}
          <div className="lg:col-span-2">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <span>🚀</span> Ihre Produkte
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <ProductCard
                name="KI-Rechnungsverarbeitung"
                description="Automatische Extraktion & DATEV-Export"
                icon="📄"
                usage={127}
                limit={200}
                color="bg-cyan-600"
                href="https://app.sbsdeutschland.com"
                status="active"
              />
              <ProductCard
                name="Vertragsanalyse"
                description="KI-gestützte Vertragsanalyse"
                icon="📝"
                usage={45}
                limit={100}
                color="bg-purple-600"
                href="https://contract.sbsdeutschland.com"
                status="active"
              />
              <ProductCard
                name="HydraulikDoc AI"
                description="Technische Dokumentation + Video"
                icon="🔧"
                usage={12}
                limit={50}
                color="bg-orange-600"
                href="https://knowledge-sbsdeutschland.streamlit.app"
                status="active"
              />
              <ProductCard
                name="Workflow Automation"
                description="n8n Enterprise Workflows"
                icon="⚡"
                usage={89}
                limit={500}
                color="bg-slate-600"
                href="https://automation.sbsdeutschland.com"
                status="active"
              />
            </div>
          </div>
          
          {/* Activity Feed */}
          <div>
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <span>📊</span> Letzte Aktivitäten
            </h2>
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              {activities.map((activity, index) => (
                <ActivityItem key={index} {...activity} />
              ))}
              <button className="w-full mt-4 py-2 text-sm text-blue-600 hover:text-blue-700 font-medium">
                Alle Aktivitäten anzeigen →
              </button>
            </div>
          </div>
        </div>
        
        {/* Quick Actions */}
        <div className="mt-8 bg-gradient-to-r from-blue-600 to-purple-600 rounded-xl p-6 text-white">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold">🆕 Neu: Video-Diagnose für Hydraulik</h3>
              <p className="text-blue-100 mt-1">
                Analysieren Sie Maschinengeräusche mit KI. Powered by Google Gemini 2.5 Pro.
              </p>
            </div>
            <Link
              href="https://knowledge-sbsdeutschland.streamlit.app"
              className="bg-white text-blue-600 px-6 py-3 rounded-lg font-semibold hover:bg-blue-50 transition-colors whitespace-nowrap"
            >
              Jetzt testen →
            </Link>
          </div>
        </div>
        
        {/* API Status */}
        <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="font-semibold text-gray-900 mb-4">🔌 API Status</h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-gray-600">Invoice API</span>
                <span className="flex items-center gap-2 text-green-600">
                  <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                  Online
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-600">Contract API</span>
                <span className="flex items-center gap-2 text-green-600">
                  <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                  Online
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-600">Vertex AI</span>
                <span className="flex items-center gap-2 text-green-600">
                  <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                  Online
                </span>
              </div>
            </div>
          </div>
          
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="font-semibold text-gray-900 mb-4">📈 Diesen Monat</h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-gray-600">API Calls</span>
                <span className="font-semibold">2.847</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-600">Dokumente</span>
                <span className="font-semibold">184</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-600">Zeitersparnis</span>
                <span className="font-semibold text-green-600">~47 Std</span>
              </div>
            </div>
          </div>
          
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="font-semibold text-gray-900 mb-4">💡 Hilfe & Support</h3>
            <div className="space-y-2">
              <a href="https://sbsdeutschland.com/ressourcen" className="block text-blue-600 hover:text-blue-700">
                📚 Dokumentation
              </a>
              <a href="mailto:support@sbsdeutschland.com" className="block text-blue-600 hover:text-blue-700">
                📧 Support kontaktieren
              </a>
              <a href="https://sbsdeutschland.com/security" className="block text-blue-600 hover:text-blue-700">
                🔒 Sicherheit & DSGVO
              </a>
            </div>
          </div>
        </div>
      </main>
      
      {/* Footer */}
      <footer className="border-t border-gray-200 mt-12 py-6">
        <div className="max-w-7xl mx-auto px-6 flex items-center justify-between text-sm text-gray-500">
          <p>© 2026 SBS Deutschland GmbH · Weinheim</p>
          <div className="flex items-center gap-4">
            <Link href="/datenschutz" className="hover:text-gray-700">Datenschutz</Link>
            <Link href="/impressum" className="hover:text-gray-700">Impressum</Link>
            <Link href="/security" className="hover:text-gray-700">Security</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
