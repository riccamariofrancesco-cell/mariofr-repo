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
INPUT_FILE = "links_suddivisione.txt"
PLAYLIST_JSON = "playlist.json"
ADDON_ID = "plugin.video.mariofr"
REPO_ID = "repository.mariofr"
AUTOEXEC_ID = "service.autoexec"

# --- CONFIGURAZIONE RETE (IDENTICA AL VECCHIO PYTHON) ---
# --- CAMBIARE RITARDO_TRA_LINK IN BASE ALLA PROPRIA CONNESSIONE (default 0 sec) ---
RITARDO_TRA_LINK = 0
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
    # Trasforma lo slug del link in un nome leggibile
    name = slug.replace("DaValutare", " OFFLINE").replace("extramediahosting", " EXTRA MH").replace("extravavoo6", " EXTRA EUROTV 6").replace("extravavoo7", " EXTRA EUROTV 7").replace("rai1", "[1] Rai 1").replace("rai2", "[2] Rai 2").replace("rai3", "[3] Rai 3").replace("rete4", "[4] Rete 4").replace("canale5", "[5] Canale 5").replace("italia1", "[6] Italia 1").replace("la7", "[7] LA7").replace("tv8", "[8] TV8").replace("nove", "[9] Nove").replace("20mediaset", "[20] 20 Mediaset").replace("rai4", "[21] Rai 4").replace("iris", "[22] Iris").replace("rai5", "[23] Rai 5").replace("raimovie", "[24] Rai Movie").replace("raipremium", "[25] Rai Premium").replace("cielo", "[26] Cielo").replace("27twentyseven", "[27] 27Twentyseven").replace("tv2000", "[28] TV2000").replace("la7d", "[29] LA7d").replace("la5", "[30] La5").replace("realtime", "[31] Real Time").replace("qvc", "[32] QVC").replace("foodnetwork", "[33] Food Network").replace("cine34", "[34] Cine34").replace("focus", "[35] Focus").replace("rtl1025", "[36] RTL 102.5").replace("warnertv", "[37] Warner TV").replace("giallo", "[38] GIALLO").replace("topcrime", "[39] TOPCrime").replace("boing", "[40] Boing").replace("k2", "[41] K2").replace("raigulp", "[42] Rai Gulp").replace("raiyoyo", "[43] Rai YoYo").replace("frisbee", "[44] frisbee").replace("boingplus", "[45] Boing Plus").replace("cartoonito", "[46] Cartoonito").replace("super", "[47] Super!").replace("rainews24", "[48] Rai News 24").replace("mediasetitalia2", "[49] Mediaset Italia 2").replace("skytg", "[50] Sky TG24 su SKY (intrattenimento)").replace("tgcom24", "[51] TGCOM 24").replace("dmax", "[52] DMAX").replace("italia53", "[53] Italia53").replace("raistoria", "[54] Rai Storia").replace("mediasetxtra", "[55] Mediaset Extra").replace("hgtv", "[56] HGTV").replace("raiscuola", "[57] Rai Scuola").replace("raisport", "[58] Rai Sport").replace("motortrend", "[59] Motor Trend").replace("sportitalia", "[60] SPORT ITALIA").replace("supertennis", "[64] SUPERTENNIS").replace("dazn1", "DAZN 1").replace("dazn2", "DAZN 2").replace("eurosport1", "EUROSPORT 1").replace("eurosport2", "EUROSPORT 2").replace("eurosport3", "EUROSPORT 3").replace("eurosport4", "EUROSPORT 4").replace("eurosport5", "EUROSPORT 5").replace("eurosport6", "EUROSPORT 6").replace("intertv", "INTER TV").replace("seriebdctv", "SERIE B DCTV").replace("daznch", "DAZN CH").replace("daznmatchtime", "DAZN MATCH TIME").replace("tg24", "TG 24").replace("plus", " PLUS").replace("historychannel", "HISTORY").replace("comedycentral", "COMEDY CENTRAL").replace("cinemauno", "CINEMA UNO").replace("cinemadue", "CINEMA DUE").replace("cinemacollection", "CINEMA COLLECTION").replace("cinemafamily", "CINEMA FAMILY").replace("cinemaaction", "CINEMA ACTION").replace("cinemasuspense", "CINEMA SUSPENSE").replace("cinemaromance", "CINEMA ROMANCE").replace("cinemadrama", "CINEMA DRAMA").replace("cinemacomedy", "CINEMA COMEDY").replace("cinemastories", "CINEMA STORIES").replace("sport24", "SPORT 24").replace("sportuno", "SPORT UNO").replace("sportcalcio", "SPORT CALCIO").replace("sporttennis", "SPORT TENNIS").replace("sportarena", "SPORT ARENA").replace("sportbasket", "SPORT BASKET").replace("sportmax", "SPORT MAX").replace("sportf1", "SPORT F1").replace("sportmotogp", "SPORT MOTOGP").replace("sportgolf", "SPORT GOLF").replace("sportlegend", "SPORT LEGEND").replace("sportmix", "SPORT MIX").replace("sport25", "SPORT 25").replace("skych", "SKY CANALE SVIZZERO").replace("deakids", "DEA KIDS").replace("nickjr", "NICK JR").replace("cartoonnetwork", "CARTOON NETWORK").replace("primafila", "PRIMAFILA ").replace("lastminute", "LAST MINUTE ").replace("lbatv", "LBA TV ").replace("rsila", "RSI LA ").replace("telefoggia", "TELE FOGGIA").replace("prime", "PRIME ").replace("paramount", "PARAMOUNT ").replace("bluesport", "BLUE SPORT ")
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
        lines = [line.strip() for line in infile if line.strip() and not line.startswith("#")]

    raw_items = []
    current_category = "Altro"
    for line in lines:
        if line == "FINE":
            break
        if not line.startswith("http"):
            current_category = line
        else:
            raw_items.append({"url": line, "category": current_category})

    if not raw_items:
        print("Nessun link trovato.")
        return

    channels_list = []

    for i, item in enumerate(raw_items):
        url = item["url"]
        category = item["category"]
        print(f"[{i+1}/{len(lines)}] Risoluzione di: {url}...")
        try:
            response = http.request('GET', url, headers=HEADERS, redirect=False)
            final_url = response.headers.get('Location', url)
            
            channel_slug = url.split('/')[-1]
            display_name = format_channel_name(channel_slug)
            url_lower = final_url.lower()

            ch_entry = {"name": display_name, "url": "", "license": "", "manifest_type": "", "category": category}

            if "%7C" in final_url:
                stream_url, params = final_url.split("%7C", 1)
                clearkey_val = params.replace("clearkey=", "").replace("ck=", "").strip()
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
        
        if i < len(lines) - 1:
            time.sleep(RITARDO_TRA_LINK)

    with open(PLAYLIST_JSON, "w", encoding="utf-8") as outfile:
        json.dump(channels_list, outfile, indent=4)
    print(f"\nGenerazione JSON completata! File creato: {PLAYLIST_JSON}")

    # --- FASE 2: GESTIONE REPOSITORY (LOGICA ORIGINALE FEDELE) ---
    print(f"\n--- FASE 2: Impacchettamento Repository e Addon ---")
    xml_header = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<addons>\n'
    xml_body = ""
    
    for aid in [ADDON_ID, AUTOEXEC_ID]:
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
