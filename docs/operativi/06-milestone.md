# Stato milestone

26 novembre 2026. Piano operativo approvato: Q1–Q4 validate dall’utente.

| Milestone | Dipendenze originali | Stato effettivo |
|---|---|---|
| M0 | Nessuna | Parziale; rinvio L01–L04 autorizzato, deroga gate M1 |
| M1 | M0 | Completata e verificata su Windows 11 x64 |
| M2 | M1 | Verificata su fixture il 26 novembre 2026, con limiti aperti |
| M3 | M2 | Meccanismo verificato su fixture Linux il 26 novembre 2026 |
| M4 | M3 | Meccanismo verificato su fixture Linux il 26 novembre 2026 |
| M5 | M2, M3 | Tutor citazionale verificato; nessun modello e nessun invio |
| M6 | M4, M5 | Meccanismo verificato; L03 aperta, nessuna certificazione scelta |
| M7 | M3, M4; hardening M1 | Scambio locale verificato; remoto e cifratura non configurati |
| M8 | M3, M6 | Isolamento Linux verificato su codice di prova; L04 e P05 aperti |
| M9 | M5, M6, M7, M8 | Checklist dichiarata; installer dei sistemi target non prodotto |

Se Q4 autorizza il rinvio, annotare M0 come parziale con deroga al gate M1,
citando la risposta dell'utente e le scadenze L01–L04. Non riscrivere lo storico.

## Task M1 dopo validazione

| ID | Dipende da | Risultato | Prova di accettazione | Stato |
|---|---|---|---|---|
| M1.1 | Gate Q1–Q4 risolto | Struttura frontend/desktop/backend, ambiente riproducibile e versioni fissate dopo compatibilità | Bootstrap in ambiente pulito, build UI e avvio desktop sul target; prerequisiti documentati | Verificato |
| M1.2 | M1.1 | Servizio loopback, ciclo di vita desktop, autenticazione locale, controlli host/origin ed errori leggibili | Richiesta autorizzata accettata; token mancante/errato e host/origin estranei rifiutati; arresto e riavvio senza processi orfani | Verificato |
| M1.3 | M1.2 | Profilo locale separato dagli originali, SQLite, schema minimo e migrazioni versionate | Creazione DB vuoto, persistenza al riavvio, vincoli referenziali; migrazione su fixture precedente con dati conservati, gestione fallimento senza perdita | Verificato |
| M1.4 | M1.3 | Impostazioni UI persistenti e confine tra configurazione e segreti | Salvataggio/riavvio coerenti; input invalido rifiutato; token/credenziali assenti da bundle e log; nessun invio cloud | Verificato |
| M1.5 | M1.3, M1.4 | Backup/export con manifest e restore su profilo vuoto | Confronto record/riferimenti dopo restore; archivio corrotto respinto senza danneggiare dati; backup pre-migrazione e ripristino verificati | Verificato |
| M1.6 | M1.1–M1.5 | Verifica integrata desktop e browser locale, istruzioni avvio e report | Ambiente pulito + avvio + impostazioni + riavvio + migrazione + restore; integrità originali; esiti reali e limiti registrati | Verificato |

## Verifica M1 — 26 novembre 2026

Bootstrap in copia pulita con venv e dipendenze npm nuove, cache compilazione
Rust riutilizzata. Build TypeScript/Vite e Tauri riuscite. Avvio della finestra
nativa, chiusura ordinaria e arresto del backend verificati su Windows 11 x64.

Otto test backend superati: autenticazione e rifiuto host/origin estranei,
persistenza e conflitti delle impostazioni, migrazioni con rollback e recupero
del backup pre-migrazione, integrità referenziale e immutabilità, backup e
ripristino su profilo vuoto, rifiuto dell'archivio corrotto e della sovrascrittura.
Edge ha verificato su viewport mobile salvataggio, download e restore su un
secondo profilo. Un riavvio reale del servizio ha conservato le preferenze.
Token di avvio e cookie assenti dal bundle e dall'output oltre al messaggio
iniziale sul canale privato. Tutti i 18 originali corrispondono al manifest e
mantengono l'attributo di sola lettura.

Limiti M1: archivi ZIP fino a 64 MiB, profili di ripristino vuoti e servizio
solo sulla macchina locale. Pytest segnala un avviso di deprecazione nel client
di test Starlette/httpx, con esito positivo di tutta la suite.
I controlli documentali effettuati sono nel manifest e nella verifica M0.
M1 si considera completata solo con accettazione comportamentale, non con la sola build.
Il packaging distributivo finale resta M9; l'avvio verificato sul target è già M1.

## Task M2

Schema SQLite portato alla versione 3 con le tabelle dei job. Le tabelle M1 restano immutabili dove già lo erano. Un backup M1 di schema 2 si ripristina e viene migrato a 3. L01–L04 restano aperte: i materiali importati non sono una revisione didattica e nessuna certificazione è stata scelta.

| ID | Dipende da | Risultato | Prova di accettazione | Stato |
|---|---|---|---|---|
| M2.1 | M1 | Importazione read-only di Python e notebook da una cartella autorizzata, con hash, versioni, job e rapporto | Reimport invariato senza nuova versione; contenuto modificato con nuova versione; notebook non valido e file illeggibile con errore visibile; due file identici in percorsi diversi; hash degli originali invariati | Verificato su fixture |
| M2.2 | M2.1 | Parser statici per testo, CSV/TSV e PDF testuale; esclusione di cache, log, pickle e collegamenti | Celle notebook lette senza output eseguiti; script Python non eseguito; PDF di prova con locator di pagina; pickle e symlink esclusi | Verificato, con i limiti sotto |
| M2.3 | M2.1 | Fase OCR senza promozione a testo revisionato | Immagine PNG con motore assente: errore visibile, nessuna versione e nessun testo inventato | Parziale |
| M2.4 | M2.1 | Deduplica per hash e job riprendibile | Stesso hash su percorsi distinti; interruzione dopo il primo file e ripresa; processo interrotto e recupero al riavvio del servizio, senza versioni duplicate | Verificato su fixture |

## Verifica M2 — 26 novembre 2026

Ambiente di questa sessione: Linux, Python 3.12.3, Chrome headless. Non è una nuova verifica sul desktop Windows 11 x64 di M1. Il corpus studyIA e i libri Drive non erano montati né autorizzati: le prove usano fixture locali. I 18 file v0.1 non sono stati modificati.

`python -m pytest -q`: 11 test superati, fra cui gli 8 di M1. Resta l'avviso di deprecazione Starlette/httpx già registrato in M1; l'esito della suite è positivo.

Coperti da test: reimport senza duplicare le versioni; modifica che crea una seconda versione e conserva la prima; notebook non valido e file illeggibile con errore; due Python identici in percorsi diversi; hash degli originali invariati prima e dopo; script e celle non eseguiti; output di cella non copiato; interruzione, ripresa e recupero dopo crash del worker; rifiuto della cartella che contiene profilo o documentazione originale; ripristino di un backup schema 2 sullo schema 3.

Chrome headless, stessa macchina del servizio, viewport 1280×800 e 375×780: apertura della Biblioteca, lettura di una cartella di prova, errore visibile sul notebook non valido, duplicato segnalato, dicitura «Originali invariati: sì», reimport con zero versioni nuove, salvataggio delle impostazioni e ritorno alla panoramica. Non rieseguito in Edge né nella finestra Tauri.

Limiti aperti: file oltre 32 MiB e cartelle oltre 20.000 file sono rifiutati; l'interruzione è osservata tra un file e l'altro; solo UTF-8; il PDF legge le stringhe testuali, non il layout né le formule; senza `tesseract` le immagini restano in errore `ocr_unavailable` e non diventano testo. Una versione già registrata per lo stesso hash non viene riestratta. L01 resta il vincolo prima dell'uso didattico. L03 resta il vincolo prima dell'accettazione dei contenuti M6.

## Task M3–M9

Schema SQLite 5. Le tabelle immutabili di M1 non sono state riscritte. Un backup di schema 2 si ripristina ancora e arriva allo schema corrente. La quota scelta il 27 novembre 2026 è 8–10 ore a settimana, con piano a 9 ore. Il campo delle certificazioni è Machine Learning e Deep Learning; la matrice del singolo esame non è chiusa. Il tutor cita file, testi aggiunti e il percorso. La rubrica 80/100 non è applicata.

| ID | Risultato | Prova | Stato |
|---|---|---|---|
| M3 | Curriculum, sessione, citazione sulla versione aperta, note, panoramica | Apertura senza sblocco del modulo successivo; pausa e ripresa con la stessa citazione; tentativo conservato | Verificato su fixture |
| M4 | Quesiti originali, risposta multipla, replay, ripasso ricostruibile | Stesso UUID non cambia esito; UUID diverso rifiutato; cambio fuso non sposta `due_at`; due giorni e prova pratica per il consolidato | Verificato su fixture |
| M5 | Tutor locale con citazione o astensione, budget atomico | Domanda fuori corpus; istruzione iniettata nel testo ignorata; cloud rifiutato senza socket; due prenotazioni concorrenti non superano il tetto | Verificato su fixture |
| M6 | Blueprint locale, mock senza suggerimenti, storico | Banca di studio assente dal mock; punteggio solo alla chiusura; nuova bozza non riscrive il mock precedente | Meccanismo verificato, L03 aperta |
| M7 | Coda eventi fra due profili | Note concorrenti entrambe conservate; tentativo con lo stesso UUID convergente; tombstone senza cancellare le versioni; remoto rifiutato | Scambio locale, non cifrato |
| M8 | Runner su richiesta | Timeout, rete e file dell'host non raggiungibili, processo fermato, nessun voto | Linux con namespace; non i laboratori studyIA |
| M9 | Limiti nel `/api/status` e in questa pagina | Suite e interfaccia locale; nessun installer Windows o macOS costruito qui | Checklist, non rilascio |

## Verifica M3–M9 — 26 novembre 2026

Ambiente: Linux, Python 3.12.3, Chrome headless e una finestra Chrome. Non è una nuova verifica sul desktop Windows 11 x64 di M1. Il corpus studyIA e i libri Drive non sono stati importati. I file v0.1 non sono stati modificati.

`python -m pytest -q`: 23 test superati, inclusi gli 8 di M1 e quelli di M2. Resta l'avviso di deprecazione Starlette/httpx; l'esito della suite è positivo.

Chrome, viewport 1280×800 e 375×780: la panoramica propone la diagnostica; un tentativo corretto a risposta multipla mostra punteggio e spiegazione e sposta il passo su Fondamenti quantitativi; pausa e ripresa; il tutor si astiene sulla carbonara e, dopo la lettura di una cartella di prova, cita il brano sul gradiente con la versione; la simulazione non mostra il rapporto prima della chiusura; il laboratorio termina senza voto; il nome salvato ricompare nel titolo. La navigazione resta usabile a 375 px.

Limiti: niente modello generativo e niente provider cloud, anche se il tetto in centesimi è configurabile e parte da zero; `ai_mode` resta `off`. La sincronizzazione non ha un server né chiavi. L'isolamento del laboratorio usa `unshare` con namespace utente, mount e rete, non un container firmato, ed è verificato solo su Linux. Il backup resta da 64 MiB su profilo vuoto. Nessuna certificazione è scelta e nessun esame è stato verificato alle fonti ufficiali.
