"use client";

import { FormEvent, useEffect, useRef, useState } from "react";

const API = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

type IEM = { name: string; slug: string; status: string; has_measurement: boolean; has_preferred: boolean; has_metadata: boolean };
type Target = { name: string; slug: string; kind?: string; status: string; collection: string; has_prepared: boolean; has_source: boolean; has_metadata: boolean };
type V44Curve = { frequency_hz: number[]; level_db: number[] } | null;
type V44Result = { mode: string; base_target: V44Curve; normalized_base_target: V44Curve; per_iem: Record<string, Record<string, V44Curve>>; personal_delta: Record<string, V44Curve>; median_delta: V44Curve; mad: V44Curve; n_plus: number[]; n_minus: number[]; n_zero: number[]; G: V44Curve; C: V44Curve; broad: V44Curve; local: V44Curve; feature_classification: string[] | null; delta_safe: V44Curve; final_target: V44Curve; warnings: string[] };

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
  const [v44Mode, setV44Mode] = useState<"robust_target" | "pure_earprint">("robust_target");
  const [selectedV44, setSelectedV44] = useState<string[]>([]);
  const [v44Result, setV44Result] = useState<V44Result | null>(null);
  const [v44Busy, setV44Busy] = useState(false);
  const [v44Message, setV44Message] = useState("");
  const [visibleStages, setVisibleStages] = useState<Record<string, boolean>>({ base_target: true, normalized_measured_fr: true, desired_response: true, final_target: true });
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

  async function generateV44() {
    if (selectedV44.length === 0) { setV44Message("Select at least one IEM."); return; }
    setV44Busy(true); setV44Message("");
    try {
      const res = await fetch(`${API}/api/v44/generate`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ mode: v44Mode, iem_ids: selectedV44 }) });
      const data = await res.json(); if (!res.ok) throw new Error(data.detail || "V4.4 generation failed.");
      setV44Result(data); setV44Message(data.final_target ? "V4.4 target generated." : "Intermediate curves generated; final target pending locked Delta Safe specification.");
    } catch (err) { setV44Message(err instanceof Error ? err.message : "V4.4 generation failed."); } finally { setV44Busy(false); }
  }

  function toggleStage(stage: string) { setVisibleStages(prev => ({ ...prev, [stage]: !prev[stage] })); }

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
      <section style={{ ...cardStyle, marginTop: 24 }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 16, alignItems: "start", flexWrap: "wrap" }}>
          <div><div style={{ fontSize: 13, letterSpacing: 2, opacity: .65 }}>TARGET MODE</div><h2 style={{ margin: "8px 0" }}>V4.4 Earprint Workspace</h2><p style={{ opacity: .65, marginTop: 0 }}>Base Target: <strong>Headphones.com IEM DF (B105 + 8 dB)</strong></p></div>
          <div style={{ display: "flex", gap: 8 }}><button onClick={() => setV44Mode("robust_target")} aria-pressed={v44Mode === "robust_target"} style={modeButton(v44Mode === "robust_target")}>Robust Target</button><button onClick={() => setV44Mode("pure_earprint")} aria-pressed={v44Mode === "pure_earprint"} style={modeButton(v44Mode === "pure_earprint")}>Pure EarPrint</button></div>
        </div>
        <Field label="Select multiple IEMs from the IEM Library"><select multiple value={selectedV44} onChange={e => setSelectedV44(Array.from(e.target.selectedOptions, option => option.value))} style={{ ...inputStyle, minHeight: 140 }}>{items.map(item => <option key={item.slug} value={item.slug}>{item.name}</option>)}</select></Field>
        <button onClick={generateV44} disabled={v44Busy} style={{ marginTop: 16, padding: 13, borderRadius: 10, border: 0, background: "#d9b36c", color: "#111", fontWeight: 700 }}>{v44Busy ? "Generating…" : "Generate V4.4 Target"}</button>{v44Message && <p style={{ opacity: .8 }}>{v44Message}</p>}
        {v44Result && <ValidationLab result={v44Result} visibleStages={visibleStages} toggleStage={toggleStage} />}
      </section>
    </main>
  );
}

function Library({ title, empty, items }: { title: string; empty: string; items: { key: string; title: string; detail: string }[] }) {
  return <div style={cardStyle}><h2 style={{ marginTop: 0 }}>{title}</h2>{items.length === 0 ? <p style={{ opacity: .55 }}>{empty}</p> : <div style={{ display: "grid", gap: 10 }}>{items.map(item => <div key={item.key} style={{ padding: 14, border: "1px solid #252525", borderRadius: 12, background: "#0b0b0b" }}><div style={{ fontWeight: 700 }}>{item.title}</div><div style={{ fontSize: 12, opacity: .6, marginTop: 5 }}>{item.detail}</div></div>)}</div>}</div>;
}

function modeButton(active: boolean) { return { padding: "10px 14px", borderRadius: 8, border: "1px solid #404040", background: active ? "#d9b36c" : "#181818", color: active ? "#111" : "#fff", fontWeight: 700 }; }

function ValidationLab({ result, visibleStages, toggleStage }: { result: V44Result; visibleStages: Record<string, boolean>; toggleStage: (stage: string) => void }) {
  const stages = ["base_target", "normalized_base_target", "normalized_measured_fr", "reconstructed_peq", "normalized_peq", "desired_response", "personal_delta", "median_delta", "mad", "n_plus", "n_minus", "n_zero", "G", "C", "broad", "local", "feature_classification", "delta_safe", "final_target"];
  const curves = Object.fromEntries(stages.map(stage => [stage, stage === "G" || stage === "C" || stage === "broad" || stage === "local" || stage === "feature_classification" || stage === "delta_safe" || stage === "final_target" ? (result as unknown as Record<string, unknown>)[stage] : (result as unknown as Record<string, unknown>)[stage]]));
  return <div style={{ marginTop: 24, borderTop: "1px solid #2b2b2b", paddingTop: 20 }}><h3>Validation Lab</h3><p style={{ opacity: .7 }}>Measured FR · Desired Response · Final V4.4 Target · Required Correction · Original Preferred Correction</p>{result.final_target === null && <p style={{ color: "#d9b36c" }}>Final Target pending locked Delta Safe specification</p>}<div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>{stages.map(stage => <label key={stage} style={{ fontSize: 12, opacity: curves[stage] === null ? .45 : 1 }}><input type="checkbox" checked={visibleStages[stage] ?? false} disabled={curves[stage] === null} onChange={() => toggleStage(stage)} /> {stage === "feature_classification" ? "Feature Classification" : stage.replaceAll("_", " ")}{curves[stage] === null && " (Not locked)"}</label>)}</div><div style={{ display: "grid", gap: 6, marginTop: 14 }}>{stages.filter(stage => visibleStages[stage] && curves[stage] !== null).map(stage => <div key={stage} style={{ fontSize: 12, opacity: .78 }}><strong>{stage.replaceAll("_", " ")}</strong>: {formatCurve(curves[stage])}</div>)}</div>{Object.entries(result.per_iem).map(([id, iem]) => <div key={id} style={{ marginTop: 18, padding: 14, background: "#0b0b0b", borderRadius: 10 }}><strong>{id}</strong><div style={{ fontSize: 12, opacity: .65, marginTop: 6 }}>Required Correction: {result.final_target ? formatCurve(iem.required_correction) : "Final Target pending locked Delta Safe specification"} · Original Preferred Correction: {formatCurve(iem.original_preferred_correction)}</div><div style={{ marginTop: 8, fontSize: 12, opacity: .75 }}>Visible curves: {Object.keys(iem).filter(key => visibleStages[key]).join(", ") || "none"}</div></div>)}</div>;
}

function formatCurve(value: unknown) { const curve = value as V44Curve; if (!curve || !curve.frequency_hz?.length) return "Not locked"; const last = curve.frequency_hz.length - 1; return `${curve.frequency_hz.length} points · ${curve.level_db[0].toFixed(2)} dB @ ${curve.frequency_hz[0].toFixed(0)} Hz → ${curve.level_db[last].toFixed(2)} dB @ ${curve.frequency_hz[last].toFixed(0)} Hz`; }
