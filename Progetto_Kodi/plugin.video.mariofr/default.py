import sys
import json
import urllib.request
import urllib.parse
import xbmcgui
import xbmcplugin

# URL ORIGINALI DELLA TUA REPO
URL_JSON = "https://raw.githubusercontent.com/riccamariofrancesco-cell/mariofr-repo/refs/heads/main/playlist.json"
URL_UA_TXT = "https://raw.githubusercontent.com/riccamariofrancesco-cell/mariofr-repo/refs/heads/main/user_agents.txt"

# UA di emergenza se il file TXT fallisce
UA_FALLBACK = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"

def get_remote_uas():
    """Scarica gli User Agent dal tuo file TXT su GitHub"""
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
    
    # --- LOGICA DI RIPRODUZIONE (Avviata al click sul canale) ---
    if params.get('action') == 'play':
        # Carica User Agents dal file remoto
        user_agents = get_remote_uas()
        
        # Mostra il popup di scelta
        dialog = xbmcgui.Dialog()
        scelta = dialog.select("Scegli User-Agent", user_agents)
        
        if scelta == -1:
            xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem())
            return
            
        selected_ua = user_agents[scelta]
        url = params.get('url')
        license_key = params.get('license')
        
        # Crea il ListItem per il Player (Uguale alla tua configurazione originale)
        li = xbmcgui.ListItem(path=url)
        li.setProperty('inputstream', 'inputstream.adaptive')
        
        # Applica l'User-Agent scelto
        li.setProperty('inputstream.adaptive.stream_headers', f'User-Agent={selected_ua}')
        li.setProperty('inputstream.adaptive.manifest_headers', f'User-Agent={selected_ua}')
        
        # DRM: Mantiene la tua logica org.w3.clearkey (fondamentale per la tua repo)
        if license_key:
            li.setProperty('inputstream.adaptive.drm_legacy', f"org.w3.clearkey|{license_key}")
        
        # MIMETYPE: Mantiene il tuo controllo DASH/HLS
        url_lower = url.lower()
        if ".mpd" in url_lower:
            li.setMimeType('application/dash+xml')
        elif ".m3u8" in url_lower:
            li.setMimeType('application/vnd.apple.mpegurl')
            
        xbmcplugin.setResolvedUrl(handle, True, li)
        return

    # --- LOGICA LISTA CANALI (Uguale alla tua repository) ---
    try:
        req = urllib.request.Request(URL_JSON, headers={'User-Agent': UA_FALLBACK})
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read().decode())
    except:
        data = []

    for ch in data:
        # Recupero campi dal tuo JSON (name, url, license)
        li = xbmcgui.ListItem(label=ch['name'])
        li.setInfo('video', {'title': ch['name']})
        li.setArt({'icon': 'DefaultVideo.png'})
        
        # Comunica a Kodi che l'elemento deve richiamare setResolvedUrl
        li.setProperty('IsPlayable', 'true')
        
        # Costruisce l'URL interno per gestire il click e il popup
        lic = ch.get('license', '')
        query = {'action': 'play', 'url': ch['url'], 'license': lic}
        plugin_url = f"{sys.argv[0]}?{urllib.parse.urlencode(query)}"
        
        xbmcplugin.addDirectoryItem(handle, plugin_url, li, isFolder=False)

    xbmcplugin.endOfDirectory(handle)

if __name__ == '__main__':
    run()
