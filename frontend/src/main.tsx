import { useEffect, useState, type FormEvent } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

type Settings = {
  display_name: string; theme: 'system' | 'light' | 'dark'; timezone: string; ai_mode: 'off';
  ai_daily_budget_cents: number; weekly_minutes: number | null; revision: number;
};
type Status = { schema_version: number; profile: string; can_restore: boolean; ocr_engine?: string; ai_enabled?: boolean; certification_chosen?: boolean };
type View = 'home' | 'library' | 'study' | 'review' | 'tutor' | 'certs' | 'labs' | 'sync' | 'settings' | 'backup';
type JobError = { path: string; code: string; message: string };
type ImportJob = { id: string; state: string; phase: string; progress_done: number; progress_total: number; can_resume: boolean; error_message?: string | null; report?: { errors: JobError[]; warnings: { path: string; message: string }[]; duplicates: { sha256: string; paths: string[] }[]; versions_created: number; versions_reused: number; original_hashes_unchanged: boolean; excluded: { path: string; reason: string }[] } | null };
type Material = { id: string; locator: string; kind: string; extraction_state: string; duplicate_locators: string[]; version_id: string };
type Chunk = { locator: string; text: string; quality: string };
type Action = { kind: string; objective_id: string; title: string; reason: string };
type Dashboard = { next_action: Action; reviews_due: { objective_id: string; title: string; due_at: string; reason: string }[]; gaps: { id: string; title: string; reason: string }[]; reading: { sessions: number; note: string }; hours_note: string; certification_chosen: boolean };
type Prompt = { id: string; prompt: string; options: { id: string; text: string }[]; kind: 'single' | 'multi' | 'flashcard'; origin: string; review: string };
type Session = { id: string; objective_id: string; title: string; state: string; citation: { kind: string; locator: string; version_id: string | null; excerpt: string | null }; question: Prompt | null; mastery_note: string };
type AttemptResult = { score: number; rationale: string; solution: string[]; next_review_at: string | null; replayed: boolean };
type TutorReply = { abstained: boolean; answer: string; citations: { locator: string; version_id: string | null; origin?: string }[]; model: null; sent_cloud: boolean };
type MockExam = { id: string; state: string; hints: boolean; questions: Prompt[]; report?: { correct: number; total: number; pass_probability: null; note: string; domains: { title: string; correct: number; total: number }[] } };
type NoteView = { versions: { id: string; content: string; base_version: string | null }[]; conflict: boolean; tombstoned: boolean };
type LabResult = { state: string; stdout: string; stderr: string; sandbox: string | null; rubric: { esito: string; soglia: null } };

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
const jsonHeaders = { 'Content-Type': 'application/json' };

function Icon({ name }: { name: string }) {
  const paths: Record<string, string> = {
    home: 'M3 10 12 3l9 7v11h-6v-7H9v7H3Z',
    settings: 'M4 7h16M4 17h16M8 4v6M16 14v6',
    backup: 'M4 16v5h16v-5M12 3v13m-5-5 5 5 5-5',
    book: 'M12 6C8 3 5 3 2 4v15c4-1 7 0 10 2 3-2 6-3 10-2V4c-3-1-6-1-10 2Zm0 0v15',
    library: 'M4 5h16M4 9h16M4 13h16M4 17h10',
    shield: 'm12 2 9 4v6c0 5-9 10-9 10S3 17 3 12V6Zm-4 10 3 3 5-6',
    arrow: 'M4 12h16m-6-6 6 6-6 6',
    study: 'M4 19V5h12l4 4v10H4Zm4-8h8M8 15h5',
    review: 'M4 12a8 8 0 1 0 2-5M4 4v5h5',
    tutor: 'M5 18V6h10l4 4v8H5Zm3-6h6',
    certs: 'M7 4h10v16H7Zm3 4h4M10 12h4M10 16h2',
    labs: 'M9 3v6L4 19h16l-5-10V3M9 3h6',
    sync: 'M7 7h11l-3-3M17 17H6l3 3',
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
  const [chunks, setChunks] = useState<Chunk[] | null>(null);
  const [home, setHome] = useState<Dashboard | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [picked, setPicked] = useState<string[]>([]);
  const [written, setWritten] = useState('');
  const [attempt, setAttempt] = useState<AttemptResult | null>(null);
  const [noteId] = useState(() => `nota-${crypto.randomUUID().slice(0, 8)}`);
  const [note, setNote] = useState('');
  const [savedNote, setSavedNote] = useState<NoteView | null>(null);
  const [cards, setCards] = useState<Prompt[]>([]);
  const [cardText, setCardText] = useState('');
  const [cardResult, setCardResult] = useState<AttemptResult | null>(null);
  const [tutorQuestion, setTutorQuestion] = useState('');
  const [tutorReply, setTutorReply] = useState<TutorReply | null>(null);
  const [referenceTitle, setReferenceTitle] = useState('');
  const [referenceText, setReferenceText] = useState('');
  const [mock, setMock] = useState<MockExam | null>(null);
  const [mockPick, setMockPick] = useState<Record<string, string>>({});
  const [labSource, setLabSource] = useState('print("prova isolata")\n');
  const [labResult, setLabResult] = useState<LabResult | null>(null);
  const [syncFile, setSyncFile] = useState<File | null>(null);
  const phaseLabel: Record<string, string> = { scanning: 'Scansione', extracting: 'Lettura', deduplicating: 'Deduplica', reporting: 'Rapporto', interrupted: 'In pausa', completed: 'Conclusa', failed: 'Non riuscita', running: 'In corso' };
  const titles: Record<View, string> = {
    home: 'BENVENUTO NEL TUO SPAZIO', library: 'LA TUA BIBLIOTECA', study: 'LA SESSIONE', review: 'IL RIPASSO',
    tutor: 'IL TUTOR LOCALE', certs: 'LA SIMULAZIONE', labs: 'IL LABORATORIO', sync: 'I DISPOSITIVI',
    settings: 'IL TUO DISPOSITIVO', backup: 'IL TUO DISPOSITIVO',
  };
  const headings: Record<View, string> = {
    home: `Pronto a costruire${settings?.display_name ? `, ${settings.display_name}` : ''}.`,
    library: 'Materiali, senza spostarli.', study: 'Un passo, già scelto.', review: 'Gli errori tornano da soli.',
    tutor: 'Citazioni, non un modello.', certs: 'Una prova, senza suggerimenti.', labs: 'Codice solo se lo chiedi.',
    sync: 'Due profili, nessun cloud.', settings: 'Uno spazio che ti somiglia.', backup: 'I tuoi dati, al sicuro.',
  };

  async function refresh() {
    const [s, info, board] = await Promise.all([
      api('settings').then(r => r.json()), api('status').then(r => r.json()), api('dashboard').then(r => r.json()),
    ]);
    setSettings(s); setDraft(s); setStatus(info); setHome(board);
    document.documentElement.dataset.theme = s.theme;
  }
  useEffect(() => { refresh().catch(e => setError(e.message)); }, []);
  useEffect(() => {
    if (view !== 'library') return;
    api('materials?limit=200').then(r => r.json()).then(data => { setMaterials(data.items); setMaterialTotal(data.total); }).catch((e: Error) => setError(e.message));
  }, [view]);
  useEffect(() => {
    if (view !== 'review') return;
    api('flashcards').then(r => r.json()).then(data => setCards(data.items)).catch((e: Error) => setError(e.message));
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
      await api('settings', { method: 'PUT', headers: jsonHeaders, body: JSON.stringify(draft) });
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
      const created: ImportJob = await api('imports', { method: 'POST', headers: jsonHeaders, body: JSON.stringify({ locator: folder, idempotency_key: crypto.randomUUID() }) }).then(r => r.json());
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
  function openMaterial(item: Material) {
    action(async () => {
      const data = await api(`materials/${item.id}/versions/${item.version_id}/chunks`).then(r => r.json());
      setChunks(data.chunks);
      setNotice('Estratto della versione indicata. Aprirlo non conta come padronanza.');
    });
  }
  function begin(objectiveId: string) {
    action(async () => {
      const opened: Session = await api('study-sessions', { method: 'POST', headers: jsonHeaders, body: JSON.stringify({ objective_id: objectiveId, mode: 'quiz' }) }).then(r => r.json());
      setSession(opened); setAttempt(null); setPicked([]); setWritten('');
      navigate('study');
    });
  }
  function followUp() {
    if (!home) return;
    if (home.next_action.kind === 'ripasso') { navigate('review'); return; }
    if (home.next_action.kind === 'simulazione') { navigate('certs'); return; }
    begin(home.next_action.objective_id);
  }
  function toggle(id: string, kind: Prompt['kind']) {
    setPicked(current => kind === 'single' ? [id] : current.includes(id) ? current.filter(item => item !== id) : [...current, id]);
  }
  function submitAttempt(event: FormEvent) {
    event.preventDefault();
    if (!session?.question) return;
    const answer = session.question.kind === 'flashcard' ? [written] : picked;
    action(async () => {
      const result: AttemptResult = await api('attempts', { method: 'POST', headers: jsonHeaders, body: JSON.stringify({ id: crypto.randomUUID(), question_version_id: session.question!.id, answer }) }).then(r => r.json());
      setAttempt(result);
      await refresh();
      setNotice(result.score >= 1 ? 'Tentativo corretto. Il modulo successivo si è sbloccato, senza chiamarlo padronanza.' : 'Tentativo registrato. La spiegazione resta qui; il ripasso torna da solo.');
    });
  }
  function pauseSession() {
    if (!session) return;
    action(async () => { setSession(await api(`study-sessions/${session.id}/interrupt`, { method: 'POST' }).then(r => r.json())); setNotice('Sessione in pausa. I tentativi restano.'); });
  }
  function resumeSession() {
    if (!session) return;
    action(async () => { setSession(await api(`study-sessions/${session.id}/resume`, { method: 'POST' }).then(r => r.json())); setNotice('Sessione ripresa sulla stessa citazione.'); });
  }
  function saveNote(event: FormEvent) {
    event.preventDefault();
    action(async () => {
      const saved: NoteView = await api('notes', { method: 'POST', headers: jsonHeaders, body: JSON.stringify({ note_id: noteId, content: note, objective_id: session?.objective_id ?? 'c00', base_version: savedNote?.versions.at(-1)?.id ?? null }) }).then(r => r.json());
      setSavedNote(saved); setNote('');
      setNotice(saved.conflict ? 'Nota salvata. C’è un conflitto: le due versioni restano.' : 'Nota salvata.');
    });
  }
  function answerCard(event: FormEvent) {
    event.preventDefault();
    const card = cards[0];
    if (!card) return;
    action(async () => {
      const result: AttemptResult = await api('attempts', { method: 'POST', headers: jsonHeaders, body: JSON.stringify({ id: crypto.randomUUID(), question_version_id: card.id, answer: [cardText] }) }).then(r => r.json());
      setCardResult(result); setCardText(''); await refresh();
    });
  }
  function addReference(event: FormEvent) {
    event.preventDefault();
    action(async () => {
      await api('references', { method: 'POST', headers: jsonHeaders, body: JSON.stringify({ title: referenceTitle, text: referenceText }) });
      setReferenceTitle(''); setReferenceText('');
      setNotice('Testo aggiunto. Il tutor può citarlo insieme ai tuoi file.');
    });
  }
  function askTutor(event: FormEvent) {
    event.preventDefault();
    action(async () => {
      const reply: TutorReply = await api('tutor/messages', { method: 'POST', headers: jsonHeaders, body: JSON.stringify({ question: tutorQuestion, policy: 'local' }) }).then(r => r.json());
      setTutorReply(reply);
    });
  }
  function startMock() {
    action(async () => {
      const seeded = await api('blueprints/local', { method: 'POST' }).then(r => r.json());
      const opened: MockExam = await api('mocks', { method: 'POST', headers: jsonHeaders, body: JSON.stringify({ blueprint_id: seeded.id }) }).then(r => r.json());
      setMock(opened); setMockPick({});
      setNotice('Simulazione aperta. Nessun punteggio fino alla chiusura. Non è un esame ufficiale.');
    });
  }
  function sendMock(event: FormEvent) {
    event.preventDefault();
    if (!mock) return;
    action(async () => {
      for (const question of mock.questions) {
        const choice = mockPick[question.id];
        if (!choice) continue;
        await api(`mocks/${mock.id}/answers`, { method: 'POST', headers: jsonHeaders, body: JSON.stringify({ id: crypto.randomUUID(), question_version_id: question.id, answer: [choice] }) });
      }
      setNotice('Risposte registrate. Il punteggio arriva solo quando chiudi.');
    });
  }
  function closeMock() {
    if (!mock) return;
    action(async () => {
      const closed: MockExam = await api(`mocks/${mock.id}/close`, { method: 'POST' }).then(r => r.json());
      setMock(closed);
    });
  }
  function runLab(event: FormEvent) {
    event.preventDefault();
    action(async () => {
      setLabResult(await api('labs/runs', { method: 'POST', headers: jsonHeaders, body: JSON.stringify({ source: labSource, timeout_s: 2 }) }).then(r => r.json()));
    });
  }
  function exportSync() {
    action(async () => {
      const payload = await api('sync/exchange', { method: 'POST', headers: jsonHeaders, body: JSON.stringify({ known_ids: [], events: [] }) }).then(r => r.json());
      const blob = new Blob([JSON.stringify(payload.outgoing)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a'); link.href = url; link.download = 'deepstudy-sync.json'; link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      setNotice('Pacchetto locale scaricato. Non è cifrato e non parte verso un server.');
    });
  }
  function importSync() {
    if (!syncFile) return;
    action(async () => {
      const events = JSON.parse(await syncFile.text());
      const result = await api('sync/exchange', { method: 'POST', headers: jsonHeaders, body: JSON.stringify({ known_ids: [], events }) }).then(r => r.json());
      setNotice(`Eventi applicati: ${result.applied.length}. Conflitti conservati: ${result.conflicts.length}.`);
    });
  }

  const nav: [View, string, string][] = [
    ['home', 'Panoramica', 'home'], ['study', 'Studio', 'study'], ['review', 'Ripasso', 'review'], ['library', 'Biblioteca', 'library'],
    ['tutor', 'Tutor', 'tutor'], ['certs', 'Simulazione', 'certs'], ['labs', 'Laboratorio', 'labs'], ['sync', 'Dispositivi', 'sync'],
    ['settings', 'Impostazioni', 'settings'], ['backup', 'Backup e ripristino', 'backup'],
  ];

  return <div className="shell">
    <aside className="sidebar">
      <div className="brand"><span className="brand-symbol"><Icon name="book"/></span><span>DeepStudy<span className="brand-sub">IL TUO SPAZIO DI APPRENDIMENTO</span></span></div>
      <div className="nav-caption">SPAZIO PERSONALE</div>
      <nav aria-label="Navigazione principale">{nav.map(([key, label, icon]) => <button key={key} className={view === key ? 'nav-item active' : 'nav-item'} aria-current={view === key ? 'page' : undefined} onClick={() => navigate(key)}><Icon name={icon}/>{label}</button>)}</nav>
      <div className="sidebar-bottom"><span className="status-dot"/> Ambiente locale<div className="muted">I tuoi dati restano su questo PC.</div><span className="version">DeepStudy 0.2 · Percorso locale</span></div>
    </aside>
    <main>
      <header className="topbar"><span>Il tuo percorso, un passo alla volta.</span><span className="badge"><span className="status-dot"/> Solo locale</span></header>
      <div className="content">
        {error && <div role="alert" className="message error">{error}<button onClick={() => action(refresh)}>Ricarica</button></div>}
        {notice && <div role="status" className="message success">{notice}</div>}
        {!settings || !status || !draft || !home ? <section className="card"><h1>{error ? 'Connessione non disponibile' : 'Preparazione dello spazio…'}</h1><p>Avvia DeepStudy per aprire una sessione locale autenticata.</p></section> : <>
          <div className="page-heading"><p className="eyebrow">{titles[view]}</p><h1>{headings[view]}</h1><p className="lede">{({
            home: 'La panoramica sceglie il passo dentro le 8–10 ore a settimana. Il campo è Machine Learning e Deep Learning. La lettura di un file non conta come padronanza.',
            library: 'DeepStudy legge la cartella che autorizzi, calcola le impronte e conserva le versioni. Non esegue script, celle o modelli.',
            study: 'La citazione resta sulla versione aperta. Sblocca il seguito un tentativo corretto, non l’apertura della pagina.',
            review: 'I ripassi si ricostruiscono dai tentativi. Cambiare fuso orario non sposta l’istante salvato.',
            tutor: 'Cita i tuoi file, i testi che aggiungi e il percorso ML e DL. Se nessuna di queste fonti sostiene la risposta, si astiene.',
            certs: 'Il campo scelto è Machine Learning e Deep Learning. Le domande sono diverse dallo studio e il rapporto arriva solo alla chiusura.',
            labs: 'Il codice parte solo da questo riquadro, isolato dal profilo. Non riceve un voto: la rubrica non è approvata.',
            sync: 'Gli eventi si scambiano tra profili locali. Non c’è un server e il pacchetto non è cifrato.',
            settings: 'Preferenze personali, salvate direttamente su questo PC.',
            backup: 'Esporta una copia del profilo o riparti da un backup verificato.',
          })[view]}</p></div>
          {view === 'home' && <>
            <section className="hero"><div><span className="pill">{home.next_action.kind === 'ripasso' ? 'RIPASSO' : 'PROSSIMO PASSO'}</span><h2>{home.next_action.title}</h2><p>{home.next_action.reason}</p><button className="primary" onClick={followUp}>Fai questo passo <Icon name="arrow"/></button></div><div className="hero-art" aria-hidden="true"><div className="orbit orbit-one"/><div className="orbit orbit-two"/><div className="book-tile"><Icon name="book"/><span>DS</span></div><span className="art-dot dot-one"/><span className="art-dot dot-two"/></div></section>
            <div className="section-heading"><h2>Cosa è distinto</h2><span className="muted">{home.reading.sessions} letture</span></div>
            <div className="card-grid"><section className="card"><span className="card-icon"><Icon name="study"/></span><h3>Letture e tentativi</h3><p>{home.reading.note}</p><button className="text-button" onClick={() => navigate('study')}>Apri lo studio <Icon name="arrow"/></button></section><section className="card"><span className="card-icon"><Icon name="review"/></span><h3>Ripassi dovuti</h3><p>{home.reviews_due.length ? home.reviews_due[0].reason : 'Nessun ripasso scaduto. Quando un tentativo scade, torna qui da solo.'}</p><button className="text-button" onClick={() => navigate('review')}>Vedi i ripassi <Icon name="arrow"/></button></section></div>
            <section className="next-step"><span className="step-number">02</span><div><h3>La biblioteca resta disponibile</h3><p>{home.hours_note} I materiali importati non sono ancora una revisione didattica.</p></div><button className="text-button" onClick={openLibrary}>Apri la biblioteca <Icon name="arrow"/></button></section>
          </>}
          {view === 'study' && <div className="library-stack">
            {!session && <section className="card"><h2>Nessuna sessione aperta</h2><p>Il passo proposto è {home.next_action.title}.</p><button className="primary" onClick={followUp}>Inizia</button></section>}
            {session && <section className="card"><div className="section-heading"><h2>{session.title}</h2><span className="pill neutral">{session.state === 'interrupted' ? 'IN PAUSA' : 'APERTA'}</span></div><p className="field-hint">{session.citation.locator}{session.citation.version_id ? ` · versione ${session.citation.version_id}` : ' · testo del percorso'}</p><blockquote>{session.citation.excerpt || 'Estratto non disponibile per questo locator.'}</blockquote><p className="field-hint">{session.mastery_note}</p><div className="button-row">{session.state === 'active' ? <button className="secondary" type="button" onClick={pauseSession}>Metti in pausa</button> : <button className="secondary" type="button" onClick={resumeSession}>Riprendi</button>}</div></section>}
            {session?.question && <form className="card" onSubmit={submitAttempt}><h2>Quesito di studio</h2><p>{session.question.prompt}</p><fieldset><legend className="field-hint">Origine: {session.question.origin === 'ai_draft' ? 'bozza AI, non valutativa' : 'quesito originale'}</legend>{session.question.options.map(option => <label key={option.id} className="checkbox"><input type={session.question!.kind === 'multi' ? 'checkbox' : 'radio'} name="answer" checked={picked.includes(option.id)} onChange={() => toggle(option.id, session.question!.kind)}/>{option.text}</label>)}{session.question.kind === 'flashcard' && <input value={written} onChange={e => setWritten(e.target.value)} aria-label="Risposta"/>}</fieldset><button className="primary" type="submit" disabled={busy}>Registra il tentativo</button>{attempt && <p role="status">Punteggio {attempt.score}. {attempt.rationale}{attempt.next_review_at ? ` Prossimo ripasso: ${attempt.next_review_at}.` : ''}</p>}</form>}
            <form className="card" onSubmit={saveNote}><h2>Nota</h2><label htmlFor="note">Appunto personale</label><textarea id="note" value={note} onChange={e => setNote(e.target.value)} required/><button className="secondary" disabled={busy}>Salva la nota</button>{savedNote?.conflict && <p role="status">Conflitto conservato: le versioni non si sovrascrivono.</p>}</form>
          </div>}
          {view === 'review' && <div className="library-stack"><section className="card"><h2>In scadenza</h2>{home.reviews_due.length ? <ul className="dup-list">{home.reviews_due.map(item => <li key={item.objective_id}><strong>{item.title}</strong> — {item.reason} <button className="text-button" onClick={() => begin(item.objective_id)}>Apri</button></li>)}</ul> : <p>Nessun ripasso scaduto.</p>}</section>
            <form className="card" onSubmit={answerCard}><h2>Flashcard</h2>{cards[0] ? <><p>{cards[0].prompt}</p><label htmlFor="card">Risposta</label><input id="card" value={cardText} onChange={e => setCardText(e.target.value)} required/><button className="primary" disabled={busy}>Scopri</button>{cardResult && <p role="status">Punteggio {cardResult.score}. {cardResult.rationale}</p>}</> : <p>Le flashcard compaiono dopo la prima sessione di studio.</p>}</form></div>}
          {view === 'tutor' && <div className="library-stack"><form className="card" onSubmit={askTutor}><h2>Chiedi al corpus</h2><p>Modalità locale: nessun modello è installato e nessun testo esce dal PC. Il cloud resta spento.</p><label htmlFor="ask">Domanda</label><textarea id="ask" value={tutorQuestion} onChange={e => setTutorQuestion(e.target.value)} required/><button className="primary" disabled={busy}>Cerca una citazione</button>{tutorReply && <div role="status"><p>{tutorReply.answer}</p>{tutorReply.citations.map(item => <p className="field-hint" key={item.locator}>{item.origin === 'aggiunta' ? 'Testo aggiunto' : item.origin === 'percorso' ? 'Percorso ML e DL' : 'Tuo file'} · {item.locator}</p>)}</div>}</form>
            <form className="card" onSubmit={addReference}><h2>Aggiungi un testo</h2><p>Vale insieme ai file della biblioteca. Non è un comando per il tutor.</p><label htmlFor="reftitle">Titolo</label><input id="reftitle" value={referenceTitle} onChange={e => setReferenceTitle(e.target.value)} required/><label htmlFor="reftext">Testo</label><textarea id="reftext" value={referenceText} onChange={e => setReferenceText(e.target.value)} required/><button className="secondary" disabled={busy}>Aggiungi al tutor</button></form></div>}
          {view === 'certs' && <div className="library-stack"><section className="card"><h2>Machine Learning e Deep Learning</h2><p>Il campo è scelto. La simulazione usa domande originali, diverse da quelle di studio. Non è ancora la matrice di un esame singolo e non stima la promozione.</p><button className="primary" onClick={startMock} disabled={busy || mock?.state === 'open'}>Apri una simulazione locale</button></section>
            {mock && <form className="card" onSubmit={sendMock}><div className="section-heading"><h2>Simulazione</h2><span className="pill neutral">{mock.state === 'open' ? 'APERTA' : 'CHIUSA'}</span></div>{mock.questions.map(question => <fieldset key={question.id}><legend>{question.prompt}</legend>{question.options.map(option => <label key={option.id} className="checkbox"><input type="radio" name={question.id} disabled={mock.state !== 'open'} checked={mockPick[question.id] === option.id} onChange={() => setMockPick({ ...mockPick, [question.id]: option.id })}/>{option.text}</label>)}</fieldset>)}{mock.state === 'open' && <div className="button-row"><button className="secondary" disabled={busy}>Invia le risposte</button><button className="primary" type="button" onClick={closeMock}>Chiudi e vedi il rapporto</button></div>}{mock.report && <div role="status"><p>{mock.report.correct}/{mock.report.total}. {mock.report.note}</p><ul className="dup-list">{mock.report.domains.map(domain => <li key={domain.title}>{domain.title}: {domain.correct}/{domain.total}</li>)}</ul></div>}</form>}</div>}
          {view === 'labs' && <form className="card form-card" onSubmit={runLab}><h2>Esecuzione isolata</h2><p>Parte solo da questo riquadro, con rete spenta e senza i file del profilo. Non assegna un voto: la rubrica 80/100 non è approvata.</p><label htmlFor="code">Codice Python</label><textarea id="code" value={labSource} onChange={e => setLabSource(e.target.value)} required/><button className="primary" disabled={busy}>Esegui</button>{labResult && <div role="status"><p>Esito: {labResult.state}. {labResult.rubric.esito}.</p><pre>{labResult.stdout || labResult.stderr}</pre></div>}</form>}
          {view === 'sync' && <div className="backup-stack"><section className="card"><h2>Pacchetto locale</h2><p>Scambia gli eventi con un altro profilo su questa macchina. Il remoto non è configurato e il file non è cifrato.</p><button className="primary" onClick={exportSync} disabled={busy}>Scarica gli eventi</button></section><section className="card"><h2>Importa eventi</h2><label htmlFor="syncfile">File JSON</label><input id="syncfile" type="file" accept="application/json,.json" onChange={e => setSyncFile(e.target.files?.[0] || null)}/><button className="secondary" disabled={!syncFile || busy} onClick={importSync}>Applica</button></section></div>}
          {view === 'library' && <div className="library-stack"><form className="card" onSubmit={startImport}><span className="card-icon"><Icon name="library"/></span><h2>Cartella autorizzata</h2><p>Indica il percorso assoluto su questo PC. Cache, log, modelli e collegamenti restano fuori dal testo didattico.</p><label htmlFor="folder">Percorso della cartella</label><input id="folder" value={folder} placeholder="C:\\Users\\tuo-nome\\corpus" onChange={e => setFolder(e.target.value)} required/><p className="field-hint">Limite per file: 32 MiB. OCR: {status.ocr_engine === 'tesseract' ? 'motore locale disponibile, testo non revisionato' : 'non disponibile, le immagini restano segnalate'}.</p><div className="button-row"><button className="primary" type="submit" disabled={busy || job?.state === 'running'}>Avvia lettura</button>{job?.state === 'running' && <button className="secondary" type="button" onClick={interruptImport}>Interrompi</button>}{job?.can_resume && <button className="secondary" type="button" onClick={resumeImport}>Riprendi</button>}</div></form>
            {job && <section className="card"><div className="section-heading"><h2>Stato della lettura</h2><span className="pill neutral">{job.state === 'running' ? 'IN CORSO' : job.state === 'interrupted' ? 'IN PAUSA' : job.state === 'failed' ? 'NON RIUSCITA' : 'CONCLUSA'}</span></div><p className="field-hint">{phaseLabel[job.phase] || job.phase} · {job.progress_done}/{job.progress_total}</p><div className="progress" aria-hidden="true"><span style={{ width: `${job.progress_total ? Math.min(100, job.progress_done / job.progress_total * 100) : 0}%` }}/></div>{job.error_message && <p role="alert">{job.error_message}</p>}{!!job.report?.errors.length && <ul className="error-list">{job.report.errors.map(item => <li role="alert" key={`${item.path}-${item.code}`}><strong>{item.path || 'Importazione'}</strong> — {item.message}</li>)}</ul>}{job.report && <p className="field-hint">Versioni nuove: {job.report.versions_created}. Già presenti: {job.report.versions_reused}. Originali invariati: {job.report.original_hashes_unchanged ? 'sì' : 'no'}.</p>}{!!job.report?.duplicates.length && <ul className="dup-list">{job.report.duplicates.map(group => <li key={group.sha256}>Stesso contenuto in {group.paths.join(' e ')}</li>)}</ul>}</section>}
            <section className="card"><div className="section-heading"><h2>Materiali catalogati</h2><span className="muted">{materialTotal ? `${materials.length}${materialTotal > materials.length ? ` di ${materialTotal}` : ''} catalogati` : 'Nessun materiale'}</span></div>{materials.length ? <table className="material-table"><thead><tr><th>Percorso</th><th>Tipo</th><th>Stato</th><th></th></tr></thead><tbody>{materials.map(item => <tr key={item.id}><td>{item.locator}{!!item.duplicate_locators.length && <div className="dup">Stesso contenuto di {item.duplicate_locators.join(', ')}</div>}</td><td>{item.kind}</td><td>{item.extraction_state === 'failed' ? 'Errore di lettura' : item.extraction_state === 'ready' ? 'Letto' : item.extraction_state}</td><td><button type="button" className="text-button" onClick={() => openMaterial(item)}>Apri versione</button></td></tr>)}</tbody></table> : <p>Quando autorizzi una cartella, qui compaiono le versioni lette. Un notebook non valido o un file illeggibile resta visibile nel rapporto, senza essere eseguito.</p>}{chunks && <ul className="dup-list">{chunks.map(chunk => <li key={chunk.locator}><strong>{chunk.locator}</strong> — {chunk.text.slice(0, 280)}</li>)}</ul>}</section></div>}
          {view === 'settings' && <form className="card form-card" onSubmit={save}><div className="section-heading"><h2>Preferenze</h2><span className="pill neutral">Profilo {status.profile}</span></div><label htmlFor="name">Come vuoi essere chiamato?</label><input id="name" maxLength={80} value={draft.display_name} placeholder="Il tuo nome" onChange={e => setDraft({ ...draft, display_name: e.target.value })}/><div className="form-row"><div><label htmlFor="theme">Aspetto</label><select id="theme" value={draft.theme} onChange={e => setDraft({ ...draft, theme: e.target.value as Settings['theme'] })}><option value="system">Segui il dispositivo</option><option value="light">Chiaro</option><option value="dark">Scuro</option></select></div><div><label htmlFor="timezone">Fuso orario</label><input id="timezone" value={draft.timezone} onChange={e => setDraft({ ...draft, timezone: e.target.value })} required/><span className="field-hint">Per esempio Europe/Rome o UTC.</span></div></div><div className="form-row"><div><label htmlFor="budget">Tetto AI giornaliero, in centesimi</label><input id="budget" type="number" min={0} max={100000} value={draft.ai_daily_budget_cents} onChange={e => setDraft({ ...draft, ai_daily_budget_cents: Number(e.target.value) })}/><span className="field-hint">Zero blocca ogni prenotazione. Il provider cloud non è configurato.</span></div><div><label htmlFor="minutes">Minuti a settimana</label><input id="minutes" type="number" min={0} max={2400} value={draft.weekly_minutes ?? ''} onChange={e => setDraft({ ...draft, weekly_minutes: e.target.value === '' ? 540 : Number(e.target.value) })}/></div></div><div className="privacy-note"><Icon name="shield"/><div><strong>Cloud AI spento</strong><p>Il tutor locale cita i tuoi file, i testi aggiunti e il percorso ML e DL. L’invio a un provider resta disattivato e non c’è un modello generativo installato.</p></div></div><button className="primary" type="submit" disabled={busy}>{busy ? 'Salvataggio…' : 'Salva preferenze'}</button></form>}
          {view === 'backup' && <div className="backup-stack"><section className="card"><span className="card-icon"><Icon name="backup"/></span><h2>Esporta il profilo</h2><p>Salva database, impostazioni e file derivati in un archivio ZIP. Le fonti originali esterne e le credenziali di sessione non sono incluse.</p><p className="field-hint">Limite della versione M1: 64 MiB. Il backup non è cifrato: conservalo in uno spazio privato.</p><button className="primary" onClick={download} disabled={busy}>Scarica backup <Icon name="backup"/></button></section><section className="card"><h2>Ripristina su un profilo vuoto</h2><p>Il controllo di integrità viene eseguito prima di applicare i dati. Un profilo già utilizzato non viene sovrascritto.</p>{status.can_restore ? <><label htmlFor="archive">Archivio DeepStudy</label><input id="archive" type="file" accept=".zip" onChange={e => { setFile(e.target.files?.[0] || null); setConfirmed(false); }}/><label className="checkbox"><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)}/>Voglio ripristinare questo archivio nel profilo vuoto.</label><button className="secondary" disabled={busy || !file || !confirmed} onClick={restore}>Verifica e ripristina</button></> : <div className="privacy-note"><Icon name="shield"/><div><strong>Il profilo contiene dati</strong><p>Per ripristinare una copia, avvia un profilo nuovo dalla cartella del progetto:</p><code>./scripts/start.ps1 -Profile ripristino</code></div></div>}</section></div>}
          <footer><span><Icon name="shield"/> Sessione locale autenticata</span><span>Schema dati v{status.schema_version} · Nessun collegamento cloud</span></footer>
        </>}
      </div>
    </main>
  </div>;
}

createRoot(document.getElementById('root')!).render(<App/>);
