import sys
import json
import os
import urllib.request
import urllib.parse
import urllib.error
import xbmcgui
import xbmcplugin
import xbmc
import xbmcaddon
import xbmcvfs
import string
import random
import re
import base64
import time

# VERSIONE 1.0.40-bigrelease - 2026-04-07

URL_JSON     = "https://raw.githubusercontent.com/riccamariofrancesco-cell/mariofr-repo/refs/heads/main/playlist.json"
URL_UA_TXT   = "https://raw.githubusercontent.com/riccamariofrancesco-cell/mariofr-repo/refs/heads/main/user_agents.txt"
URL_MANDRA   = "https://test34344.herokuapp.com/filter.php"
URL_EPG_LIST = "https://test34344.herokuapp.com/filter.php?numTest=A1A201A"
URL_ZAPPR    = "https://channels.zappr.stream/it/dtt/national.json"
FANART_DEFAULT = "https://www.stadiotardini.it/wp-content/uploads/2016/12/mandrakata.jpg"

UA_FALLBACK = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"

AMSTAFF_HEADERS = (
    "Referer=https://amstaff.city/"
    "&Origin=https://amstaff.city"
    "&User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

# Domini EUROTV (vavoo + alias)
EUROTV_DOMAINS = ('vavoo.to', 'kool.to', 'oha.to', 'huhu.to')

# ===========================================================================
# UTILITY
# ===========================================================================

def logga(msg):
    xbmc.log(f"MARIOFR_REPO: {msg}", xbmc.LOGINFO)

def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

def strip_kodi_tags(title):
    title = re.sub(r'\[COLOR [^\]]+\]', '', title)
    title = re.sub(r'\[/COLOR\]', '', title, flags=re.IGNORECASE)
    title = re.sub(r'\[/?[BI]\]', '', title, flags=re.IGNORECASE)
    return title.strip()

def get_remote_uas():
    try:
        req = urllib.request.Request(URL_UA_TXT, headers={'User-Agent': UA_FALLBACK})
        with urllib.request.urlopen(req, timeout=10) as r:
            content = r.read().decode('utf-8')
            uas = [line.strip() for line in content.splitlines() if line.strip()]
            return uas if uas else [UA_FALLBACK]
    except:
        return [UA_FALLBACK]

def makeJob(url, hdr=None):
    logga('TRY TO OPEN ' + url)
    html = ""
    deviceId = id_generator()
    if hdr is None:
        hdr = {'User-Agent': "MandraKodi2@@2.2.1@@@@" + deviceId}
    try:
        req = urllib.request.Request(url, headers=hdr)
        response = urllib.request.urlopen(req, timeout=45)
        html = response.read().decode('utf-8')
        response.close()
        logga('OK REQUEST FROM ' + url + ' resp: ' + html[:30])
    except Exception as e:
        logga('Error to open job: ' + url + ' - ' + str(e))
    return html

def makeRequest(url):
    return http_get(url)

# ===========================================================================
# HTTP HELPERS
# ===========================================================================

def http_get(url, headers=None, timeout=20):
    hdr = {'User-Agent': UA_FALLBACK}
    if headers:
        hdr.update(headers)
    try:
        req = urllib.request.Request(url, headers=hdr)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode('utf-8', errors='replace')
    except Exception as e:
        logga(f"http_get ERROR [{url}]: {e}")
        return ''

def http_post_json(url, data_dict, headers=None, timeout=20):
    payload = json.dumps(data_dict).encode('utf-8')
    hdr = {'User-Agent': 'MediaHubMX/2', 'Content-Type': 'application/json; charset=utf-8', 'Accept': 'application/json'}
    if headers:
        hdr.update(headers)
    try:
        req = urllib.request.Request(url, data=payload, headers=hdr, method='POST')
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode('utf-8', errors='replace')
    except Exception as e:
        logga(f"http_post_json ERROR [{url}]: {e}")
        return ''

def preg_match(data, patron):
    try:
        m = re.search(patron, data, re.DOTALL)
        if m:
            return m.group(1) if m.lastindex else m.group(0)
        return ''
    except:
        return ''

def get_my_ip():
    try:
        return json.loads(http_get("https://api.ipify.org?format=json", timeout=5)).get('ip', '0.0.0.0')
    except:
        return '0.0.0.0'

# ===========================================================================
# SKY RESOLVER  (xor decrypt + API)
# ===========================================================================

def xor_decrypt(data_b64, key):
    """XOR decrypt con chiave ripetuta, input base64."""
    data      = base64.b64decode(data_b64)
    key_bytes = key.encode('utf-8')
    out = bytearray()
    for i in range(len(data)):
        out.append(data[i] ^ key_bytes[i % len(key_bytes)])
    return out.decode('utf-8')

SKY_SECRET = "my_secret_key"
SKY_UA_API = "MandraKodi2@@2.2.1@@@@A7B9X2"
SKY_UA_PLAY = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
SKY_HOST    = "https://www.nowtv.it"

def resolve_sky_channel(par_in):
    """Chiama l'API Sky MandraKodi, decripta XOR, restituisce (manifest, kid:key)."""
    logga(f"resolve_sky_channel: {par_in}")
    api_url = f"https://test34344.herokuapp.com/filter.php?numTest=A1A159&id={par_in}"
    resp    = http_get(api_url, headers={'User-Agent': SKY_UA_API})
    if not resp:
        return ('', '')
    try:
        res       = json.loads(resp)
        decrypted = xor_decrypt(res["data"], SKY_SECRET)
        data      = json.loads(decrypted)
        manifest  = data["manifest"]
        key64     = data["kid"] + ":" + data["key"]
        logga(f"Sky manifest: {manifest}")
        return (manifest, key64)
    except Exception as e:
        logga(f"resolve_sky_channel error: {e}")
        return ('', '')

# ===========================================================================
# EUROTV RESOLVER  (vavoo.to / kool.to / oha.to / huhu.to)
# ===========================================================================

def resolve_eurotv(eurotv_url):
    """
    Risolve URL di tipo EUROTV (vavoo.to, kool.to, oha.to, huhu.to).
    Prova prima l'API addonSig di vavoo, poi il redirect diretto.
    """
    logga(f"resolve_eurotv: {eurotv_url}")
    # Metodo 1: API MediaHubMX con firma addonSig
    try:
        adesso    = int(time.time() * 1000)
        client_ip = get_my_ip()
        ping_data = {
            'token': '', 'reason': 'app-blur', 'locale': 'de', 'theme': 'dark',
            'metadata': {
                'device': {'type': 'Handset', 'brand': 'google', 'model': 'Pixel',
                           'name': 'sdk_gphone64_arm64', 'uniqueId': 'd10e5d99ab665233'},
                'os': {'name': 'android', 'version': '13', 'host': 'android',
                       'abis': ['arm64-v8a', 'armeabi-v7a', 'armeabi']},
                'app': {'platform': 'android', 'version': '3.1.21', 'buildId': '289515000',
                        'engine': 'hbc85',
                        'signatures': ['6e8a975e3cbf07d5de823a760d4c2547f86c1403105020adee5de67ac510999e'],
                        'installer': 'app.revanced.manager.flutter'},
                'version': {'package': 'tv.vavoo.app', 'binary': '3.1.21', 'js': '3.1.21'}
            },
            'appFocusTime': 0, 'playerActive': False, 'playDuration': 0,
            'devMode': False, 'hasAddon': True, 'castConnected': False,
            'package': 'tv.vavoo.app', 'version': '3.1.21', 'process': 'app',
            'firstAppStart': adesso, 'lastAppStart': adesso,
            'ipLocation': client_ip, 'adblockEnabled': True,
            'proxy': {'supported': ['ss', 'openvpn'], 'engine': 'ss', 'ssVersion': 1,
                      'enabled': True, 'autoServer': True, 'id': 'de-fra'},
            'iap': {'supported': False}
        }
        ping_resp = http_post_json('https://www.vavoo.tv/api/app/ping', ping_data,
                                   headers={'user-agent': 'okhttp/4.11.0', 'accept': 'application/json'}, timeout=10)
        signature = json.loads(ping_resp).get('addonSig') if ping_resp else None
        if signature:
            res_resp = http_post_json(
                'https://vavoo.to/mediahubmx-resolve.json',
                {'language': 'de', 'region': 'AT', 'url': eurotv_url, 'clientVersion': '3.0.2'},
                headers={'user-agent': 'MediaHubMX/2', 'accept': 'application/json',
                         'mediahubmx-signature': signature}, timeout=10)
            if res_resp:
                result = json.loads(res_resp)
                if isinstance(result, list) and result and result[0].get('url'):
                    logga(f"eurotv resolved (API): {result[0]['url']}")
                    return result[0]['url']
                elif isinstance(result, dict) and result.get('url'):
                    logga(f"eurotv resolved (API dict): {result['url']}")
                    return result['url']
    except Exception as e:
        logga(f"eurotv API error: {e}")
    # Metodo 2: redirect diretto
    try:
        req = urllib.request.Request(eurotv_url, headers={'User-Agent': 'VAVOO/2.6'})
        with urllib.request.urlopen(req, timeout=15) as r:
            final_url = r.geturl()
            if final_url != eurotv_url:
                logga(f"eurotv resolved (redirect): {final_url}")
                return final_url
    except Exception as e:
        logga(f"eurotv redirect error: {e}")
    logga("eurotv: fallback URL originale")
    return eurotv_url

# ===========================================================================
# SKY TV  (usato da zappr per canali zappr://)
# ===========================================================================

def resolve_skytv(channel_id):
    logga(f"resolve_skytv: {channel_id}")
    page = http_get(f"https://apid.sky.it/vdp/v1/getLivestream?id={channel_id}&isMobile=false")
    try:
        url = json.loads(page).get('streaming_url', '')
        logga(f"skyTV URL: {url}")
        return url
    except:
        return ''

# ===========================================================================
# DISPATCH  (solo tipi usati da zappr ed EPG)
# ===========================================================================

def dispatch_resolver(tipo, param):
    """
    Restituisce ('url', url, is_ffmpeg) oppure ('error', msg, None).
    Gestisce solo i tipi effettivamente prodotti da zappr e EPG.
    """
    tipo = tipo.lower()
    if tipo == 'amstaff':
        # param = url|licensekey  oppure  url|0000
        parts = param.split('|', 1)
        url   = parts[0].strip()
        lic   = parts[1].strip() if len(parts) > 1 and parts[1].strip() not in ('0000', '') else ''
        # Se base64 e non http → decode
        if url and not url.startswith('http'):
            try:
                padded = url + '=' * ((4 - len(url) % 4) % 4)
                url = base64.b64decode(padded).decode('utf-8').strip()
            except:
                pass
        return ('url', url + ('|' + lic if lic else ''), False)
    elif tipo == 'skytv':
        url = resolve_skytv(param)
        return ('url', url, False) if url else ('error', f'skyTV: nessun URL per {param}', None)
    else:
        return ('error', f"Tipo '{tipo}' non gestito", None)

# ===========================================================================
# AUTO HEADERS  +  LISTITEM BUILDERS
# ===========================================================================

def _auto_headers_for_url(url_lower):
    if "dazn" in url_lower or "dai.google.com" in url_lower:
        ua   = urllib.parse.quote("Mozilla/5.0 (Web0S; Linux/SmartTV) AppleWebKit/537.41 (KHTML, like Gecko) Large Screen Safari/537.41 LG Browser/7.00.00(LGE; WEBOS1; 05.06.10; 1); webOS.TV-2014; LG NetCast.TV-2013 Compatible (LGE, WEBOS1, wireless)")
        host = "https://www.dazn.com"
        return f'User-Agent={ua}&Referer={host}/&Origin={host}'
    elif "lba-ew" in url_lower:
        ua   = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:143.0) Gecko/20100101 Firefox/143.0"
        host = "https://www.lbatv.com"
        return f'User-Agent={ua}&Referer={host}/&Origin={host}&verifypeer=false'
    elif "discovery" in url_lower:
        ua   = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0"
        host = "https://www.discoveryplus.com"
        return f'User-Agent={ua}&Referer={host}/&Origin={host}&verifypeer=false'
    elif "nowitlin" in url_lower:
        ua   = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
        host = "https://www.nowtv.it"
        return f'User-Agent={ua}&Referer={host}/&Origin={host}&verifypeer=false'
    elif "vodafone.pt" in url_lower:
        ua   = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0"
        host = "http://rr.cdn.vodafone.pt"
        return f'User-Agent={ua}&Referer={host}/&Origin={host}&verifypeer=false'
    elif "clarovideo.com" in url_lower:
        ua   = urllib.parse.quote_plus("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 OPR/124.0.0.0")
        host = "https://clarovideo.com"
        return f'User-Agent={ua}&Referer={host}/&Origin={host}&verifypeer=false'
    elif "starzplayarabia" in url_lower:
        ua = urllib.parse.quote("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 OPR/120.0.0.0")
        return f'User-Agent={ua}&verifypeer=false'
    elif any(d in url_lower for d in EUROTV_DOMAINS):
        ua   = "Mozilla/5.0 (X11; Linux armv7l) AppleWebKit/537.36 (KHTML, like Gecko) QtWebEngine/5.9.7 Chrome/56.0.2924.122 Safari/537.36 Sky_STB_ST412_2018/1.0.0 (Sky, EM150UK,)"
        host = "https://vavoo.to"
        return f'User-Agent={ua}&Referer={host}/&Origin={host}&Connection=keep-alive'
    return None

def _build_listitem_adaptive(url, headers_str, license_key):
    """Costruisce ListItem per inputstream.adaptive (MPD/HLS con DRM o DASH)."""
    url_lower = url.lower()
    li = xbmcgui.ListItem(path=url)
    li.setProperty('inputstream', 'inputstream.adaptive')
    li.setProperty('inputstream.adaptive.stream_headers',   headers_str)
    li.setProperty('inputstream.adaptive.manifest_headers', headers_str)
    if license_key and license_key not in ('0000', ''):
        if ':' in license_key:
            li.setProperty('inputstream.adaptive.drm_legacy', f"org.w3.clearkey|{license_key}")
        else:
            try:
                padded  = license_key + '=' * ((4 - len(license_key) % 4) % 4)
                decoded = base64.b64decode(padded).decode('utf-8').replace('{','').replace('}','').replace('"','')
                li.setProperty('inputstream.adaptive.license_type', 'clearkey')
                li.setProperty('inputstream.adaptive.license_key',  decoded)
            except Exception as e:
                logga(f"clearkey base64 fallback: {e}")
                li.setProperty('inputstream.adaptive.drm_legacy', f"org.w3.clearkey|{license_key}")
    if '.mpd' in url_lower:
        li.setMimeType('application/dash+xml')
    elif '.m3u8' in url_lower:
        li.setMimeType('application/vnd.apple.mpegurl')
    return li

def _build_listitem_ffmpeg(url):
    """Costruisce ListItem per inputstream.ffmpegdirect. L'URL può avere headers inline."""
    li = xbmcgui.ListItem(path=url)
    li.setProperty('inputstream', 'inputstream.ffmpegdirect')
    li.setMimeType('application/x-mpegURL')
    li.setProperty('inputstream.ffmpegdirect.manifest_type',      'hls')
    li.setProperty('inputstream.ffmpegdirect.is_realtime_stream', 'true')
    return li

# ===========================================================================
# PLAY URL  con dialog HLS
# ===========================================================================

def _play_url(handle, url, headers_str='', license_key='', use_setresolved=True):
    """
    Funzione centrale di riproduzione.
    - Se URL è HLS (.m3u8) senza DRM → mostra Dialog per scegliere FFMPEG / Adaptive
    - Se URL è MPD o HLS con DRM → adaptive diretto, nessun dialog
    - use_setresolved=True  → setResolvedUrl (canali playlist IsPlayable)
    - use_setresolved=False → xbmc.Player().play() (EPG)
    """
    # Separa URL pulito da eventuali headers inline
    if '|' in url:
        base_url, inline_h = url.split('|', 1)
    else:
        base_url, inline_h = url, ''

    url_check = base_url.lower()
    merged_headers = headers_str or inline_h

    # HLS senza DRM → dialog
    if '.m3u8' in url_check and not license_key:
        choice = xbmcgui.Dialog().select(
            "Scegli player",
            ["\u25b6 FFMPEG Direct (consigliato)", "\u25b6 InputStream Adaptive"]
        )
        if choice == -1:
            if use_setresolved:
                xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem())
            return
        use_ffmpeg = (choice == 0)
    else:
        use_ffmpeg = False

    if use_ffmpeg:
        ffmpeg_url = f"{base_url}|{merged_headers}" if merged_headers else base_url
        li = _build_listitem_ffmpeg(ffmpeg_url)
    else:
        li = _build_listitem_adaptive(base_url, merged_headers, license_key)

    if use_setresolved:
        xbmcplugin.setResolvedUrl(handle, True, li)
    else:
        xbmc.Player().play(li.getPath(), li)

# ===========================================================================
# EPG  helpers
# ===========================================================================

def _norm_ch_name(name):
    """Normalizza nome canale per confronto fuzzy."""
    n = name.lower()
    for drop in (' hd', ' fhd', ' 4k', ' full hd', '+', '.', '-'):
        n = n.replace(drop, ' ')
    n = (n.replace('à','a').replace('è','e').replace('é','e')
          .replace('ì','i').replace('ò','o').replace('ù','u'))
    return ' '.join(n.split())

def _ch_matches(epg_norm, ch_norm):
    """True se i nomi normalizzati si sovrappongono (fuzzy multi-livello)."""
    # 1. Uguaglianza esatta
    if epg_norm == ch_norm:
        return True
    # 2. Sottostringa
    if epg_norm in ch_norm or ch_norm in epg_norm:
        return True
    # 3. Senza spazi: "la 7"=="la7", "sky tg 24"=="sky tg24"
    e_ns = epg_norm.replace(' ', '')
    c_ns = ch_norm.replace(' ', '')
    if e_ns == c_ns or e_ns in c_ns or c_ns in e_ns:
        return True
    # 4. Varianti numeriche: "rai due"=="rai 2"
    num_map = {'uno':'1','due':'2','tre':'3','quattro':'4','cinque':'5',
               'sei':'6','sette':'7','otto':'8','nove':'9','zero':'0'}
    e2, c2 = epg_norm, ch_norm
    for word, digit in num_map.items():
        e2 = e2.replace(word, digit)
        c2 = c2.replace(word, digit)
    e2 = ' '.join(e2.split())
    c2 = ' '.join(c2.split())
    if e2 == c2 or e2 in c2 or c2 in e2:
        return True
    # 5. Intersezione parole: almeno il 60% delle parole dell'EPG compaiono
    #    nel canale → cattura "Sky Sport 24" in "SPORT 24 EXTRA VAVOO 6"
    epg_words = set(epg_norm.split())
    ch_words  = set(ch_norm.split())
    if epg_words:
        overlap = len(epg_words & ch_words)
        if overlap > 0 and overlap / len(epg_words) > 0.60:
            return True
        # stesso con varianti numeriche
        epg_w2 = set(e2.split())
        ch_w2  = set(c2.split())
        if epg_w2:
            ov2 = len(epg_w2 & ch_w2)
            if ov2 > 0 and ov2 / len(epg_w2) > 0.60:
                return True
    return False

def search_epg_matches(epg_title):
    """
    Cerca in playlist.json e zappr i canali che corrispondono a epg_title.
    Restituisce lista di dict con sezione, nome, url, resolver tipo/param.
    """
    epg_norm = _norm_ch_name(epg_title)
    matches  = []

    # Playlist.json
    try:
        req = urllib.request.Request(URL_JSON, headers={'User-Agent': UA_FALLBACK})
        with urllib.request.urlopen(req, timeout=15) as r:
            playlist = json.loads(r.read().decode())
        for ch in playlist:
            ch_norm = _norm_ch_name(ch.get('name', ''))
            if _ch_matches(epg_norm, ch_norm):
                matches.append({
                    'section': ch.get('category', 'Playlist'),
                    'name':    ch.get('name', ''),
                    'url':     ch.get('url', ''),
                    'license': ch.get('license', ''),
                    'thumb':   ch.get('icon', 'DefaultVideo.png'),
                    'tipo':    'playlist',
                    'param':   '',
                })
    except Exception as e:
        logga(f"EPG search playlist error: {e}")

    # Zappr
    try:
        zappr_data = json.loads(http_get(URL_ZAPPR, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15))
        for item in zappr_data.get('channels', []):
            ch_norm = _norm_ch_name(item.get('name', ''))
            if not _ch_matches(epg_norm, ch_norm):
                continue
            lcn     = item.get('lcn', '')
            tit     = item.get('name', '')
            url_str = item.get('url', '')
            tipo_ch = item.get('type', '')
            logo    = item.get('logo', 'DefaultVideo.png') or 'DefaultVideo.png'
            if tipo_ch not in ('hls', 'dash'):
                continue
            if tipo_ch == 'hls':
                if 'zappr://' in url_str:
                    r_tipo  = 'skytv'
                    r_param = url_str.split('/')[-1]
                else:
                    r_tipo  = 'amstaff'
                    r_param = url_str + '|0000'
            else:
                lic = item.get('license', '')
                if lic == 'clearkey':
                    url_str = url_str + '|' + item.get('licensedetails', '0000')
                else:
                    url_str = url_str + '|0000'
                r_tipo, r_param = 'amstaff', url_str
            matches.append({
                'section': 'DVB-T2 (zappr)',
                'name':    f"[{lcn}] {tit}",
                'url':     '',
                'license': '',
                'thumb':   logo,
                'tipo':    r_tipo,
                'param':   r_param,
            })
    except Exception as e:
        logga(f"EPG search zappr error: {e}")

    return matches

def fetch_epg_info(epg_id):
    """Recupera da guidatv.org il programma attualmente in onda."""
    try:
        page = http_get(f"https://guidatv.org/canali/{epg_id}",
                        headers={'User-Agent': 'Kodi/EPG-Addon', 'Accept-Language': 'it-IT,it;q=0.9'},
                        timeout=10)
        if not page:
            return ('', '', '')
        current_h = time.localtime().tm_hour
        current_m = time.localtime().tm_min
        rows = re.findall(r'(\d{1,2}:\d{2})[^<]*</[^>]+>[^<]*<[^>]+>[^<]*<[^>]+>([^<]{3,80})', page)
        if not rows:
            rows = re.findall(r'(\d{1,2}:\d{2})\s*[-\u2013]\s*([^\n<]{3,80})', page)
        best_title = ''
        best_time  = ''
        for t_str, title in rows:
            try:
                h, m    = int(t_str.split(':')[0]), int(t_str.split(':')[1])
                t_min   = h * 60 + m
                now_min = current_h * 60 + current_m
                if t_min <= now_min:
                    best_time  = t_str
                    best_title = title.strip()
            except:
                pass
        return (best_time, best_title, '')
    except Exception as e:
        logga(f"fetch_epg_info error: {e}")
        return ('', '', '')

# ===========================================================================
# ZAPPR  items
# ===========================================================================

def resolve_zappr_to_items():
    """Fetcha channels.zappr.stream e restituisce lista di item-dict per il menu."""
    items = []
    try:
        data = json.loads(http_get(URL_ZAPPR, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15))
        for item in data.get('channels', []):
            lcn     = item.get('lcn', '')
            tit     = item.get('name', '')
            url_str = item.get('url', '')
            tipo_ch = item.get('type', '')
            logo    = item.get('logo', '') or 'DefaultVideo.png'
            if tipo_ch not in ('hls', 'dash'):
                continue
            if tipo_ch == 'hls':
                if 'zappr://' in url_str:
                    myres = f"skyTV@@{url_str.split('/')[-1]}"
                else:
                    myres = f'amstaff@@{url_str}|0000'
            else:
                lic = item.get('license', '')
                if lic == 'clearkey':
                    url_str = url_str + '|' + item.get('licensedetails', '0000')
                else:
                    url_str = url_str + '|0000'
                myres = f'amstaff@@{url_str}'
            items.append({
                'title':     f'[COLOR gold][{lcn}] {tit}[/COLOR]',
                'thumbnail': logo,
                'fanart':    FANART_DEFAULT,
                'myresolve': myres,
                'info':      tipo_ch,
            })
            for chExt in item.get('hbbtv', []):
                sublcn  = chExt.get('sublcn', '')
                tit_ext = chExt.get('name', '')
                tipo_e  = chExt.get('type', '')
                url_e   = chExt.get('url', '')
                if tipo_e not in ('hls', 'dash'):
                    continue
                if tipo_e == 'hls':
                    myres_e = f'amstaff@@{url_e}|0000'
                else:
                    lic_e = item.get('license', '')
                    if lic_e == 'clearkey':
                        url_e = url_e + '|' + item.get('licensedetails', '0000')
                    else:
                        url_e = url_e + '|0000'
                    myres_e = f'amstaff@@{url_e}'
                items.append({
                    'title':     f'[COLOR cyan][{lcn}-{sublcn}] {tit_ext}[/COLOR]',
                    'thumbnail': logo,
                    'fanart':    FANART_DEFAULT,
                    'myresolve': myres_e,
                    'info':      tipo_e,
                })
    except Exception as e:
        logga(f"resolve_zappr_to_items error: {e}")
    return items

# ===========================================================================
# ZAPPR  menu  —  render items con myresolve amstaff/skyTV
# ===========================================================================

def _render_zappr_items(handle, items):
    """Renderizza items zappr: amstaff → action=zappr_play, skyTV → action=zappr_play."""
    for item in items:
        title    = strip_kodi_tags(item.get('title', ''))
        thumb    = item.get('thumbnail', 'DefaultVideo.png')
        fanart   = item.get('fanart', FANART_DEFAULT)
        info_str = item.get('info', '')
        myres    = item.get('myresolve', '')
        if not myres:
            continue
        li = xbmcgui.ListItem(label=title)
        li.setArt({'thumb': thumb, 'fanart': fanart})
        _tag = li.getVideoInfoTag()
        _tag.setTitle(title)
        _tag.setPlot(info_str)
        li.setProperty('IsPlayable', 'true')
        # Separa tipo@@param
        if '@@' in myres:
            tipo, param = myres.split('@@', 1)
        else:
            tipo, param = 'amstaff', myres
        query      = {'action': 'zappr_play', 'tipo': tipo, 'param': param}
        plugin_url = f"{sys.argv[0]}?{urllib.parse.urlencode(query)}"
        xbmcplugin.addDirectoryItem(handle, plugin_url, li, isFolder=False)

# ===========================================================================
# MAIN  run()
# ===========================================================================

def run():
    handle = int(sys.argv[1])
    params = dict(urllib.parse.parse_qsl(sys.argv[2][1:]))

    # -----------------------------------------------------------------------
    # AZIONE: PLAY  — stream dalla playlist.json
    # -----------------------------------------------------------------------
    if params.get('action') == 'play':
        original_url   = params.get('url', '')
        license_key    = params.get('license', '')
        url            = original_url
        original_lower = original_url.lower()

        # --- RESOLVER SKY: sky%40@ / sky%40%40 / sky@@ ---
        sky_par = None
        for marker in ('sky%40@', 'sky%40%40', 'sky@@'):
            if marker in original_lower:
                sky_par = original_url[original_lower.index(marker) + len(marker):]
                sky_par = sky_par.split('?')[0].split('&')[0].split('/')[0].strip()
                break
        if sky_par:
            logga(f"Sky resolver attivato per canale: {sky_par}")
            manifest, key64 = resolve_sky_channel(sky_par)
            if manifest:
                sky_headers = (f'User-Agent={SKY_UA_PLAY}'
                               f'&Referer={SKY_HOST}/&Origin={SKY_HOST}&verifypeer=false')
                li = xbmcgui.ListItem(path=manifest, offscreen=True)
                li.setContentLookup(False)
                li.setProperty('inputstream', 'inputstream.adaptive')
                li.setProperty('inputstream.adaptive.drm_legacy', f'org.w3.clearkey|{key64}')
                li.setProperty('inputstream.adaptive.stream_headers',   sky_headers)
                li.setProperty('inputstream.adaptive.manifest_headers', sky_headers)
                xbmcplugin.setResolvedUrl(handle, True, li)
            else:
                xbmcgui.Dialog().notification("Sky", f"Errore resolver: {sky_par}",
                                               xbmcgui.NOTIFICATION_ERROR, 4000)
                xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem())
            return

        # --- RESOLVER EUROTV: vavoo.to / kool.to / oha.to / huhu.to ---
        if any(d in original_lower for d in EUROTV_DOMAINS):
            try:
                resolved = resolve_eurotv(original_url)
                if resolved and resolved != original_url:
                    url = resolved
                    logga(f"EUROTV resolved → {url}")
            except Exception as e:
                logga(f"EUROTV resolve error (uso URL originale): {e}")

        # --- AUTO HEADERS basati sull'URL ORIGINALE ---
        auto_headers = None
        token = ""

        if "dazn" in original_lower or "dai.google.com" in original_lower:
            ua = urllib.parse.quote("Mozilla/5.0 (Web0S; Linux/SmartTV) AppleWebKit/537.41 (KHTML, like Gecko) Large Screen Safari/537.41 LG Browser/7.00.00(LGE; WEBOS1; 05.06.10; 1); webOS.TV-2014; LG NetCast.TV-2013 Compatible (LGE, WEBOS1, wireless)")
            host = "https://www.dazn.com"
            auto_headers = f'User-Agent={ua}&Referer={host}/&Origin={host}'
            if token:
                ua = urllib.parse.quote_plus("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36")
                auto_headers = f'{token}&referer={host}/&origin={host}&user-agent={ua}'
        elif "lba-ew" in original_lower:
            ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:143.0) Gecko/20100101 Firefox/143.0"
            host = "https://www.lbatv.com"
            auto_headers = f'User-Agent={ua}&Referer={host}/&Origin={host}&verifypeer=false'
        elif "discovery" in original_lower:
            ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0"
            host = "https://www.discoveryplus.com"
            auto_headers = f'User-Agent={ua}&Referer={host}/&Origin={host}&verifypeer=false'
        elif "nowitlin" in original_lower:
            ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
            host = "https://www.nowtv.it"
            auto_headers = f'User-Agent={ua}&Referer={host}/&Origin={host}&verifypeer=false'
        elif "vodafone.pt" in original_lower:
            ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0"
            host = "http://rr.cdn.vodafone.pt"
            auto_headers = f'User-Agent={ua}&Referer={host}/&Origin={host}&verifypeer=false'
        elif "clarovideo.com" in original_lower:
            ua = urllib.parse.quote_plus("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 OPR/124.0.0.0")
            host = "https://clarovideo.com"
            auto_headers = f'User-Agent={ua}&Referer={host}/&Origin={host}&verifypeer=false'
        elif "starzplayarabia" in original_lower:
            ua = urllib.parse.quote("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 OPR/120.0.0.0")
            auto_headers = f'User-Agent={ua}&verifypeer=false'
        elif any(d in original_lower for d in EUROTV_DOMAINS):
            ua   = "Mozilla/5.0 (X11; Linux armv7l) AppleWebKit/537.36 (KHTML, like Gecko) QtWebEngine/5.9.7 Chrome/56.0.2924.122 Safari/537.36 Sky_STB_ST412_2018/1.0.0 (Sky, EM150UK,)"
            host = "https://vavoo.to"
            auto_headers = f'User-Agent={ua}&Referer={host}/&Origin={host}&Connection=keep-alive'

        # --- SELEZIONE MANUALE ---
        if auto_headers:
            selected_headers = auto_headers
        else:
            user_agents = get_remote_uas()
            dialog  = xbmcgui.Dialog()
            scelta  = dialog.select("Scegli User-Agent", user_agents)
            if scelta == -1:
                xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem())
                return
            selected_headers = f"User-Agent={user_agents[scelta]}"

        # --- PLAY (con dialog HLS) ---
        _play_url(handle, url, selected_headers, license_key, use_setresolved=True)
        return

    # -----------------------------------------------------------------------
    # AZIONE: ZAPPR_PLAY  — risolve e riproduce un canale zappr
    # -----------------------------------------------------------------------
    if params.get('action') == 'zappr_play':
        tipo  = params.get('tipo', '')
        param = params.get('param', '')
        logga(f"zappr_play tipo={tipo} param={param[:80]}")
        result_type, result_data, _ = dispatch_resolver(tipo, param)
        if result_type == 'url':
            url = result_data
            # Separa eventuale license key inline
            if '|' in url:
                parts = url.split('|', 1)
                base  = parts[0]
                lic   = parts[1] if parts[1] not in ('0000', '') else ''
            else:
                base, lic = url, ''
            headers_str = _auto_headers_for_url(base.lower()) or AMSTAFF_HEADERS
            _play_url(handle, base, headers_str, lic, use_setresolved=True)
        else:
            xbmcgui.Dialog().notification("Errore", result_data,
                                           xbmcgui.NOTIFICATION_ERROR, 4000)
            xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem())
        return

    # -----------------------------------------------------------------------
    # AZIONE: EPG_LIST  — lista canali EPG
    # -----------------------------------------------------------------------
    if params.get('action') == 'epg_list':
        logga("EPG list")
        try:
            raw   = makeJob(URL_EPG_LIST)
            items = json.loads(raw).get('items', [])
        except Exception as e:
            logga(f"EPG list error: {e}")
            items = []
        for item in items:
            raw_title   = item.get('title', '')
            myres       = item.get('myresolve', '')
            epg_id      = myres.split('@@', 1)[1] if myres.startswith('epg@@') else ''
            clean_title = strip_kodi_tags(raw_title)
            thumb  = item.get('thumbnail', 'DefaultVideo.png')
            fanart = item.get('fanart', FANART_DEFAULT)
            info   = item.get('info', '')
            label  = f"{info}  {clean_title}" if info else clean_title
            li = xbmcgui.ListItem(label=label)
            li.setArt({'thumb': thumb, 'fanart': fanart})
            _tag = li.getVideoInfoTag()
            _tag.setTitle(clean_title)
            _tag.setPlot(info)
            query      = {'action': 'epg_search', 'epg_title': clean_title,
                          'epg_id': epg_id, 'epg_thumb': thumb}
            plugin_url = f"{sys.argv[0]}?{urllib.parse.urlencode(query)}"
            xbmcplugin.addDirectoryItem(handle, plugin_url, li, isFolder=True)
        xbmcplugin.endOfDirectory(handle)
        return

    # -----------------------------------------------------------------------
    # AZIONE: EPG_SEARCH  — cerca canale, dialog selezione, resolver, play
    # -----------------------------------------------------------------------
    if params.get('action') == 'epg_search':
        epg_title = params.get('epg_title', '')
        epg_id    = params.get('epg_id', '')
        epg_thumb = params.get('epg_thumb', 'DefaultVideo.png')
        logga(f"EPG search: {epg_title} (id={epg_id})")

        dialog = xbmcgui.Dialog()
        dialog.notification("EPG", f"Ricerca: {epg_title}...",
                            xbmcgui.NOTIFICATION_INFO, 2000)

        matches = search_epg_matches(epg_title)

        if not matches:
            dialog.notification("EPG", "Nessun canale trovato",
                                xbmcgui.NOTIFICATION_WARNING, 3000)
            xbmcplugin.endOfDirectory(handle, succeeded=False)
            return

        labels = [f"{m['section']} > {m['name']}" for m in matches]
        scelta = dialog.select(f"EPG - {epg_title}", labels)
        if scelta == -1:
            xbmcplugin.endOfDirectory(handle, succeeded=False)
            return

        chosen = matches[scelta]

        # Recupera info EPG
        epg_time, epg_prog, _ = ('', '', '')
        if epg_id:
            epg_time, epg_prog, _ = fetch_epg_info(epg_id)
        epg_plot = f"[{epg_time}] {epg_prog}" if epg_prog else epg_title

        # --- Risoluzione ---
        if chosen['tipo'] == 'playlist':
            url           = chosen['url']
            lic           = chosen['license']
            original_lower = url.lower()

            # Sky detector
            sky_par = None
            for marker in ('sky%40@', 'sky%40%40', 'sky@@'):
                if marker in original_lower:
                    sky_par = url[original_lower.index(marker) + len(marker):]
                    sky_par = sky_par.split('?')[0].split('&')[0].split('/')[0].strip()
                    break
            if sky_par:
                manifest, key64 = resolve_sky_channel(sky_par)
                if manifest:
                    sky_h = f'User-Agent={SKY_UA_PLAY}&Referer={SKY_HOST}/&Origin={SKY_HOST}&verifypeer=false'
                    li = xbmcgui.ListItem(path=manifest, offscreen=True)
                    li.setContentLookup(False)
                    li.setProperty('inputstream', 'inputstream.adaptive')
                    li.setProperty('inputstream.adaptive.drm_legacy', f'org.w3.clearkey|{key64}')
                    li.setProperty('inputstream.adaptive.stream_headers',   sky_h)
                    li.setProperty('inputstream.adaptive.manifest_headers', sky_h)
                    _tag = li.getVideoInfoTag()
                    _tag.setTitle(chosen['name'])
                    _tag.setPlot(epg_plot)
                    xbmc.Player().play(li.getPath(), li)
                else:
                    dialog.notification("EPG Sky", f"Errore resolver: {sky_par}",
                                        xbmcgui.NOTIFICATION_ERROR, 3000)
                xbmcplugin.endOfDirectory(handle, succeeded=False)
                return

            # EUROTV
            if any(d in original_lower for d in EUROTV_DOMAINS):
                resolved = resolve_eurotv(url)
                if resolved and resolved != url:
                    url = resolved

            headers_str = _auto_headers_for_url(original_lower) or f'User-Agent={UA_FALLBACK}'

            # Costruisce URL finale con headers, poi play con dialog
            if '|' in url:
                base_url, _ = url.split('|', 1)
            else:
                base_url = url
            url_check = base_url.lower()
            if '.m3u8' in url_check and not lic:
                choice = dialog.select(
                    "Scegli player",
                    ["\u25b6 FFMPEG Direct (consigliato)", "\u25b6 InputStream Adaptive"]
                )
                if choice == -1:
                    xbmcplugin.endOfDirectory(handle, succeeded=False)
                    return
                if choice == 0:
                    ffmpeg_url = f"{base_url}|{headers_str}" if headers_str else base_url
                    li = _build_listitem_ffmpeg(ffmpeg_url)
                else:
                    li = _build_listitem_adaptive(base_url, headers_str, lic)
            else:
                li = _build_listitem_adaptive(base_url, headers_str, lic)
                if '.mpd' in url_check:
                    li.setMimeType('application/dash+xml')
                elif '.m3u8' in url_check:
                    li.setMimeType('application/vnd.apple.mpegurl')
            _tag = li.getVideoInfoTag()
            _tag.setTitle(chosen['name'])
            _tag.setPlot(epg_plot)
            xbmc.Player().play(li.getPath(), li)

        else:
            # Resolver (amstaff, skytv da zappr)
            result_type, result_data, _ = dispatch_resolver(chosen['tipo'], chosen['param'])
            if result_type != 'url':
                dialog.notification("EPG", f"Errore: {result_data}",
                                    xbmcgui.NOTIFICATION_ERROR, 3000)
                xbmcplugin.endOfDirectory(handle, succeeded=False)
                return

            url   = result_data
            if '|' in url:
                parts    = url.split('|', 1)
                base_url = parts[0]
                lic      = parts[1] if parts[1] not in ('0000', '') else ''
            else:
                base_url, lic = url, ''

            url_check   = base_url.lower()
            headers_str = _auto_headers_for_url(url_check) or AMSTAFF_HEADERS

            if '.m3u8' in url_check and not lic:
                choice = dialog.select(
                    "Scegli player",
                    ["\u25b6 FFMPEG Direct (consigliato)", "\u25b6 InputStream Adaptive"]
                )
                if choice == -1:
                    xbmcplugin.endOfDirectory(handle, succeeded=False)
                    return
                if choice == 0:
                    ffmpeg_url = f"{base_url}|{headers_str}"
                    li = _build_listitem_ffmpeg(ffmpeg_url)
                else:
                    li = _build_listitem_adaptive(base_url, headers_str, lic)
            else:
                li = _build_listitem_adaptive(base_url, headers_str, lic)
            _tag = li.getVideoInfoTag()
            _tag.setTitle(chosen['name'])
            _tag.setPlot(epg_plot)
            xbmc.Player().play(li.getPath(), li)

        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return

    # -----------------------------------------------------------------------
    # AZIONE: ZAPPR_MENU  — canali DVB-T2
    # -----------------------------------------------------------------------
    if params.get('action') == 'zappr_menu':
        logga("Zappr menu")
        items = resolve_zappr_to_items()
        _render_zappr_items(handle, items)
        xbmcplugin.endOfDirectory(handle)
        return

    # -----------------------------------------------------------------------
    # NAVIGAZIONE PLAYLIST NORMALE
    # -----------------------------------------------------------------------
    action = params.get('action')

    try:
        req = urllib.request.Request(URL_JSON, headers={'User-Agent': UA_FALLBACK})
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read().decode())
    except:
        data = []

    if not action:
        # MENU PRINCIPALE: EPG → DVB-T2 → categorie playlist → MandraKodi

        li_epg = xbmcgui.ListItem(label="\U0001f4cb EPG")
        li_epg.setArt({'icon': 'DefaultFolder.png'})
        xbmcplugin.addDirectoryItem(
            handle,
            f"{sys.argv[0]}?{urllib.parse.urlencode({'action': 'epg_list'})}",
            li_epg, isFolder=True)

        li_z = xbmcgui.ListItem(label="\U0001f4e1 DVB-T2 (zappr)")
        li_z.setArt({'icon': 'DefaultFolder.png'})
        xbmcplugin.addDirectoryItem(
            handle,
            f"{sys.argv[0]}?{urllib.parse.urlencode({'action': 'zappr_menu'})}",
            li_z, isFolder=True)

        categories = []
        for ch in data:
            cat = ch.get('category', 'Altro')
            if cat not in categories:
                categories.append(cat)
        for cat in categories:
            li = xbmcgui.ListItem(label=cat)
            li.setArt({'icon': 'DefaultFolder.png'})
            xbmcplugin.addDirectoryItem(
                handle,
                f"{sys.argv[0]}?{urllib.parse.urlencode({'action': 'category', 'category': cat})}",
                li, isFolder=True)

        li_m = xbmcgui.ListItem(label="\U0001f4fa MandraKodi")
        li_m.setArt({'icon': 'DefaultFolder.png'})
        xbmcplugin.addDirectoryItem(handle, "plugin://plugin.video.mandrakodi/", li_m, isFolder=True)

    elif action == 'category':
        selected_cat = params.get('category')
        for ch in data:
            if ch.get('category', 'Altro') == selected_cat:
                li = xbmcgui.ListItem(label=ch['name'])
                li.getVideoInfoTag().setTitle(ch['name'])
                li.setArt({'icon': 'DefaultVideo.png'})
                li.setProperty('IsPlayable', 'true')
                lic   = ch.get('license', '')
                query = {'action': 'play', 'url': ch['url'], 'license': lic}
                xbmcplugin.addDirectoryItem(
                    handle,
                    f"{sys.argv[0]}?{urllib.parse.urlencode(query)}",
                    li, isFolder=False)

    xbmcplugin.endOfDirectory(handle)


if __name__ == '__main__':
    run()
