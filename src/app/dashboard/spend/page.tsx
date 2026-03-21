"use client";
import { useState, useEffect } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, CartesianGrid } from "recharts";
import { useAuth } from "@/lib/useAuth";

const API = "https://app.sbsdeutschland.com/api/erechnung";

export default function SpendAnalyticsPage() {
  const { user, token } = useAuth();
  const [invoices, setInvoices] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    fetch(API+"/invoices",{headers:{Authorization:"Bearer "+token,"X-Tenant-ID":user?.tenant_id||""}})
      .then(r=>r.json()).then(d=>{ setInvoices(Array.isArray(d)?d:d.items||[]); setLoading(false); }).catch(()=>setLoading(false));
  },[token,user]);

  if (!user) return null;

  // Aggregate by supplier
  const bySupplier: Record<string,{count:number,total:number}> = {};
  let totalSpend = 0;
  invoices.forEach(inv => {
    const s = inv.supplier || "Unbekannt";
    if (!bySupplier[s]) bySupplier[s] = {count:0,total:0};
    bySupplier[s].count++;
    const amt = inv.total_amount || 0;
    bySupplier[s].total += amt;
    totalSpend += amt;
  });

  const supplierData = Object.entries(bySupplier)
    .map(([name,d])=>({name:name.length>20?name.slice(0,20)+"…":name,fullName:name,...d}))
    .sort((a,b)=>b.total-a.total);

  const colors = ["#e85d04","#8b5cf6","#10b981","#f59e0b","#ef4444","#06b6d4","#ec4899","#6366f1"];

  // Monthly aggregation
  const byMonth: Record<string,number> = {};
  invoices.forEach(inv => {
    const d = inv.created_at || inv.uploaded_at;
    if (d) { const m = d.slice(0,7); byMonth[m] = (byMonth[m]||0) + (inv.total_amount||0); }
  });
  const monthlyData = Object.entries(byMonth).sort().map(([m,v])=>({month:m.slice(5)+"/"+m.slice(2,4),amount:Math.round(v*100)/100}));

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-white">
      <div className="border-b border-white/[0.06] bg-[#0a0a0a]/80 backdrop-blur-xl sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center gap-3">
          <a href="/dashboard" className="text-[#737373] hover:text-white transition">← Dashboard</a>
          <div className="h-6 w-px bg-[#262626]"/>
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center text-lg">💰</div>
            <div><h1 className="text-lg font-semibold">Spend Analytics</h1><p className="text-xs text-[#737373]">Ausgabenanalyse</p></div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        {loading ? (
          <div className="flex justify-center py-20"><div className="flex gap-1.5">
            <div className="w-3 h-3 bg-[#e85d04] rounded-full animate-bounce" style={{animationDelay:"0ms"}}/><div className="w-3 h-3 bg-[#e85d04] rounded-full animate-bounce" style={{animationDelay:"150ms"}}/><div className="w-3 h-3 bg-[#e85d04] rounded-full animate-bounce" style={{animationDelay:"300ms"}}/>
          </div></div>
        ) : (
          <>
            {/* KPIs */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                {l:"Gesamtausgaben",v:totalSpend.toLocaleString("de-DE",{style:"currency",currency:"EUR"}),i:"💰"},
                {l:"Rechnungen",v:invoices.length,i:"📄"},
                {l:"Lieferanten",v:Object.keys(bySupplier).length,i:"🏢"},
                {l:"Ø pro Rechnung",v:invoices.length?(totalSpend/invoices.length).toLocaleString("de-DE",{style:"currency",currency:"EUR"}):"—",i:"📊"},
              ].map((k,i)=>(
                <div key={i} className="bg-[#171717]/50 border border-[#262626] rounded-xl p-4">
                  <span className="text-lg">{k.i}</span>
                  <div className="text-xl font-bold mt-1">{k.v}</div>
                  <div className="text-xs text-[#737373] mt-1">{k.l}</div>
                </div>
              ))}
            </div>

            {/* Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="bg-[#171717]/50 border border-[#262626] rounded-xl p-6">
                <h3 className="text-sm font-semibold text-[#d4d4d4] mb-4">Ausgaben nach Lieferant</h3>
                {supplierData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={supplierData.slice(0,8)} layout="vertical" margin={{left:10}}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#262626" horizontal={false}/>
                      <XAxis type="number" stroke="#525252" tick={{fontSize:11}} tickFormatter={v=>v.toLocaleString("de-DE")}/>
                      <YAxis type="category" dataKey="name" stroke="#525252" tick={{fontSize:11}} width={120}/>
                      <Tooltip contentStyle={{background:"#171717",border:"1px solid #262626",borderRadius:8,fontSize:12}} formatter={(v:number)=>v.toLocaleString("de-DE",{style:"currency",currency:"EUR"})}/>
                      <Bar dataKey="total" fill="#e85d04" radius={[0,4,4,0]} barSize={20}/>
                    </BarChart>
                  </ResponsiveContainer>
                ) : <div className="h-[300px] flex items-center justify-center text-[#525252] text-sm">Keine Daten</div>}
              </div>

              <div className="bg-[#171717]/50 border border-[#262626] rounded-xl p-6">
                <h3 className="text-sm font-semibold text-[#d4d4d4] mb-4">Verteilung nach Lieferant</h3>
                {supplierData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart><Pie data={supplierData.slice(0,6)} dataKey="total" nameKey="name" cx="50%" cy="50%" innerRadius={50} outerRadius={100} paddingAngle={2}
                      label={({name,total}:any)=>name+" ("+Math.round(total)+"€)"}>
                      {supplierData.slice(0,6).map((_,i)=><Cell key={i} fill={colors[i%colors.length]}/>)}
                    </Pie><Tooltip contentStyle={{background:"#171717",border:"1px solid #262626",borderRadius:8,fontSize:12}}/></PieChart>
                  </ResponsiveContainer>
                ) : <div className="h-[300px] flex items-center justify-center text-[#525252] text-sm">Keine Daten</div>}
              </div>
            </div>

            {/* Monthly Trend */}
            {monthlyData.length > 0 && (
              <div className="bg-[#171717]/50 border border-[#262626] rounded-xl p-6">
                <h3 className="text-sm font-semibold text-[#d4d4d4] mb-4">Monatlicher Trend</h3>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={monthlyData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#262626"/>
                    <XAxis dataKey="month" stroke="#525252" tick={{fontSize:11}}/>
                    <YAxis stroke="#525252" tick={{fontSize:11}} tickFormatter={v=>v+"€"}/>
                    <Tooltip contentStyle={{background:"#171717",border:"1px solid #262626",borderRadius:8}} formatter={(v:number)=>v.toLocaleString("de-DE",{style:"currency",currency:"EUR"})}/>
                    <Bar dataKey="amount" fill="#8b5cf6" radius={[4,4,0,0]}/>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Supplier Table */}
            <div className="bg-[#171717]/50 border border-[#262626] rounded-xl p-6">
              <h3 className="text-sm font-semibold text-[#d4d4d4] mb-4">Alle Lieferanten ({supplierData.length})</h3>
              <div className="space-y-2">
                <div className="hidden sm:grid grid-cols-12 gap-4 px-3 py-2 text-xs text-[#525252] uppercase tracking-wider">
                  <div className="col-span-5">Lieferant</div><div className="col-span-2 text-right">Rechnungen</div><div className="col-span-3 text-right">Gesamt</div><div className="col-span-2 text-right">Anteil</div>
                </div>
                {supplierData.map((s,i)=>(
                  <div key={i} className="grid grid-cols-12 gap-4 px-3 py-2 rounded-lg hover:bg-[#262626]/30 items-center">
                    <div className="col-span-5 flex items-center gap-2"><div className="w-2 h-2 rounded-full" style={{background:colors[i%colors.length]}}/><span className="text-sm truncate">{s.fullName}</span></div>
                    <div className="col-span-2 text-right text-sm text-[#a3a3a3]">{s.count}</div>
                    <div className="col-span-3 text-right text-sm font-medium">{s.total.toLocaleString("de-DE",{style:"currency",currency:"EUR"})}</div>
                    <div className="col-span-2 text-right text-xs text-[#737373]">{totalSpend>0?Math.round(s.total/totalSpend*100):0}%</div>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
