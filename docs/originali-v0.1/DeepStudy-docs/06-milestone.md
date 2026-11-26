# Milestone di sviluppo proposte
Nessuna milestone di implementazione risulta avviata. M0 è documentale. Le dipendenze sotto sono vincolanti nella proposta; le durate di sviluppo richiedono disponibilità e hardware concordati.

| ID | Dipendenze | Task | Verifica significativa | Accettazione |
|---|---|---|---|---|
| M0 Documentazione | Nessuna | Chiudere verifica Drive, matrice per obiettivo, target hardware, stack e priorità certificazione | Revisione requisiti↔curriculum↔milestone e registro lacune | Validazione utente prima del codice prodotto |
| M1 Fondazione locale | M0 | Struttura app, servizio locale autenticato, schema e migrazioni, impostazioni | Avvio da installazione pulita, migrazione e restore | Dati persistono; segreti assenti da bundle/log |
| M2 Catalogo | M1 | Import read-only, hash, dedup, parser, OCR e job | Import stesso corpus due volte; file rotto; job interrotto | Nessun doppione versione, nessuna modifica originali, errore visibile |
| M3 Studio e progresso | M2 | Curriculum, lettore, note, sessioni e tentativi | Sessione offline interrotta e ripresa; citazioni su versione precedente | Nessun tentativo perso; riferimenti coerenti |
| M4 Quiz e ripasso | M3 | Quesiti revisionati, flashcard, scheduler versionato | Quesiti multi-risposta, replay tentativo, cambio fuso/data | Score corretto e ripasso ricostruibile |
| M5 Tutor ibrido | M2,M3 | Retrieval, citazioni, policy, adapter AI e budget | Domanda fuori corpus, prompt injection nel testo, locale senza modello, richieste concorrenti al budget | Astensione/errore corretto; nessun invio cloud vietato e nessuno sforamento |
| M6 Certificazioni | M4,M5 | Blueprint versionato, matrice, mock e report gap | Mock con domande nuove; aggiornamento blueprint | Nessun dump, banca studio separata dal mock, storico preservato |
| M7 Sync personale | M3,M4; hardening M1 | Auth remoto, coda eventi, conflitti, cifratura e recovery | Due device offline, note concorrenti, retry e tombstone | Convergenza senza perdita; accesso isolato per profilo |
| M8 Laboratori | M3,M6 | Runner isolato, artefatti, rubriche progetti e variante cloud scelta | Timeout, accesso rete/file vietato, risultato fallito | Processo fermato e host protetto; feedback riproducibile |
| M9 Distribuzione | M5,M6,M7,M8 | Packaging target, aggiornamenti, export e ripristino | Installazione pulita sui sistemi target e restore reale | Checklist rilascio soddisfatta e limitazioni dichiarate |

## MVP e release
Primo MVP personale: M1–M5 più backup/export di M1, con corpus limitato revisionato. Funzioni certificazione strutturate con M6; sincronizzazione M7 e runner M8 nelle release successive. Il prodotto finale include desktop e web, sync, pratica e certificazioni; MVP locale non soddisfa da solo tutto il perimetro finale.

## Esempio di task eseguibile dopo validazione
Task M2.1: importer Python/notebook read-only. Input: cartella autorizzata, allowlist formati e snapshot hash. Output: record MaterialVersion, job e report. Dipendenze: schema M1. Non eseguire import Python o notebook. Accettazione: reimport invariato non duplica; contenuto cambiato crea versione; file non leggibile resta in errore; hash corpus originale invariato. Prove su fixture rappresentative con notebook invalido e due file identici in percorsi diversi. Un task non è completato solo perché compila.

## Gate di qualità
Ogni milestone produce riepilogo cambiamenti, test realmente eseguiti, risultati e limiti. Non dichiarare test superati se non eseguiti. Aggiornare documentazione insieme alle decisioni. Non servono test per una semplice modifica di testo; parser, score, budget, sync e migrazioni richiedono verifiche di comportamento. Nessun deploy o apertura pubblica impliciti in questa roadmap.
