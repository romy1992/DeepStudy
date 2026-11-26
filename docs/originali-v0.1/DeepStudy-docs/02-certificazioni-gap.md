# Certificazioni e gap analysis
Verifica fonti ufficiali: 26 novembre 2026. È una mappatura per dominio; la mappatura di ogni singolo obiettivo delle guide deve essere completata e versionata prima di dichiarare un percorso pronto all'esame.

## Obiettivi
Databricks ML Associate e AWS ML Engineer erano priorità proposte, non ancora scelte esplicitamente dall'utente. Proposta di lavoro: nucleo comune, poi una sola specializzazione iniziale per contenere costi e dispersione; Google e Azure come percorsi successivi o alternativi.

| Percorso | Stato verificato | Conseguenza |
|---|---|---|
| Databricks Certified Machine Learning Associate | Pagina ufficiale disponibile; aree piattaforma, workflow, sviluppo e deployment [S1] | Candidato iniziale; servono laboratori Databricks/MLflow/Unity Catalog |
| AWS Certified Machine Learning Engineer – Associate | Guida MLA-C02 in uso dal 29/09/2026 [S2] | Usare C02: include anche foundation model e RAG |
| Google Professional Machine Learning Engineer | Pagina corrente include ML e AI generativa, pipeline e produzione [S3] | Percorso avanzato; recuperare la nuova guida collegata prima della matrice per obiettivo |
| Microsoft Machine Learning Operations Engineer Associate | Pagina corrente: MLOps e GenAIOps, Azure ML e Foundry [S4] | Possibile percorso Azure; non sostituire automaticamente una preferenza dell'utente |
| TensorFlow Developer Certificate | Esame chiuso [S5] | TensorFlow resta competenza tecnica; rimuovere obiettivo di prenotazione |
| Azure AI Engineer Associate / Azure Data Scientist Associate | Ritirati il 30/06/2026 e 01/06/2026 [S6] | Non pianificarli come nuovi esami |

Fonti S1–S6 e URL in 09-fonti.md. Non sono state verificate qui altre certificazioni NVIDIA: nessun programma specifico viene assunto come requisito. Corsi DeepLearning.AI/fast.ai sono risorse formative, non equivalenti a certificazioni professionali con esame sorvegliato.

## Confronto Databricks per domini
Pesi della pagina ufficiale: piattaforma 38%, workflow 19%, sviluppo 31%, deployment 12% [S1].

| Dominio | Evidenza interna | Copertura qualitativa | Integrazione e prova |
|---|---|---|---|
| Databricks ML | Python e notebook generici | Piattaforma non dimostrata | AutoML, Unity Catalog, MLflow: eseguire un esperimento e registrarne gli artefatti |
| ML workflows | Preprocessing, split e pipeline sklearn; appunti leakage | Parziale, trasferibile | Portare pipeline in workflow tracciabile con feature e lineage |
| Model development | Regressione, classificazione, ensemble e CV | Buona base concettuale, non validata in esecuzione | Tuning tracciato e confronto con baseline su holdout |
| Model deployment | Modelli serializzati presenti | Operatività non dimostrata | Registrazione, serving, gestione versione e test inferenza |

## Confronto AWS MLA-C02
I quattro domini correnti pesano 28%, 24%, 24%, 24% [S2].

| Dominio | Evidenza interna | Gap principale | Laboratorio |
|---|---|---|---|
| Preparazione dati ML/AI | CSV, encoding, scaling, pipeline | Storage/ingestion AWS, embedding, dati RAG e protezione dati | Pipeline dati con ruoli minimi, validazione e tracciamento |
| Sviluppo ML e foundation model | sklearn e Keras; NLP classico | SageMaker/Bedrock, selezione FM, RAG e valutazione generativa | Confrontare baseline ML e un caso RAG con dataset di valutazione |
| Deployment e orchestrazione | Esempi locali | Endpoint, pipeline gestite, CI/CD e infrastruttura | Deploy riproducibile, test e rollback |
| Operazioni, monitoraggio e sicurezza | Appunti concettuali | Metriche operative, drift, IAM e gestione costi | Simulare drift, allarme, recupero e rimozione risorse |

## Google e Azure: confronto preliminare
Google valuta architettura low-code, collaborazione su dati/modelli, scala, serving, orchestrazione e monitoraggio [S3]. I sorgenti sostengono soprattutto prototipazione e modellazione: mancano evidenze operative sulla piattaforma. La pagina segnala aggiornamenti di piattaforma: evitare programmi basati su una vecchia guida o solo sui nomi storici dei servizi.

Azure richiede infrastruttura MLOps/GenAIOps, ciclo di vita, qualità, osservabilità e ottimizzazione [S4]. Mancano laboratori dimostrati con Azure ML, Foundry, GitHub Actions e IaC. La copertura teorica del DL non colma questi requisiti.

## Gap trasversali ordinati

| Priorità | Lacuna | Risorsa ufficiale da integrare | Evidenza richiesta |
|---|---|---|---|
| P0 | Diagnosi competenze e leakage | sklearn User Guide [S7] | Pipeline fit solo sui fold train, holdout separato |
| P0 | Riproducibilità | Guide framework [S7–S9] | Ambiente bloccato, seed e istruzioni di esecuzione |
| P0 | MLOps | MLflow docs e guida del percorso scelto [S10] | Run, registro modello, serving, rollback |
| P0 | Piattaforma d'esame | S1 oppure S2 e relativi percorsi ufficiali | Laboratorio completo con evidenze |
| P1 | LLM, embedding, RAG e valutazione | Guide correnti del provider scelto | Test retrieval e groundedness, costo e latenza |
| P1 | Monitoring, sicurezza, governance | Guide del provider scelto | Drift simulato, autorizzazioni e audit |
| P1 | PyTorch | Tutorials ufficiali [S9] | Training loop, checkpoint e inferenza |
| P2 | Matematica e teoria avanzata | Libro Goodfellow già presente | Derivazione e spiegazione applicata |

«Non dimostrata» significa assenza di evidenza sufficiente nel materiale esaminato, non incapacità personale. Completare la matrice con `exam_version`, `objective_id`, `material_id`, `evidence_locator`, stato, confidence, laboratorio e data controllo. Evitare percentuali di copertura finché ogni obiettivo non ha evidenza revisionata.
