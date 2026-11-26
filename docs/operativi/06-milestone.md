# Stato milestone e piano M1

26 novembre 2026. Piano operativo approvato: Q1–Q4 validate dall’utente.

| Milestone | Dipendenze originali | Stato effettivo |
|---|---|---|
| M0 | Nessuna | Parziale; rinvio L01–L04 autorizzato, deroga gate M1 |
| M1 | M0 | Completata e verificata su Windows 11 x64 |
| M2 | M1 | Non avviata |
| M3 | M2 | Non avviata |
| M4 | M3 | Non avviata |
| M5 | M2, M3 | Non avviata |
| M6 | M4, M5 | Non avviata |
| M7 | M3, M4; hardening M1 | Non avviata |
| M8 | M3, M6 | Non avviata |
| M9 | M5, M6, M7, M8 | Non avviata |

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
