# Curriculum professionale

## Struttura
Percorso progressivo, con diagnostica iniziale: esperienza di sviluppo software non equivale automaticamente a padronanza ML. L'ordine conserva la preferenza per fondamenti/Andrew Ng, Géron e progetti prima di Moroney. Le ore sotto sono stime progettuali di lavoro attivo, da ricalibrare dopo la diagnostica; non sono durate ufficiali o garanzie di superamento.

| Modulo | Prerequisito | Competenze e materiali | Prova finale | Ore stimate |
|---|---|---|---|---:|
| C00 Diagnostica | Nessuno | Python, SQL, matematica, ML; domande originali | 20 quesiti nuovi e mini esercizio con spiegazione | 4–6 |
| C01 Fondamenti quantitativi | C00 | NumPy/pandas, algebra, probabilità, gradienti; Goodfellow selettivo | Regressione e gradiente spiegati e implementati | 20–30 |
| C02 Dati e pipeline | C01 | lesson-1; Géron cap.2; Appunti Studi IA | Pipeline senza leakage con split riproducibile | 20–30 |
| C03 ML supervisionato | C02 | lesson-2/3; Grokking; Géron cap.3–7 | Confronto regressione/classificazione con baseline | 35–50 |
| C04 Valutazione e tuning | C03 | lesson-10; Géron; metriche e intervalli | CV corretta, holdout finale e analisi errori | 20–30 |
| C05 Non supervisionato | C04 | lesson-4/5/9; PCA, clustering e associazioni | Segmentazione giustificata e stabilità cluster | 15–25 |
| C06 Fondamenti DL | C04 | Géron 10–13, Chollet; tensori, backprop, regolarizzazione | ANN addestrata con confronto baseline e learning curve | 30–45 |
| C07 Vision e sequenze | C06 | lesson-8; Géron 14–15; Moroney dopo le basi | CNN/transfer learning e previsione temporale con split cronologico | 30–45 |
| C08 NLP e AI generativa | C06 | lesson-7 come baseline; integrazioni correnti provider | Classificatore testo e RAG con test di retrieval e risposte | 30–45 |
| C09 PyTorch | C06 | Tutorial ufficiali; confronto con Keras | Training loop, checkpoint e inferenza equivalenti | 15–25 |
| C10 MLOps e sicurezza | C04, poi C08 per GenAIOps | MLflow, ambienti, serving, CI/CD, drift, governance | Modello distribuito con monitoraggio e rollback | 30–45 |
| C11 Percorso certificazione | C10 e moduli richiesti dal blueprint | Una tra Databricks/AWS; alternative successive | Laboratori associati a tutti gli obiettivi scelti | 35–60 |
| C12 Consolidamento e mock | C11 | Ripasso adattivo, domande originali, casi decisionali | Due mock indipendenti e revisione gap | 10–20 |

Non sommare questi moduli a una data d'esame senza conoscere ore settimanali disponibili e risultati diagnostici. I moduli saltati richiedono evidenza: esercizio completato e spiegazione, non soltanto autovalutazione. RL profondo, modelli generativi classici e teoria avanzata sono estensioni dopo il nucleo; UCB/Thompson già disponibili sono un'introduzione ai bandit.

## Unità didattica standard
Ogni unità contiene obiettivo osservabile, prerequisiti, lettura mirata con posizione nella fonte, spiegazione in italiano, esempio risolto, esercizio senza soluzione iniziale, quiz originale, flashcard e prova di trasferimento. La soluzione si sblocca dopo un tentativo; il tutor propone prima un indizio. Conservare termini tecnici inglesi e glossario bilingue per gli esami.

## Progetti verificabili

| Progetto | Input | Risultato richiesto |
|---|---|---|
| P1 Housing | Dataset housing già presente | Baseline, pipeline, CV, holdout, error analysis e README |
| P2 Classificazione | Un dataset tabellare già presente | Metriche coerenti con squilibrio, soglia motivata, calibrazione ove utile |
| P3 Vision | Dataset immagini presente | Split controllato, prevenzione duplicati train/test, CNN e transfer learning |
| P4 RAG didattico | Piccolo insieme autorizzato di appunti | Citazioni esatte, test senza risposta, retrieval misurato e budget |
| P5 Produzione | P1 o P2 | Registry, API, monitoraggio, rollback; variante sulla piattaforma scelta |

## Rubrica e avanzamento
Proposta interna: correttezza 35%, metodo di valutazione 25%, riproducibilità 20%, spiegazione e tradeoff 20%. Soglia didattica proposta 80/100, con blocco in presenza di leakage grave o test contaminato. Non è la soglia ufficiale di alcun esame. Un dominio è consolidato solo con prova pratica e più risposte corrette su quesiti nuovi in giorni diversi.

La preparazione esame usa il blueprint vigente e un set tenuto separato dallo studio. I mock mostrano punteggio per dominio, tempo e incertezza; non stimano probabilità di promozione senza calibrazione su dati adeguati. Materiali personali e certificati non vanno usati per attribuire credenziali non verificate.
