"use client";

import { FormEvent, useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type IEM = {
  name: string;
  slug: string;
  status: string;
  has_measurement: boolean;
  has_preferred: boolean;
  has_metadata: boolean;
};

export default function Home() {
  const [items, setItems] = useState<IEM[]>([]);
  const [name, setName] = useState("");
  const [measurement, setMeasurement] = useState<File | null>(null);
  const [preferred, setPreferred] = useState<File | null>(null);
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function load() {
    const res = await fetch(`${API}/api/iems`, { cache: "no-store" });
    const data = await res.json();
    setItems(data.items || []);
  }

  useEffect(() => { load(); }, []);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setMessage("");

    if (!name || !measurement || !preferred) {
      setMessage("Nama IEM, measurement dan PEQ diperlukan.");
      return;
    }

    const form = new FormData();
    form.append("name", name);
    form.append("measurement_file", measurement);
    form.append("preferred_file", preferred);
    form.append("notes", notes);

    setBusy(true);
    try {
      const res = await fetch(`${API}/api/iems/import`, { method: "POST", body: form });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Import failed");
      setMessage(`Imported: ${data.item.name}`);
      setName("");
      setMeasurement(null);
      setPreferred(null);
      setNotes("");
      (document.getElementById("measurement") as HTMLInputElement | null)?.value = "";
      (document.getElementById("preferred") as HTMLInputElement | null)?.value = "";
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Import failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main style={{maxWidth: 1100, margin: "0 auto", padding: "48px 24px"}}>
      <header style={{marginBottom: 36}}>
        <div style={{fontSize: 13, opacity: .55, letterSpacing: 2}}>ZUHIR</div>
        <h1 style={{fontSize: 34, margin: "8px 0"}}>Personal Earprint Engine</h1>
        <p style={{opacity: .7}}>IEM Library • V4.4 Backbone</p>
      </header>

      <section style={{display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24}}>
        <div style={{border: "1px solid #242424", borderRadius: 16, padding: 24, background: "#101010"}}>
          <h2 style={{marginTop: 0}}>Add IEM</h2>
          <p style={{opacity: .65, fontSize: 14}}>
            Upload measurement FR + SoundEQ Dore PEQ. Metadata and prepared files are generated automatically.
          </p>

          <form onSubmit={submit} style={{display: "grid", gap: 16}}>
            <label>
              <div style={{fontSize: 13, opacity: .7, marginBottom: 6}}>IEM Name</div>
              <input value={name} onChange={e => setName(e.target.value)}
                placeholder="e.g. 7Hz Timeless"
                style={{width: "100%", padding: 12, background: "#080808", color: "#fff", border: "1px solid #303030", borderRadius: 10}} />
            </label>

            <label>
              <div style={{fontSize: 13, opacity: .7, marginBottom: 6}}>Measurement FR</div>
              <input id="measurement" type="file" accept=".txt,.csv"
                onChange={e => setMeasurement(e.target.files?.[0] || null)} />
            </label>

            <label>
              <div style={{fontSize: 13, opacity: .7, marginBottom: 6}}>SoundEQ Dore PEQ</div>
              <input id="preferred" type="file" accept=".txt,.csv"
                onChange={e => setPreferred(e.target.files?.[0] || null)} />
            </label>

            <label>
              <div style={{fontSize: 13, opacity: .7, marginBottom: 6}}>Notes (optional)</div>
              <textarea value={notes} onChange={e => setNotes(e.target.value)}
                rows={3}
                style={{width: "100%", padding: 12, background: "#080808", color: "#fff", border: "1px solid #303030", borderRadius: 10}} />
            </label>

            <button disabled={busy} type="submit"
              style={{padding: 13, borderRadius: 10, border: 0, background: "#fff", color: "#000", fontWeight: 700, cursor: "pointer"}}>
              {busy ? "Importing…" : "Import IEM"}
            </button>

            {message && <div style={{fontSize: 13, opacity: .8}}>{message}</div>}
          </form>
        </div>

        <div style={{border: "1px solid #242424", borderRadius: 16, padding: 24, background: "#101010"}}>
          <h2 style={{marginTop: 0}}>IEM Library</h2>
          {items.length === 0 ? (
            <p style={{opacity: .55}}>No IEMs imported yet.</p>
          ) : (
            <div style={{display: "grid", gap: 10}}>
              {items.map(item => (
                <div key={item.slug} style={{padding: 14, border: "1px solid #252525", borderRadius: 12, background: "#0b0b0b"}}>
                  <div style={{fontWeight: 700}}>{item.name}</div>
                  <div style={{fontSize: 12, opacity: .6, marginTop: 5}}>
                    {item.status} · FR ✓ · PEQ ✓ · metadata ✓
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>
    </main>
  );
}
