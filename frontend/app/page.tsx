"use client";

import { FormEvent, useEffect, useRef, useState } from "react";

const API = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

type IEM = { name: string; slug: string; status: string; has_measurement: boolean; has_preferred: boolean; has_metadata: boolean };
type Target = { name: string; slug: string; kind?: string; status: string; collection: string; has_prepared: boolean; has_source: boolean; has_metadata: boolean };

const cardStyle = { border: "1px solid #242424", borderRadius: 16, padding: 24, background: "#101010" };
const inputStyle = { width: "100%", padding: 12, background: "#080808", color: "#fff", border: "1px solid #303030", borderRadius: 10 };

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label><div style={{ fontSize: 13, opacity: .7, marginBottom: 6 }}>{label}</div>{children}</label>;
}

export default function Home() {
  const [items, setItems] = useState<IEM[]>([]);
  const [targets, setTargets] = useState<Target[]>([]);
  const [name, setName] = useState("");
  const [measurement, setMeasurement] = useState<File | null>(null);
  const [preferred, setPreferred] = useState<File | null>(null);
  const [notes, setNotes] = useState("");
  const [targetName, setTargetName] = useState("");
  const [targetFile, setTargetFile] = useState<File | null>(null);
  const [targetKind, setTargetKind] = useState("base");
  const [targetNotes, setTargetNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [targetBusy, setTargetBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [targetMessage, setTargetMessage] = useState("");
  const measurementRef = useRef<HTMLInputElement>(null);
  const preferredRef = useRef<HTMLInputElement>(null);
  const targetRef = useRef<HTMLInputElement>(null);

  async function load() {
    const [iemsResponse, targetsResponse] = await Promise.all([
      fetch(`${API}/api/iems`, { cache: "no-store" }),
      fetch(`${API}/api/targets`, { cache: "no-store" }),
    ]);
    if (!iemsResponse.ok || !targetsResponse.ok) throw new Error("Backend API tidak boleh dicapai.");
    const iems = await iemsResponse.json();
    const targetData = await targetsResponse.json();
    setItems(iems.items || []);
    setTargets(targetData.items || []);
  }

  useEffect(() => { load().catch(err => setMessage(err instanceof Error ? err.message : "Backend API tidak boleh dicapai.")); }, []);

  async function submitIEM(e: FormEvent) {
    e.preventDefault(); setMessage("");
    if (!name.trim() || !measurement || !preferred) { setMessage("Nama IEM, measurement dan PEQ diperlukan."); return; }
    const form = new FormData(); form.append("name", name); form.append("measurement_file", measurement); form.append("preferred_file", preferred); form.append("notes", notes);
    setBusy(true);
    try {
      const res = await fetch(`${API}/api/iems/import`, { method: "POST", body: form });
      const data = await res.json(); if (!res.ok) throw new Error(data.detail || "Import IEM gagal.");
      setMessage(`IEM diimport: ${data.item.name}`); setName(""); setMeasurement(null); setPreferred(null); setNotes("");
      if (measurementRef.current) measurementRef.current.value = ""; if (preferredRef.current) preferredRef.current.value = "";
      await load();
    } catch (err) { setMessage(err instanceof Error ? err.message : "Import IEM gagal."); } finally { setBusy(false); }
  }

  async function submitTarget(e: FormEvent) {
    e.preventDefault(); setTargetMessage("");
    if (!targetName.trim() || !targetFile) { setTargetMessage("Nama target dan fail target diperlukan."); return; }
    const form = new FormData(); form.append("name", targetName); form.append("target_file", targetFile); form.append("kind", targetKind); form.append("notes", targetNotes);
    setTargetBusy(true);
    try {
      const res = await fetch(`${API}/api/targets/import`, { method: "POST", body: form });
      const data = await res.json(); if (!res.ok) throw new Error(data.detail || "Import target gagal.");
      setTargetMessage(`Target diimport: ${data.item.name}`); setTargetName(""); setTargetFile(null); setTargetNotes("");
      if (targetRef.current) targetRef.current.value = ""; await load();
    } catch (err) { setTargetMessage(err instanceof Error ? err.message : "Import target gagal."); } finally { setTargetBusy(false); }
  }

  return (
    <main style={{ maxWidth: 1160, margin: "0 auto", padding: "48px 24px" }}>
      <header style={{ marginBottom: 36 }}><div style={{ fontSize: 13, opacity: .55, letterSpacing: 2 }}>ZUHIR</div><h1 style={{ fontSize: 34, margin: "8px 0" }}>Personal Earprint Engine</h1><p style={{ opacity: .7 }}>IEM Library • Target Library • V4.4 Backbone</p></header>
      <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 24 }}>
        <div style={cardStyle}>
          <h2 style={{ marginTop: 0 }}>Add IEM</h2><p style={{ opacity: .65, fontSize: 14 }}>Upload measurement FR + SoundEQ Dore PEQ. Metadata dan fail prepared dijana automatik.</p>
          <form onSubmit={submitIEM} style={{ display: "grid", gap: 16 }}>
            <Field label="IEM Name"><input value={name} onChange={e => setName(e.target.value)} placeholder="e.g. 7Hz Timeless" style={inputStyle} /></Field>
            <Field label="Measurement FR"><input ref={measurementRef} type="file" accept=".txt,.csv" onChange={e => setMeasurement(e.target.files?.[0] || null)} /></Field>
            <Field label="SoundEQ Dore PEQ"><input ref={preferredRef} type="file" accept=".txt,.csv" onChange={e => setPreferred(e.target.files?.[0] || null)} /></Field>
            <Field label="Notes (optional)"><textarea value={notes} onChange={e => setNotes(e.target.value)} rows={3} style={inputStyle} /></Field>
            <button disabled={busy} type="submit" style={{ padding: 13, borderRadius: 10, border: 0, background: "#fff", color: "#000", fontWeight: 700 }}>{busy ? "Importing…" : "Import IEM"}</button>{message && <div style={{ fontSize: 13, opacity: .8 }}>{message}</div>}
          </form>
        </div>
        <div style={cardStyle}>
          <h2 style={{ marginTop: 0 }}>Add Target</h2><p style={{ opacity: .65, fontSize: 14 }}>Upload Base Target asal. Fail asal dikekalkan dan salinan prepared mempunyai titik tepat 1000 Hz.</p>
          <form onSubmit={submitTarget} style={{ display: "grid", gap: 16 }}>
            <Field label="Target Name"><input value={targetName} onChange={e => setTargetName(e.target.value)} placeholder="e.g. Headphones.com IEM DF" style={inputStyle} /></Field>
            <Field label="Target Type"><select value={targetKind} onChange={e => setTargetKind(e.target.value)} style={inputStyle}><option value="base">Base Target</option><option value="custom">Custom Target</option></select></Field>
            <Field label="Target FR"><input ref={targetRef} type="file" accept=".txt,.csv" onChange={e => setTargetFile(e.target.files?.[0] || null)} /></Field>
            <Field label="Notes (optional)"><textarea value={targetNotes} onChange={e => setTargetNotes(e.target.value)} rows={3} style={inputStyle} /></Field>
            <button disabled={targetBusy} type="submit" style={{ padding: 13, borderRadius: 10, border: 0, background: "#fff", color: "#000", fontWeight: 700 }}>{targetBusy ? "Importing…" : "Import Target"}</button>{targetMessage && <div style={{ fontSize: 13, opacity: .8 }}>{targetMessage}</div>}
          </form>
        </div>
      </section>
      <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 24, marginTop: 24 }}>
        <Library title="IEM Library" empty="No IEMs imported yet." items={items.map(item => ({ key: item.slug, title: item.name, detail: `${item.status} · FR ${item.has_measurement ? "✓" : "—"} · PEQ ${item.has_preferred ? "✓" : "—"} · metadata ${item.has_metadata ? "✓" : "—"}` }))} />
        <Library title="Target Library" empty="No targets imported yet." items={targets.map(item => ({ key: `${item.collection}/${item.slug}`, title: item.name, detail: `${item.kind === "base" ? "Base Target" : "Custom Target"} · ${item.status} · prepared ${item.has_prepared ? "✓" : "—"} · original ${item.has_source ? "✓" : "—"}` }))} />
      </section>
    </main>
  );
}

function Library({ title, empty, items }: { title: string; empty: string; items: { key: string; title: string; detail: string }[] }) {
  return <div style={cardStyle}><h2 style={{ marginTop: 0 }}>{title}</h2>{items.length === 0 ? <p style={{ opacity: .55 }}>{empty}</p> : <div style={{ display: "grid", gap: 10 }}>{items.map(item => <div key={item.key} style={{ padding: 14, border: "1px solid #252525", borderRadius: 12, background: "#0b0b0b" }}><div style={{ fontWeight: 700 }}>{item.title}</div><div style={{ fontSize: 12, opacity: .6, marginTop: 5 }}>{item.detail}</div></div>)}</div>}</div>;
}
