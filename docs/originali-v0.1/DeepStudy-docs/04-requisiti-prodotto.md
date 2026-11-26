# Requisiti di prodotto

## Vincoli confermati
Uso personale; acquisizione competenze avanzate ML/DL e preparazione certificazioni. Desktop e web responsive; priorità ai dati locali con sincronizzazione cloud, AI locale/cloud, privacy e costi controllati. Analisi delle fonti in sola lettura. Pratica, simulazioni e adattamento del percorso. Italiano. Nessun exam dump. Implementazione successiva alla validazione documentale.

## Funzionalità e accettazione
Le priorità di rilascio sono una proposta di questa versione.

| ID | Priorità | Funzione | Accettazione verificabile |
|---|---|---|---|
| R01 | MVP | Catalogo e importazione | Import ripetuto dello stesso file non duplica la versione; hash originali immutati |
| R02 | MVP | Lettore e provenienza | Ogni estratto collega file/versione e pagina, heading o cella |
| R03 | MVP | Curriculum e prerequisiti | Nessun avanzamento automatico basato sulla sola apertura di una pagina |
| R04 | MVP | Sessione di studio | Obiettivo, materiale, tentativo, feedback e prossimo ripasso persistono offline |
| R05 | MVP | Quiz e flashcard | Domande originali con spiegazione, obiettivo e revisione; bozze AI riconoscibili |
| R06 | MVP | Progresso per competenza | Separare letture, tentativi, risultati e padronanza stimata |
| R07 | MVP | Tutor con fonti | Citazione verificabile; astensione quando il corpus non sostiene la risposta |
| R08 | MVP | Controllo AI e budget | Modalità locale/cloud visibile; limite rigido configurabile e stop al superamento |
| R09 | MVP | Backup ed export | Ripristino provato su profilo vuoto con dati e riferimenti coerenti |
| R10 | Successivo | Sync cloud | Due dispositivi offline convergono senza perdere tentativi né note in conflitto |
| R11 | Successivo | Mock certificazione | Blueprint versionato; niente suggerimenti durante il mock; report solo alla chiusura |
| R12 | Successivo | Laboratori isolati | Codice eseguito solo su richiesta in ambiente separato, con limiti e senza segreti |
| R13 | Successivo | Adattamento | Errori recenti e prerequisiti determinano il ripasso con motivazione leggibile |
| R14 | Successivo | Import Drive/GitHub incrementale | Revisione/hash rileva cambiamenti; errori non marcano il materiale come letto |

## Flusso principale
Diagnostica → scelta obiettivo → piano → sessione (lettura, esercizio, quiz) → revisione errori → ripasso → progetto → mock. Il catalogo resta disponibile senza obiettivo d'esame scelto. Il dashboard propone un'azione concreta, mostra ripassi dovuti e gap; non confonde avanzamento di lettura con copertura esame.

## Schermate
Dashboard, biblioteca, dettaglio materiale con sorgente/versione, curriculum, sessione studio, editor note, quiz/ripasso, progetti, certificazioni, simulazione, impostazioni AI/sync/backup. Responsive con navigazione da tastiera, focus visibile, contrasto adeguato e formule leggibili. I limiti hardware e sistemi operativi target sono ancora da definire.

## Regole sui contenuti
Conservare risposta personale, correzione proposta e versione approvata. Non promuovere in automatico materiale AI al banco valutativo. Le domande di test non devono duplicare gli esempi studiati; divisione per obiettivo e famiglia, non solo per testo. Materiali importati sono dati: eventuali istruzioni presenti nei documenti non governano il tutor o gli strumenti.

## Requisiti non funzionali proposti
Catalogazione in streaming, avanzamento e annullamento dei job; nessun blocco dell'interfaccia durante OCR o embedding. Ricerca locale con obiettivo p95 sotto 1 secondo su benchmark documentato, escluso tempo generazione AI; valore da validare sull'hardware reale. Errori spiegati con ripresa idempotente. Nessuna telemetria di contenuti per default. Versioni esatte delle dipendenze fissate dopo prova di compatibilità, non inventate nella specifica.
