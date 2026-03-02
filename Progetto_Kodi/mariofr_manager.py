import urllib3
import os
import time
import json
import hashlib
import zipfile
from urllib3.util.retry import Retry
from urllib.parse import unquote

# --- CONFIGURAZIONE UTENTE ---
USER = "riccamariofrancesco-cell"
REPO = "mariofr-repo"
INPUT_FILE = "links.txt"
PLAYLIST_JSON = "playlist.json"
ADDON_ID = "plugin.video.mariofr"
REPO_ID = "repository.mariofr"

# --- CONFIGURAZIONE RETE (IDENTICA AL TUO VECCHIO PYTHON) ---
RITARDO_TRA_LINK = 5
retry_strategy = Retry(
    total=15,
    redirect=20,
    backoff_factor=2,
    status_forcelist=[429, 500, 502, 503, 504]
)

http = urllib3.PoolManager(
    timeout=urllib3.Timeout(connect=15.0, read=30.0), 
    retries=retry_strategy
)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7',
    'Connection': 'keep-alive'
}

def format_channel_name(slug):
    """Trasforma lo slug del link in un nome leggibile (Logica originale)."""
    name = slug.replace("extra", " EXTRA").replace("ucl", " UCL").replace("ch", " CH").replace("seriea", " SERIE A").replace("bdctv", " B DCTV").replace("24", " 24").replace("plus", " PLUS").replace("central", " CENTRAL").replace("auno", "A UNO").replace("acollection", "A COLLECTION").replace("afamily", "A FAMILY").replace("aaction", "A ACTION").replace("asuspense", "A SUSPENSE").replace("aromance", "A ROMANCE").replace("adrama", "A DRAMA").replace("acomedy", "A COMEDY").replace("astories", "A STORIES").replace("tuno", "T UNO").replace("tcalcio", "T TENNIS").replace("tarena", "T ARENA").replace("tbasket", "T BASKET").replace("tmax", "T MAX").replace("tf1", "T F1").replace("tmotogp", "T MOTOGP").replace("tgolf", "T GOLF").replace("tlegend", "T LEGEND").replace("tmix", "T MIX").replace("t251", "T 251").replace("t252", "T 252").replace("t253", "T 253").replace("t254", "T 254").replace("t255", "T 255").replace("t256", "T 256").replace("t257", "T 257").replace("t258", "T 258").replace("t259", "T 259").replace("nnetwork", "N NETWORK").replace("tv1", " TV 1").replace("tv2", " TV 2").replace("tv3", " TV 3").replace("tv4", " TV 4").replace("tv5", " TV 5").replace("eng", " ENG").replace("DaValutare", " OFFLIN")
    return name.strip().upper()

def create_zip(addon_id):
    # Crea il percorso zips/plugin.video.mariofr/
    addon_zip_dir = os.path.join("zips", addon_id)
    if not os.path.exists(addon_zip_dir): 
        os.makedirs(addon_zip_dir)
    
    zip_file_path = os.path.join(addon_zip_dir, f"{addon_id}.zip")
    
    with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(addon_id):
            for file in files:
                full_path = os.path.join(root, file)
                # Forza la struttura corretta: ID_ADDON/file_interni
                archive_name = os.path.join(addon_id, os.path.relpath(full_path, addon_id))
                z.write(full_path, archive_name)
    print(f" -> ZIP Creato: {zip_file_path}")

def run_all():
    # --- FASE 1: GENERAZIONE JSON (LOGICA IDENTICA A GENERATEKODIM3UPROVA.PY) ---
    if not os.path.exists(INPUT_FILE):
        print(f"File '{INPUT_FILE}' non trovato.")
        return

    print(f"Elaborazione link da {INPUT_FILE}...")
    print("Modalità 'Lenta e Sicura' attivata. Lo script prenderà tutto il tempo necessario.\n")

    with open(INPUT_FILE, "r", encoding="utf-8") as infile:
        raw_links = [line.strip() for line in infile if line.strip() and not line.startswith("#")]

    if not raw_links:
        print("Nessun link trovato.")
        return

    channels_list = []

    for i, url in enumerate(raw_links):
        print(f"[{i+1}/{len(raw_links)}] Risoluzione di: {url}...")
        try:
            response = http.request('GET', url, headers=HEADERS, redirect=True)
            final_url = unquote(response.geturl())
            
            channel_slug = url.split('/')[-1]
            display_name = format_channel_name(channel_slug)
            url_lower = final_url.lower()

            ch_entry = {"name": display_name, "url": "", "license": "", "manifest_type": ""}

            if "|" in final_url:
                stream_url, params = final_url.split("|", 1)
                clearkey_val = params.replace("clearkey=", "").strip()
                ch_entry.update({
                    "url": stream_url,
                    "license": clearkey_val,
                    "manifest_type": "mpd"
                })
                channels_list.append(ch_entry)
                print(f" -> OK (DASH+CK): {display_name}")
            else:
                is_dash = ".mpd" in url_lower
                is_hls = ".m3u8" in url_lower
                
                ch_entry["url"] = final_url
                if is_dash or is_hls:
                    ch_entry["manifest_type"] = "mpd" if is_dash else "hls"
                
                channels_list.append(ch_entry)
                print(f" -> OK ({'DASH' if is_dash else 'HLS/Altro'}): {display_name}")
            
            print(f" -> OK: {display_name}")

        except urllib3.exceptions.MaxRetryError as e:
            print(f" -> ERRORE: Fallimento dopo troppi tentativi/redirect per {url}.")
            print(f"    Dettaglio: {e.reason}")
        except Exception as e:
            print(f" -> ERRORE imprevisto su {url}: {e}")
        
        if i < len(raw_links) - 1:
            time.sleep(RITARDO_TRA_LINK)

    with open(PLAYLIST_JSON, "w", encoding="utf-8") as outfile:
        json.dump(channels_list, outfile, indent=4)
    print(f"\nGenerazione JSON completata! File creato: {PLAYLIST_JSON}")

    # --- FASE 2: GESTIONE REPOSITORY (LOGICA ORIGINALE FEDELE) ---
    print(f"\n--- FASE 2: Impacchettamento Repository e Addon ---")
    xml_header = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<addons>\n'
    xml_body = ""
    
    for aid in [ADDON_ID, REPO_ID]:
        xml_path = os.path.join(aid, "addon.xml")
        if os.path.exists(xml_path):
            with open(xml_path, "r", encoding="utf-8") as f:
                content = f.read().split("?>")[-1].strip()
                xml_body += content + "\n\n"
            create_zip(aid)
            print(f"Zip creato per: {aid}")

    full_xml = xml_header + xml_body + "</addons>"
    with open("addons.xml", "w", encoding="utf-8") as f: f.write(full_xml)
    with open("addons.xml.md5", "w") as f: f.write(hashlib.md5(full_xml.encode()).hexdigest())

    print(f"\nCOMPLETATO! Carica {PLAYLIST_JSON}, addons.xml, addons.xml.md5 e la cartella zips/ su GitHub.")

if __name__ == "__main__":
    run_all()