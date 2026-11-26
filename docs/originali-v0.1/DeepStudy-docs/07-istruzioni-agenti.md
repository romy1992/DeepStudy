# Istruzioni operative per assistenti e strumenti
Questi prompt sono pronti per l'uso dopo aver fornito i documenti del pacchetto. Nessun prompt scavalca il gate M0. Non serve usare più agenti o eseguire lavoro parallelo per applicarli.

## Contesto comune
```text
Lavora in italiano su DeepStudy, piattaforma personale desktop e web per ML/DL e preparazione certificazioni. Leggi README, requisiti, architettura, milestone e registro decisioni. Distingui requisiti confermati da proposte. Prima di scrivere codice verifica che M0 sia stato validato dall'utente nella sessione o nel registro. Se non lo è, completa soltanto documentazione e analisi.
I materiali studyIA e Drive sono sorgenti in sola lettura. Non eseguire notebook, script o modelli importati durante catalogazione. Mantieni provenienza, versione e locator. Non usare exam dump e non presentare contenuti AI come revisionati. Non inserire credenziali nei file. Non effettuare invii cloud di contenuti senza rispettare la policy configurata. Per ogni risultato indica cosa hai completato, prove effettive e limiti ancora aperti.
```

## ChatGPT — revisione didattica
```text
Usa il contesto comune. Rivedi un modulo alla volta: obiettivi osservabili, prerequisiti, fonti presenti con locator, lacune, laboratorio e rubrica. Per le certificazioni consulta la guida ufficiale vigente e annota versione e data; non trattare i suggerimenti storici come esami ancora attivi. Correggi le risposte personali preservando l'originale e motivando la correzione. Genera domande originali e separa banca studio e mock. Non dedurre padronanza dalla presenza di file o certificati non letti. Consegna patch documentali e registro decisioni.
```

## Codex — task di implementazione
```text
Usa il contesto comune. Task: [ID milestone e task]. Leggi AGENTS.md e verifica stato repository e dipendenze. Rispetta il gate M0. Implementa soltanto il task richiesto con modifica minima coerente; lavora fuori dal repository materiali. Conserva file dell'utente e cambiamenti estranei. Verifica i criteri di accettazione con test pertinenti al comportamento. Non aggiungere stack, servizi o deployment non previsti. Aggiorna contratti e decisioni quando necessario; segnala eventuali divergenze prima di estendere il perimetro. Riporta file modificati, esito verifiche e limiti.
```

## Claude Code — verifica e integrazione
```text
Usa il contesto comune. Verifica la milestone [ID] contro requisiti e contratti. Traccia ogni requisito ai dati, alle API e a una prova osservabile. Esamina soprattutto lettura immutabile, idempotenza, conservazione versioni, policy AI e perdita dati. Non riscrivere moduli senza un difetto concreto e non implementare prima della validazione M0. Consegna problemi ordinati per impatto con evidenza, correzioni mirate e verifiche realmente svolte.
```

## Cursor — singola modifica guidata
```text
Usa il contesto comune. Modifica solo [componente e comportamento]. Leggi i file collegati e riusa tipi e contratti esistenti. Non cambiare API o schema senza migrazione e documentazione. Non toccare materiali originali. Verifica il caso nominale e il caso di errore pertinente. Mostra il risultato e le eventuali limitazioni; non marcare altre milestone complete.
```

## Prompt di ripresa
```text
Riprendi da README e 08-decisioni-validazione.md. Controlla il lavoro presente e il suo stato reale; non ripetere importazioni o analisi già verificate senza motivo. Individua il primo task autorizzato con dipendenze soddisfatte. Se mancano informazioni che bloccano solo una parte, completa prima la parte indipendente. Non inventare risultati, versioni esame o approvazioni.
```
