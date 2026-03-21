"use client";
import { useState, useEffect } from "react";
import { useAuth } from "@/lib/useAuth";

const API = "https://app.sbsdeutschland.com/api/erechnung";

const ROLES: Record<string,{label:string,color:string,limit:string}> = {
  viewer: {label:"Viewer",color:"bg-gray-500/20 text-gray-400",limit:"Keine Freigabe"},
  editor: {label:"Editor",color:"bg-blue-500/20 text-blue-400",limit:"Bis €500"},
  admin: {label:"Admin",color:"bg-[#e85d04]/20 text-[#f48c06]",limit:"Unbegrenzt"},
};

const RULES = [
  {range:"€0 — €100",auto:true,role:"editor",desc:"Automatische Freigabe für Kleinstbeträge"},
  {range:"€100 — €500",auto:false,role:"editor",desc:"Editor kann freigeben"},
  {range:"€500 — €5.000",auto:false,role:"admin",desc:"Admin-Freigabe erforderlich"},
  {range:"Über €5.000",auto:false,role:"admin",desc:"Admin + Vier-Augen-Prinzip empfohlen"},
];

export default function FreigabenPage() {
  const { user, token } = useAuth();
  const [invoices, setInvoices] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    fetch(API+"/invoices",{headers:{Authorization:"Bearer "+token,"X-Tenant-ID":user?.tenant_id||""}})
      .then(r=>r.json()).then(d=>{
        const all = Array.isArray(d)?d:d.items||[];
        setInvoices(all.filter((inv:any)=>["suggested","validated","classified"].includes(inv.current_state||inv.status)));
        setLoading(false);
      }).catch(()=>setLoading(false));
  },[token,user]);

  const approve = async (docId:string) => {
    const r = await fetch(API+"/invoices/"+docId+"/transition",{
      method:"POST",headers:{"Content-Type":"application/json",Authorization:"Bearer "+token,"X-Tenant-ID":user?.tenant_id||""},
      body:JSON.stringify({to_state:"approved",actor:user?.name||"User"}),
    });
    if(r.ok) setInvoices(invoices.filter(i=>i.document_id!==docId));
  };

  const reject = async (docId:string) => {
    const r = await fetch(API+"/invoices/"+docId+"/transition",{
      method:"POST",headers:{"Content-Type":"application/json",Authorization:"Bearer "+token,"X-Tenant-ID":user?.tenant_id||""},
      body:JSON.stringify({to_state:"rejected",actor:user?.name||"User"}),
    });
    if(r.ok) setInvoices(invoices.filter(i=>i.document_id!==docId));
  };

  if (!user) return null;

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-white">
      <div className="border-b border-white/[0.06] bg-[#0a0a0a]/80 backdrop-blur-xl sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center gap-3">
          <a href="/dashboard" className="text-[#737373] hover:text-white transition">← Dashboard</a>
          <div className="h-6 w-px bg-[#262626]"/>
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-teal-500 to-emerald-600 flex items-center justify-center text-lg">✅</div>
            <div><h1 className="text-lg font-semibold">Freigaben</h1><p className="text-xs text-[#737373]">{invoices.length} ausstehend</p></div>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-8 space-y-8">
        {/* Pending Approvals */}
        <div>
          <h2 className="text-sm font-semibold text-[#737373] uppercase tracking-wider mb-4">Ausstehende Freigaben</h2>
          {loading ? (
            <div className="flex justify-center py-12"><div className="flex gap-1.5">
              <div className="w-3 h-3 bg-[#e85d04] rounded-full animate-bounce"/><div className="w-3 h-3 bg-[#e85d04] rounded-full animate-bounce" style={{animationDelay:"150ms"}}/><div className="w-3 h-3 bg-[#e85d04] rounded-full animate-bounce" style={{animationDelay:"300ms"}}/>
            </div></div>
          ) : invoices.length === 0 ? (
            <div className="bg-[#171717]/50 border border-[#262626] rounded-xl p-8 text-center">
              <div className="text-4xl mb-3">✅</div>
              <p className="text-[#737373]">Keine ausstehenden Freigaben</p>
            </div>
          ) : (
            <div className="space-y-2">
              {invoices.map((inv,i)=>(
                <div key={i} className="bg-[#171717]/50 border border-[#262626] rounded-xl px-5 py-4 flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <a href={`/dashboard/rechnungen/${inv.document_id}`} className="text-sm font-medium text-white hover:text-[#e85d04] truncate block">{inv.supplier || inv.file_name || inv.document_id}</a>
                    <div className="flex items-center gap-3 mt-1">
                      <span className="text-xs text-[#525252]">{inv.file_name}</span>
                      {inv.total_amount && <span className="text-sm font-semibold text-white">{Number(inv.total_amount).toLocaleString("de-DE",{style:"currency",currency:inv.currency||"EUR"})}</span>}
                      <span className={"text-xs px-2 py-0.5 rounded-full bg-violet-500/20 text-violet-400"}>{inv.current_state||inv.status}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 ml-4">
                    <button onClick={()=>approve(inv.document_id)} className="px-4 py-2 bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 rounded-lg text-sm hover:bg-emerald-500/20 transition">Freigeben</button>
                    <button onClick={()=>reject(inv.document_id)} className="px-4 py-2 bg-red-500/10 text-red-400 border border-red-500/30 rounded-lg text-sm hover:bg-red-500/20 transition">Ablehnen</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Approval Rules */}
        <div>
          <h2 className="text-sm font-semibold text-[#737373] uppercase tracking-wider mb-4">Freigabe-Regeln</h2>
          <div className="space-y-2">
            {RULES.map((r,i)=>(
              <div key={i} className={"bg-[#171717]/50 border rounded-xl px-5 py-4 "+(r.auto?"border-emerald-500/20":"border-[#262626]")}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <span className="text-sm font-mono font-medium text-[#d4d4d4] w-32">{r.range}</span>
                    <span className={"text-xs px-2.5 py-1 rounded-full "+ROLES[r.role].color}>{ROLES[r.role].label}</span>
                    {r.auto && <span className="text-xs px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400">Auto</span>}
                  </div>
                  <span className="text-xs text-[#525252]">{r.desc}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Team Roles */}
        <div>
          <h2 className="text-sm font-semibold text-[#737373] uppercase tracking-wider mb-4">Rollen & Berechtigungen</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {Object.entries(ROLES).map(([key,r])=>(
              <div key={key} className="bg-[#171717]/50 border border-[#262626] rounded-xl p-5">
                <span className={"text-xs px-2.5 py-1 rounded-full "+r.color}>{r.label}</span>
                <p className="text-sm text-[#d4d4d4] mt-3">{r.limit}</p>
                <p className="text-xs text-[#525252] mt-1">{key==="viewer"?"Nur Ansicht":key==="editor"?"Bearbeiten + Freigabe (begrenzt)":"Volle Kontrolle"}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
