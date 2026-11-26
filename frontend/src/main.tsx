import { useEffect, useState, type FormEvent } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

type Settings = { display_name: string; theme: 'system' | 'light' | 'dark'; timezone: string; ai_mode: 'off'; revision: number };
type Status = { schema_version: number; profile: string; can_restore: boolean };
type View = 'home' | 'settings' | 'backup';
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

  async function refresh() {
    const [s, info] = await Promise.all([api('settings').then(r => r.json()), api('status').then(r => r.json())]);
    setSettings(s); setDraft(s); setStatus(info);
    document.documentElement.dataset.theme = s.theme;
  }
  useEffect(() => { refresh().catch(e => setError(e.message)); }, []);

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
        ['home', 'Panoramica'], ['settings', 'Impostazioni'], ['backup', 'Backup e ripristino']
      ] as [View, string][]).map(([key, label]) => <button key={key} className={view === key ? 'nav-item active' : 'nav-item'} aria-current={view === key ? 'page' : undefined} onClick={() => navigate(key)}><Icon name={key}/>{label}</button>)}</nav>
      <div className="sidebar-bottom"><span className="status-dot"/> Ambiente locale<div className="muted">I tuoi dati restano su questo PC.</div><span className="version">DeepStudy 0.1 · Fondazione M1</span></div>
    </aside>
    <main>
      <header className="topbar"><span>Il tuo percorso, un passo alla volta.</span><span className="badge"><span className="status-dot"/> Solo locale</span></header>
      <div className="content">
        {error && <div role="alert" className="message error">{error}<button onClick={() => action(refresh)}>Ricarica</button></div>}
        {notice && <div role="status" className="message success">{notice}</div>}
        {!settings || !status || !draft ? <section className="card"><h1>{error ? 'Connessione non disponibile' : 'Preparazione dello spazio…'}</h1><p>Avvia DeepStudy per aprire una sessione locale autenticata.</p></section> : <>
          <div className="page-heading"><p className="eyebrow">{view === 'home' ? 'BENVENUTO NEL TUO SPAZIO' : 'IL TUO DISPOSITIVO'}</p><h1>{view === 'home' ? `Pronto a costruire${settings.display_name ? `, ${settings.display_name}` : ''}.` : view === 'settings' ? 'Uno spazio che ti somiglia.' : 'I tuoi dati, al sicuro.'}</h1><p className="lede">{view === 'home' ? 'Le basi sono pronte. Personalizza il profilo e prepara il tuo primo backup.' : view === 'settings' ? 'Preferenze personali, salvate direttamente su questo PC.' : 'Esporta una copia del profilo o riparti da un backup verificato.'}</p></div>
          {view === 'home' && <>
            <section className="hero"><div><span className="pill">FONDAZIONE LOCALE</span><h2>Un luogo per imparare.<br/>Una base da cui partire.</h2><p>DeepStudy cresce per tappe. In questa prima versione puoi configurare il tuo spazio e custodire i dati prima di iniziare il percorso ML e Deep Learning.</p><button className="primary" onClick={() => navigate('settings')}>Personalizza il profilo <Icon name="arrow"/></button></div><div className="hero-art" aria-hidden="true"><div className="orbit orbit-one"/><div className="orbit orbit-two"/><div className="book-tile"><Icon name="book"/><span>DS</span></div><span className="art-dot dot-one"/><span className="art-dot dot-two"/></div></section>
            <div className="section-heading"><h2>Le tue fondamenta</h2><span className="muted">Disponibili ora</span></div>
            <div className="card-grid"><section className="card"><span className="card-icon"><Icon name="settings"/></span><h3>Profilo personale</h3><p>Nome, aspetto e fuso orario. Le preferenze ti aspettano anche dopo un riavvio.</p><button className="text-button" onClick={() => navigate('settings')}>Apri impostazioni <Icon name="arrow"/></button></section><section className="card"><span className="card-icon"><Icon name="backup"/></span><h3>Una copia da conservare</h3><p>Un archivio del tuo profilo, con controlli di integrità prima del ripristino.</p><button className="text-button" onClick={() => navigate('backup')}>Gestisci backup <Icon name="arrow"/></button></section></div>
            <section className="next-step"><span className="step-number">02</span><div><h3>Il prossimo passo: la biblioteca</h3><p>Catalogo, importazione e fonti arriveranno in M2. Studio, quiz e tutor seguiranno nelle tappe successive.</p></div><span className="pill neutral">NON ANCORA DISPONIBILE</span></section>
          </>}
          {view === 'settings' && <form className="card form-card" onSubmit={save}><div className="section-heading"><h2>Preferenze</h2><span className="pill neutral">Profilo {status.profile}</span></div><label htmlFor="name">Come vuoi essere chiamato?</label><input id="name" maxLength={80} value={draft.display_name} placeholder="Il tuo nome" onChange={e => setDraft({ ...draft, display_name: e.target.value })}/><div className="form-row"><div><label htmlFor="theme">Aspetto</label><select id="theme" value={draft.theme} onChange={e => setDraft({ ...draft, theme: e.target.value as Settings['theme'] })}><option value="system">Segui il dispositivo</option><option value="light">Chiaro</option><option value="dark">Scuro</option></select></div><div><label htmlFor="timezone">Fuso orario</label><input id="timezone" value={draft.timezone} onChange={e => setDraft({ ...draft, timezone: e.target.value })} required/><span className="field-hint">Per esempio Europe/Rome o UTC.</span></div></div><div className="privacy-note"><Icon name="shield"/><div><strong>AI e sincronizzazione non attive</strong><p>Questa versione non invia contenuti a servizi AI o cloud. Le relative scelte restano per le prossime milestone.</p></div></div><button className="primary" type="submit" disabled={busy}>{busy ? 'Salvataggio…' : 'Salva preferenze'}</button></form>}
          {view === 'backup' && <div className="backup-stack"><section className="card"><span className="card-icon"><Icon name="backup"/></span><h2>Esporta il profilo</h2><p>Salva database, impostazioni e file derivati in un archivio ZIP. Le fonti originali esterne e le credenziali di sessione non sono incluse.</p><p className="field-hint">Limite della versione M1: 64 MiB. Il backup non è cifrato: conservalo in uno spazio privato.</p><button className="primary" onClick={download} disabled={busy}>Scarica backup <Icon name="backup"/></button></section><section className="card"><h2>Ripristina su un profilo vuoto</h2><p>Il controllo di integrità viene eseguito prima di applicare i dati. Un profilo già utilizzato non viene sovrascritto.</p>{status.can_restore ? <><label htmlFor="archive">Archivio DeepStudy</label><input id="archive" type="file" accept=".zip" onChange={e => { setFile(e.target.files?.[0] || null); setConfirmed(false); }}/><label className="checkbox"><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)}/>Voglio ripristinare questo archivio nel profilo vuoto.</label><button className="secondary" disabled={busy || !file || !confirmed} onClick={restore}>Verifica e ripristina</button></> : <div className="privacy-note"><Icon name="shield"/><div><strong>Il profilo contiene dati</strong><p>Per ripristinare una copia, avvia un profilo nuovo dalla cartella del progetto:</p><code>./scripts/start.ps1 -Profile ripristino</code></div></div>}</section></div>}
          <footer><span><Icon name="shield"/> Sessione locale autenticata</span><span>Schema dati v{status.schema_version} · Nessun collegamento cloud</span></footer>
        </>}
      </div>
    </main>
  </div>;
}

createRoot(document.getElementById('root')!).render(<App/>);
