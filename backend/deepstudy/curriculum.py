"""Percorso v0.1. Le ore sono stime del documento, non una quota personale."""
from __future__ import annotations

CURRICULUM_VERSION = "v0.1"
HOURS_NOTE = (
    "Le ore indicate sono stime del documento v0.1, non una quota settimanale personale. "
    "La quota non è stata fissata: il passo successivo segue prerequisiti, errori e ripassi."
)

UNITS = (
    {
        "id": "c00",
        "title": "Diagnostica",
        "prerequisites": (),
        "estimate": "4–6",
        "summary": "Verifica Python, dati e idea di generalizzazione prima di attribuire padronanza al machine learning.",
        "explanation": "Aprire un file o possedere un certificato non dimostra un obiettivo. Un tentativo corretto su un quesito nuovo conta come prova, separata dalla lettura.",
    },
    {
        "id": "c01",
        "title": "Fondamenti quantitativi",
        "prerequisites": ("c00",),
        "estimate": "20–30",
        "summary": "Algebra, probabilità e gradiente, con una regressione spiegata passo per passo.",
        "explanation": "Per minimizzare un costo ci si muove nel verso opposto al gradiente: il gradiente indica la salita più ripida, non la direzione del passo di discesa.",
    },
    {
        "id": "c02",
        "title": "Dati e pipeline",
        "prerequisites": ("c01",),
        "estimate": "20–30",
        "summary": "Split riproducibile e trasformazioni adattate solo sui dati di training.",
        "explanation": "Lo scaler e le altre trasformazioni si adattano sul training. Calcolarli sull'intero dataset prima dello split fa trapelare informazione del test.",
    },
    {
        "id": "c03",
        "title": "ML supervisionato",
        "prerequisites": ("c02",),
        "estimate": "35–50",
        "summary": "Confronto fra regressione, classificazione e una baseline semplice.",
        "explanation": "Un modello più grande si giudica contro una baseline riproducibile. Senza quel confronto, l'accuratezza da sola non dice se il modello è utile.",
    },
    {
        "id": "c04",
        "title": "Valutazione e tuning",
        "prerequisites": ("c03",),
        "estimate": "20–30",
        "summary": "Validazione per scegliere, holdout finale tenuto fuori dalle decisioni.",
        "explanation": "La cross-validation serve a confrontare scelte. L'holdout finale non si usa per ritoccare soglie o iperparametri.",
    },
    {
        "id": "c05",
        "title": "Non supervisionato",
        "prerequisites": ("c04",),
        "estimate": "15–25",
        "summary": "Clustering e riduzione di dimensione, con un criterio di stabilità.",
        "explanation": "Un cluster non ha un'accuratezza etichettata. Si motiva la segmentazione e si controlla se i gruppi restano stabili al variare del seme.",
    },
    {
        "id": "c06",
        "title": "Fondamenti di deep learning",
        "prerequisites": ("c04",),
        "estimate": "30–45",
        "summary": "Reti, regolarizzazione e lettura di una learning curve.",
        "explanation": "La learning curve confronta errore di training e di validazione nel tempo. La loss di una sola epoca non basta a dire che la rete generalizza.",
    },
    {
        "id": "c07",
        "title": "Vision e sequenze",
        "prerequisites": ("c06",),
        "estimate": "30–45",
        "summary": "Immagini con split controllato e serie temporali in ordine cronologico.",
        "explanation": "In una serie temporale lo split mescola il futuro nel training se è casuale. Lo split cronologico tiene il passato per addestrare e il futuro per valutare.",
    },
    {
        "id": "c08",
        "title": "NLP e AI generativa",
        "prerequisites": ("c06",),
        "estimate": "30–45",
        "summary": "Classificazione di testo e risposte ancorate a passaggi recuperati.",
        "explanation": "Una risposta generativa senza un passaggio recuperato che la sostenga va sospesa. La citazione deve corrispondere al brano, non a un titolo inventato.",
    },
    {
        "id": "c09",
        "title": "PyTorch",
        "prerequisites": ("c06",),
        "estimate": "15–25",
        "summary": "Training loop, checkpoint e inferenza, distinti dalla generalizzazione.",
        "explanation": "Un checkpoint è lo stato salvato dei pesi. Riuscire a ricaricarlo non dimostra che il modello funzioni su dati nuovi.",
    },
    {
        "id": "c10",
        "title": "MLOps e sicurezza",
        "prerequisites": ("c04",),
        "estimate": "30–45",
        "summary": "Rilascio, monitoraggio e rollback. La parte generativa arriva dopo il modulo NLP.",
        "explanation": "Un rilascio prevede un modo per tornare indietro. Il monitoraggio non riaddestra da solo sulle etichette di produzione senza una regola esplicita.",
    },
    {
        "id": "c11",
        "title": "Percorso certificazione",
        "prerequisites": ("c10",),
        "estimate": "35–60",
        "summary": "Spazio per un blueprint ufficiale, ancora non scelto.",
        "explanation": "Un file, un badge o un certificato non letto non copre un obiettivo d'esame. La certificazione prioritaria non è stata scelta.",
    },
    {
        "id": "c12",
        "title": "Consolidamento e simulazioni",
        "prerequisites": ("c11",),
        "estimate": "10–20",
        "summary": "Simulazioni separate dallo studio e revisione dei gap, senza stimare la promozione.",
        "explanation": "Il punteggio di una simulazione descrive quel tentativo. Non è una probabilità di superare un esame, finché non esiste una calibrazione.",
    },
)

QUESTIONS = (
    {
        "id": "q-study-c00-memoria",
        "objective_id": "c00",
        "kind": "single",
        "bank": "study",
        "family": "studio-c00",
        "prompt": "Un programma che ripete sul test gli stessi esempi visti nel foglio sta dimostrando soprattutto:",
        "options": (("a", "generalizzazione su casi nuovi"), ("b", "memorizzazione degli esempi già visti")),
        "solution": ("b",),
        "rationale": "Ripetere gli esempi del foglio non è generalizzazione. La prova utile usa quesiti diversi da quelli studiati.",
    },
    {
        "id": "q-study-c00-leak",
        "objective_id": "c00",
        "kind": "multi",
        "bank": "study",
        "family": "studio-c00",
        "prompt": "Quali due controlli riducono il leakage in una pipeline tabellare?",
        "options": (
            ("a", "Adattare lo scaler solo sul training"),
            ("b", "Calcolare media e varianza sull'intero dataset prima dello split"),
            ("c", "Tenere un holdout finale fuori dalla scelta del modello"),
            ("d", "Scegliere la soglia guardando le etichette del test"),
        ),
        "solution": ("a", "c"),
        "rationale": "Lo scaler va adattato sul training e l'holdout non partecipa alle scelte. Usare il test per medie o soglie fa trapelare informazione.",
    },
    {
        "id": "q-card-c00",
        "objective_id": "c00",
        "kind": "flashcard",
        "bank": "flashcard",
        "family": "studio-c00",
        "prompt": "Come si chiama l'uso di informazioni del test durante l'addestramento o la scelta del modello?",
        "options": (),
        "solution": ("leakage",),
        "rationale": "Il termine tecnico è leakage: informazione che non sarebbe disponibile al momento della previsione entra nella pipeline.",
    },
    {
        "id": "q-study-c01",
        "objective_id": "c01",
        "kind": "single",
        "bank": "study",
        "family": "studio-c01",
        "prompt": "Per ridurre un costo differenziabile, il passo di aggiornamento si muove:",
        "options": (("a", "nello stesso verso del gradiente"), ("b", "nel verso opposto al gradiente")),
        "solution": ("b",),
        "rationale": "Il gradiente indica la salita più ripida. La discesa fa un passo nel verso opposto.",
    },
    {
        "id": "q-study-c02",
        "objective_id": "c02",
        "kind": "single",
        "bank": "study",
        "family": "studio-c02",
        "prompt": "Quando va adattato uno scaler in una pipeline supervisionata?",
        "options": (("a", "Prima dello split, su tutti i dati"), ("b", "Dopo lo split, solo sul training")),
        "solution": ("b",),
        "rationale": "Adattare lo scaler prima dello split usa statistiche del test. Si adatta sul training e si applica al resto.",
    },
    {
        "id": "q-study-c03",
        "objective_id": "c03",
        "kind": "single",
        "bank": "study",
        "family": "studio-c03",
        "prompt": "Prima di dichiarare utile un modello più complesso, che confronto serve?",
        "options": (("a", "Una baseline semplice e riproducibile"), ("b", "Solo l'accuratezza sul training")),
        "solution": ("a",),
        "rationale": "Senza baseline non si capisce se la complessità aggiunge qualcosa. L'accuratezza di training da sola non basta.",
    },
    {
        "id": "q-study-c04",
        "objective_id": "c04",
        "kind": "single",
        "bank": "study",
        "family": "studio-c04",
        "prompt": "A che serve l'holdout finale rispetto alla cross-validation?",
        "options": (("a", "A scegliere gli iperparametri a ogni giro"), ("b", "A una verifica tenuta fuori dalle scelte")),
        "solution": ("b",),
        "rationale": "La validazione confronta le scelte. L'holdout resta fermo finché quelle scelte non sono chiuse.",
    },
    {
        "id": "q-study-c05",
        "objective_id": "c05",
        "kind": "single",
        "bank": "study",
        "family": "studio-c05",
        "prompt": "Che controllo è appropriato per un clustering senza etichette?",
        "options": (("a", "L'accuratezza rispetto alle classi vere"), ("b", "La stabilità dei gruppi al variare del seme")),
        "solution": ("b",),
        "rationale": "Senza etichette non c'è un'accuratezza di classe. Si guarda se la segmentazione resta stabile e se è motivata.",
    },
    {
        "id": "q-study-c06",
        "objective_id": "c06",
        "kind": "single",
        "bank": "study",
        "family": "studio-c06",
        "prompt": "Che cosa mostra una learning curve utile?",
        "options": (("a", "Errore di training e di validazione nel tempo"), ("b", "Solo la loss dell'ultima batch")),
        "solution": ("a",),
        "rationale": "Il confronto tra training e validazione nel tempo dice se la rete sta memorizzando o sta ancora migliorando sui dati non usati per il passo.",
    },
    {
        "id": "q-study-c07",
        "objective_id": "c07",
        "kind": "single",
        "bank": "study",
        "family": "studio-c07",
        "prompt": "Come si divide una serie temporale per una valutazione onesta?",
        "options": (("a", "Con uno split casuale delle righe"), ("b", "In ordine cronologico, futuro nel test")),
        "solution": ("b",),
        "rationale": "Lo split casuale mette il futuro nel training. L'ordine cronologico rispetta l'informazione disponibile al momento della previsione.",
    },
    {
        "id": "q-study-c08",
        "objective_id": "c08",
        "kind": "single",
        "bank": "study",
        "family": "studio-c08",
        "prompt": "Se nessun passaggio recuperato sostiene la risposta, il tutor deve:",
        "options": (("a", "completare con una spiegazione plausibile"), ("b", "astenersi e dirlo")),
        "solution": ("b",),
        "rationale": "Senza un brano che sostiene la risposta non si inventa il contenuto. L'astensione è il risultato corretto.",
    },
    {
        "id": "q-study-c09",
        "objective_id": "c09",
        "kind": "single",
        "bank": "study",
        "family": "studio-c09",
        "prompt": "Un checkpoint ricaricato con successo dimostra che:",
        "options": (("a", "lo stato dei pesi è stato salvato e riletto"), ("b", "il modello generalizza su dati nuovi")),
        "solution": ("a",),
        "rationale": "Il checkpoint è uno stato salvato. La generalizzazione richiede una valutazione su dati non usati per costruirlo.",
    },
    {
        "id": "q-study-c10",
        "objective_id": "c10",
        "kind": "single",
        "bank": "study",
        "family": "studio-c10",
        "prompt": "Che elemento accompagna un rilascio di modello oltre al monitoraggio?",
        "options": (("a", "Un rollback eseguibile"), ("b", "Il riaddestramento automatico su ogni etichetta di produzione")),
        "solution": ("a",),
        "rationale": "Il rollback permette di tornare a uno stato precedente. Riaddestrare da solo sulle etichette di produzione non è una regola di rilascio.",
    },
    {
        "id": "q-study-c11",
        "objective_id": "c11",
        "kind": "single",
        "bank": "study",
        "family": "studio-c11",
        "prompt": "Un badge o un PDF di certificato non letto, nel percorso, conta come:",
        "options": (("a", "copertura degli obiettivi d'esame"), ("b", "nessuna evidenza di obiettivo")),
        "solution": ("b",),
        "rationale": "Il file non è stato confrontato con un blueprint. Non attribuisce padronanza né copertura d'esame.",
    },
    {
        "id": "q-study-c12",
        "objective_id": "c12",
        "kind": "single",
        "bank": "study",
        "family": "studio-c12",
        "prompt": "Il punteggio di una simulazione, da solo, rappresenta:",
        "options": (("a", "l'esito di quel tentativo"), ("b", "la probabilità di superare l'esame")),
        "solution": ("a",),
        "rationale": "Senza una calibrazione su dati adeguati il punteggio non è una probabilità di promozione.",
    },
)

MOCK_QUESTIONS = (
    {
        "id": "q-mock-c00",
        "objective_id": "c00",
        "kind": "single",
        "bank": "mock",
        "family": "mock-c00",
        "prompt": "Perché si calcola una baseline prima di un modello più grande?",
        "options": (("a", "Per avere un confronto riproducibile"), ("b", "Perché la baseline sostituisce la metrica")),
        "solution": ("a",),
        "rationale": "La baseline è il confronto. Non sostituisce la metrica scelta per il problema.",
    },
    {
        "id": "q-mock-c04",
        "objective_id": "c04",
        "kind": "single",
        "bank": "mock",
        "family": "mock-c04",
        "prompt": "Durante una simulazione d'esame, quando si vede il punteggio per dominio?",
        "options": (("a", "Dopo ogni domanda, come suggerimento"), ("b", "Solo a simulazione chiusa")),
        "solution": ("b",),
        "rationale": "La simulazione non mostra suggerimenti né punteggio mentre è aperta. Il rapporto arriva alla chiusura.",
    },
    {
        "id": "q-mock-c12",
        "objective_id": "c12",
        "kind": "single",
        "bank": "mock",
        "family": "mock-c12",
        "prompt": "La banca di una simulazione rispetto ai quesiti di studio deve essere:",
        "options": (("a", "lo stesso testo, così il punteggio sale"), ("b", "un insieme distinto, anche sullo stesso obiettivo")),
        "solution": ("b",),
        "rationale": "Studio e simulazione non condividono le stesse domande. Condividere il testo misura la memoria del quesito.",
    },
)

LOCAL_BLUEPRINT = {
    "id": "bp-locale-nessuna",
    "provider": "locale",
    "code": "NESSUNA",
    "version": "2026-11-26",
    "checked_at": "2026-11-26",
    "source": "Nessuna certificazione scelta (L03 aperta). Domande originali di prova, non un esame e non un dump.",
    "status": "bozza",
}


def unit(objective_id: str) -> dict:
    found = next((item for item in UNITS if item["id"] == objective_id), None)
    if not found:
        raise KeyError(objective_id)
    return found


def ensure_curriculum(db) -> None:
    for item in UNITS:
        db.execute(
            "INSERT OR IGNORE INTO objectives(id, curriculum_version, title) VALUES(?,?,?)",
            (item["id"], CURRICULUM_VERSION, item["title"]),
        )
    for item in UNITS:
        for prerequisite in item["prerequisites"]:
            db.execute(
                "INSERT OR IGNORE INTO prerequisites(objective_id, prerequisite_id) VALUES(?,?)",
                (item["id"], prerequisite),
            )


def _insert_question(db, item: dict) -> None:
    if db.execute("SELECT 1 FROM question_versions WHERE id=?", (item["id"],)).fetchone():
        return
    options = [{"id": key, "text": text} for key, text in item["options"]]
    import json
    db.execute(
        """INSERT INTO question_versions(id, objective_id, prompt, options, solution, rationale, sources, review)
           VALUES(?,?,?,?,?,?,?,?)""",
        (
            item["id"],
            item["objective_id"],
            item["prompt"],
            json.dumps(options, ensure_ascii=False),
            json.dumps(list(item["solution"]), ensure_ascii=False),
            item["rationale"],
            "[]",
            "reviewed",
        ),
    )
    db.execute(
        """INSERT INTO question_meta(question_version_id, bank, family, kind, origin)
           VALUES(?,?,?,?,?)""",
        (item["id"], item["bank"], item["family"], item["kind"], "authored"),
    )


def ensure_study_questions(db) -> None:
    ensure_curriculum(db)
    for item in QUESTIONS:
        _insert_question(db, item)


def ensure_mock_bank(db) -> None:
    ensure_curriculum(db)
    for item in MOCK_QUESTIONS:
        _insert_question(db, item)
    if db.execute("SELECT 1 FROM exam_blueprints WHERE id=?", (LOCAL_BLUEPRINT["id"],)).fetchone():
        return
    db.execute(
        """INSERT INTO exam_blueprints(id, provider, code, version, checked_at, source, status)
           VALUES(:id,:provider,:code,:version,:checked_at,:source,:status)""",
        LOCAL_BLUEPRINT,
    )
    for position, item in enumerate(MOCK_QUESTIONS):
        db.execute(
            "INSERT INTO blueprint_questions(blueprint_id, position, question_version_id) VALUES(?,?,?)",
            (LOCAL_BLUEPRINT["id"], position, item["id"]),
        )
