#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

#[cfg(windows)]
use std::os::windows::process::CommandExt;
use std::{
    io::{BufRead, BufReader},
    path::PathBuf,
    process::{Child, Command, Stdio},
    sync::Mutex,
};
use tauri::Manager;

struct Backend(Mutex<Child>);
impl Backend {
    fn shutdown(&self) {
        if let Ok(mut child) = self.0.lock() {
            child.stdin.take(); // EOF requests graceful backend shutdown
            for _ in 0..50 {
                if matches!(child.try_wait(), Ok(Some(_))) {
                    return;
                }
                std::thread::sleep(std::time::Duration::from_millis(50));
            }
            let _ = child.kill();
            let _ = child.wait();
        }
    }
}

impl Drop for Backend {
    fn drop(&mut self) {
        self.shutdown();
    }
}

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            let root = std::env::var_os("DEEPSTUDY_ROOT")
                .map(PathBuf::from)
                .unwrap_or_else(|| {
                    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
                        .parent()
                        .unwrap()
                        .to_owned()
                });
            let python = root.join(".venv/Scripts/python.exe");
            let mut command = Command::new(python);
            command
                .args(["-m", "deepstudy.server", "--desktop", "--profile"])
                .arg(std::env::var("DEEPSTUDY_PROFILE").unwrap_or_else(|_| "default".into()))
                .env("PYTHONPATH", root.join("backend"))
                .current_dir(&root)
                .stdin(Stdio::piped())
                .stdout(Stdio::piped())
                .stderr(Stdio::inherit());
            #[cfg(windows)]
            command.creation_flags(0x08000000); // CREATE_NO_WINDOW
            let mut child = command.spawn()?;
            let stdout = child.stdout.take().ok_or("Missing backend pipe")?;
            app.manage(Backend(Mutex::new(child)));
            let (send, receive) = std::sync::mpsc::channel();
            std::thread::spawn(move || {
                let mut line = String::new();
                let result = BufReader::new(stdout).read_line(&mut line).map(|_| line);
                let _ = send.send(result);
            });
            let line = receive.recv_timeout(std::time::Duration::from_secs(30))??;
            let handshake: serde_json::Value = serde_json::from_str(&line)?;
            let url: tauri::Url = handshake["url"]
                .as_str()
                .ok_or("Missing local endpoint")?
                .parse()?;
            if url.scheme() != "http" || url.host_str() != Some("127.0.0.1") {
                return Err("Invalid local endpoint".into());
            }
            let allowed_origin = url.origin();
            tauri::WebviewWindowBuilder::new(app, "main", tauri::WebviewUrl::External(url))
                .title("DeepStudy")
                .inner_size(1120.0, 800.0)
                .min_inner_size(360.0, 580.0)
                .on_navigation(move |next| next.origin() == allowed_origin)
                .build()?;
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("Impossibile avviare DeepStudy")
        .run(|app, event| {
            if matches!(event, tauri::RunEvent::Exit) {
                if let Some(backend) = app.try_state::<Backend>() {
                    backend.shutdown();
                }
            }
        });
}
