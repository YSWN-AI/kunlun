#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::{Command, Child};
use std::sync::Mutex;
use tauri::Manager;

struct BackendProcess(Mutex<Option<Child>>);

#[tauri::command]
fn greet(name: &str) -> String {
    format!("你好，{}！昆仑引擎已就绪。", name)
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![greet])
        .setup(|app| {
            // 获取资源目录中的 backend 路径
            let resource_dir = app.path().resource_dir()
                .expect("无法获取资源目录");

            // 开发模式下直接使用项目目录
            let backend_dir = if cfg!(debug_assertions) {
                let mut dir = std::env::current_dir().unwrap();
                dir.push("..");
                dir.push("..");
                dir.push("kunlun");
                dir
            } else {
                resource_dir.join("backend")
            };

            let main_py = backend_dir.join("api").join("main.py");
            if !main_py.exists() {
                println!("后端未找到: {}", main_py.display());
                return Ok(());
            }

            println!("启动后端: python {}", main_py.display());

            let child = Command::new("python")
                .arg(&main_py)
                .current_dir(&backend_dir)
                .env("DEEPSEEK_API_KEY", std::env::var("DEEPSEEK_API_KEY").unwrap_or_default())
                .spawn()
                .expect("昆仑引擎后端启动失败");

            app.manage(BackendProcess(Mutex::new(Some(child))));

            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                if let Some(state) = window.try_state::<BackendProcess>() {
                    if let Ok(mut guard) = state.0.lock() {
                        if let Some(ref mut child) = *guard {
                            let _ = child.kill();
                        }
                    }
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
