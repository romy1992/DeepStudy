# Analisi dei materiali

## Metodo e tracciabilità
Snapshot GitHub del 26/11/2026, commit indicato nel README. Inventario per percorso, formato, dimensione, SHA-256, argomenti e stato di lettura. Notebook analizzati nelle celle sorgente, senza eseguire output o import. CSV e TSV profilati contando record dopo la prima riga e registrando la prima riga; alcuni dataset non hanno intestazione. Modelli pickle/Keras, archivi e file di log sono inventariati, non deserializzati.

I tag automatici sono indizi, non valutazioni definitive. In particolare la ricerca della parola `transformers` produceva tre falsi positivi dovuti a `ColumnTransformer`: non documentano LLM. Nessuna evidenza di un laboratorio RAG o di MLOps nei sorgenti individuati. Le stime di difficoltà sotto sono valutazioni didattiche, non misure dell'abilità dell'utente.

## Inventario GitHub

| Tipo | Numero | Utilizzo |
|---|---:|---|
| Python | 163 | Esercizi, implementazioni, alcuni file inizializzazione vuoti |
| Notebook | 38 | ML classico e reti neurali, incluse varianti refactored |
| PDF | 10 | Cheatsheet, 11 pagine complessive |
| CSV | 74 | Dataset, più copie tra esercizi |
| TSV | 1 | Dataset NLP |
| JPG | 10.002 | Asset del dataset di immagini, non lezioni distinte |
| PNG / JPEG | 6 / 1 | Figure e asset |
| Pickle / Keras | 9 / 1 | Modelli serializzati; non caricati |
| Altri file | 3022 | Include cache, log, archivi e altri asset |
| **Totale** | **13.327** | Il CSV completo permette controlli per singolo file |

Il repository non contiene file Word o PowerPoint nello snapshot. I libri Word sono su Drive. Il numero di script non equivale al numero di lezioni originali: ci sono file vuoti e duplicati da raggruppare per hash durante l'importazione.

## Collezioni e competenze

| Percorso | Contenuti verificati nei sorgenti | Livello stimato | Impiego |
|---|---|---|---|
| lesson-1-Preprocessing | Imputazione, codifica, scaling | Base | Fondamenti dei dati |
| lesson-2-Regression | Lineare, polinomiale, SVR, alberi e foreste | Base/intermedio | Confronto modelli e metriche |
| lesson-3-Classification | Logistica, KNN, SVM, Bayes, alberi | Base/intermedio | Classificazione e valutazione |
| lesson-4-Clustering | K-means e gerarchico | Intermedio | Segmentazione |
| lesson-5-Association Rule Learning | Regole associative | Intermedio | Modulo complementare |
| lesson-6-Reinforcement Learning | UCB e Thompson sampling | Intermedio | Bandit; non equivale a RL profondo |
| lesson-7-Natural Language Processing | NLTK, bag-of-words, Naive Bayes | Base/intermedio | Baseline NLP |
| lesson-8-Deep Learning | ANN, CNN, RNN e dati immagine | Intermedio | Progetti DL |
| lesson-9-Dimensionality Reduction | PCA e riduzione supervisionata/non supervisionata | Intermedio | Rappresentazioni |
| lesson-10-Model Selection | Cross-validation e ricerca iperparametri | Intermedio | Selezione corretta |
| Hands On Machine Learning… | Capitoli 2–15 presenti in parte; pipeline, ensemble, personalizzazioni Keras, dati e sequenze | Intermedio/avanzato | Percorso principale pratico |
| apogeo/manning-master | Grokking Machine Learning: regressione, perceptron, Bayes, alberi, ensemble, NN | Base/intermedio | Spiegazioni intuitive e implementazioni |
| mix-exercise | Esercizi trasversali | Da graduare per esercizio | Diagnostica e consolidamento |

## Cheatsheet
OCR effettuato su tutte le pagine, con possibili errori su formule e grafici. 1: rami ML; 2: algoritmi DL; 3: architetture neurali, SOM, autoencoder e RBM; 4: algoritmi AI e MDP; 5: domini data science; 6: ciclo progetto; 7: R/Python; 8: strumenti statistici; 9: competenze data science; 10: sistemi database. Utili al ripasso, insufficienti come programma o prova di competenza. Le trascrizioni OCR restano da verificare visivamente prima di generare domande basate sulle formule.

## Drive: libri e appunti

| Materiale | Evidenza | Uso e cautele |
|---|---|---|
| Hands-On ML, Géron, seconda edizione | Word estratto: frontespizio 2019 e indice ML/DL; PDF e OLD_COPY elencati | Testo principale; confrontare esempi con API attuali. Non usare OLD_COPY come canonico |
| AI and Machine Learning for Coders, Moroney | Word estratto: edizione 2020, TensorFlow, vision, NLP e distribuzione | Dopo basi ML e Géron, come preferenza già espressa |
| Deep Learning with Python, Chollet | Word estratto: copyright 2018, tensori, gradienti, Keras, vision e sequenze | Fondamenti DL; il nome ITA non garantisce testo tradotto: l'estrazione contiene inglese |
| Deep Learning, Goodfellow/Bengio/Courville | Word estratto: algebra, probabilità, ottimizzazione, reti e modelli generativi | Riferimento teorico avanzato, lettura selettiva; anno nel titolo non assunto come edizione verificata |
| Appunti Studi IA | Estratto con EDA, split, leakage, pipeline, CV e tuning | Collegare ai concetti; conservare note originali |
| Esercizi Domande e Risposte | Testo letto: domande introduttive e risposte personali | Generare revisione ragionata; non assumere corrette le risposte |
| Tre PDF Coursera in Certificati | Nomi e metadati elencati | Non dedurre corsi o competenze senza leggere i certificati |
| Stime | Foglio elencato | Contenuto non analizzato in questa versione |

Esempio da correggere nella didattica: la risposta sulla segmentazione con gruppi noti cita «anche Lineare». Con classi note si tratta normalmente di classificazione supervisionata; regressione lineare non è la risposta generale. La correzione deve avere spiegazione e riferimento, conservando la risposta originale.

## Limiti e completamento
Restano da controllare formule/immagini dei libri, equivalenza tra Word/PDF, certificati, foglio Stime e riproducibilità degli esercizi. La futura scansione dovrà escludere cache e log dall'indice didattico mantenendoli nel manifest. Non assegnare percentuali di copertura certificativa dal conteggio dei file. I dati originali restano in sola lettura; ogni adattamento vive in una copia di lavoro separata.
