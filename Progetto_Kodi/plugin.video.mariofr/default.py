import sys, json, urllib.request, xbmcgui, xbmcplugin

# SOSTITUISCI CON IL LINK RAW DI GITHUB DEL TUO PLAYLIST.JSON
URL_JSON = "https://raw.githubusercontent.com/riccamariofrancesco-cell/mariofr-repo/refs/heads/main/playlist.json"

def run():
    handle = int(sys.argv[1])
    try:
        req = urllib.request.Request(URL_JSON, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read().decode())
    except:
        data = []

    for ch in data:
        li = xbmcgui.ListItem(label=ch['name'])
        li.setInfo('video', {'title': ch['name']})
        li.setProperty('inputstream', 'inputstream.adaptive')
        li.setProperty('inputstream.adaptive.manifest_type', ch['manifest_type'])
        if ch['license']:
            li.setProperty('inputstream.adaptive.license_type', 'clearkey')
            li.setProperty('inputstream.adaptive.license_key', ch['license'])
        xbmcplugin.addDirectoryItem(handle, ch['url'], li, False)
    xbmcplugin.endOfDirectory(handle)

if __name__ == '__main__':
    run()