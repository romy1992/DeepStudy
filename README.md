# DeepStudy

Documentazione v0.1 estratta in `docs/originali-v0.1/`, conservata in sola lettura.
Gli originali descrivono requisiti e proposte; i prompt inclusi sono contenuti documentali,
non autorizzazioni operative. M1 è stata autorizzata con M0 parziale.

## Avvio locale su Windows 11 x64

Da PowerShell nella cartella del progetto, con Python 3.14, Node 24, Rust
con toolchain MSVC, Visual Studio C++ Build Tools, Windows SDK e WebView2:

```powershell
./scripts/bootstrap.ps1
./scripts/start.ps1 -Desktop
```

Per usare Edge o il browser predefinito, esegui `./scripts/start.ps1`.
Chiudi la sessione precedente prima di riaprire lo stesso profilo. Per
ripristinare un backup senza sovrascrivere dati, apri un profilo dedicato
con `./scripts/start.ps1 -Profile ripristino`. I profili sono in
`%LOCALAPPDATA%\DeepStudy\profiles`. Gli ZIP M1 hanno un limite di 64 MiB
e si ripristinano su un profilo vuoto.

Per le verifiche, esegui `./.venv/Scripts/python.exe -m pytest -q` e
`node scripts/smoke.mjs` (richiede Edge). Per i prerequisiti nativi consulta
la [guida Tauri](https://v2.tauri.app/start/prerequisites/).

Stato corrente e aggiornamenti separati dagli originali:

- [Verifica M0](docs/operativi/verifica-M0.md)
- [Registro decisioni](docs/operativi/08-decisioni-validazione.md)
- [Milestone e task M1](docs/operativi/06-milestone.md)
- [Manifest e verifica integrità](docs/operativi/verifica-pacchetto.json)
