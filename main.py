"""
Shellino MovieBox Recovery
Flet v0.85 — @ft.component + hooks (use_state, on_mounted)
API interactive : Génération automatique de dossiers, transferts immédiats et Logs.
"""

import os
import subprocess
import asyncio
from datetime import datetime
import flet as ft

# ─── ADB Module ──────────────────────────────────────────────────────────────
def get_adb_devices():
    try:
        result = subprocess.run(
            ["adb", "devices"], capture_output=True, text=True, timeout=5
        )
        lines = result.stdout.strip().split('\n')[1:]
        devices =[]
        for line in lines:
            if line.strip() and '\t' in line:
                device_id, status = line.split('\t')
                devices.append({"id": device_id.strip(), "status": status.strip()})
        return devices
    except Exception as e:
        print(f"ADB Error: {e}")
        return[]

def get_android_files(device_id: str, path: str = "/sdcard/Android/data/"):
    try:
        result = subprocess.run(
            ["adb", "-s", device_id, "shell", "ls", "-p", path],
            capture_output=True, text=True, timeout=10
        )
        files =[]
        lines = result.stdout.strip().split('\n')
        for line in lines:
            if line.strip():
                name = line.rstrip('/')
                if name in ['.', '..']: continue
                is_dir = line.endswith('/')
                full_path = f"{path}{name}" if path.endswith('/') else f"{path}/{name}"
                files.append({
                    "name": name, "is_dir": is_dir, "size": "-", "path": full_path
                })
        return files
    except Exception as e:
        print(f"ADB Files Error: {e}")
        return[]

def search_android_files(device_id: str, path: str, query: str):
    try:
        result = subprocess.run(
            ["adb", "-s", device_id, "shell", "find", path, "-iname", f"'*{query}*'"],
            capture_output=True, text=True, timeout=20
        )
        files =[]
        lines = result.stdout.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith("find:"):
                name = line.split('/')[-1]
                files.append({"name": name, "is_dir": False, "size": "-", "path": line})
        return files
    except Exception:
        return[]

def get_unique_folder_name(device_id: str, base_path: str = "/sdcard/", prefix: str = "Shellino_Export"):
    """Génère un nom de dossier qui n'existe pas encore sur le téléphone."""
    counter = 0
    while True:
        name = prefix if counter == 0 else f"{prefix}_{counter}"
        full_path = f"{base_path.rstrip('/')}/{name}"
        # On demande à ADB si le dossier existe
        res = subprocess.run(
            ["adb", "-s", device_id, "shell", f"if [ -d '{full_path}' ]; then echo 'EXISTS'; else echo 'OK'; fi"],
            capture_output=True, text=True
        )
        if "EXISTS" not in res.stdout:
            return full_path
        counter += 1

def create_adb_folder(device_id: str, full_path: str):
    subprocess.run(["adb", "-s", device_id, "shell", "mkdir", "-p", f'"{full_path}"'])

def delete_adb_files(device_id: str, paths: list):
    for p in paths:
        subprocess.run(["adb", "-s", device_id, "shell", "rm", "-rf", f'"{p}"'])

def copy_adb_files(device_id: str, paths: list, dest: str):
    for p in paths:
        subprocess.run(["adb", "-s", device_id, "shell", "cp", "-r", f'"{p}"', f'"{dest}/"'])

def move_adb_files(device_id: str, paths: list, dest: str):
    for p in paths:
        subprocess.run(["adb", "-s", device_id, "shell", "mv", f'"{p}"', f'"{dest}/"'])


# ─── Palette ─────────────────────────────────────────────────────────────────
C = {
    "bg_main":    "#2b2d30", "bg_sidebar": "#1e1f22", "bg_card":    "#3c3f41",
    "bg_input":   "#2d2f31", "accent":     "#6b9bd2", "accent_lt":  "#8fb3e0",
    "green":      "#5faa5f", "text":       "#d4d4d4", "muted":      "#888888",
    "white":      "#ffffff", "nav_active": "#2c4a6e", "border":     "#4a4d50",
    "header":     "#252628", "hover":      "#44474a", "danger":     "#e74c3c"
}

NAV_ITEMS = [
    ("ADB Devices",  ft.Icons.PHONE_ANDROID_OUTLINED),
    ("Export Queue", ft.Icons.QUEUE_OUTLINED),
    ("Logs",         ft.Icons.ARTICLE_OUTLINED),
]
HEADER_TABS = ["Dashboard", "Settings"]


# ─── Composants Communs ──────────────────────────────────────────────────────
@ft.component
def Logo():
    return ft.Row([
        ft.Container(
            content=ft.Text("S", color=C["white"], size=17, weight=ft.FontWeight.BOLD),
            width=32, height=32, bgcolor=C["accent"], border_radius=8, alignment=ft.Alignment.CENTER,
        ),
        ft.Text("Shellino MovieBox", color=C["white"], size=13, weight=ft.FontWeight.W_600),
    ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER)

@ft.component
def NavItem(label: str, icon, active: bool = False, on_click=None):
    hovered, set_hovered = ft.use_state(False)
    bg = C["nav_active"] if active else (C["hover"] if hovered else "transparent")
    return ft.Container(
        content=ft.Row([
            ft.Icon(icon, color=C["accent"] if active else C["muted"], size=17),
            ft.Text(label, color=C["text"] if active else C["muted"], size=13),
        ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.Padding.symmetric(horizontal=12, vertical=9), border_radius=6, bgcolor=bg,
        border=ft.Border.only(left=ft.BorderSide(3, C["accent"])) if active else None,
        on_hover=lambda e: set_hovered(e.data == "true"), on_click=on_click,
        animate=ft.Animation(120, ft.AnimationCurve.EASE_IN_OUT),
    )

@ft.component
def Sidebar(active_view: str, on_nav_change):
    return ft.Container(
        width=215, bgcolor=C["bg_sidebar"], padding=ft.Padding.symmetric(horizontal=10, vertical=18),
        content=ft.Column([
            ft.Text("Recovery Mode", color=C["white"], size=15, weight=ft.FontWeight.BOLD),
            ft.Text("Connected via ADB", color=C["muted"], size=11),
            ft.Container(height=20),
            *[NavItem(lbl, ico, active=(lbl == active_view), on_click=lambda e, lbl=lbl: on_nav_change(lbl))
              for lbl, ico in NAV_ITEMS],
        ], expand=True, spacing=2),
    )

@ft.component
def HeaderTab(label: str, active: bool = False, on_click=None):
    return ft.Container(
        content=ft.Text(label, color=C["white"] if active else C["muted"], size=13, weight=ft.FontWeight.W_500 if active else ft.FontWeight.NORMAL),
        padding=ft.Padding.symmetric(horizontal=4, vertical=6),
        border=ft.Border.only(bottom=ft.BorderSide(2, C["accent"])) if active else None,
        on_click=on_click,
    )

@ft.component
def Header(active_tab: str, on_tab_change):
    return ft.Container(
        height=50, bgcolor=C["header"], border=ft.Border.only(bottom=ft.BorderSide(1, C["border"])),
        padding=ft.Padding.symmetric(horizontal=18),
        content=ft.Row([
            Logo(), ft.Container(expand=True),
            ft.Row([HeaderTab(tab, active=(tab == active_tab), on_click=lambda e, tab=tab: on_tab_change(tab)) for tab in HEADER_TABS], spacing=18),
            ft.Container(expand=True),
            ft.Container(
                content=ft.Row([ft.Container(width=7, height=7, bgcolor=C["green"], border_radius=4), ft.Text("ADB OK", color=C["text"], size=11)], spacing=5, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=ft.Padding.symmetric(horizontal=10, vertical=5), border_radius=14, border=ft.Border.all(1, C["border"]), bgcolor=C["bg_card"],
            ),
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
    )


# ─── LogsView (Historique des opérations) ────────────────────────────────────
@ft.component
def LogsView(logs):
    log_items =[]
    for log in logs:
        log_items.append(
            ft.Container(
                content=ft.Column([
                    ft.Text(log["time"], color=C["accent"], size=11),
                    ft.Text(log["msg"], color=C["text"], size=13),
                ], spacing=2),
                padding=ft.Padding.all(10), bgcolor=C["bg_card"], border_radius=6, border=ft.Border.all(1, C["border"])
            )
        )
    
    if not log_items:
        log_items.append(ft.Text("Aucun historique pour le moment.", color=C["muted"], size=13))

    return ft.Container(
        expand=True,
        content=ft.Column([
            ft.Text("Historique des Opérations (Logs)", color=C["white"], size=18, weight=ft.FontWeight.BOLD),
            ft.Container(height=10),
            ft.Column(log_items, spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
        ])
    )


# ─── ADB DevicesView (Explorateur Android Avancé) ────────────────────────────
@ft.component
def ADBDevicesView(show_snack, add_log):
    devices, set_devices = ft.use_state([])
    selected_device, set_selected_device = ft.use_state(None)
    android_files, set_android_files = ft.use_state([])
    current_path, set_current_path = ft.use_state("/sdcard/Android/data/")
    
    search_query, set_search_query = ft.use_state("")
    selected_paths, set_selected_paths = ft.use_state(set())
    is_loading, set_is_loading = ft.use_state(False)

    def on_mount():
        set_devices(get_adb_devices())
    ft.on_mounted(on_mount)

    async def refresh_files_async():
        files = await asyncio.to_thread(get_android_files, selected_device, current_path)
        set_android_files(files)
        set_is_loading(False)

    def select_device(device_id):
        set_selected_device(device_id)
        set_selected_paths(set())
        set_android_files(get_android_files(device_id, "/sdcard/Android/data/"))

    def navigate_to_path(path):
        if selected_device:
            set_selected_paths(set())
            set_search_query("")
            set_android_files(get_android_files(selected_device, path))
            set_current_path(path)

    def go_back():
        if selected_device and current_path != "/":
            parent = "/".join(current_path.rstrip('/').split('/')[:-1]) or "/"
            if not parent.endswith('/'): parent += '/'
            navigate_to_path(parent)

    # NOUVEAU: Opération de transfert automatique vers un dossier généré
    async def do_auto_transfer(e, action: str):
        if not selected_device or not selected_paths: return
        set_is_loading(True)

        try:
            # 1. Générer le nom du dossier cible unique
            target_path = await asyncio.to_thread(get_unique_folder_name, selected_device, "/sdcard/", "Shellino_Export")
            
            # 2. Créer ce dossier
            await asyncio.to_thread(create_adb_folder, selected_device, target_path)

            paths_list = list(selected_paths)
            nb_files = len(paths_list)

            # 3. Exécuter l'action demandée
            if action == "copy":
                await asyncio.to_thread(copy_adb_files, selected_device, paths_list, target_path)
                msg = f"{nb_files} fichier(s) copié(s) avec succès dans : {target_path}"
            elif action == "move":
                await asyncio.to_thread(move_adb_files, selected_device, paths_list, target_path)
                msg = f"{nb_files} fichier(s) déplacé(s) avec succès dans : {target_path}"

            # 4. Logger et Notifier
            add_log(msg)
            show_snack(msg)
            
            # 5. Réinitialiser et rafraichir
            set_selected_paths(set())
            await refresh_files_async()
            
        except Exception as ex:
            show_snack(f"Erreur lors du transfert: {ex}")
            set_is_loading(False)

    async def do_delete(e):
        if not selected_device or not selected_paths: return
        set_is_loading(True)
        paths_list = list(selected_paths)
        await asyncio.to_thread(delete_adb_files, selected_device, paths_list)
        msg = f"{len(paths_list)} élément(s) supprimé(s) de {current_path}"
        add_log(msg)
        show_snack(msg)
        set_selected_paths(set())
        await refresh_files_async()

    async def run_deep_search(e):
        q = search_query.strip()
        if not selected_device or not q: return
        set_is_loading(True)
        set_selected_paths(set())
        files = await asyncio.to_thread(search_android_files, selected_device, current_path, q)
        set_android_files(files)
        set_is_loading(False)

    def toggle_select(path):
        new_set = selected_paths.copy()
        if path in new_set: new_set.remove(path)
        else: new_set.add(path)
        set_selected_paths(new_set)

    q_lower = search_query.lower()
    visible_files = [f for f in android_files if q_lower in f["name"].lower() or q_lower in f["path"].lower()]

    def toggle_all(e):
        if len(selected_paths) == len(visible_files) and len(visible_files) > 0:
            set_selected_paths(set())
        else:
            set_selected_paths(set([f["path"] for f in visible_files]))

    # --- UI : Appareils ---
    device_list =[]
    for dev in devices:
        status_color = C["green"] if dev["status"] == "device" else C["muted"]
        device_list.append(
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.PHONE_ANDROID, color=C["accent_lt"], size=20),
                    ft.Column([ft.Text(dev["id"], color=C["white"], size=13, weight=ft.FontWeight.W_600), ft.Text(dev["status"], color=status_color, size=11)], expand=True),
                    ft.Button("Explorer", bgcolor=C["accent"], color=C["white"], on_click=lambda e, dev_id=dev["id"]: select_device(dev_id)) if dev["status"] == "device" else ft.Container(),
                ]), padding=ft.Padding.all(12), bgcolor=C["bg_card"], border_radius=8, border=ft.Border.all(1, C["border"])
            )
        )
    if not device_list:
        device_list.append(ft.Text("Aucun appareil détecté.", color=C["muted"], size=13))

    explorer_ui = ft.Column(spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)

    if selected_device:
        explorer_ui.controls.append(
            ft.Row([
                ft.TextField(
                    label="Rechercher des fichiers", hint_text="Filtre local ou appuyez sur Entrée pour recherche globale ADB",
                    value=search_query, on_change=lambda e: set_search_query(e.control.value), on_submit=run_deep_search,
                    expand=True, border_color=C["border"], bgcolor=C["bg_input"], color=C["text"], border_radius=6, height=45
                ),
                ft.IconButton(icon=ft.Icons.SEARCH, icon_color=C["accent"], on_click=run_deep_search)
            ])
        )

        explorer_ui.controls.append(
            ft.Text(f"Chemin: {current_path}", color=C["muted"], size=11)
        )

        # Barre d'actions contextuelles simplifiée (Boutons automatiques)
        action_bar = ft.Row([
            ft.Checkbox(label="Tout", value=len(selected_paths)>0 and len(selected_paths)==len(visible_files), on_change=toggle_all),
            ft.Text(f"{len(selected_paths)} sélectionné(s)", color=C["accent_lt"], size=13),
            ft.Container(expand=True),
        ])

        if selected_paths:
            action_bar.controls.extend([
                ft.Button("Copier vers /sdcard", icon=ft.Icons.COPY, bgcolor=C["bg_input"], color=C["white"], tooltip="Crée un dossier automatique et copie", on_click=lambda e: asyncio.create_task(do_auto_transfer(e, "copy"))),
                ft.Button("Déplacer vers /sdcard", icon=ft.Icons.DRIVE_FILE_MOVE, bgcolor=C["accent"], color=C["white"], tooltip="Crée un dossier automatique et déplace", on_click=lambda e: asyncio.create_task(do_auto_transfer(e, "move"))),
                ft.Button("Supprimer", icon=ft.Icons.DELETE, bgcolor=C["danger"], color=C["white"], on_click=lambda e: asyncio.create_task(do_delete(e)))
            ])
            
        explorer_ui.controls.append(action_bar)

        if current_path != "/" and not search_query.strip():
            explorer_ui.controls.append(
                ft.Container(
                    content=ft.Row([ft.Icon(ft.Icons.FOLDER_OPEN, color=C["accent_lt"], size=18), ft.Text(".. (Retour)", color=C["text"], size=13)]),
                    padding=ft.Padding.all(10), bgcolor=C["hover"], border_radius=6, on_click=lambda e: go_back()
                )
            )

        if is_loading:
            explorer_ui.controls.append(ft.Row([ft.ProgressRing(width=20, height=20, stroke_width=2), ft.Text("Opération ADB en cours...", color=C["muted"])], alignment=ft.MainAxisAlignment.CENTER))
        else:
            for f in visible_files[:100]:
                icon = ft.Icons.FOLDER if f["is_dir"] else ft.Icons.DESCRIPTION
                explorer_ui.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Checkbox(value=f["path"] in selected_paths, on_change=lambda e, p=f["path"]: toggle_select(p)),
                            ft.Icon(icon, color=C["accent_lt"] if f["is_dir"] else C["muted"], size=18),
                            ft.Column([
                                ft.Text(f["name"], color=C["text"], size=13, weight=ft.FontWeight.W_500),
                                ft.Text(f["path"] if search_query else f["size"], color=C["muted"], size=11),
                            ], expand=True),
                        ]), padding=ft.Padding.symmetric(horizontal=10, vertical=4), bgcolor=C["hover"] if f["is_dir"] else "transparent", border_radius=6,
                        on_click=lambda e, file=f: navigate_to_path(file["path"]) if file["is_dir"] else toggle_select(file["path"])
                    )
                )

    return ft.Container(
        expand=True,
        content=ft.Column([
            ft.Text("Explorateur ADB Android", color=C["white"], size=18, weight=ft.FontWeight.BOLD),
            ft.Column(device_list, spacing=8),
            ft.Divider(height=20, color=C["border"]),
            explorer_ui,
        ], spacing=0, expand=True),
    )


# ─── SettingsView ────────────────────────────────────────────────────────────
@ft.component
def SettingsView():
    return ft.Container(
        expand=True,
        content=ft.Column([
            ft.Text("Paramètres", color=C["white"], size=18, weight=ft.FontWeight.BOLD),
            ft.Container(height=14),
            ft.Text("La configuration se fait désormais directement sur l'appareil Android.", color=C["muted"], size=13)
        ]),
    )


# ─── App Principale ──────────────────────────────────────────────────────────
@ft.component
def App():
    page = ft.context.page
    active_tab, set_active_tab = ft.use_state("Dashboard")
    active_nav, set_active_nav = ft.use_state("ADB Devices")
    
    # État global pour les logs
    logs, set_logs = ft.use_state([])

    snackbar = ft.SnackBar(content=ft.Text(""), bgcolor=C["bg_card"], duration=5000)

    def on_mount():
        page.title = "Shellino MovieBox Manager"
        page.bgcolor = C["bg_main"]
        page.padding = 0
        page.snack_bar = snackbar

    ft.on_mounted(on_mount)

    def show_snackbar(msg: str):
        snackbar.content = ft.Text(msg, color=C["white"])
        snackbar.open = True
        page.update()

    def add_log(msg: str):
        time_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        set_logs(lambda prev: [{"time": time_str, "msg": msg}] + prev)

    def render_content():
        if active_tab == "Dashboard":
            if active_nav == "ADB Devices":
                return ADBDevicesView(show_snack=show_snackbar, add_log=add_log)
            elif active_nav == "Logs":
                return LogsView(logs=logs)
            return ft.Text("Menu en cours de développement...", color=C["muted"])
        elif active_tab == "Settings":
            return SettingsView()
        return ft.Text("Vue non disponible", color=C["white"])

    return ft.Column(
        controls=[
            Header(active_tab, set_active_tab),
            ft.Row([
                Sidebar(active_nav, set_active_nav),
                ft.VerticalDivider(width=1, color=C["border"]),
                ft.Container(expand=True, padding=ft.Padding.symmetric(horizontal=18, vertical=12), content=render_content()),
            ], expand=True, spacing=0, vertical_alignment=ft.CrossAxisAlignment.STRETCH),
        ], spacing=0, expand=True,
    )

def main(page: ft.Page):
    page.render(App)

if __name__ == "__main__":
    ft.run(main)