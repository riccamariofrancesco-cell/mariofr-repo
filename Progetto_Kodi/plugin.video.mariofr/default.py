import sys
import json
import urllib.request
import urllib.parse
import xbmcgui
import xbmcplugin
import xbmc

# VERSIONE 1.0.26 - 2026-03-07

# URL ORIGINALI DELLA TUA REPO
URL_JSON = "https://raw.githubusercontent.com/riccamariofrancesco-cell/mariofr-repo/refs/heads/main/playlist.json"
URL_UA_TXT = "https://raw.githubusercontent.com/riccamariofrancesco-cell/mariofr-repo/refs/heads/main/user_agents.txt"

# UA di emergenza se il file TXT fallisce
UA_FALLBACK = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"

def logga(msg):
    xbmc.log(f"MARIOFR_REPO: {msg}", xbmc.LOGINFO)

def get_remote_uas():
    # Scarica gli User Agent dal tuo file TXT su GitHub
    try:
        req = urllib.request.Request(URL_UA_TXT, headers={'User-Agent': UA_FALLBACK})
        with urllib.request.urlopen(req, timeout=10) as r:
            content = r.read().decode('utf-8')
            uas = [line.strip() for line in content.splitlines() if line.strip()]
            return uas if uas else [UA_FALLBACK]
    except:
        return [UA_FALLBACK]

def run():
    handle = int(sys.argv[1])
    params = dict(urllib.parse.parse_qsl(sys.argv[2][1:]))
    
    # --- LOGICA DI RIPRODUZIONE ---
    if params.get('action') == 'play':
        url = params.get('url')
        license_key = params.get('license')
        url_lower = url.lower()
        
        # --- LOGICA AUTOMATICA HEADERS ---
        auto_headers = None
        token = "" # Eventuale token se presente nei parametri futuri
        
        if "dazn" in url_lower or "dai.google.com" in url_lower:
            ua = urllib.parse.quote("Mozilla/5.0 (Web0S; Linux/SmartTV) AppleWebKit/537.41 (KHTML, like Gecko) Large Screen Safari/537.41 LG Browser/7.00.00(LGE; WEBOS1; 05.06.10; 1); webOS.TV-2014; LG NetCast.TV-2013 Compatible (LGE, WEBOS1, wireless)")
            host = "https://www.dazn.com"
            auto_headers = f'User-Agent={ua}&Referer={host}/&Origin={host}'
            if token != "":
                ua = urllib.parse.quote_plus("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36")
                auto_headers = f'{token}&referer={host}/&origin={host}&user-agent={ua}'
            logga(f"Auto-Header DAZN rilevato: {auto_headers}")
            
        elif "lba-ew" in url_lower:
            ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:143.0) Gecko/20100101 Firefox/143.0"
            host = "https://www.lbatv.com"
            auto_headers = f'User-Agent={ua}&Referer={host}/&Origin={host}&verifypeer=false'
            logga("Auto-Header LBA rilevato")
            
        elif "discovery" in url_lower:
            ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0"
            host = "https://www.discoveryplus.com"
            auto_headers = f'User-Agent={ua}&Referer={host}/&Origin={host}&verifypeer=false'
            logga("Auto-Header Discovery rilevato")
            
        elif "nowitlin" in url_lower:
            ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
            host = "https://www.nowtv.it"
            auto_headers = f'User-Agent={ua}&Referer={host}/&Origin={host}&verifypeer=false'
            logga("Auto-Header NOW rilevato")
            
        elif "vodafone.pt" in url_lower:
            ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0"
            host = "http://rr.cdn.vodafone.pt"
            auto_headers = f'User-Agent={ua}&Referer={host}/&Origin={host}&verifypeer=false'
            logga("Auto-Header Vodafone rilevato")
            
        elif "clarovideo.com" in url_lower:
            ua = urllib.parse.quote_plus("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 OPR/124.0.0.0")
            host = "https://clarovideo.com"
            auto_headers = f'User-Agent={ua}&Referer={host}/&Origin={host}&verifypeer=false'
            logga("Auto-Header Claro rilevato")
            
        elif "starzplayarabia" in url_lower:
            ua = urllib.parse.quote("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 OPR/120.0.0.0")
            auto_headers = f'User-Agent={ua}&verifypeer=false'
            logga("Auto-Header Starz rilevato")
        
        elif "vavoo" in url_lower:
            ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
            host = "https://vavoo.to"
            auto_headers = f'User-Agent={ua}&Referer={host}/&Origin={host}'
            logga("Auto-Header VAVOO rilevato")

        # --- SELEZIONE MANUALE SE NON AUTOMATICO ---
        if auto_headers:
            selected_headers = auto_headers
        else:
            # Carica User Agents dal file remoto per la scelta manuale
            user_agents = get_remote_uas()
            dialog = xbmcgui.Dialog()
            scelta = dialog.select("Scegli User-Agent", user_agents)
            if scelta == -1:
                xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem())
                return
            selected_ua = user_agents[scelta]
            selected_headers = f"User-Agent={selected_ua}"

        # --- CREAZIONE LISTITEM ---
        li = xbmcgui.ListItem(path=url)
        li.setProperty('inputstream', 'inputstream.adaptive')
        li.setProperty('inputstream.adaptive.stream_headers', selected_headers)
        li.setProperty('inputstream.adaptive.manifest_headers', selected_headers)
        
        # DRM: Mantiene la tua logica org.w3.clearkey
        if license_key:
            li.setProperty('inputstream.adaptive.drm_legacy', f"org.w3.clearkey|{license_key}")
        
        # MIMETYPE
        if ".mpd" in url_lower:
            li.setMimeType('application/dash+xml')
        elif ".m3u8" in url_lower:
            li.setMimeType('application/vnd.apple.mpegurl')
            
        xbmcplugin.setResolvedUrl(handle, True, li)
        return

    # --- LOGICA NAVIGAZIONE A CARTELLE ---
    action = params.get('action')
    
    try:
        req = urllib.request.Request(URL_JSON, headers={'User-Agent': UA_FALLBACK})
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read().decode())
    except:
        data = []

    if not action:
        # MENU PRINCIPALE: Mostra le categorie come cartelle
        categories = []
        for ch in data:
            cat = ch.get('category', 'Altro')
            if cat not in categories:
                categories.append(cat)

        for cat in categories:
            li = xbmcgui.ListItem(label=cat)
            li.setArt({'icon': 'DefaultFolder.png'}) # Icona standard per le cartelle
            query = {'action': 'category', 'category': cat}
            plugin_url = f"{sys.argv[0]}?{urllib.parse.urlencode(query)}"
            # isFolder=True dice a Kodi che questo è un sottomenu navigabile
            xbmcplugin.addDirectoryItem(handle, plugin_url, li, isFolder=True)

    elif action == 'category':
        # SOTTOMENU: Mostra solo i canali appartenenti alla categoria cliccata
        selected_cat = params.get('category')
        for ch in data:
            if ch.get('category', 'Altro') == selected_cat:
                li = xbmcgui.ListItem(label=ch['name'])
                li.setInfo('video', {'title': ch['name']})
                li.setArt({'icon': 'DefaultVideo.png'})
                li.setProperty('IsPlayable', 'true')
                
                lic = ch.get('license', '')
                query = {'action': 'play', 'url': ch['url'], 'license': lic}
                plugin_url = f"{sys.argv[0]}?{urllib.parse.urlencode(query)}"
                xbmcplugin.addDirectoryItem(handle, plugin_url, li, isFolder=False)

    xbmcplugin.endOfDirectory(handle)

if __name__ == '__main__':
    run()
