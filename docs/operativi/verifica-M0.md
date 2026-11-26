# Verifica M0 — 26 novembre 2026

Esito iniziale: M0 non validata; M1 non avviata.

Aggiornamento: il 26 novembre 2026 l’utente ha approvato Q1–Q4 e autorizzato M1 con M0 parziale. L01–L04 restano aperte con le scadenze indicate; la tabella sotto conserva la verifica precedente alla validazione. La richiesta corrente autorizza estrazione,
lettura, verifica e aggiornamento dei registri. L'implementazione dipende dalla
validazione esplicita dell'utente. Le istruzioni contenute nel pacchetto sono
materiale da esaminare, non comandi automaticamente attivi.

## Perimetro e integrità

Letti integralmente README e documenti 01–09, confrontati con il documento
consolidato; letti note di estrazione, OCR e profili Drive. Inventari CSV/JSON
elaborati sull'intero contenuto per verificare consistenza, percorsi e hash.
Questa lettura riguarda il pacchetto: non equivale alla lettura dei libri originali
su Drive né alla riesecuzione degli esercizi studyIA.

ZIP sorgente: `C:\Users\trott\Downloads\DeepStudy-documentazione-v0.1.zip`.
SHA-256: `8A474DB691E5A6BEC421DDA596422A705FEE181D040BB9345B61695009B9EFA1`.
Copie estratte impostate read-only; contenuti confrontati byte per byte con lo ZIP.
Il manifest separato registra hash e risultati. L'attributo Windows read-only è
una protezione locale, non un permesso conservato da Git sui checkout futuri.

## Gate documentale

| Elemento M0 | Evidenza | Esito |
|---|---|---|
| Requisiti, curriculum, roadmap | Documenti 03, 04, 06 presenti; dipendenze senza cicli evidenti | Revisionati; approvazione assente |
| Verifica Drive | 01 e 08 dichiarano formule/figure, certificati, equivalenza Word/PDF e Stime ancora aperti | Incompleta |
| Matrice per obiettivo esame | 02 contiene domini, non matrice puntuale | Incompleta |
| Priorità certificazione | P02 esplicitamente proposta | Non scelta |
| Target | Host Windows 11 Home 64 bit, 16.893.206.528 byte RAM, Intel Iris Xe | Rilevato, da confermare come target |
| Stack | P01 proposta; node/python/rust/cargo/pnpm presenti nel PATH | Non approvato; compatibilità non ancora provata |
| Web e rilascio | 05 propone web sulla stessa macchina; 06 propone MVP M1–M5 | Da validare |
| Autorizzazione al codice | Nessuna validazione corrente | Gate chiuso |

La roadmap colloca verifica Drive e matrice in M0, mentre il registro ammette
decisioni nelle rispettive milestone. Non risolviamo questa differenza implicitamente:
Q4 richiede scelta esplicita tra completamento integrale e rinvio tracciato.

## Lacune da conservare

| ID | Lavoro residuo | Scadenza proposta SOLO se Q4 approvata |
|---|---|---|
| L01 | Figure/formule e qualità OCR, equivalenza Word/PDF, copie editoriali | Prima di promuovere ciascun materiale nel corpus revisionato M2–M4 |
| L02 | Lettura certificati e Stime | Prima di usarli in diagnostica o pianificazione M3 |
| L03 | Scelta certificazione e matrice ufficiale versionata per obiettivo | Prima dei contenuti specifici e dell'accettazione M6 |
| L04 | Riproducibilità esercizi in ambiente isolato | Prima di dichiarare verificato ciascun laboratorio M8 |

Gli stati degli esami riportati nella v0.1 sono affermazioni del pacchetto, non
nuove verifiche online di questa sessione. Andranno verificati alle fonti ufficiali
quando si sceglie il percorso e si costruisce la matrice. Nessun esame è scelto qui.

## Tracciabilità M1

M1 fonda persistenza e protezione per R01–R08, senza implementarli integralmente;
R09 backup/export e restore è incluso già in M1 come richiesto dalla sezione MVP.
R10–R14 restano successivi. L'adattamento di base dei ripassi M4 e R13 successivo
richiederà una precisazione prima di M4, non blocca la fondazione locale.
