import { useEffect, useState, type FormEvent } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

type Settings = { display_name: string; theme: 'system' | 'light' | 'dark'; timezone: string; ai_mode: 'off'; revision: number };
type Status = { schema_version: number; profile: string; can_restore: boolean; ocr_engine?: string };
type View = 'home' | 'library' | 'settings' | 'backup';
type JobError = { path: string; code: string; message: string };
type ImportJob = { id: string; state: string; phase: string; progress_done: number; progress_total: number; can_resume: boolean; error_message?: string | null; report?: { errors: JobError[]; warnings: { path: string; message: string }[]; duplicates: { sha256: string; paths: string[] }[]; versions_created: number; versions_reused: number; original_hashes_unchanged: boolean; excluded: { path: string; reason: string }[] } | null };
type Material = { id: string; locator: string; kind: string; extraction_state: string; duplicate_locators: string[] };
const token = new URLSearchParams(location.hash.slice(1)).get('token');
if (location.hash) history.replaceState(null, '', location.pathname);
const sessionReady = token ? fetch('/api/session', { method: 'POST', headers: { Authorization: `Bearer ${token}` } }).then(async r => {
  if (!r.ok) throw new Error((await r.json()).message);
}) : Promise.resolve();

async function api(path: string, init?: RequestInit) {
  await sessionReady;
  const response = await fetch(`/api/${path}`, init);
  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Servizio non disponibile. Riapri DeepStudy.' }));
    throw new Error(error.message);
  }
  return response;
}

function Icon({ name }: { name: string }) {
  const paths: Record<string, string> = {
    home: 'M3 10 12 3l9 7v11h-6v-7H9v7H3Z',
    settings: 'M4 7h16M4 17h16M8 4v6M16 14v6',
    backup: 'M4 16v5h16v-5M12 3v13m-5-5 5 5 5-5',
    book: 'M12 6C8 3 5 3 2 4v15c4-1 7 0 10 2 3-2 6-3 10-2V4c-3-1-6-1-10 2Zm0 0v15',
    library: 'M4 5h16M4 9h16M4 13h16M4 17h10',
    shield: 'm12 2 9 4v6c0 5-9 10-9 10S3 17 3 12V6Zm-4 10 3 3 5-6',
    arrow: 'M4 12h16m-6-6 6 6-6 6',
  };
  return <svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name] || paths.book}/></svg>;
}

function App() {
  const [view, setView] = useState<View>('home');
  const [settings, setSettings] = useState<Settings | null>(null);
  const [draft, setDraft] = useState<Settings | null>(null);
  const [status, setStatus] = useState<Status | null>(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [folder, setFolder] = useState('');
  const [job, setJob] = useState<ImportJob | null>(null);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [materialTotal, setMaterialTotal] = useState(0);
  const phaseLabel: Record<string, string> = { scanning: 'Scansione', extracting: 'Lettura', deduplicating: 'Deduplica', reporting: 'Rapporto', interrupted: 'In pausa', completed: 'Conclusa', failed: 'Non riuscita', running: 'In corso' };

  async function refresh() {
    const [s, info] = await Promise.all([api('settings').then(r => r.json()), api('status').then(r => r.json())]);
    setSettings(s); setDraft(s); setStatus(info);
    document.documentElement.dataset.theme = s.theme;
  }
  useEffect(() => { refresh().catch(e => setError(e.message)); }, []);
  useEffect(() => {
    if (view !== 'library') return;
    api('materials?limit=200').then(r => r.json()).then(data => { setMaterials(data.items); setMaterialTotal(data.total); }).catch((e: Error) => setError(e.message));
  }, [view]);
  useEffect(() => {
    if (!job || job.state !== 'running') return;
    const timer = window.setInterval(() => {
      api(`jobs/${job.id}`).then(r => r.json()).then((next: ImportJob) => {
        setJob(next);
        if (next.state !== 'running') api('materials?limit=200').then(r => r.json()).then(data => { setMaterials(data.items); setMaterialTotal(data.total); }).catch(() => undefined);
      }).catch((e: Error) => setError(e.message));
    }, 400);
    return () => window.clearInterval(timer);
  }, [job]);

  async function action(work: () => Promise<void>) {
    setBusy(true); setError(''); setNotice('');
    try { await work(); } catch (e) { setError(e instanceof Error ? e.message : 'Operazione non riuscita.'); }
    finally { setBusy(false); }
  }
  function navigate(next: View) { setView(next); setNotice(''); setError(''); }
  function save(event: FormEvent) {
    event.preventDefault();
    action(async () => {
      await api('settings', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(draft) });
      await refresh(); setNotice('Impostazioni salvate sul dispositivo.');
    });
  }
  function download() {
    action(async () => {
      const response = await api('exports', { method: 'POST' });
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement('a'); link.href = url; link.download = `deepstudy-${new Date().toISOString().slice(0, 10)}.zip`;
      link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
      setNotice('Backup preparato. Conserva il file in un luogo sicuro.');
    });
  }
  function loadMaterials() {
    return api('materials?limit=200').then(r => r.json()).then(data => { setMaterials(data.items); setMaterialTotal(data.total); });
  }
  function openLibrary() {
    navigate('library');
    action(async () => { await loadMaterials(); });
  }
  function startImport(event: FormEvent) {
    event.preventDefault();
    action(async () => {
      const created: ImportJob = await api('imports', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ locator: folder, idempotency_key: crypto.randomUUID() }) }).then(r => r.json());
      setJob(created);
      setNotice('Lettura avviata. I file della cartella restano al loro posto.');
    });
  }
  function interruptImport() {
    if (!job) return;
    action(async () => { setJob(await api(`jobs/${job.id}/interrupt`, { method: 'POST' }).then(r => r.json())); setNotice('Importazione in pausa.'); });
  }
  function resumeImport() {
    if (!job) return;
    action(async () => { setJob(await api(`jobs/${job.id}/resume`, { method: 'POST' }).then(r => r.json())); setNotice('Importazione ripresa.'); });
  }
  function restore() {
    if (!file || !confirmed) return;
    action(async () => {
      await api('restore', { method: 'POST', headers: { 'Content-Type': 'application/zip' }, body: file });
      await refresh(); setFile(null); setConfirmed(false); setNotice('Ripristino completato. Dati e impostazioni sono disponibili.');
    });
  }

  return <div className="shell">
    <aside className="sidebar">
      <div className="brand"><span className="brand-symbol"><Icon name="book"/></span><span>DeepStudy<span className="brand-sub">IL TUO SPAZIO DI APPRENDIMENTO</span></span></div>
      <div className="nav-caption">SPAZIO PERSONALE</div>
      <nav aria-label="Navigazione principale">{([
        ['home', 'Panoramica'], ['library', 'Biblioteca'], ['settings', 'Impostazioni'], ['backup', 'Backup e ripristino']
      ] as [View, string][]).map(([key, label]) => <button key={key} className={view === key ? 'nav-item active' : 'nav-item'} aria-current={view === key ? 'page' : undefined} onClick={() => navigate(key)}><Icon name={key}/>{label}</button>)}</nav>
      <div className="sidebar-bottom"><span className="status-dot"/> Ambiente locale<div className="muted">I tuoi dati restano su questo PC.</div><span className="version">DeepStudy 0.1 · Catalogo M2</span></div>
    </aside>
    <main>
      <header className="topbar"><span>Il tuo percorso, un passo alla volta.</span><span className="badge"><span className="status-dot"/> Solo locale</span></header>
      <div className="content">
        {error && <div role="alert" className="message error">{error}<button onClick={() => action(refresh)}>Ricarica</button></div>}
        {notice && <div role="status" className="message success">{notice}</div>}
        {!settings || !status || !draft ? <section className="card"><h1>{error ? 'Connessione non disponibile' : 'Preparazione dello spazio…'}</h1><p>Avvia DeepStudy per aprire una sessione locale autenticata.</p></section> : <>
          <div className="page-heading"><p className="eyebrow">{view === 'home' ? 'BENVENUTO NEL TUO SPAZIO' : view === 'library' ? 'LA TUA BIBLIOTECA' : 'IL TUO DISPOSITIVO'}</p><h1>{view === 'home' ? `Pronto a costruire${settings.display_name ? `, ${settings.display_name}` : ''}.` : view === 'library' ? 'Materiali, senza spostarli.' : view === 'settings' ? 'Uno spazio che ti somiglia.' : 'I tuoi dati, al sicuro.'}</h1><p className="lede">{view === 'home' ? 'Le basi sono pronte. Personalizza il profilo e prepara il tuo primo backup.' : view === 'library' ? 'DeepStudy legge la cartella che autorizzi, calcola le impronte e conserva le versioni. Non esegue script, celle o modelli.' : view === 'settings' ? 'Preferenze personali, salvate direttamente su questo PC.' : 'Esporta una copia del profilo o riparti da un backup verificato.'}</p></div>
          {view === 'home' && <>
            <section className="hero"><div><span className="pill">FONDAZIONE LOCALE</span><h2>Un luogo per imparare.<br/>Una base da cui partire.</h2><p>DeepStudy cresce per tappe. In questa prima versione puoi configurare il tuo spazio e custodire i dati prima di iniziare il percorso ML e Deep Learning.</p><button className="primary" onClick={() => navigate('settings')}>Personalizza il profilo <Icon name="arrow"/></button></div><div className="hero-art" aria-hidden="true"><div className="orbit orbit-one"/><div className="orbit orbit-two"/><div className="book-tile"><Icon name="book"/><span>DS</span></div><span className="art-dot dot-one"/><span className="art-dot dot-two"/></div></section>
            <div className="section-heading"><h2>Le tue fondamenta</h2><span className="muted">Disponibili ora</span></div>
            <div className="card-grid"><section className="card"><span className="card-icon"><Icon name="settings"/></span><h3>Profilo personale</h3><p>Nome, aspetto e fuso orario. Le preferenze ti aspettano anche dopo un riavvio.</p><button className="text-button" onClick={() => navigate('settings')}>Apri impostazioni <Icon name="arrow"/></button></section><section className="card"><span className="card-icon"><Icon name="backup"/></span><h3>Una copia da conservare</h3><p>Un archivio del tuo profilo, con controlli di integrità prima del ripristino.</p><button className="text-button" onClick={() => navigate('backup')}>Gestisci backup <Icon name="arrow"/></button></section></div>
            <section className="next-step"><span className="step-number">02</span><div><h3>Il prossimo passo: la biblioteca</h3><p>Puoi importare una cartella locale. Studio, quiz e tutor restano nelle tappe successive. I materiali importati non sono ancora una revisione didattica.</p></div><button className="text-button" onClick={openLibrary}>Apri la biblioteca <Icon name="arrow"/></button></section>
          </>}
          {view === 'library' && <div className="library-stack"><form className="card" onSubmit={startImport}><span className="card-icon"><Icon name="library"/></span><h2>Cartella autorizzata</h2><p>Indica il percorso assoluto su questo PC. Cache, log, modelli e collegamenti restano fuori dal testo didattico.</p><label htmlFor="folder">Percorso della cartella</label><input id="folder" value={folder} placeholder="C:\\Users\\tuo-nome\\corpus" onChange={e => setFolder(e.target.value)} required/><p className="field-hint">Limite per file: 32 MiB. OCR: {status.ocr_engine === 'tesseract' ? 'motore locale disponibile, testo non revisionato' : 'non disponibile, le immagini restano segnalate'}.</p><div className="button-row"><button className="primary" type="submit" disabled={busy || job?.state === 'running'}>Avvia lettura</button>{job?.state === 'running' && <button className="secondary" type="button" onClick={interruptImport}>Interrompi</button>}{job?.can_resume && <button className="secondary" type="button" onClick={resumeImport}>Riprendi</button>}</div></form>
            {job && <section className="card"><div className="section-heading"><h2>Stato della lettura</h2><span className="pill neutral">{job.state === 'running' ? 'IN CORSO' : job.state === 'interrupted' ? 'IN PAUSA' : job.state === 'failed' ? 'NON RIUSCITA' : 'CONCLUSA'}</span></div><p className="field-hint">{phaseLabel[job.phase] || job.phase} · {job.progress_done}/{job.progress_total}</p><div className="progress" aria-hidden="true"><span style={{ width: `${job.progress_total ? Math.min(100, job.progress_done / job.progress_total * 100) : 0}%` }}/></div>{job.error_message && <p role="alert">{job.error_message}</p>}{!!job.report?.errors.length && <ul className="error-list">{job.report.errors.map(item => <li role="alert" key={`${item.path}-${item.code}`}><strong>{item.path || 'Importazione'}</strong> — {item.message}</li>)}</ul>}{job.report && <p className="field-hint">Versioni nuove: {job.report.versions_created}. Già presenti: {job.report.versions_reused}. Originali invariati: {job.report.original_hashes_unchanged ? 'sì' : 'no'}.</p>}{!!job.report?.duplicates.length && <ul className="dup-list">{job.report.duplicates.map(group => <li key={group.sha256}>Stesso contenuto in {group.paths.join(' e ')}</li>)}</ul>}</section>}
            <section className="card"><div className="section-heading"><h2>Materiali catalogati</h2><span className="muted">{materialTotal ? `${materials.length}${materialTotal > materials.length ? ` di ${materialTotal}` : ''} catalogati` : 'Nessun materiale'}</span></div>{materials.length ? <table className="material-table"><thead><tr><th>Percorso</th><th>Tipo</th><th>Stato</th></tr></thead><tbody>{materials.map(item => <tr key={item.id}><td>{item.locator}{!!item.duplicate_locators.length && <div className="dup">Stesso contenuto di {item.duplicate_locators.join(', ')}</div>}</td><td>{item.kind}</td><td>{item.extraction_state === 'failed' ? 'Errore di lettura' : item.extraction_state === 'ready' ? 'Letto' : item.extraction_state}</td></tr>)}</tbody></table> : <p>Quando autorizzi una cartella, qui compaiono le versioni lette. Un notebook non valido o un file illeggibile resta visibile nel rapporto, senza essere eseguito.</p>}</section></div>}
          {view === 'settings' && <form className="card form-card" onSubmit={save}><div className="section-heading"><h2>Preferenze</h2><span className="pill neutral">Profilo {status.profile}</span></div><label htmlFor="name">Come vuoi essere chiamato?</label><input id="name" maxLength={80} value={draft.display_name} placeholder="Il tuo nome" onChange={e => setDraft({ ...draft, display_name: e.target.value })}/><div className="form-row"><div><label htmlFor="theme">Aspetto</label><select id="theme" value={draft.theme} onChange={e => setDraft({ ...draft, theme: e.target.value as Settings['theme'] })}><option value="system">Segui il dispositivo</option><option value="light">Chiaro</option><option value="dark">Scuro</option></select></div><div><label htmlFor="timezone">Fuso orario</label><input id="timezone" value={draft.timezone} onChange={e => setDraft({ ...draft, timezone: e.target.value })} required/><span className="field-hint">Per esempio Europe/Rome o UTC.</span></div></div><div className="privacy-note"><Icon name="shield"/><div><strong>AI e sincronizzazione non attive</strong><p>Questa versione non invia contenuti a servizi AI o cloud. Le relative scelte restano per le prossime milestone.</p></div></div><button className="primary" type="submit" disabled={busy}>{busy ? 'Salvataggio…' : 'Salva preferenze'}</button></form>}
          {view === 'backup' && <div className="backup-stack"><section className="card"><span className="card-icon"><Icon name="backup"/></span><h2>Esporta il profilo</h2><p>Salva database, impostazioni e file derivati in un archivio ZIP. Le fonti originali esterne e le credenziali di sessione non sono incluse.</p><p className="field-hint">Limite della versione M1: 64 MiB. Il backup non è cifrato: conservalo in uno spazio privato.</p><button className="primary" onClick={download} disabled={busy}>Scarica backup <Icon name="backup"/></button></section><section className="card"><h2>Ripristina su un profilo vuoto</h2><p>Il controllo di integrità viene eseguito prima di applicare i dati. Un profilo già utilizzato non viene sovrascritto.</p>{status.can_restore ? <><label htmlFor="archive">Archivio DeepStudy</label><input id="archive" type="file" accept=".zip" onChange={e => { setFile(e.target.files?.[0] || null); setConfirmed(false); }}/><label className="checkbox"><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)}/>Voglio ripristinare questo archivio nel profilo vuoto.</label><button className="secondary" disabled={busy || !file || !confirmed} onClick={restore}>Verifica e ripristina</button></> : <div className="privacy-note"><Icon name="shield"/><div><strong>Il profilo contiene dati</strong><p>Per ripristinare una copia, avvia un profilo nuovo dalla cartella del progetto:</p><code>./scripts/start.ps1 -Profile ripristino</code></div></div>}</section></div>}
          <footer><span><Icon name="shield"/> Sessione locale autenticata</span><span>Schema dati v{status.schema_version} · Nessun collegamento cloud</span></footer>
        </>}
      </div>
    </main>
  </div>;
}

createRoot(document.getElementById('root')!).render(<App/>);
