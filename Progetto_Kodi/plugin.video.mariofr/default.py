import sys, json, urllib.request, urllib.parse, xbmcgui, xbmcplugin

# URL della tua playlist su GitHub
URL_JSON = "https://raw.githubusercontent.com/riccamariofrancesco-cell/mariofr-repo/refs/heads/main/playlist.json"

# Inserisci qui tutti gli User-Agent che vuoi testare.
# Il popup li mostrerà in quest'ordine.
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Web0S; Linux/SmartTV) AppleWebKit/537.41 (KHTML, like Gecko) Large Screen Safari/537.41 LG Browser/7.00.00(LGE; WEBOS1; 05.06.10; 1); webOS.TV-2014; LG NetCast.TV-2013 Compatible (LGE, WEBOS1, wireless)"
]

def run():
    handle = int(sys.argv[1])
    # Leggiamo i parametri per capire se Kodi sta creando la lista o se hai cliccato su un canale
    params = dict(urllib.parse.parse_qsl(sys.argv[2][1:]))
    
    # ---------------------------------------------------------
    # AZIONE 1: L'utente ha cliccato su un canale da riprodurre
    # ---------------------------------------------------------
    if params.get('action') == 'play':
        # Mostra il popup standard di Kodi per scegliere l'User-Agent
        dialog = xbmcgui.Dialog()
        scelta = dialog.select("Scegli quale User-Agent usare:", USER_AGENTS)
        
        # Se l'utente preme "Annulla" o il tasto indietro
        if scelta == -1:
            xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem())
            return
            
        # Recuperiamo l'User-Agent scelto dal popup
        selected_ua = USER_AGENTS[scelta]
        url = params.get('url')
        
        # Creiamo l'elemento da passare al player
        li = xbmcgui.ListItem(path=url)
        
        # 1. Attivazione InputStream Adaptive
        li.setProperty('inputstream', 'inputstream.adaptive')
        
        # INIETTA L'USER AGENT SCELTO QUI
        li.setProperty('inputstream.adaptive.stream_headers', f'User-Agent={selected_ua}')
        
        # 2. Gestione DRM ClearKey 
        if params.get('license'):
            li.setProperty('inputstream.adaptive.drm_legacy', f"org.w3.clearkey|{params.get('license')}")
        
        # 3. MimeType
        url_lower = url.lower()
        if ".mpd" in url_lower:
            li.setMimeType('application/dash+xml')
        elif ".m3u8" in url_lower:
            li.setMimeType('application/vnd.apple.mpegurl')
            
        # Diciamo a Kodi: "Tutto pronto, risolvi e fai partire il video!"
        xbmcplugin.setResolvedUrl(handle, True, li)
        return

    # ---------------------------------------------------------
    # AZIONE 2: Caricamento della lista canali (Apertura Addon)
    # ---------------------------------------------------------
    try:
        # Usiamo il primo User-Agent di default per leggere il JSON da GitHub
        req = urllib.request.Request(URL_JSON, headers={'User-Agent': USER_AGENTS[0]})
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read().decode())
    except Exception as e:
        data = []

    for ch in data:
        # Creazione dell'elemento della lista
        li = xbmcgui.ListItem(label=ch['name'])
        li.setInfo('video', {'title': ch['name']})
        li.setArt({'icon': 'DefaultVideo.png'})
        
        # IMPORTANTE: isPlayable=true dice a Kodi che questo link avvierà un video (serve per setResolvedUrl)
        li.setProperty('IsPlayable', 'true')
        
        # Creiamo un "URL finto" che rimanda all'interno di questo stesso script passando i dati del canale
        lic = ch.get('license', '')
        plugin_url = f"{sys.argv[0]}?action=play&url={urllib.parse.quote(ch['url'])}&license={urllib.parse.quote(lic)}"
        
        # 'False' indica che il link non è una cartella
        xbmcplugin.addDirectoryItem(handle, plugin_url, li, isFolder=False)

    xbmcplugin.endOfDirectory(handle)

if __name__ == '__main__':
    run()