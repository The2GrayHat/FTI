#!/usr/bin/env python3
# main.py - Launcher + cli-universal integrated (complete)
# Save this file as main.py. Put your other .py scripts inside ./options/
# Dependencies (recommended):
#   pip install yt-dlp requests beautifulsoup4
#   pip install telethon   # optional, only if you want Telegram search
#   sudo apt install mpv

import os
import sys
import subprocess
import tempfile
import re
from urllib.parse import quote_plus

# Optional imports
try:
    import yt_dlp
except Exception:
    yt_dlp = None

try:
    import requests
    from bs4 import BeautifulSoup
except Exception:
    requests = None
    BeautifulSoup = None

try:
    from telethon import TelegramClient
except Exception:
    TelegramClient = None

# ---------------- CONFIG ----------------
PAGE_SIZE = 10
OPTIONS_DIR = "options"
TG_CONFIG_FILE = "tg_config.txt"   # optional file with api_id and api_hash (two lines)
MPV_COMMAND = "mpv"                # change if needed
SEARCH_LIMIT_PER_SITE = 80
TEMP_DIR = os.path.join(tempfile.gettempdir(), "ani_cli_universal_cache")
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR, exist_ok=True)
# ----------------------------------------

BANNER = r"""
                                                 
                                                 
                                                 
                         
 ▄▄▄▄▄▄▄ ▄▄▄▄▄▄▄▄▄ ▄▄▄▄▄ 
███▀▀▀▀▀ ▀▀▀███▀▀▀  ███  
███▄▄       ███     ███  
███▀▀       ███     ███  
███         ███    ▄███▄ 
                         
                         
                                                          
                                                 
                                                 
                                                 
"""

# ----------------- MENU (script launcher) -----------------
def ensure_options_dir():
    if not os.path.exists(OPTIONS_DIR):
        os.makedirs(OPTIONS_DIR)

def listar_scripts():
    ensure_options_dir()
    files = [os.path.join(OPTIONS_DIR, f) for f in os.listdir(OPTIONS_DIR) if f.endswith(".py")]
    files.sort()
    return files

def mostrar_pagina(scripts, page):
    os.system('cls' if os.name == 'nt' else 'clear')
    print(BANNER)
    print("=== XS MENU — Página {} ===\n".format(page + 1))

    total_pages = (len(scripts) - 1) // PAGE_SIZE + 1 if scripts else 1
    page_items = scripts[page * PAGE_SIZE: page * PAGE_SIZE + PAGE_SIZE]

    if not scripts:
        print("No hay scripts en 'options/'. Pon .py dentro de ./options/ y presiona R para refrescar.\n")
    else:
        for i, script in enumerate(page_items, start=1):
            print(f"{i}. {os.path.basename(script)}")

    # special option appended at end of the page view
    print(f"{len(page_items) + 1}. MultiStreamingUniversalV5")
    print(f"\nPágina {page+1} de {total_pages}")
    print("Usa número | B=Siguiente | P=Anterior | R=Refrescar | Q=Salir")

def ejecutar_script(filepath):
    print(f"\nEjecutando: {filepath}\n--- espere... ---\n")
    try:
        subprocess.run([sys.executable, filepath], check=False)
    except Exception as e:
        print(f"\nError ejecutando '{filepath}': {e}")
    input("\nENTER para volver al menú...")

# ----------------- streaming-universal implementation -----------------
def sane_name(title: str) -> str:
    t = re.sub(r"[\[\(].*?[\]\)]", "", title)
    t = re.sub(r"(?i)\b(official|subbed|sub|full|trailer|hd|1080p|720p)\b", "", t)
    t = re.sub(r"\s*[-–|]\s*.*$", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

def extract_episode_number(title: str):
    patterns = [
        r'(?i)\b(?:episodio|ep|ep\.|cap[ií]tulo|cap)\s*#?\s*(\d{1,4})\b',
        r'(?i)\bS?(\d{1,2})[xE ]+(\d{1,3})\b',
        r'(?i)\bepisode\s*(\d{1,4})\b',
    ]
    for p in patterns:
        m = re.search(p, title)
        if m:
            if len(m.groups()) >= 2 and m.group(2) and m.group(2).isdigit():
                return int(m.group(2))
            for g in m.groups():
                if g and g.isdigit():
                    return int(g)
    m = re.search(r'(\d{1,4})', title)
    if m:
        n = int(m.group(1))
        if 0 < n < 10000:
            return n
    return None

def ddg_search_site(site_domain: str, query: str, max_results=50):
    if requests is None or BeautifulSoup is None:
        return []
    q = f"site:{site_domain} {query}"
    url = "https://duckduckgo.com/html/?q=" + quote_plus(q)
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        r.raise_for_status()
    except Exception:
        return []
    soup = BeautifulSoup(r.text, "html.parser")
    out = []
    for a in soup.select("a.result__a")[:max_results]:
        title = a.get_text(strip=True)
        href = a.get("href")
        if title and href:
            out.append((title, href))
    return out

def yt_search_titles(query: str, limit=50):
    out = []
    if yt_dlp is None:
        return out
    ydl_opts = {'quiet': True, 'skip_download': True, 'extract_flat': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
            entries = info.get('entries') or []
            for e in entries:
                title = e.get('title') or ""
                url = e.get('webpage_url') or (f"https://www.youtube.com/watch?v={e.get('id')}" if e.get('id') else None)
                if title and url:
                    out.append((title, url))
        except Exception:
            return out
    return out

def search_universal(query: str, limit_per_site=SEARCH_LIMIT_PER_SITE):
    grouped = {}
    query = query.strip()
    # YouTube via yt-dlp
    if yt_dlp is not None:
        try:
            yts = yt_search_titles(f"{query} episodio OR capitulo OR temporada", limit=limit_per_site)
            for title, url in yts:
                ep = extract_episode_number(title)
                if not ep:
                    continue
                name = sane_name(title)
                grouped.setdefault(name, {}).setdefault(ep, []).append((title, url, "youtube"))
        except Exception:
            pass
    # other domains via DuckDuckGo
    domains = [
        ("Dailymotion", "dailymotion.com/video"),
        ("Vimeo", "vimeo.com"),
        ("BiliBili", "bilibili.com"),
        ("SoundCloud", "soundcloud.com"),
    ]
    if requests is not None and BeautifulSoup is not None:
        for site_name, domain in domains:
            try:
                hits = ddg_search_site(domain, query, max_results=limit_per_site)
                for title, href in hits:
                    ep = extract_episode_number(title)
                    if not ep:
                        continue
                    name = sane_name(title)
                    grouped.setdefault(name, {}).setdefault(ep, []).append((title, href, site_name.lower()))
            except Exception:
                continue
    # Telegram (optional)
    if TelegramClient is not None and os.path.exists(TG_CONFIG_FILE):
        try:
            with open(TG_CONFIG_FILE, "r", encoding="utf8") as fh:
                lines = [l.strip() for l in fh.read().splitlines() if l.strip()]
            api_id = int(lines[0])
            api_hash = lines[1]
            client = TelegramClient("ani_cli_universal_tg", api_id, api_hash)
            client.start()
            import asyncio
            tg_entries = []
            async def _iter():
                async for msg in client.iter_messages(None, search=query, limit=100):
                    text = (msg.message or "")
                    url = ""
                    if msg.media and getattr(msg, "web_preview", None):
                        wp = getattr(msg, "web_preview", None)
                        url = getattr(wp, "url", "") if wp else ""
                    if not url and getattr(msg, "chat_id", None):
                        if str(msg.chat_id).startswith("-100"):
                            url = f"https://t.me/c/{str(msg.chat_id)[4:]}/{msg.id}"
                        else:
                            url = f"https://t.me/{getattr(msg.chat, 'username', '')}/{msg.id}"
                    if extract_episode_number(text):
                        tg_entries.append((text.replace("\n", " "), url or f"t.me message {msg.id}", "telegram"))
                await client.disconnect()
            asyncio.get_event_loop().run_until_complete(_iter())
            for title, href, site in tg_entries:
                ep = extract_episode_number(title)
                if not ep:
                    continue
                name = sane_name(title)
                grouped.setdefault(name, {}).setdefault(ep, []).append((title, href, "telegram"))
        except Exception:
            pass
    return grouped

def present_and_play(grouped):
    if not grouped:
        print("\n⚠️ No se encontraron episodios numerados en las fuentes buscadas.")
        input("ENTER para volver...")
        return
    names = sorted(grouped.keys(), key=lambda s: s.lower())
    print("\nSeries encontradas:\n")
    for i, name in enumerate(names, start=1):
        eps_count = len(grouped[name])
        print(f"[{i}] {name} ({eps_count} episodios detectados)")
    try:
        s_idx = int(input("\nSelecciona serie (num): ").strip()) - 1
    except Exception:
        print("Entrada inválida.")
        input("ENTER para volver...")
        return
    if s_idx < 0 or s_idx >= len(names):
        print("Índice fuera de rango.")
        input("ENTER para volver...")
        return
    sel_name = names[s_idx]
    ep_nums = sorted(grouped[sel_name].keys())
    print(f"\nEpisodios de {sel_name}:\n")
    for ep in ep_nums:
        entries = grouped[sel_name][ep]
        entries_sorted = sorted(entries, key=lambda e: (0 if 'youtube' in e[2].lower() else 1, len(e[0])))
        title_show = entries_sorted[0][0]
        print(f"  {ep:03d}. {title_show}")
    try:
        e_sel = int(input("\nSelecciona episodio (número de episodio): ").strip())
    except Exception:
        print("Entrada inválida.")
        input("ENTER para volver...")
        return
    if e_sel not in grouped[sel_name]:
        print("Episodio no encontrado.")
        input("ENTER para volver...")
        return
    candidates = grouped[sel_name][e_sel]
    chosen = sorted(candidates, key=lambda e: (0 if 'youtube' in e[2].lower() else 1, len(e[0])))[0]
    chosen_title, chosen_url, chosen_site = chosen
    print(f"\n▶ Reproduciendo: {chosen_title} ({chosen_site})\n")
    try:
        subprocess.run([MPV_COMMAND, chosen_url])
    except FileNotFoundError:
        print("mpv no encontrado. Instala mpv o cambia MPV_COMMAND en el script.")
    except Exception as e:
        print("Error lanzando mpv:", e)
    input("\nENTER para volver al menú...")

def ani_cli_universal_interactive():
    os.system('cls' if os.name == 'nt' else 'clear')
    print("===-MultiStreamingV5-===\n")
    q = input("Buscar (anime/serie): ").strip()
    if not q:
        print("Cancelado.")
        input("ENTER para volver...")
        return
    print("\nBuscando (esto puede tardar unos segundos)...")
    grouped = search_universal(q, limit_per_site=SEARCH_LIMIT_PER_SITE)
    present_and_play(grouped)

# ----------------- MAIN -----------------
def main():
    page = 0
    while True:
        scripts = listar_scripts()
        total_pages = max(1, (len(scripts) - 1) // PAGE_SIZE + 1)
        if page < 0:
            page = 0
        if page >= total_pages:
            page = total_pages - 1
        mostrar_pagina(scripts, page)
        choice = input("\nTu elección: ").strip()
        if not choice:
            continue
        c = choice.upper()
        if c == 'Q':
            print("Saliendo...")
            break
        elif c == 'R':
            continue
        elif c == 'B':
            page += 1
            continue
        elif c == 'P':
            page = max(0, page - 1)
            continue
        elif choice.isdigit():
            num = int(choice)
            page_items = scripts[page * PAGE_SIZE: page * PAGE_SIZE + PAGE_SIZE]
            if num == len(page_items) + 1:
                ani_cli_universal_interactive()
                continue
            elif 1 <= num <= len(page_items):
                idx = page * PAGE_SIZE + (num - 1)
                if 0 <= idx < len(scripts):
                    ejecutar_script(scripts[idx])
                else:
                    print("Número fuera de rango.")
                    input("ENTER para continuar...")
            else:
                print("Número inválido.")
                input("ENTER para continuar...")
        else:
            print("Entrada no reconocida.")
            input("ENTER para continuar...")

if __name__ == "__main__":
    main()
