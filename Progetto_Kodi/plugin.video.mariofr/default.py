import sys, json, urllib.request, xbmcgui, xbmcplugin

# URL della tua playlist su GitHub
URL_JSON = "https://raw.githubusercontent.com/riccamariofrancesco-cell/mariofr-repo/refs/heads/main/playlist.json"

def run():
    handle = int(sys.argv[1])
    try:
        # Recupero del JSON generato dal tuo manager
        req = urllib.request.Request(URL_JSON, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36'})
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read().decode())
    except Exception as e:
        data = []

    for ch in data:
        # Creazione dell'elemento della lista
        li = xbmcgui.ListItem(label=ch['name'])
        li.setInfo('video', {'title': ch['name']})
        
        # 1. Attivazione InputStream Adaptive
        li.setProperty('inputstream', 'inputstream.adaptive')
        
        # 2. Gestione DRM ClearKey (Formato moderno richiesto dai log e documentazione)
        # Anche se il JSON contiene altri campi, noi leggiamo solo 'license'
        if ch.get('license'):
            # Utilizziamo org.w3.clearkey come richiesto dagli standard moderni
            # Il formato 'sistema|chiave' risolve l'errore "not supported" del tuo log
            li.setProperty('inputstream.adaptive.drm_legacy', f"org.w3.clearkey|{ch['license']}")
        
        # 3. MimeType (Sostituisce manifest_type che ora ignoriamo)
        # Kodi userà questo per capire se è DASH o HLS senza warning di deprecazione
        url_lower = ch['url'].lower()
        if ".mpd" in url_lower:
            li.setMimeType('application/dash+xml')
        elif ".m3u8" in url_lower:
            li.setMimeType('application/vnd.apple.mpegurl')

        # Impostazione icona e aggiunta alla directory
        li.setArt({'icon': 'DefaultVideo.png'})
        # 'False' indica che il link punta a un file multimediale, non a un'altra cartella
        xbmcplugin.addDirectoryItem(handle, ch['url'], li, False)

    xbmcplugin.endOfDirectory(handle)

if __name__ == '__main__':
    run()
