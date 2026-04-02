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

# VERSIONE 1.0.39 - 2026-04-02

URL_JSON   = "https://raw.githubusercontent.com/riccamariofrancesco-cell/mariofr-repo/refs/heads/main/playlist.json"
URL_UA_TXT = "https://raw.githubusercontent.com/riccamariofrancesco-cell/mariofr-repo/refs/heads/main/user_agents.txt"
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

# Resolver che restituiscono JSON sub-menu (isFolder=True, nessun dialog di player)
FOLDER_RESOLVER_TYPES = {
    'taxi', 'anyplay', 'toonita', 'm3uplus', 'ppv', 'daddycode',
    'webcam', 'sansat', 'mototv', 'sportzx', 'sports99',
    'seriesc', 'vavooch', 'imdblist', 'rocktalk',
}

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

def http_post(url, data, headers=None, timeout=20):
    hdr = {'User-Agent': UA_FALLBACK, 'Content-Type': 'application/x-www-form-urlencoded'}
    if headers:
        hdr.update(headers)
    try:
        if isinstance(data, dict):
            payload = urllib.parse.urlencode(data).encode('utf-8')
        else:
            payload = data.encode('utf-8') if isinstance(data, str) else data
        req = urllib.request.Request(url, data=payload, headers=hdr, method='POST')
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode('utf-8', errors='replace')
    except Exception as e:
        logga(f"http_post ERROR [{url}]: {e}")
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

def xor_decrypt(data_b64, key):
    """XOR decrypt con chiave ripetuta, input base64 (anche URL-safe)."""
    padded = data_b64.strip().replace(' ', '+')
    padded += '=' * ((4 - len(padded) % 4) % 4)
    data      = base64.b64decode(padded)
    key_bytes = key.encode('utf-8')
    return bytearray(b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(data)).decode('utf-8')

SKY_SECRET = "my_secret_key"
SKY_UA_API = "MandraKodi2@@2.2.1@@@@A7B9X2"
SKY_UA_PLAY = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
SKY_HOST   = "https://www.nowtv.it"

def resolve_sky_channel(par_in):
    """
    Chiama l'API Sky MandraKodi, decripta XOR, restituisce (manifest, kid:key).
    parIn = nome canale, es. 'skysport24'
    """
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

def _mandra_url(url):
    """Risolve URL relativi MandraKodi in assoluti."""
    if not url:
        return ''
    if url.startswith('http'):
        return url
    if url.startswith('?'):
        return URL_MANDRA + url
    return URL_MANDRA + '?' + url

def fetch_mandra_json(url):
    """Scarica e parsa JSON MandraKodi. Gestisce sia lista radice che {"items":[...]}."""
    try:
        content = makeJob(url)
        if not content:
            return []
        data = json.loads(content)
        if isinstance(data, list):
            return data
        return data.get('items', [])
    except Exception as e:
        logga(f"fetch_mandra_json ERROR [{url}]: {e}")
        return []

# ===========================================================================
# PARSER myresolve
# ===========================================================================

def parse_myresolve(myresolve_str):
    if '@@' not in myresolve_str:
        return ('unknown', myresolve_str, '')
    tipo, dati = myresolve_str.split('@@', 1)
    tipo_lower = tipo.lower().strip()
    if tipo_lower == 'amstaff':
        raw = dati.strip()
        if not raw.startswith('http'):
            try:
                padded = raw + '=' * ((4 - len(raw) % 4) % 4)
                raw = base64.b64decode(padded).decode('utf-8').strip()
            except Exception as e:
                logga(f"amstaff base64 error: {e}")
        parts = raw.split('|', 1)
        url = parts[0].strip()
        lic = parts[1].strip() if len(parts) > 1 else ''
        return ('amstaff', url, lic)
    return (tipo_lower, dati.strip(), '')

# ===========================================================================
# RESOLVERS - stream diretti
# ===========================================================================

def resolve_freeshot(code):
    logga(f"resolve_freeshot: {code}")
    headers = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 OPR/120.0.0.0",
        'Referer': "https://thisnot.business/"
    }
    page = http_get(f"https://popcdn.day/player/{code}", headers=headers)
    m = re.search(r'currentToken:\s*"(.*?)"', page)
    if not m:
        logga(f"freeshot: token non trovato per '{code}'")
        return ('', '')
    token = m.group(1)
    url   = f"https://planetary.lovecdn.ru/{code}/tracks-v1a1/mono.m3u8?token={token}"
    ref   = "https://popcdn.day/"
    logga(f"freeshot URL: {url}")
    return (url, ref)

def resolve_mediahosting(stream_id):
    logga(f"resolve_mediahosting: {stream_id}")
    page = http_get(f"https://mediahosting.space/embed/player?stream={stream_id}",
                    headers={'Referer': "https://mediahosting.space/"})
    m = re.search(r'<source src="(.*?)"', page)
    if m:
        return (m.group(1), "https://mediahosting.space/")
    return ('', '')

def resolve_streamtp(stream_id):
    logga(f"resolve_streamtp: {stream_id}")
    page = http_get(f"https://streamtp501.com/global1.php?stream={stream_id}",
                    headers={'Referer': "https://streamtp501.com/"})
    m = re.search(r'playbackURL\s*=\s*"(.*?)"', page)
    if m:
        return (m.group(1), "https://streamtp501.com/")
    return ('', '')

def resolve_tvapp(channel_name):
    logga(f"resolve_tvapp: {channel_name}")
    headers = {'User-Agent': "Mozilla/5.0", 'Referer': "https://thetvapp.to/"}
    page1 = http_get(f"https://thetvapp.to/tv/{channel_name}", headers=headers)
    m = re.search(r'<div id="stream_name" name="(.*?)">', page1)
    if not m:
        return ('', '')
    stream_key = m.group(1)
    page2 = http_get(f"https://thetvapp.to/token/{stream_key}", headers=headers)
    try:
        url = json.loads(page2).get('url', '')
        return (url, "https://thetvapp.to/")
    except:
        return ('', '')

def resolve_skytv(channel_id):
    logga(f"resolve_skytv: {channel_id}")
    page = http_get(f"https://apid.sky.it/vdp/v1/getLivestream?id={channel_id}&isMobile=false")
    try:
        url = json.loads(page).get('streaming_url', '')
        return (url, "https://www.sky.it/")
    except:
        return ('', '')

def resolve_antenacode(code):
    logga(f"resolve_antenacode: {code}")
    ua  = "Mozilla/5.0 (iPad; CPU OS 133 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
    url = f"https://webufffit.mizhls.ru/lb/prima{code}/index.m3u8"
    ref = "https://1qwebplay.xyz/"
    return (url, ref)

def resolve_antena(page_url):
    logga(f"resolve_antena: {page_url}")
    page = http_get(page_url, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://antenasports.ru/'})
    iframe_url = preg_match(page, r'iframe\s*src="([^"]+)')
    arr = iframe_url.split("=")
    id_ch = arr[1] if len(arr) > 1 else ''
    if not id_ch:
        return ('', '')
    url = f"https://webufffit.mizhls.ru/lb/{id_ch}/index.m3u8"
    return (url, "https://1qwebplay.xyz/")

def resolve_koolto(code):
    logga(f"resolve_koolto: {code}")
    url = f"https://www.kool.to/play/{code}/index.m3u8"
    return (url, "https://www.kool.to/")

def resolve_pulive(stream_id):
    logga(f"resolve_pulive: {stream_id}")
    url_page = f"https://pulivetv146.com/player.html?id={stream_id}"
    page = http_get(url_page, headers={'User-Agent': 'Mozilla/5.0'})
    txt  = preg_match(page, r'window\.config=(.*?)<\/script>')
    x    = txt.split("match:")
    if len(x) < 2:
        return ('', '')
    src = preg_match(x[1], r'source:"(.*?)"')
    return (src, "https://pulivetv146.com/") if src else ('', '')

def resolve_vudeo(vid_id):
    logga(f"resolve_vudeo: {vid_id}")
    page_in = f"https://vudeo.ws/{vid_id}.html"
    page = http_get(page_in, headers={'User-Agent': 'iPad', 'Referer': page_in})
    if '<b>File Not Found</b>' in page:
        return ('', '')
    src = preg_match(page, r'sources:\s*\["(.*?)"\]')
    return (src, page_in) if src else ('', '')

def resolve_voe(page_url):
    logga(f"resolve_voe: {page_url}")
    page = http_get(page_url, headers={'User-Agent': 'iPad', 'Referer': page_url})
    src = preg_match(page, r"'hls':\s*'(.*?)'")
    if not src:
        return ('', '')
    try:
        url = base64.b64decode(src).decode('utf-8')
        return (url, page_url)
    except:
        return ('', '')

def resolve_sibnet(video_id):
    logga(f"resolve_sibnet: {video_id}")
    url_p = f"https://video.sibnet.ru/shell.php?videoid={video_id}"
    page  = http_get(url_p, headers={'User-Agent': 'iPad', 'Referer': 'https://video.sibnet.ru/'})
    iframe_url = preg_match(page, r'player\.src\(\[\{src:\s*"(.*?)",\s*type')
    if not iframe_url:
        return ('', '')
    return (f"https://video.sibnet.ru{iframe_url}", "https://video.sibnet.ru/")

def resolve_streamtape(page_url):
    logga(f"resolve_streamtape: {page_url}")
    page = http_get(urllib.parse.unquote(page_url),
                    headers={'User-Agent': UA_FALLBACK, 'Referer': 'https://toonitalia.green/'})
    html_code   = preg_match(page, r'<\/video><script>(.*?)<\/body>')
    iframe_url  = preg_match(html_code, r'style="display:none;">(.*?)<\/div>')
    if not iframe_url:
        return ('', '')
    link1    = iframe_url.split('&token=')
    link_pre = link1[0]
    info1    = preg_match(page, r'<script>document\.getElementById(.*?)<\/script>')
    info     = info1.split(';')[0]
    tkn      = preg_match(info, r"&token=(.*?)'")
    link_split = link_pre.split("?")[1] if "?" in link_pre else link_pre
    final = f"https://streamta.pe/get_video?{link_split}&token={tkn}&stream=1"
    return (final, "https://streamta.pe/")

def resolve_markky(page_url):
    logga(f"resolve_markky: {page_url}")
    page = http_get(page_url, headers={'User-Agent': UA_FALLBACK, 'Referer': 'https://markkystreams.com/'})
    url  = preg_match(page, r'source:\s*"(.*?)"')
    return (url, page_url) if url else ('', '')

def resolve_daddylive_direct(code):
    logga(f"resolve_daddylive_direct: {code}")
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 OPR/124.0.0.0'
    try:
        iframe_url = f"https://codepcplay.fun/premiumtv/daddyhd.php?id={code}"
        js = http_get(iframe_url, headers={'User-Agent': user_agent, 'Referer': 'https://dlhd.link/'})
        pattern = r'const\s+var_[a-zA-Z0-9]+\s*=\s*["\']([^"\']+)["\']'
        matches = re.findall(pattern, js)
        if len(matches) < 5:
            return ('', '')
        auth_token, channel_key = matches[0], matches[1]
        fingerprint  = f"{user_agent}|1920x1080|Europe/Rome|it-IT"
        sign_data    = f"{channel_key}|{matches[2]}|{auth_token}|{user_agent}|{fingerprint}"
        client_token = base64.b64encode(sign_data.encode('utf-8')).decode('ascii')
        lookup_url   = f"https://chevy.giokko.ru/server_lookup?channel_id={channel_key}"
        lookup_resp  = http_get(lookup_url, headers={
            'User-Agent': user_agent, 'Referer': 'https://codepcplay.fun',
            'Origin': 'https://codepcplay.fun', 'Authorization': f'Bearer {auth_token}',
            'X-Channel-Key': channel_key, 'X-Client-Token': client_token
        })
        server_key = preg_match(lookup_resp, r'"server_key":"(.*?)"')
        if not server_key:
            return ('', '')
        if server_key == 'top1/cdn':
            stream_url = f'https://top1.kiko2.ru/top1/cdn/{channel_key}/mono.css'
        else:
            stream_url = f'https://{server_key}new.kiko2.ru/{server_key}/{channel_key}/mono.css'
        return (stream_url, "https://codepcplay.fun/")
    except Exception as e:
        logga(f"resolve_daddylive_direct error: {e}")
        return ('', '')

def resolve_daddy(page_url):
    logga(f"resolve_daddy: {page_url}")
    page = http_get(page_url, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://daddylivestream.com/'})
    iframe_url = preg_match(page, r'iframe\s*src="([^"]+)')
    if iframe_url.endswith(".mp4"):
        return (iframe_url, page_url)
    if iframe_url.startswith("http"):
        page2 = http_get(iframe_url.replace("caq21harderv991gpluralplay", "forcedtoplay"),
                          headers={'User-Agent': 'Mozilla/5.0', 'Referer': page_url})
        iframe_url2 = preg_match(page2, r'iframe\s*src="([^"]+)')
        if not iframe_url2:
            video_url = preg_match(page2.replace('//source:', '//source_no:'), "source:'(.*?)'")
            if video_url:
                ip64 = "MTUxLjI1LjIzMS43MQ=="
                return (f"{video_url}?auth={ip64}", page_url)
        if iframe_url2.startswith("http"):
            page3 = http_get(iframe_url2, headers={'User-Agent': 'Mozilla/5.0',
                                                    'Referer': 'https://widevine.licenses4.me/'})
            video_url = preg_match(page3, r"Clappr\.Player[\w\W]*?\.source:'(.*?)'")
            if "|" in video_url:
                video_url = video_url.split("?auth")[0]
            if video_url:
                ip64 = "MTUxLjI1LjIzMS43MQ=="
                return (f"{video_url}?auth={ip64}", page_url)
    try:
        v_id = page_url.split("stream-")[1].split(".")[0]
        return resolve_daddylive_direct(v_id)
    except:
        return ('', '')

def resolve_wikisport(param):
    logga(f"resolve_wikisport: {param}")
    ua = UA_FALLBACK
    page_url = f"https://fiveyardlab.com/wiki.php?player=desktop&live={param}"
    page = http_get(page_url, headers={'User-Agent': ua, 'Referer': 'https://wikisport.click'})
    iframe_url = preg_match(page, r'return\(\[(.*?)\]')
    final = iframe_url.replace('"', '').replace(',', '').replace('\\', '').replace('https:////', 'https://')
    return (final, "https://wikisport.click/")

def resolve_vividmosaica(param):
    logga(f"resolve_vividmosaica: {param}")
    player_url = f"https://vividmosaica.com/embed3.php?player=desktop&live=do{param}"
    page = http_get(player_url, headers={'Referer': 'https://l2l2.link/'})
    match = re.search(r'return\s*\(\s*\[(.*?)\]\s*', page, re.DOTALL)
    src = "ignore"
    if match:
        content = match.group(1)
        src = content.replace('"', '').replace(',', '').replace('\\/', '/').replace('https:////', 'https://')
    return (src, "https://vividmosaica.com/")

def resolve_daily(video_id):
    logga(f"resolve_daily: {video_id}")
    url_api = f"https://www.dailymotion.com/player/metadata/video/{video_id}"
    data_str = http_get(url_api, headers={'Referer': 'https://www.dailymotion.com'})
    try:
        url = json.loads(data_str)["qualities"]["auto"][0]["url"]
        return (url, "https://www.dailymotion.com/")
    except:
        return ('', '')

def resolve_livetv(page_url):
    logga(f"resolve_livetv: {page_url}")
    page = http_get(page_url)
    flat = page.replace("\n","").replace("\r","").replace("\t","")
    src  = preg_match(flat, r'<iframe\s+allowFullScreen="true"[^>]+src="([^"]*)')
    if not src:
        return ('', '')
    if src.startswith("//"):
        src = "https:" + src
    if "topembed.pw" in src:
        arr      = src.split("/")
        ext_code = arr[-1].replace("ex", "bet")
        srv_resp = http_get(f"https://topembed.pw/server_lookup.php?channel_id={ext_code}")
        try:
            server_key = json.loads(srv_resp).get("server_key", "")
        except:
            server_key = ""
        if server_key == "top1/cdn":
            final = f"https://top1.kiko2.ru/top1/cdn/{ext_code}/mono.m3u8"
        elif server_key:
            final = f"https://{server_key}new.kiko2.ru/{server_key}/{ext_code}/mono.m3u8"
        else:
            return ('', '')
    else:
        arr_p2 = src.split("play?url=")
        if len(arr_p2) > 1:
            final = urllib.parse.unquote(arr_p2[1])
        else:
            page2 = http_get(src)
            final = preg_match(page2, "source: '(.*?)'")
    host_parts = src.split("/")
    host = host_parts[0] + "//" + host_parts[2] if len(host_parts) >= 3 else ""
    return (final, host + "/")

def resolve_hunterjs(page_url):
    logga(f"resolve_hunterjs: {page_url}")
    _0xce1e = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ+/"

    def duf(d, e, f):
        g = list(_0xce1e)
        h = g[0:e]
        i_list = g[0:f]
        d = list(d)[::-1]
        j = 0
        for c, b in enumerate(d):
            if b in h:
                j = j + h.index(b) * (e ** c)
        k = ""
        while j > 0:
            k = i_list[j % f] + k
            j = (j - (j % f)) // f
        return int(k) or 0

    def hunter(h, u, n, t, e, r):
        r_str = ""
        i = 0
        while i < len(h):
            s = ""
            while h[i] != n[e]:
                s += h[i]
                i += 1
            j = 0
            while j < len(n):
                s = s.replace(n[j], str(j))
                j += 1
            r_str += chr(duf(s, e, 10) - t)
            i += 1
        return r_str

    page = http_get(page_url, headers={'User-Agent': 'iPad', 'Referer': page_url})
    flat_page = page.replace("\n","").replace("\r","").replace("\t","")
    tit = preg_match(flat_page, r'<div id="player"><\/div><script>(.*?)\)\)<\/script>')
    if not tit:
        return ('', '')
    sd = tit.split("(")
    code = sd[-1]
    code_list = code.split(',')
    for idx, c in enumerate(code_list):
        c2 = c.strip().replace('"', '')
        if c2.isdigit():
            code_list[idx] = int(c2)
        else:
            code_list[idx] = c2
    try:
        result = hunter(*code_list)
        link   = preg_match(result, "source: '(.*?)'")
        return (link, page_url) if link else ('', '')
    except Exception as e:
        logga(f"hunterjs decode error: {e}")
        return ('', '')

def resolve_scws(scws_id):
    logga(f"resolve_scws: {scws_id}")
    from hashlib import md5 as _md5
    from base64 import b64encode as _b64e
    try:
        ip_page   = http_get("http://test34344.herokuapp.com/getMyIp.php")
        client_ip = json.loads(ip_page).get("client_ip", "")
    except:
        client_ip = get_my_ip()
    expires = int(time.time() + 172800)
    token   = (_b64e(_md5(f'{expires}{client_ip} Yc8U6r8KjAKAepEA'.encode()).digest())
               .decode().replace('=', '').replace('+', '-').replace('/', '_'))
    url = f'https://scws.work/master/{scws_id}?token={token}&expires={expires}&canCast=1&b=1&n=1'
    return (url, "https://scws.work/")

def resolve_scommunity(param):
    logga(f"resolve_scommunity: {param}")
    sc_url = "https://raw.githubusercontent.com/mandrakodi/mandrakodi.github.io/main/data/cs_url.txt"
    base   = makeRequest(sc_url).replace("\n", '') + "watch/"
    url_comm = base + param
    http_get(url_comm)
    time.sleep(2.5)
    page = http_get(url_comm)
    data_json = preg_match(page, r'<div id="app" data-page="(.*?)"?>').replace('&quot;', '"')
    try:
        arr_j   = json.loads(data_json)
        scws_id = str(arr_j["props"]["episode"]["scws_id"])
        return resolve_scws(scws_id)
    except Exception as e:
        logga(f"scommunity error: {e}")
        return ('', '')

def resolve_vavoo(vavoo_url):
    logga(f"resolve_vavoo: {vavoo_url}")
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
                {'language': 'de', 'region': 'AT', 'url': vavoo_url, 'clientVersion': '3.0.2'},
                headers={'user-agent': 'MediaHubMX/2', 'accept': 'application/json',
                         'mediahubmx-signature': signature}, timeout=10)
            if res_resp:
                result = json.loads(res_resp)
                if isinstance(result, list) and result and result[0].get('url'):
                    return result[0]['url']
                elif isinstance(result, dict) and result.get('url'):
                    return result['url']
    except Exception as e:
        logga(f"vavoo API error: {e}")
    try:
        req = urllib.request.Request(vavoo_url, headers={'User-Agent': 'VAVOO/2.6'})
        with urllib.request.urlopen(req, timeout=15) as r:
            final_url = r.geturl()
            if final_url != vavoo_url:
                return final_url
    except Exception as e:
        logga(f"vavoo redirect error: {e}")
    return vavoo_url

def _try_jsunpack_resolve(page_url, referer=''):
    try:
        import jsunpack
        refe = referer or page_url
        page = http_get(page_url, headers={'User-Agent': UA_FALLBACK, 'Referer': refe})
        find = re.findall(r'eval\(function(.+?.+)', page)
        if not find:
            return ('', '')
        unpack = jsunpack.unpack(find[0])
        for pattern in (r'src:"([^"]*)', r'file:"([^"]*)', r'src="([^"]*)', r'source:"([^"]*)'):
            m = re.search(pattern, unpack)
            if m:
                url = m.group(1)
                url = ('https:' + url) if url.startswith('//') else url
                return (url, page_url)
        return ('', '')
    except ImportError:
        logga("jsunpack non disponibile")
        return ('', '')
    except Exception as e:
        logga(f"jsunpack error: {e}")
        return ('', '')

# ===========================================================================
# RESOLVERS - JSON sub-menu
# ===========================================================================

def resolve_ppv(page_url):
    logga(f"resolve_ppv: {page_url}")
    ua   = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 OPR/124.0.0.0'
    page = http_get(page_url, headers={'User-Agent': ua, 'Referer': 'https://ppvs.to/'})
    match = re.findall(r'const src = atob\("(.*?)"\)', page)
    if not match:
        return None
    stream_url = base64.b64decode(match[0]).decode('utf-8')
    link = stream_url.replace("index.m3u8",
            f"tracks-v1a1/mono.ts.m3u8|Referer=https://playembed.top/&Origin=https://playembed.top&User-Agent={ua}")
    items = [
        {'title': '[COLOR lime]▶ PLAY STREAM[/COLOR] [COLOR gold](DIRECT)[/COLOR]',
         'link': link,
         'thumbnail': 'https://i.imgur.com/8EL6mr3.png',
         'fanart': 'https://www.stadiotardini.it/wp-content/uploads/2016/12/mandrakata.jpg',
         'info': 'by MandraKodi'},
        {'title': '[COLOR orange]▶ PLAY STREAM[/COLOR] [COLOR gold](FFMPEG)[/COLOR]',
         'myresolve': f'ffmpeg_noRef@@{link}',
         'thumbnail': 'https://i.imgur.com/8EL6mr3.png',
         'fanart': 'https://www.stadiotardini.it/wp-content/uploads/2016/12/mandrakata.jpg',
         'info': 'by MandraKodi'}
    ]
    return json.dumps({'SetViewMode': '50', 'items': items})

def resolve_anyplay(serie_id):
    logga(f"resolve_anyplay: {serie_id}")
    url_any = f"https://aniplay.co/series/{serie_id}"
    page    = http_get(url_any, headers={'User-Agent': UA_FALLBACK, 'Referer': 'https://aniplay.co/'})
    data_j  = preg_match(page, r'const data = \[(.*?)\];')
    arr_p1  = data_j.split(',episodes:')
    if len(arr_p1) < 2:
        return None
    srrs = arr_p1[1].split(',similarSeries:')[0]
    dj2  = '{"episodes":' + srrs
    mapping = {
        'old_id:': '"old_id":', 'id:': '"id":', 'subbed:': '"subbed":',
        'download_link:': '"download_link":', 'title:': '"title":', 'slug:': '"slug":',
        'number:': '"number":', 'score:': '"score":', 'streaming_link:': '"streaming_link":',
        'seconds:null': '"seconds":"0"', 'seconds:': '"seconds":', 'embed:': '"embed":',
        'createdAt:': '"createdAt":', 'updatedAt:': '"updatedAt":', 'publishedAt:': '"publishedAt":',
        'release_date:': '"release_date":', 'quality:': '"quality":',
    }
    for k, v in mapping.items():
        dj2 = dj2.replace(k, v)
    try:
        logo  = "https://png.pngtree.com/png-vector/20230124/ourmid/pngtree-arrow-icon-3d-play-png-image_6565151.png"
        items = []
        for ep in json.loads(dj2).get("episodes", []):
            link     = ep.get("streaming_link", "")
            num_ep   = str(ep.get("number", ""))
            title_ep = ep.get("title") or ""
            tit      = f"Ep. {num_ep} - {title_ep}"
            items.append({'title': f'[COLOR gold]{tit}[/COLOR]', 'link': link,
                          'thumbnail': logo,
                          'fanart': 'https://www.stadiotardini.it/wp-content/uploads/2016/12/mandrakata.jpg',
                          'info': 'by MandraKodi'})
        return json.dumps({'SetViewMode': '503', 'items': items})
    except Exception as e:
        logga(f"anyplay JSON error: {e}")
        return None

def resolve_taxi(slug):
    logga(f"resolve_taxi: {slug}")
    sc_url = "https://raw.githubusercontent.com/mandrakodi/mandrakodi.github.io/main/data/taxi_url.txt"
    base   = makeRequest(sc_url).replace("\n", '')
    url    = f"{base}stream/{slug}"
    page   = http_get(url).replace("\n","").replace("\r","").replace("\t","")
    ret    = re.findall(
        r'<a href="#" allowfullscreen data-link="(.*?)" id="(.*?)" data-num="(.*?)" data-title="(.*?)">\d+</a>(.*?)</li>',
        page, re.DOTALL)
    items  = []
    logo   = "https://www.giardiniblog.it/wp-content/uploads/2018/12/serie-tv-streaming.jpg"
    for (link, id_, ep, tito, mirror) in ret:
        ret2 = re.findall(r'<a href="#" class="mr" data-link="(.*?)">', mirror, re.DOTALL)
        if not ret2:
            continue
        link = ret2[1] if (len(ret2) > 1 and "supervideo" in ret2[0]) else ret2[0]
        items.append({'title': f'[COLOR lime]{ep}[/COLOR]', 'myresolve': f'proData@@{link}',
                      'thumbnail': logo,
                      'fanart': 'https://www.stadiotardini.it/wp-content/uploads/2016/12/mandrakata.jpg',
                      'info': tito.replace('"', '')})
    if not items:
        items.append({'title': '[COLOR red]NO HOST FOUND[/COLOR]', 'link': 'ignore',
                      'thumbnail': logo,
                      'fanart': 'https://www.stadiotardini.it/wp-content/uploads/2016/12/mandrakata.jpg',
                      'info': 'NO INFO'})
    return json.dumps({'SetViewMode': '503', 'items': items})

def resolve_webcam(param):
    logga(f"resolve_webcam: {param}")
    arr_t     = param.split('_', 1)
    mode      = arr_t[0]
    page_path = arr_t[1] if len(arr_t) > 1 else param
    page_url  = f"https://www.skylinewebcams.com/it/{page_path}.html"
    headers   = {'User-Agent': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36"}
    page      = http_get(page_url, headers=headers)
    html_flat = page.replace("\n",'').replace("\r",'').replace("\t",'')
    if mode == "0":
        lista     = re.findall(r'<a href="it/webcam/(.*?)" class="col-xs-12 col-sm-6 col-md-4">(.*?)</a>', html_flat, re.DOTALL)
        lista_cam = []
        for (link, tit) in lista:
            titolo   = preg_match(tit, r'<p class="tcam">(.*?)</p>') or "Cam"
            img      = preg_match(tit, r'<img src="(.*?)"') or ""
            info     = preg_match(tit, r'<p class="subt">(.*?)</p>') or "by MandraKodi"
            info_p   = preg_match(tit, r'<span class="lcam">(.*?)</span>') or ""
            lista_cam.append(f"{titolo}@@{img}@@{link}@@{info}@@{info_p}")
        lista_cam.sort()
        items = []
        for wCam in lista_cam:
            arr   = wCam.split("@@")
            tit_c, img_c, lnk, inf, inf_plus = arr[0], arr[1], arr[2], arr[3], arr[4]
            extra = f" [COLOR lime]({inf_plus})[/COLOR]" if inf_plus else ""
            items.append({'title': f'[COLOR gold]{tit_c}[/COLOR]{extra}',
                          'myresolve': f'webcam@@1_webcam/{lnk.replace(".html","")}',
                          'thumbnail': img_c,
                          'fanart': 'https://www.stadiotardini.it/wp-content/uploads/2016/12/mandrakata.jpg',
                          'info': inf})
    else:
        titolo = (preg_match(html_flat, r'<h1>(.*?)</h1>') or "Watch Stream").replace("Live webcam", "")
        info   = preg_match(html_flat, r'<h2>(.*?)</h2>') or "by @mandrakodi"
        img    = preg_match(html_flat, r'<meta property="og:image" content="(.*?)"') or ""
        src    = preg_match(html_flat, r"source:'(.*?)'")
        url1   = f"https://hd-auth.skylinewebcams.com/{src.replace('livee', 'live')}|Referer={page_url}&User-Agent=Mozilla" if src else "ignore"
        items  = [{'title': f'[COLOR gold]{titolo}[/COLOR]', 'link': url1,
                   'thumbnail': img,
                   'fanart': 'https://www.stadiotardini.it/wp-content/uploads/2016/12/mandrakata.jpg',
                   'info': info}]
    return json.dumps({'SetViewMode': '503', 'items': items})

def resolve_m3uplus(param):
    logga(f"resolve_m3uplus: {param}")
    win    = xbmcgui.Window(10000)
    arr_in = param.split("_@|@_")
    mode   = arr_in[0]
    headers = {'User-Agent': 'ipad'}
    items   = []
    FANART  = 'https://www.stadiotardini.it/wp-content/uploads/2016/12/mandrakata.jpg'
    FOLDER_ICON = 'https://static.vecteezy.com/system/resources/thumbnails/065/914/783/small/stylized-3d-rendering-of-a-file-folder-icon-for-data-management-free-png.png'

    if mode == "0":
        win.setProperty("sessionVar1", param)
        host, usr, pwd = arr_in[1], arr_in[2], arr_in[3]
        api_url = f"http://{host}/player_api.php?username={usr}&password={pwd}&action=get_live_categories"
        lista   = json.loads(http_get(api_url, headers=headers))
        for item in lista:
            cat_id = item.get("category_id", "")
            name   = item.get("category_name", "")
            items.append({'title': f'[COLOR orange]=*= {name} =*=[/COLOR]',
                          'myresolve': f'm3uPlus@@1_@|@_{name}_@|@_{cat_id}',
                          'thumbnail': FOLDER_ICON, 'fanart': FANART, 'info': 'by MandraKodi'})

    elif mode == "1":
        par_sess = win.getProperty("sessionVar1")
        cat_id   = arr_in[2]
        arr_sess = par_sess.split("_@|@_")
        host, usr, pwd = arr_sess[1], arr_sess[2], arr_sess[3]
        api_url  = f"http://{host}/player_api.php?username={usr}&password={pwd}&action=get_live_streams&category_id={cat_id}"
        lista    = json.loads(http_get(api_url, headers=headers))
        for item in lista:
            stream_id = item.get("stream_id", "")
            link_url  = f"http://{host}/live/{usr}/{pwd}/{stream_id}.m3u8"
            name      = item.get("name", "")
            icon      = item.get("stream_icon") or "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8f/Microsoft_Stream.svg/512px-Microsoft_Stream.svg.png"
            items.append({'title': f'[COLOR lime]{name}[/COLOR]', 'link': link_url,
                          'thumbnail': icon, 'fanart': FANART, 'info': 'by MandraKodi'})

    return json.dumps({'SetViewMode': '503', 'items': items}) if items else None

# ===========================================================================
# DISPATCH resolver  →  ('url', url, is_ffmpeg) | ('json', json_str, None) | ('error', msg, None)
# ===========================================================================

def _make_options(url, ref, noref=False):
    """
    Costruisce JSON con opzioni di riproduzione (FFMPEG / Adaptive Stream),
    come fa l'addon ufficiale quando ci sono più scelte.
    """
    FANART = 'https://www.stadiotardini.it/wp-content/uploads/2016/12/mandrakata.jpg'
    THUMB  = 'https://png.pngtree.com/png-vector/20230124/ourmid/pngtree-arrow-icon-3d-play-png-image_6565151.png'
    if ref:
        url_with_headers = f"{url}|Referer={ref}&Origin={ref.rstrip('/')}&User-Agent=Mozilla/5.0 (iPad; CPU OS 133 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
    else:
        url_with_headers = url
    tipo_ffmpeg = 'ffmpeg_noRef@@' if noref else 'ffmpeg@@'
    items = [
        {'title': '[COLOR lime]▶ FFMPEG Direct[/COLOR] [COLOR gold](consigliato)[/COLOR]',
         'myresolve': f'{tipo_ffmpeg}{url_with_headers}', 'thumbnail': THUMB, 'fanart': FANART, 'info': 'FFmpegDirect'},
        {'title': '[COLOR orange]▶ Adaptive Stream[/COLOR] [COLOR gold](inputstream)[/COLOR]',
         'link': url_with_headers, 'thumbnail': THUMB, 'fanart': FANART, 'info': 'inputstream.adaptive'}
    ]
    return json.dumps({'SetViewMode': '50', 'items': items})

# ===========================================================================
# EPG  helpers
# ===========================================================================

def _norm_ch_name(name):
    """Normalizza nome canale per confronto fuzzy."""
    n = name.lower()
    for drop in (' hd', ' fhd', ' 4k', ' full hd', '+', '.', '-'):
        n = n.replace(drop, ' ')
    # rimuovi accenti comuni
    n = n.replace('à','a').replace('è','e').replace('é','e').replace('ì','i').replace('ò','o').replace('ù','u')
    return ' '.join(n.split())

def _ch_matches(epg_norm, ch_norm):
    """True se i nomi normalizzati si sovrappongono."""
    if epg_norm == ch_norm:
        return True
    if epg_norm in ch_norm or ch_norm in epg_norm:
        return True
    # confronto senza spazi: "la 7" == "la7", "sky tg 24" == "sky tg24"
    e_ns = epg_norm.replace(' ', '')
    c_ns = ch_norm.replace(' ', '')
    if e_ns == c_ns or e_ns in c_ns or c_ns in e_ns:
        return True
    # gestisce varianti tipo "rai 1" vs "rai uno"
    num_map = {'uno':'1','due':'2','tre':'3','quattro':'4','cinque':'5',
               'sei':'6','sette':'7','otto':'8','nove':'9','zero':'0'}
    e2 = epg_norm
    c2 = ch_norm
    for word, digit in num_map.items():
        e2 = e2.replace(word, digit)
        c2 = c2.replace(word, digit)
    e2 = ' '.join(e2.split())
    c2 = ' '.join(c2.split())
    return e2 == c2 or e2 in c2 or c2 in e2

def search_epg_matches(epg_title):
    """
    Cerca in playlist.json e zappr tutti i canali il cui nome
    corrisponde (fuzzy) a epg_title.
    Restituisce lista di dict:
      {section, name, url, license, thumb, resolver_tipo, resolver_param}
    """
    epg_norm = _norm_ch_name(epg_title)
    matches  = []

    # --- Playlist.json ---
    try:
        req  = urllib.request.Request(URL_JSON, headers={'User-Agent': UA_FALLBACK})
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

    # --- Zappr ---
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
            # Costruisce resolver tipo/param identici a zappr() di myResolver
            if tipo_ch == 'hls':
                if 'zappr://' in url_str:
                    par_sky = url_str.split('/')[-1]
                    r_tipo, r_param = 'skytv', par_sky
                else:
                    r_tipo, r_param = 'amstaff', url_str + '|0000'
            else:  # dash
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
    """
    Recupera da guidatv.org il programma attualmente in onda.
    Restituisce (orario, titolo, descrizione) o ('','','').
    """
    try:
        from html.parser import HTMLParser as _HP

        class _EpgParser(_HP):
            def __init__(self):
                super().__init__()
                self.items  = []
                self._cur   = {}
                self._field = None
                self._buf   = []

            def handle_starttag(self, tag, attrs):
                a = dict(attrs)
                cls = a.get('class', '')
                if 'schedule-item' in cls or 'program-item' in cls:
                    self._cur   = {}
                    self._field = None
                if 'time' in cls or 'orario' in cls:
                    self._field = 'time'
                    self._buf   = []
                elif 'title' in cls or 'titolo' in cls:
                    self._field = 'title'
                    self._buf   = []
                elif 'desc' in cls or 'descrizione' in cls:
                    self._field = 'desc'
                    self._buf   = []

            def handle_data(self, data):
                if self._field:
                    self._buf.append(data.strip())

            def handle_endtag(self, tag):
                if self._field and self._buf:
                    self._cur[self._field] = ' '.join(self._buf).strip()
                    self._buf   = []
                    self._field = None
                if tag in ('li', 'div') and self._cur.get('title'):
                    self.items.append(dict(self._cur))
                    self._cur = {}

        page = http_get(f"https://guidatv.org/canali/{epg_id}",
                        headers={'User-Agent': 'Kodi/EPG-Addon', 'Accept-Language': 'it-IT,it;q=0.9'},
                        timeout=10)
        if not page:
            return ('', '', '')
        # Cerca il programma corrente con regex semplice come fallback
        # Pattern: orario + titolo nella guida
        import time as _time
        current_h = _time.localtime().tm_hour
        current_m = _time.localtime().tm_min

        # Cerca tutte le righe orario/titolo con regex
        rows = re.findall(
            r'(\d{1,2}:\d{2})[^<]*</[^>]+>[^<]*<[^>]+>[^<]*<[^>]+>([^<]{3,80})',
            page)
        if not rows:
            rows = re.findall(r'(\d{1,2}:\d{2})\s*[-–]\s*([^\n<]{3,80})', page)

        best_title = ''
        best_time  = ''
        for t_str, title in rows:
            try:
                h, m = int(t_str.split(':')[0]), int(t_str.split(':')[1])
                t_min = h * 60 + m
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

def resolve_zappr_to_items():
    """
    Fetcha channels.zappr.stream e restituisce lista di item-dict
    pronti per _render_mandra_items.
    """
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
                    par_sky = url_str.split('/')[-1]
                    myres = f'skyTV@@{par_sky}'
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
            # canali extra hbbtv
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

def dispatch_resolver(tipo, param):
    tipo = tipo.lower()

    # ---- stream che non mostrano il menu opzioni (uso diretto) ----
    if tipo == 'amstaff':
        # DRM clearkey → sempre adaptive, nessuna scelta
        return ('url', param, False)
    elif tipo in ('ffmpeg', 'ffmpeg_noref'):
        return ('url', param, True)
    elif tipo == 'vavooplay':
        url = resolve_vavoo(param)
        return ('url', url, False) if url else ('error', 'Vavoo: risoluzione fallita', None)

    # ---- stream che mostrano opzioni FFMPEG / Adaptive ----
    elif tipo == 'freeshot':
        url, ref = resolve_freeshot(param)
        return ('json', _make_options(url, ref), None) if url else ('error', f'freeshot: URL non trovato per {param}', None)
    elif tipo == 'mediahosting':
        url, ref = resolve_mediahosting(param)
        return ('json', _make_options(url, ref), None) if url else ('error', f'mediahosting: URL non trovato per {param}', None)
    elif tipo == 'streamtp':
        url, ref = resolve_streamtp(param)
        return ('json', _make_options(url, ref), None) if url else ('error', f'streamtp: URL non trovato per {param}', None)
    elif tipo == 'tvapp':
        url, ref = resolve_tvapp(param)
        return ('json', _make_options(url, ref), None) if url else ('error', f'tvapp: URL non trovato per {param}', None)
    elif tipo == 'skytv':
        url, ref = resolve_skytv(param)
        return ('json', _make_options(url, ref), None) if url else ('error', f'skyTV: URL non trovato per {param}', None)
    elif tipo == 'antenacode':
        url, ref = resolve_antenacode(param)
        return ('json', _make_options(url, ref), None)
    elif tipo == 'antena':
        url, ref = resolve_antena(param)
        return ('json', _make_options(url, ref), None) if url else ('error', 'antena: URL non trovato', None)
    elif tipo == 'koolto':
        url, ref = resolve_koolto(param)
        return ('json', _make_options(url, ref), None)
    elif tipo == 'pulive':
        url, ref = resolve_pulive(param)
        return ('json', _make_options(url, ref), None) if url else ('error', f'pulive: URL non trovato per {param}', None)
    elif tipo == 'vudeo':
        url, ref = resolve_vudeo(param)
        return ('json', _make_options(url, ref), None) if url else ('error', f'vudeo: non trovato per {param}', None)
    elif tipo == 'voe':
        url, ref = resolve_voe(param)
        return ('json', _make_options(url, ref), None) if url else ('error', f'voe: non trovato per {param}', None)
    elif tipo in ('sib', 'sibnet'):
        url, ref = resolve_sibnet(param)
        return ('json', _make_options(url, ref), None) if url else ('error', f'sibNet: non trovato per {param}', None)
    elif tipo in ('stape', 'streamtape'):
        url, ref = resolve_streamtape(param)
        return ('json', _make_options(url, ref), None) if url else ('error', 'streamTape: URL non trovato', None)
    elif tipo == 'markky':
        url, ref = resolve_markky(param)
        return ('json', _make_options(url, ref), None) if url else ('error', 'markky: URL non trovato', None)
    elif tipo == 'daddy':
        url, ref = resolve_daddy(param)
        return ('json', _make_options(url, ref), None) if url else ('error', 'daddy: URL non trovato', None)
    elif tipo in ('lvtv', 'livetv'):
        url, ref = resolve_livetv(param)
        return ('json', _make_options(url, ref), None) if url else ('error', 'livetv: URL non trovato', None)
    elif tipo == 'hunter':
        url, ref = resolve_hunterjs(param)
        return ('json', _make_options(url, ref), None) if url else ('error', 'hunterjs: URL non trovato', None)
    elif tipo in ('scom', 'scommunity'):
        url, ref = resolve_scommunity(param)
        return ('json', _make_options(url, ref), None) if url else ('error', 'scommunity: URL non trovato', None)
    elif tipo in ('scws', 'scws2', 'moviesc'):
        url, ref = resolve_scws(param)
        return ('json', _make_options(url, ref), None) if url else ('error', 'scws: URL non trovato', None)
    elif tipo == 'gaga':
        url, ref = _try_jsunpack_resolve(param, "https://calcio.events")
        return ('json', _make_options(url, ref), None) if url else ('error', 'gaga: jsunpack non disponibile', None)
    elif tipo == 'wigi':
        wigi_url, refe = (param.split("|")[0], param.split("|")[1]) if "|" in param else (param, param)
        url, ref = _try_jsunpack_resolve(wigi_url, refe)
        return ('json', _make_options(url, ref), None) if url else ('error', 'wigi: jsunpack non disponibile', None)
    elif tipo == 'prodata':
        url, ref = _try_jsunpack_resolve(param)
        return ('json', _make_options(url, ref, noref=True), None) if url else ('error', 'proData: jsunpack non disponibile', None)
    elif tipo == 'wikisport':
        url, ref = resolve_wikisport(param)
        return ('json', _make_options(url, ref), None) if url else ('error', 'wikisport: URL non trovato', None)
    elif tipo in ('sansat', 'vividmosaica'):
        url, ref = resolve_vividmosaica(param)
        return ('json', _make_options(url, ref), None) if url else ('error', 'sansat/vividmosaica: URL non trovato', None)
    elif tipo == 'daily':
        url, ref = resolve_daily(param)
        return ('json', _make_options(url, ref), None) if url else ('error', f'daily: URL non trovato per {param}', None)

    # ---- sub-menu JSON ----
    elif tipo == 'ppv':
        jt = resolve_ppv(param)
        return ('json', jt, None) if jt else ('error', 'ppv: URL non trovato', None)
    elif tipo == 'anyplay':
        jt = resolve_anyplay(param)
        return ('json', jt, None) if jt else ('error', 'anyplay: errore parsing', None)
    elif tipo == 'taxi':
        return ('json', resolve_taxi(param), None)
    elif tipo == 'm3uplus':
        jt = resolve_m3uplus(param)
        return ('json', jt, None) if jt else ('error', 'm3uPlus: errore', None)
    elif tipo == 'webcam':
        jt = resolve_webcam(param)
        return ('json', jt, None) if jt else ('error', 'webcam: errore', None)
    else:
        return ('error', f"Tipo '{tipo}' non supportato", None)

# ===========================================================================
# HELPERS ListItem
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
    elif "vavoo" in url_lower:
        ua   = "Mozilla/5.0 (X11; Linux armv7l) AppleWebKit/537.36 (KHTML, like Gecko) QtWebEngine/5.9.7 Chrome/56.0.2924.122 Safari/537.36 Sky_STB_ST412_2018/1.0.0 (Sky, EM150UK,)"
        host = "https://vavoo.to"
        return f'User-Agent={ua}&Referer={host}/&Origin={host}&Connection=keep-alive'
    return None

def _build_listitem_adaptive(url, headers_str, license_key):
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
    """
    Costruisce ListItem per inputstream.ffmpegdirect.
    L'URL può avere headers inline nel formato: url|Header=Value&Header2=Value2
    """
    li = xbmcgui.ListItem(path=url)
    li.setProperty('inputstream', 'inputstream.ffmpegdirect')
    li.setMimeType('application/x-mpegURL')
    li.setProperty('inputstream.ffmpegdirect.manifest_type',      'hls')
    li.setProperty('inputstream.ffmpegdirect.is_realtime_stream', 'true')
    return li

# ===========================================================================
# MAIN  run()
# ===========================================================================

def run():
    handle = int(sys.argv[1])
    params = dict(urllib.parse.parse_qsl(sys.argv[2][1:]))

    # -----------------------------------------------------------------------
    # AZIONE: PLAY  — stream diretto dalla playlist.json
    # -----------------------------------------------------------------------
    if params.get('action') == 'play':
        original_url = params.get('url', '')
        license_key  = params.get('license', '')
        url          = original_url

        # Per la rilevazione degli auto-header usiamo SEMPRE l'URL originale
        # (prima del redirect vavoo) così "vavoo" rimane nel lower per il match
        original_lower = original_url.lower()

        # --- RESOLVER SKY: URL shortener con sky@@<canale> ---
        # Short.io manda l'URL con doppio @, che Kodi double-decoda in vari modi:
        #   sky%40@nomecanale  (formato reale che arriva al plugin dopo parse_qsl)
        #   sky%40%40nomecanale (entrambi gli @ encodati)
        #   sky@@nomecanale (nessun encoding, fallback)
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
                xbmcgui.Dialog().notification("Sky", f"Errore resolver canale: {sky_par}",
                                               xbmcgui.NOTIFICATION_ERROR, 4000)
                xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem())
            return

        # Risoluzione redirect vavoo (solo per playlist.json con URL vavoo diretti)
        if "vavoo" in original_lower:
            try:
                req_v = urllib.request.Request(original_url, headers={'User-Agent': 'VAVOO/2.6'})
                with urllib.request.urlopen(req_v, timeout=15) as response:
                    resolved = response.geturl()
                    if resolved != original_url:
                        url = resolved
                        logga(f"Vavoo redirect → {url}")
            except Exception as e:
                logga(f"Vavoo redirect error (uso URL originale): {e}")

        # --- LOGICA AUTOMATICA HEADERS basata su URL ORIGINALE ---
        auto_headers = None
        token = ""

        if "dazn" in original_lower or "dai.google.com" in original_lower:
            ua = urllib.parse.quote("Mozilla/5.0 (Web0S; Linux/SmartTV) AppleWebKit/537.41 (KHTML, like Gecko) Large Screen Safari/537.41 LG Browser/7.00.00(LGE; WEBOS1; 05.06.10; 1); webOS.TV-2014; LG NetCast.TV-2013 Compatible (LGE, WEBOS1, wireless)")
            host = "https://www.dazn.com"
            auto_headers = f'User-Agent={ua}&Referer={host}/&Origin={host}'
            if token != "":
                ua = urllib.parse.quote_plus("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36")
                auto_headers = f'{token}&referer={host}/&origin={host}&user-agent={ua}'
            logga(f"Auto-Header DAZN: {auto_headers}")
        elif "lba-ew" in original_lower:
            ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:143.0) Gecko/20100101 Firefox/143.0"
            host = "https://www.lbatv.com"
            auto_headers = f'User-Agent={ua}&Referer={host}/&Origin={host}&verifypeer=false'
            logga("Auto-Header LBA")
        elif "discovery" in original_lower:
            ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0"
            host = "https://www.discoveryplus.com"
            auto_headers = f'User-Agent={ua}&Referer={host}/&Origin={host}&verifypeer=false'
            logga("Auto-Header Discovery")
        elif "nowitlin" in original_lower:
            ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
            host = "https://www.nowtv.it"
            auto_headers = f'User-Agent={ua}&Referer={host}/&Origin={host}&verifypeer=false'
            logga("Auto-Header NOW")
        elif "vodafone.pt" in original_lower:
            ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0"
            host = "http://rr.cdn.vodafone.pt"
            auto_headers = f'User-Agent={ua}&Referer={host}/&Origin={host}&verifypeer=false'
            logga("Auto-Header Vodafone")
        elif "clarovideo.com" in original_lower:
            ua = urllib.parse.quote_plus("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 OPR/124.0.0.0")
            host = "https://clarovideo.com"
            auto_headers = f'User-Agent={ua}&Referer={host}/&Origin={host}&verifypeer=false'
            logga("Auto-Header Claro")
        elif "starzplayarabia" in original_lower:
            ua = urllib.parse.quote("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 OPR/120.0.0.0")
            auto_headers = f'User-Agent={ua}&verifypeer=false'
            logga("Auto-Header Starz")
        elif "vavoo" in original_lower:
            ua = "Mozilla/5.0 (X11; Linux armv7l) AppleWebKit/537.36 (KHTML, like Gecko) QtWebEngine/5.9.7 Chrome/56.0.2924.122 Safari/537.36 Sky_STB_ST412_2018/1.0.0 (Sky, EM150UK,)"
            host = "https://vavoo.to"
            auto_headers = f'User-Agent={ua}&Referer={host}/&Origin={host}&Connection=keep-alive'
            logga("Auto-Header VAVOO")

        # --- SELEZIONE MANUALE SE NON AUTOMATICO ---
        if auto_headers:
            selected_headers = auto_headers
        else:
            user_agents = get_remote_uas()
            dialog  = xbmcgui.Dialog()
            scelta  = dialog.select("Scegli User-Agent", user_agents)
            if scelta == -1:
                xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem())
                return
            selected_ua      = user_agents[scelta]
            selected_headers = f"User-Agent={selected_ua}"

        # --- CREAZIONE LISTITEM ---
        url_lower = url.lower()

        if ".m3u8" in url_lower and not license_key:
            # HLS senza DRM → ffmpegdirect (come MandraKodi)
            # Ricostruisce URL con headers inline per ffmpegdirect
            ua_part  = selected_headers  # già nel formato "Key=Value&Key2=Value2"
            # ffmpegdirect accetta headers nel path: url|Header=Val&Header2=Val2
            # ma selected_headers potrebbe già essere in quel formato, lo usiamo direttamente
            final_url = f"{url}|{ua_part}"
            li = xbmcgui.ListItem(path=final_url)
            li.setProperty('inputstream', 'inputstream.ffmpegdirect')
            li.setMimeType('application/x-mpegURL')
            li.setProperty('inputstream.ffmpegdirect.manifest_type',      'hls')
            li.setProperty('inputstream.ffmpegdirect.is_realtime_stream', 'true')
        else:
            # MPD (DASH) o HLS con DRM clearkey → inputstream.adaptive
            li = xbmcgui.ListItem(path=url)
            li.setProperty('inputstream', 'inputstream.adaptive')
            li.setProperty('inputstream.adaptive.stream_headers',   selected_headers)
            li.setProperty('inputstream.adaptive.manifest_headers', selected_headers)
            if license_key:
                li.setProperty('inputstream.adaptive.drm_legacy', f"org.w3.clearkey|{license_key}")
            if ".mpd" in url_lower:
                li.setMimeType('application/dash+xml')
            elif ".m3u8" in url_lower:
                li.setMimeType('application/vnd.apple.mpegurl')

        xbmcplugin.setResolvedUrl(handle, True, li)
        return

    # -----------------------------------------------------------------------
    # AZIONE: MANDRA_PLAY  — risoluzione runtime resolver MandraKodi
    # -----------------------------------------------------------------------
    if params.get('action') == 'mandra_play':
        tipo  = params.get('tipo', '')
        param = params.get('param', '')
        logga(f"mandra_play tipo={tipo} param={param[:80]}")

        result_type, result_data, extra = dispatch_resolver(tipo, param)

        if result_type == 'url':
            url       = result_data
            is_ffmpeg = extra if extra is not None else False
            if is_ffmpeg:
                li = _build_listitem_ffmpeg(url)
            else:
                lic         = params.get('lic', '')
                headers_str = _auto_headers_for_url(url.lower()) or AMSTAFF_HEADERS
                li = _build_listitem_adaptive(url, headers_str, lic)
            xbmcplugin.setResolvedUrl(handle, True, li)

        elif result_type == 'json':
            try:
                data  = json.loads(result_data)
                items = data.get('items', [])
                _render_mandra_items(handle, items)
                xbmcplugin.endOfDirectory(handle)
            except Exception as e:
                logga(f"mandra_play JSON render error: {e}")
                xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem())

        else:
            xbmcgui.Dialog().notification("Errore resolver", result_data,
                                           xbmcgui.NOTIFICATION_ERROR, 4000)
            xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem())
        return

    # -----------------------------------------------------------------------
    # AZIONE: MANDRA_SUB  — naviga un sottolivello MandraKodi
    # -----------------------------------------------------------------------
    if params.get('action') == 'mandra_sub':
        sub_url = params.get('url', URL_MANDRA)
        logga(f"MandraKodi sub-menu: {sub_url}")
        items = fetch_mandra_json(sub_url)
        _render_mandra_items(handle, items)
        xbmcplugin.endOfDirectory(handle)
        return

    # -----------------------------------------------------------------------
    # AZIONE: EPG_LIST  — mostra lista canali EPG
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
            raw_title  = item.get('title', '')
            epg_id     = ''
            myres      = item.get('myresolve', '')
            if myres.startswith('epg@@'):
                epg_id = myres.split('@@', 1)[1]
            clean_title = strip_kodi_tags(raw_title)
            thumb  = item.get('thumbnail', 'DefaultVideo.png')
            fanart = item.get('fanart', FANART_DEFAULT)
            info   = item.get('info', '')
            li = xbmcgui.ListItem(label=f"{info}  {clean_title}" if info else clean_title)
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
    # AZIONE: EPG_SEARCH  — cerca canale nelle sorgenti, mostra dialog, play
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

        epg_time, epg_prog, epg_desc = ('', '', '')
        if epg_id:
            epg_time, epg_prog, epg_desc = fetch_epg_info(epg_id)
        epg_plot = f"[{epg_time}] {epg_prog}" if epg_prog else epg_title

        if chosen['tipo'] == 'playlist':
            url       = chosen['url']
            lic       = chosen['license']
            url_lower = url.lower()
            li = xbmcgui.ListItem(label=chosen['name'], path=url)
            _tag = li.getVideoInfoTag()
            _tag.setTitle(chosen['name'])
            _tag.setPlot(epg_plot)
            li.setArt({'thumb': epg_thumb})
            if '.m3u8' in url_lower and not lic:
                li.setProperty('inputstream', 'inputstream.ffmpegdirect')
                li.setMimeType('application/x-mpegURL')
                li.setProperty('inputstream.ffmpegdirect.manifest_type',      'hls')
                li.setProperty('inputstream.ffmpegdirect.is_realtime_stream', 'true')
            else:
                headers_str = _auto_headers_for_url(url_lower) or f'User-Agent={UA_FALLBACK}'
                li.setProperty('inputstream', 'inputstream.adaptive')
                li.setProperty('inputstream.adaptive.stream_headers',   headers_str)
                li.setProperty('inputstream.adaptive.manifest_headers', headers_str)
                if lic:
                    li.setProperty('inputstream.adaptive.drm_legacy', f'org.w3.clearkey|{lic}')
                if '.mpd' in url_lower:
                    li.setMimeType('application/dash+xml')
                elif '.m3u8' in url_lower:
                    li.setMimeType('application/vnd.apple.mpegurl')
        else:
            result_type, result_data, extra = dispatch_resolver(chosen['tipo'], chosen['param'])
            if result_type == 'url':
                url = result_data
                if extra:
                    li = _build_listitem_ffmpeg(url)
                else:
                    hs = _auto_headers_for_url(url.lower()) or AMSTAFF_HEADERS
                    li = _build_listitem_adaptive(url, hs, '')
                _tag = li.getVideoInfoTag()
                _tag.setTitle(chosen['name'])
                _tag.setPlot(epg_plot)
                li.setArt({'thumb': epg_thumb})
            elif result_type == 'json':
                try:
                    sub_items = json.loads(result_data).get('items', [])
                    direct = next((i for i in sub_items if i.get('link')
                                   and i['link'] != 'ignore'), None)
                    if direct:
                        url = direct['link'].split('|')[0]
                        hs  = _auto_headers_for_url(url.lower()) or AMSTAFF_HEADERS
                        li  = _build_listitem_adaptive(url, hs, '')
                        _tag = li.getVideoInfoTag()
                        _tag.setTitle(chosen['name'])
                        _tag.setPlot(epg_plot)
                        li.setArt({'thumb': epg_thumb})
                    else:
                        dialog.notification("EPG", "Stream non risolvibile",
                                            xbmcgui.NOTIFICATION_ERROR, 3000)
                        xbmcplugin.endOfDirectory(handle, succeeded=False)
                        return
                except Exception as e:
                    logga(f"EPG json resolver error: {e}")
                    xbmcplugin.endOfDirectory(handle, succeeded=False)
                    return
            else:
                dialog.notification("EPG", f"Errore: {result_data}",
                                    xbmcgui.NOTIFICATION_ERROR, 3000)
                xbmcplugin.endOfDirectory(handle, succeeded=False)
                return

        xbmc.Player().play(li.getPath(), li)
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return

    # -----------------------------------------------------------------------
    # AZIONE: ZAPPR_MENU  — canali DVB-T2 da zappr.stream
    # -----------------------------------------------------------------------
    if params.get('action') == 'zappr_menu':
        logga("Zappr menu")
        items = resolve_zappr_to_items()
        _render_mandra_items(handle, items)
        xbmcplugin.endOfDirectory(handle)
        return

    # -----------------------------------------------------------------------
    # NAVIGAZIONE PLAYLIST NORMALE  (identica all'originale)
    # -----------------------------------------------------------------------
    action = params.get('action')

    try:
        req = urllib.request.Request(URL_JSON, headers={'User-Agent': UA_FALLBACK})
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read().decode())
    except:
        data = []

    if not action:
        # MENU PRINCIPALE: EPG -> DVB-T2 -> categorie playlist -> MandraKodi

        # 1. EPG
        li_epg = xbmcgui.ListItem(label="\U0001f4cb EPG")
        li_epg.setArt({'icon': 'DefaultFolder.png'})
        xbmcplugin.addDirectoryItem(
            handle,
            f"{sys.argv[0]}?{urllib.parse.urlencode({'action': 'epg_list'})}",
            li_epg, isFolder=True)

        # 2. DVB-T2 (zappr)
        li_z = xbmcgui.ListItem(label="\U0001f4e1 DVB-T2 (zappr)")
        li_z.setArt({'icon': 'DefaultFolder.png'})
        xbmcplugin.addDirectoryItem(
            handle,
            f"{sys.argv[0]}?{urllib.parse.urlencode({'action': 'zappr_menu'})}",
            li_z, isFolder=True)

        # 3. Categorie playlist
        categories = []
        for ch in data:
            cat = ch.get('category', 'Altro')
            if cat not in categories:
                categories.append(cat)
        for cat in categories:
            li = xbmcgui.ListItem(label=cat)
            li.setArt({'icon': 'DefaultFolder.png'})
            query      = {'action': 'category', 'category': cat}
            plugin_url = f"{sys.argv[0]}?{urllib.parse.urlencode(query)}"
            xbmcplugin.addDirectoryItem(handle, plugin_url, li, isFolder=True)

        # 4. MandraKodi
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

                lic        = ch.get('license', '')
                query      = {'action': 'play', 'url': ch['url'], 'license': lic}
                plugin_url = f"{sys.argv[0]}?{urllib.parse.urlencode(query)}"
                xbmcplugin.addDirectoryItem(handle, plugin_url, li, isFolder=False)

    xbmcplugin.endOfDirectory(handle)



# ===========================================================================
# RENDER items MandraKodi (usato da mandra_sub e mandra_play con JSON)
# ===========================================================================

def _render_mandra_items(handle, items):
    for item in items:
        if str(item.get('enabled', '1')) == '0':
            continue

        title    = strip_kodi_tags(item.get('title', 'Senza titolo'))
        thumb    = item.get('thumbnail', 'DefaultVideo.png')
        fanart   = item.get('fanart', '')
        info_str = item.get('info', '')

        link      = item.get('link', '')
        ext_link  = item.get('externallink', '') or item.get('externallink2', '')
        myresolve = item.get('myresolve', '')

        # --- Separatore / intestazione ---
        if str(link).lower() == 'ignore' and not myresolve and not ext_link:
            li = xbmcgui.ListItem(label=f"── {title} ──")
            li.setArt({'thumb': thumb, 'fanart': fanart})
            _tag = li.getVideoInfoTag()
            _tag.setTitle(title)
            _tag.setPlot(info_str)
            xbmcplugin.addDirectoryItem(handle, '', li, isFolder=False)
            continue

        # --- Sottocartella (livello successivo MandraKodi) ---
        if ext_link:
            full_url   = _mandra_url(ext_link)
            li = xbmcgui.ListItem(label=title)
            li.setArt({'thumb': thumb, 'fanart': fanart})
            _tag = li.getVideoInfoTag()
            _tag.setTitle(title)
            _tag.setPlot(info_str)
            query      = {'action': 'mandra_sub', 'url': full_url}
            plugin_url = f"{sys.argv[0]}?{urllib.parse.urlencode(query)}"
            xbmcplugin.addDirectoryItem(handle, plugin_url, li, isFolder=True)
            continue

        # --- Stream tramite myresolve ---
        if myresolve:
            tipo, param, lic = parse_myresolve(myresolve)
            is_folder_type   = tipo in FOLDER_RESOLVER_TYPES

            li = xbmcgui.ListItem(label=title)
            li.setArt({'thumb': thumb, 'fanart': fanart})
            _tag = li.getVideoInfoTag()
            _tag.setTitle(title)
            _tag.setPlot(info_str)

            if is_folder_type or tipo in ('freeshot', 'koolto', 'antenacode', 'antena',
                                           'mediahosting', 'streamtp', 'tvapp', 'skytv',
                                           'pulive', 'vudeo', 'voe', 'sib', 'sibnet',
                                           'stape', 'streamtape', 'markky', 'daddy',
                                           'lvtv', 'livetv', 'hunter', 'scom', 'scommunity',
                                           'scws', 'scws2', 'moviesc', 'gaga', 'wigi',
                                           'prodata', 'wikisport', 'sansat', 'vividmosaica',
                                           'daily'):
                # Questi mostrano sub-menu con opzioni di player
                query      = {'action': 'mandra_play', 'tipo': tipo, 'param': param}
                plugin_url = f"{sys.argv[0]}?{urllib.parse.urlencode(query)}"
                xbmcplugin.addDirectoryItem(handle, plugin_url, li, isFolder=True)
            elif param:
                # Playback diretto (amstaff, ffmpeg, vavooPlay, ppv JSON, ecc.)
                li.setProperty('IsPlayable', 'true')
                query = {'action': 'mandra_play', 'tipo': tipo, 'param': param}
                if lic:
                    query['lic'] = lic
                plugin_url = f"{sys.argv[0]}?{urllib.parse.urlencode(query)}"
                xbmcplugin.addDirectoryItem(handle, plugin_url, li, isFolder=False)
            else:
                li2 = xbmcgui.ListItem(label=f"[{tipo.upper()}] {title}")
                li2.setArt({'thumb': thumb, 'fanart': fanart})
                _tag = li2.getVideoInfoTag()
                _tag.setTitle(title)
                _tag.setPlot(f"Tipo non supportato: {tipo}")
                xbmcplugin.addDirectoryItem(handle, '', li2, isFolder=False)
            continue

        # --- Link diretto (link= nel JSON MandraKodi) ---
        if link and str(link).lower() != 'ignore' and not str(link).startswith('acestream://'):
            # Estrae URL pulito da eventuale notazione |headers per controllare il tipo
            clean_url  = link.split('|')[0] if '|' in link else link
            li = xbmcgui.ListItem(label=title)
            li.setArt({'thumb': thumb, 'fanart': fanart})
            _tag = li.getVideoInfoTag()
            _tag.setTitle(title)
            _tag.setPlot(info_str)
            li.setProperty('IsPlayable', 'true')
            query      = {'action': 'play', 'url': link, 'license': ''}
            plugin_url = f"{sys.argv[0]}?{urllib.parse.urlencode(query)}"
            xbmcplugin.addDirectoryItem(handle, plugin_url, li, isFolder=False)
            continue

        # --- AceStream (non supportato) ---
        if str(link).startswith('acestream://'):
            li = xbmcgui.ListItem(label=f"[ACE] {title}")
            li.setArt({'thumb': thumb, 'fanart': fanart})
            _tag = li.getVideoInfoTag()
            _tag.setTitle(title)
            _tag.setPlot('AceStream non supportato in questo addon')
            xbmcplugin.addDirectoryItem(handle, '', li, isFolder=False)
            continue

        logga(f"Item senza azione riconoscibile: '{title}'")


if __name__ == '__main__':
    run()
