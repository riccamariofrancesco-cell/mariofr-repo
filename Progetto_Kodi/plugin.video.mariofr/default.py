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

# VERSIONE 1.0.33 - 2026-03-12

# URL ORIGINALI DELLA TUA REPO
URL_JSON   = "https://raw.githubusercontent.com/riccamariofrancesco-cell/mariofr-repo/refs/heads/main/playlist.json"
URL_UA_TXT = "https://raw.githubusercontent.com/riccamariofrancesco-cell/mariofr-repo/refs/heads/main/user_agents.txt"
URL_MANDRA = "https://test34344.herokuapp.com/filter.php"

UA_FALLBACK = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"

AMSTAFF_HEADERS = (
    "Referer=https://amstaff.city/"
    "&Origin=https://amstaff.city"
    "&User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

# Resolver che restituiscono JSON sub-menu (isFolder=True)
FOLDER_RESOLVER_TYPES = {
    'taxi', 'anyplay', 'toonita', 'm3uplus', 'ppv', 'daddycode',
    'webcam', 'sansat', 'mototv', 'sportzx', 'sports99',
    'seriesc', 'vavooch', 'imdblist', 'rocktalk',
}

# ===========================================================================
# UTILITY  (identiche all'originale)
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

def remove_control_chars(s):
    if not s:
        return ""
    return ''.join(c for c in s if ord(c) >= 32)

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
        ua = "MandraKodi2@@2.2.1@@@@" + deviceId
        hdr = {'User-Agent': ua}
    try:
        req = urllib.request.Request(url, headers=hdr)
        response = urllib.request.urlopen(req, timeout=45)
        html = response.read().decode('utf-8')
        response.close()
        retff = html[0:30] if html else "NOCODE"
        logga('OK REQUEST FROM ' + url + ' resp: ' + retff)
    except:
        logga('Error to open job: ' + url)
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

def fetch_mandra_json(url):
    try:
        content = makeJob(url)
        data = json.loads(content)
        return data.get('items', [])
    except Exception as e:
        logga(f"fetch_mandra_json ERROR [{url}]: {e}")
        return []

# ===========================================================================
# PARSER  myresolve
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
# RESOLVERS - stream diretti (restituiscono URL stringa)
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
        return ''
    token = m.group(1)
    url = f"https://planetary.lovecdn.ru/{code}/tracks-v1a1/mono.m3u8?token={token}"
    logga(f"freeshot URL: {url}")
    return url

def resolve_mediahosting(stream_id):
    logga(f"resolve_mediahosting: {stream_id}")
    page = http_get(f"https://mediahosting.space/embed/player?stream={stream_id}",
                    headers={'Referer': "https://mediahosting.space/"})
    m = re.search(r'<source src="(.*?)"', page)
    if m:
        logga(f"mediahosting URL: {m.group(1)}")
        return m.group(1)
    return ''

def resolve_streamtp(stream_id):
    logga(f"resolve_streamtp: {stream_id}")
    page = http_get(f"https://streamtp501.com/global1.php?stream={stream_id}",
                    headers={'Referer': "https://streamtp501.com/"})
    m = re.search(r'playbackURL\s*=\s*"(.*?)"', page)
    if m:
        logga(f"streamtp URL: {m.group(1)}")
        return m.group(1)
    return ''

def resolve_tvapp(channel_name):
    logga(f"resolve_tvapp: {channel_name}")
    headers = {'User-Agent': "Mozilla/5.0", 'Referer': "https://thetvapp.to/"}
    page1 = http_get(f"https://thetvapp.to/tv/{channel_name}", headers=headers)
    m = re.search(r'<div id="stream_name" name="(.*?)">', page1)
    if not m:
        return ''
    stream_key = m.group(1)
    page2 = http_get(f"https://thetvapp.to/token/{stream_key}", headers=headers)
    try:
        url = json.loads(page2).get('url', '')
        logga(f"tvapp URL: {url}")
        return url
    except Exception as e:
        logga(f"tvapp JSON error: {e}")
        return ''

def resolve_skytv(channel_id):
    logga(f"resolve_skytv: {channel_id}")
    page = http_get(f"https://apid.sky.it/vdp/v1/getLivestream?id={channel_id}&isMobile=false")
    try:
        url = json.loads(page).get('streaming_url', '')
        logga(f"skyTV URL: {url}")
        return url
    except Exception as e:
        logga(f"skyTV error: {e}")
        return ''

def resolve_antenacode(code):
    logga(f"resolve_antenacode: {code}")
    ua = "Mozilla/5.0 (iPad; CPU OS 133 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
    url = (f"https://webufffit.mizhls.ru/lb/prima{code}/index.m3u8"
           f"|Referer=https://1qwebplay.xyz/&Origin=https://1qwebplay.xyz"
           f"&Connection=keep-alive&User-Agent={ua}")
    logga(f"antenaCode URL: {url}")
    return url

def resolve_antena(page_url):
    logga(f"resolve_antena: {page_url}")
    page = http_get(page_url, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://antenasports.ru/'})
    iframe_url = preg_match(page, r'iframe\s*src="([^"]+)')
    arr = iframe_url.split("=")
    id_ch = arr[1] if len(arr) > 1 else ''
    if not id_ch:
        return ''
    ua = "Mozilla/5.0 (iPad; CPU OS 133 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
    url = (f"https://webufffit.mizhls.ru/lb/{id_ch}/index.m3u8"
           f"|Referer=https://1qwebplay.xyz/&Origin=https://1qwebplay.xyz"
           f"&Connection=keep-alive&User-Agent={ua}")
    logga(f"antena URL: {url}")
    return url

def resolve_koolto(code):
    logga(f"resolve_koolto: {code}")
    url = (f"https://www.kool.to/play/{code}/index.m3u8"
           f"|Referer=https://www.kool.to/&Origin=https://www.kool.to"
           f"&Connection=keep-alive&User-Agent=ipad")
    logga(f"koolto URL: {url}")
    return url

def resolve_pulive(stream_id):
    logga(f"resolve_pulive: {stream_id}")
    url_page = f"https://pulivetv146.com/player.html?id={stream_id}"
    page = http_get(url_page, headers={'User-Agent': 'Mozilla/5.0'})
    txt = preg_match(page, r'window\.config=(.*?)<\/script>')
    x = txt.split("match:")
    if len(x) < 2:
        return ''
    src = preg_match(x[1], r'source:"(.*?)"')
    url = src + "|verifypeer=false" if src else ''
    logga(f"pulive URL: {url}")
    return url

def resolve_vudeo(vid_id):
    logga(f"resolve_vudeo: {vid_id}")
    page_in = f"https://vudeo.ws/{vid_id}.html"
    page = http_get(page_in, headers={'User-Agent': 'iPad', 'Referer': page_in})
    if preg_match(page, '<b>File Not Found</b>'):
        return ''
    src = preg_match(page, r'sources:\s*\["(.*?)"\]')
    if not src:
        return ''
    url = f"{src}|referer={page_in}"
    logga(f"vudeo URL: {url}")
    return url

def resolve_voe(page_url):
    logga(f"resolve_voe: {page_url}")
    page = http_get(page_url, headers={'User-Agent': 'iPad', 'Referer': page_url})
    src = preg_match(page, r"'hls':\s*'(.*?)'")
    if not src:
        return ''
    try:
        url = base64.b64decode(src).decode('utf-8') + f"|referer={page_url}"
        logga(f"voe URL: {url}")
        return url
    except Exception as e:
        logga(f"voe base64 error: {e}")
        return ''

def resolve_sibnet(video_id):
    logga(f"resolve_sibnet: {video_id}")
    url_p = f"https://video.sibnet.ru/shell.php?videoid={video_id}"
    page = http_get(url_p, headers={'User-Agent': 'iPad', 'Referer': 'https://video.sibnet.ru/'})
    iframe_url = preg_match(page, r"player\.src\(\[\{src:\s*\"(.*?)\",\s*type")
    if not iframe_url:
        return ''
    final = f"https://video.sibnet.ru{iframe_url}|Referer=https://video.sibnet.ru/&Origin=https://video.sibnet.ru&User-Agent=iPad"
    logga(f"sibNet URL: {final}")
    return final

def resolve_streamtape(page_url):
    logga(f"resolve_streamtape: {page_url}")
    page = http_get(urllib.parse.unquote(page_url),
                    headers={'User-Agent': UA_FALLBACK, 'Referer': 'https://toonitalia.green/'})
    html_code = preg_match(page, r'<\/video><script>(.*?)<\/body>')
    iframe_url = preg_match(html_code, r'style="display:none;">(.*?)<\/div>')
    if not iframe_url:
        return ''
    link1 = iframe_url.split('&token=')
    link_pre = link1[0]
    info1 = preg_match(page, r'<script>document\.getElementById(.*?)<\/script>')
    info = info1.split(';')[0]
    tkn = preg_match(info, r"&token=(.*?)'")
    link_split = link_pre.split("?")[1] if "?" in link_pre else link_pre
    final = f"https://streamta.pe/get_video?{link_split}&token={tkn}&stream=1"
    logga(f"streamTape URL: {final}")
    return final

def resolve_markky(page_url):
    logga(f"resolve_markky: {page_url}")
    page = http_get(page_url, headers={'User-Agent': UA_FALLBACK, 'Referer': 'https://markkystreams.com/'})
    url = preg_match(page, r'source:\s*"(.*?)"')
    if not url:
        return ''
    final = f"{url}|connection=keepalive&verifypeer=false&Referer={page_url}"
    logga(f"markky URL: {final}")
    return final

def resolve_daddylive_direct(code):
    """Risoluzione diretta backend daddylive (dalla resolve_link di myResolver)."""
    logga(f"resolve_daddylive_direct: {code}")
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 OPR/124.0.0.0'
    try:
        iframe_url = f"https://codepcplay.fun/premiumtv/daddyhd.php?id={code}"
        js = http_get(iframe_url, headers={'User-Agent': user_agent, 'Referer': 'https://dlhd.link/'})
        pattern = r'const\s+var_[a-zA-Z0-9]+\s*=\s*["\']([^"\']+)["\']'
        matches = re.findall(pattern, js)
        if len(matches) < 5:
            logga("daddylive: parametri insufficienti")
            return ''
        auth_token, channel_key, auth_country, auth_ts, auth_expiry = matches[:5]
        fingerprint = f"{user_agent}|1920x1080|Europe/Rome|it-IT"
        sign_data   = f"{channel_key}|{auth_country}|{auth_token}|{user_agent}|{fingerprint}"
        client_token = base64.b64encode(sign_data.encode('utf-8')).decode('ascii')
        lookup_url = f"https://chevy.giokko.ru/server_lookup?channel_id={channel_key}"
        lookup_resp = http_get(lookup_url, headers={
            'User-Agent': user_agent, 'Referer': 'https://codepcplay.fun',
            'Origin': 'https://codepcplay.fun',
            'Authorization': f'Bearer {auth_token}',
            'X-Channel-Key': channel_key,
            'X-Client-Token': client_token
        })
        server_key = preg_match(lookup_resp, r'"server_key":"(.*?)"')
        if not server_key:
            return ''
        if server_key == 'top1/cdn':
            stream_url = f'https://top1.kiko2.ru/top1/cdn/{channel_key}/mono.css'
        else:
            stream_url = f'https://{server_key}new.kiko2.ru/{server_key}/{channel_key}/mono.css'
        ua_enc = urllib.parse.quote(user_agent, safe='')
        cookie_enc = urllib.parse.quote(f"eplayer_session={auth_token}", safe='')
        m3u8 = (f"{stream_url}|Referer=https://codepcplay.fun/&Origin=https://codepcplay.fun"
                f"&Connection=Keep-Alive&User-Agent={ua_enc}&Cookie={cookie_enc}")
        logga(f"daddylive URL: {m3u8}")
        return m3u8
    except Exception as e:
        logga(f"resolve_daddylive_direct error: {e}")
        return ''

def resolve_daddy(page_url):
    logga(f"resolve_daddy: {page_url}")
    page = http_get(page_url, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://daddylivestream.com/'})
    iframe_url = preg_match(page, r'iframe\s*src="([^"]+)')
    logga(f"daddy iframe: {iframe_url}")
    if iframe_url.endswith(".mp4"):
        return iframe_url
    if iframe_url.startswith("http"):
        page2 = http_get(iframe_url.replace("caq21harderv991gpluralplay", "forcedtoplay"),
                          headers={'User-Agent': 'Mozilla/5.0', 'Referer': page_url})
        iframe_url2 = preg_match(page2, r'iframe\s*src="([^"]+)')
        if not iframe_url2:
            video_url = preg_match(page2.replace('//source:', '//source_no:'), "source:'(.*?)'")
            if video_url:
                ip64 = "MTUxLjI1LjIzMS43MQ=="
                return f"{video_url}?auth={ip64}|Keep-Alive=true&Referer={page_url}&User-Agent={UA_FALLBACK}"
        if "http" in iframe_url2:
            page3 = http_get(iframe_url2, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://widevine.licenses4.me/'})
            video_url = preg_match(page3, r"Clappr\.Player[\w\W]*?\.source:'(.*?)'")
            if "|" in video_url:
                video_url = video_url.split("?auth")[0]
            if video_url:
                ip64 = "MTUxLjI1LjIzMS43MQ=="
                return f"{video_url}?auth={ip64}|Keep-Alive=true&Referer={page_url}&User-Agent={UA_FALLBACK}"
    # Fallback diretto
    try:
        arr_tmp = page_url.split("stream-")
        v_id = arr_tmp[1].split(".")[0]
        return resolve_daddylive_direct(v_id)
    except:
        return ''

def resolve_wikisport(param):
    logga(f"resolve_wikisport: {param}")
    ua = UA_FALLBACK
    page_url = f"https://fiveyardlab.com/wiki.php?player=desktop&live={param}"
    page = http_get(page_url, headers={'User-Agent': ua, 'Referer': 'https://wikisport.click'})
    iframe_url = preg_match(page, r'return\(\[(.*?)\]')
    final_url = iframe_url.replace('"', '').replace(',', '').replace('\\', '').replace('https:////', 'https://')
    logga(f"wikisport URL: {final_url}")
    url = (f"{final_url}|connection=keepalive&Referer={page_url}"
           f"&Origin=https://wikisport.click&User-Agent={ua}")
    return url

def resolve_vividmosaica(param):
    logga(f"resolve_vividmosaica: {param}")
    player_url = f"https://vividmosaica.com/embed3.php?player=desktop&live=do{param}"
    page = http_get(player_url, headers={'Referer': 'https://l2l2.link/'})
    match = re.search(r'return\s*\(\s*\[(.*?)\]\s*', page, re.DOTALL)
    src = "ignore"
    if match:
        content = match.group(1)
        src = content.replace('"', '').replace(',', '').replace('\\/', '/').replace('https:////', 'https://')
    url = f"{src}|Referer=https://vividmosaica.com/"
    logga(f"vividmosaica URL: {url}")
    return url

def resolve_sansat(param):
    """sansat delega a vividmosaica."""
    return resolve_vividmosaica(param)

def resolve_daily(video_id):
    logga(f"resolve_daily: {video_id}")
    url_api = f"https://www.dailymotion.com/player/metadata/video/{video_id}"
    data_str = http_get(url_api, headers={'User-Agent': UA_FALLBACK, 'Referer': 'https://www.dailymotion.com'})
    try:
        data_j = json.loads(data_str)
        url = data_j["qualities"]["auto"][0]["url"]
        logga(f"daily URL: {url}")
        return url
    except Exception as e:
        logga(f"daily error: {e}")
        return ''

def resolve_livetv(page_url):
    logga(f"resolve_livetv: {page_url}")
    page = http_get(page_url)
    flat = page.replace("\n", "").replace("\r", "").replace("\t", "")
    src = preg_match(flat, r'<iframe\s+allowFullScreen="true"[^>]+src="([^"]*)')
    if not src:
        return ''
    if src.startswith("//"):
        src = "https:" + src
    if "topembed.pw" in src:
        arr = src.split("/")
        ext_code = arr[-1].replace("ex", "bet")
        server_resp = http_get(f"https://topembed.pw/server_lookup.php?channel_id={ext_code}")
        try:
            server_key = json.loads(server_resp).get("server_key", "")
        except:
            server_key = ""
        if server_key == "top1/cdn":
            final = f"https://top1.kiko2.ru/top1/cdn/{ext_code}/mono.m3u8"
        elif server_key:
            final = f"https://{server_key}new.kiko2.ru/{server_key}/{ext_code}/mono.m3u8"
        else:
            return ''
    else:
        arr_p2 = src.split("play?url=")
        if len(arr_p2) > 1:
            final = urllib.parse.unquote(arr_p2[1])
        else:
            page2 = http_get(src)
            final = preg_match(page2, "source: '(.*?)'")
    host_parts = src.split("/")
    host = host_parts[0] + "//" + host_parts[2] if len(host_parts) >= 3 else ""
    if final and "|" not in final:
        final = f"{final}|Referer={host}/&Origin={host}&User-Agent=iPad"
    logga(f"livetv URL: {final}")
    return final

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
    flat_page = page.replace("\n", "").replace("\r", "").replace("\t", "")
    tit = preg_match(flat_page, r'<div id="player"><\/div><script>(.*?)\)\)<\/script>')
    if not tit:
        return ''
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
        link = preg_match(result, "source: '(.*?)'")
        logga(f"hunterjs URL: {link}")
        return f"{link}|referer={page_url}" if link else ''
    except Exception as e:
        logga(f"hunterjs decode error: {e}")
        return ''

def resolve_scws(scws_id):
    logga(f"resolve_scws: {scws_id}")
    from hashlib import md5 as _md5
    from base64 import b64encode as _b64e
    try:
        ip_page = http_get("http://test34344.herokuapp.com/getMyIp.php")
        client_ip = json.loads(ip_page).get("client_ip", "")
    except:
        client_ip = get_my_ip()
    expires = int(time.time() + 172800)
    token = (_b64e(_md5(f'{expires}{client_ip} Yc8U6r8KjAKAepEA'.encode()).digest())
             .decode().replace('=', '').replace('+', '-').replace('/', '_'))
    url = f'https://scws.work/master/{scws_id}?token={token}&expires={expires}&canCast=1&b=1&n=1'
    logga(f"scws URL: {url}")
    return url

def resolve_scommunity(param):
    logga(f"resolve_scommunity: {param}")
    sc_url = "https://raw.githubusercontent.com/mandrakodi/mandrakodi.github.io/main/data/cs_url.txt"
    base = makeRequest(sc_url).replace("\n", '') + "watch/"
    url_comm = base + param
    http_get(url_comm)
    time.sleep(2.5)
    page = http_get(url_comm)
    patron = r'<div id="app" data-page="(.*?)">'
    json_video = preg_match(page, patron)
    data_json = json_video.replace('&quot;', '"')
    try:
        arr_j = json.loads(data_json)
        scws_id = str(arr_j["props"]["episode"]["scws_id"])
        return resolve_scws(scws_id)
    except Exception as e:
        logga(f"scommunity error: {e}")
        return ''

def resolve_vavoo(vavoo_url):
    logga(f"resolve_vavoo: {vavoo_url}")
    # Metodo 1: API MediaHubMX con firma addonSig
    try:
        adesso = int(time.time() * 1000)
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
                    logga(f"vavoo resolved (API): {result[0]['url']}")
                    return result[0]['url']
                elif isinstance(result, dict) and result.get('url'):
                    logga(f"vavoo resolved (API dict): {result['url']}")
                    return result['url']
    except Exception as e:
        logga(f"vavoo API error: {e}")
    # Metodo 2: redirect diretto
    try:
        req = urllib.request.Request(vavoo_url, headers={'User-Agent': 'VAVOO/2.6'})
        with urllib.request.urlopen(req, timeout=15) as r:
            final_url = r.geturl()
            if final_url != vavoo_url:
                logga(f"vavoo resolved (redirect): {final_url}")
                return final_url
    except Exception as e:
        logga(f"vavoo redirect error: {e}")
    logga("vavoo: fallback URL originale")
    return vavoo_url

# jsunpack-dependent resolvers con graceful fallback
def _try_jsunpack_resolve(page_url, referer=''):
    try:
        import jsunpack
        refe = referer or page_url
        page = http_get(page_url, headers={'User-Agent': UA_FALLBACK, 'Referer': refe})
        find = re.findall(r'eval\(function(.+?.+)', page)
        if not find:
            return ''
        unpack = jsunpack.unpack(find[0])
        for pattern in (r'src:"([^"]*)', r'file:"([^"]*)', r'src="([^"]*)', r'source:"([^"]*)'):
            m = re.search(pattern, unpack)
            if m:
                url = m.group(1)
                return ('https:' + url) if url.startswith('//') else url
        return ''
    except ImportError:
        logga("jsunpack non disponibile - resolver non supportato")
        return ''
    except Exception as e:
        logga(f"jsunpack error: {e}")
        return ''

def resolve_gaga(page_url):
    logga(f"resolve_gaga: {page_url}")
    url = _try_jsunpack_resolve(page_url, "https://calcio.events")
    logga(f"gaga URL: {url}")
    return url

def resolve_wigi(param):
    logga(f"resolve_wigi: {param}")
    wigi_url, refe = (param.split("|")[0], param.split("|")[1]) if "|" in param else (param, param)
    url = _try_jsunpack_resolve(wigi_url, refe)
    if url:
        host_parts = wigi_url.split("/")
        host = host_parts[0] + "//" + host_parts[2] if len(host_parts) >= 3 else ""
        return f"{url}|Referer={host}/&Origin={host}&User-Agent={UA_FALLBACK}"
    return ''

def resolve_prodata(page_url):
    logga(f"resolve_prodata: {page_url}")
    url = _try_jsunpack_resolve(page_url)
    if url:
        return url + "&verifypeer=false"
    return ''

# ===========================================================================
# RESOLVERS - restituiscono JSON (sub-menu cartella)
# ===========================================================================

def resolve_ppv(page_url):
    logga(f"resolve_ppv: {page_url}")
    ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 OPR/124.0.0.0'
    page = http_get(page_url, headers={'User-Agent': ua, 'Referer': 'https://ppvs.to/'})
    match = re.findall(r'const src = atob\("(.*?)"\)', page)
    if not match:
        return None
    stream_url = base64.b64decode(match[0]).decode('utf-8')
    link = stream_url.replace("index.m3u8",
            f"tracks-v1a1/mono.ts.m3u8|Referer=https://playembed.top/&Origin=https://playembed.top&User-Agent={ua}")
    json_text = (
        '{"SetViewMode":"50","items":['
        '{"title":"[COLOR lime]PLAY STREAM[/COLOR] [COLOR gold](DIRECT)[/COLOR]","link":"' + link + '",'
        '"thumbnail":"https://i.imgur.com/8EL6mr3.png",'
        '"fanart":"https://www.stadiotardini.it/wp-content/uploads/2016/12/mandrakata.jpg",'
        '"info":"by MandraKodi"},'
        '{"title":"[COLOR orange]PLAY STREAM[/COLOR] [COLOR gold](FFMPEG)[/COLOR]","myresolve":"ffmpeg_noRef@@' + link + '",'
        '"thumbnail":"https://i.imgur.com/8EL6mr3.png",'
        '"fanart":"https://www.stadiotardini.it/wp-content/uploads/2016/12/mandrakata.jpg",'
        '"info":"by MandraKodi"}'
        ']}'
    )
    return json_text

def resolve_anyplay(serie_id):
    logga(f"resolve_anyplay: {serie_id}")
    url_any = f"https://aniplay.co/series/{serie_id}"
    page = http_get(url_any, headers={'User-Agent': UA_FALLBACK, 'Referer': 'https://aniplay.co/'})
    data_j = preg_match(page, r'const data = \[(.*?)\];')
    arr_p1 = data_j.split(',episodes:')
    if len(arr_p1) < 2:
        return None
    srrs = arr_p1[1].split(',similarSeries:')[0]
    dj2 = '{"episodes":' + srrs
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
        json_text = '{"SetViewMode":"503","items":['
        num_it = 0
        logo = "https://png.pngtree.com/png-vector/20230124/ourmid/pngtree-arrow-icon-3d-play-png-image_6565151.png"
        for ep in json.loads(dj2).get("episodes", []):
            link = ep.get("streaming_link", "")
            num_ep = str(ep.get("number", ""))
            title_ep = ep.get("title") or ""
            tit = f"Ep. {num_ep} - {title_ep}"
            if num_it > 0:
                json_text += ','
            json_text += (f'{{"title":"[COLOR gold]{tit}[/COLOR]","link":"{link}",'
                          f'"thumbnail":"{logo}",'
                          f'"fanart":"https://www.stadiotardini.it/wp-content/uploads/2016/12/mandrakata.jpg",'
                          f'"info":"by MandraKodi"}}')
            num_it += 1
        json_text += ']}'
        return json_text
    except Exception as e:
        logga(f"anyplay JSON error: {e}")
        return None

def resolve_taxi(slug):
    logga(f"resolve_taxi: {slug}")
    sc_url = "https://raw.githubusercontent.com/mandrakodi/mandrakodi.github.io/main/data/taxi_url.txt"
    base = makeRequest(sc_url).replace("\n", '')
    url = f"{base}stream/{slug}"
    page = http_get(url).replace("\n", "").replace("\r", "").replace("\t", "")
    ret = re.findall(
        r'<a href="#" allowfullscreen data-link="(.*?)" id="(.*?)" data-num="(.*?)" data-title="(.*?)">\d+</a>(.*?)</li>',
        page, re.DOTALL)
    json_text = '{"SetViewMode":"503","items":['
    num_it = 0
    for (link, id_, ep, tito, mirror) in ret:
        ret2_list = re.findall(r'<a href="#" class="mr" data-link="(.*?)">', mirror, re.DOTALL)
        if not ret2_list:
            continue
        link = ret2_list[1] if (len(ret2_list) > 1 and "supervideo" in ret2_list[0]) else ret2_list[0]
        if num_it > 0:
            json_text += ','
        json_text += (f'{{"title":"[COLOR lime]{ep}[/COLOR]","myresolve":"proData@@{link}",'
                      f'"thumbnail":"https://www.giardiniblog.it/wp-content/uploads/2018/12/serie-tv-streaming.jpg",'
                      f'"fanart":"https://www.stadiotardini.it/wp-content/uploads/2016/12/mandrakata.jpg",'
                      f'"info":"{tito.replace(chr(34), "")}"' + '}}')
        num_it += 1
    if num_it == 0:
        json_text += ('{"title":"[COLOR red]NO HOST FOUND[/COLOR]","link":"ignore",'
                      '"thumbnail":"https://www.giardiniblog.it/wp-content/uploads/2018/12/serie-tv-streaming.jpg",'
                      '"fanart":"https://www.stadiotardini.it/wp-content/uploads/2016/12/mandrakata.jpg",'
                      '"info":"NO INFO"}')
    json_text += ']}'
    return json_text

def resolve_webcam(param):
    """Webcam da skylinewebcams. mode_page formato: '0_webcam/...' o '1_webcam/...'"""
    logga(f"resolve_webcam: {param}")
    arr_t = param.split('_', 1)
    mode = arr_t[0]
    page_path = arr_t[1] if len(arr_t) > 1 else param
    page_url = f"https://www.skylinewebcams.com/it/{page_path}.html"
    headers = {'User-Agent': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36"}
    page = http_get(page_url, headers=headers)
    html_flat = page.replace("\n", '').replace("\r", '').replace("\t", '')

    if mode == "0":
        lista = re.findall(r'<a href="it/webcam/(.*?)" class="col-xs-12 col-sm-6 col-md-4">(.*?)</a>',
                           html_flat, re.DOTALL)
        json_text = '{"SetViewMode":"503","items":['
        lista_cam = []
        for (link, tit) in lista:
            titolo = preg_match(tit, r'<p class="tcam">(.*?)</p>') or "Cam"
            img = preg_match(tit, r'<img src="(.*?)"') or ""
            info = preg_match(tit, r'<p class="subt">(.*?)</p>') or "by MandraKodi"
            info_plus = preg_match(tit, r'<span class="lcam">(.*?)</span>') or ""
            lista_cam.append(f"{titolo}@@{img}@@{link}@@{info}@@{info_plus}")
        lista_cam.sort()
        for i, wCam in enumerate(lista_cam):
            arr = wCam.split("@@")
            tit_c, img_c, lnk, inf, inf_plus = arr[0], arr[1], arr[2], arr[3], arr[4]
            info_p = f" [COLOR lime]({inf_plus})[/COLOR]" if inf_plus else ""
            if i > 0:
                json_text += ','
            json_text += (f'{{"title":"[COLOR gold]{tit_c}[/COLOR]{info_p}",'
                          f'"myresolve":"webcam@@1_webcam/{lnk.replace(".html","")}",'
                          f'"thumbnail":"{img_c}",'
                          f'"fanart":"https://www.stadiotardini.it/wp-content/uploads/2016/12/mandrakata.jpg",'
                          f'"info":"{inf}"}}')
    else:
        # mode 1: singola webcam
        titolo = preg_match(html_flat, r'<h1>(.*?)</h1>').replace("Live webcam", "") or "Watch Stream"
        info = preg_match(html_flat, r'<h2>(.*?)</h2>') or "by @mandrakodi"
        img = preg_match(html_flat, r'<meta property="og:image" content="(.*?)"') or ""
        url1 = "ignore"
        src = preg_match(html_flat, r"source:'(.*?)'")
        if src:
            url1 = f"https://hd-auth.skylinewebcams.com/{src.replace('livee', 'live')}|Referer={page_url}&User-Agent=Mozilla%2F5.0"
        json_text = (f'{{"SetViewMode":"503","items":['
                     f'{{"title":"[COLOR gold]{titolo}[/COLOR]","link":"{url1}",'
                     f'"thumbnail":"{img}",'
                     f'"fanart":"https://www.stadiotardini.it/wp-content/uploads/2016/12/mandrakata.jpg",'
                     f'"info":"{info}"}}')
    json_text += ']}'
    logga(f"webcam JSON len: {len(json_text)}")
    return json_text

def resolve_m3uplus(param):
    logga(f"resolve_m3uplus: {param}")
    win = xbmcgui.Window(10000)
    arr_in = param.split("_@|@_")
    mode = arr_in[0]
    headers = {'User-Agent': 'ipad'}
    json_text = ""

    if mode == "0":
        win.setProperty("sessionVar1", param)
        host, usr, pwd = arr_in[1], arr_in[2], arr_in[3]
        api_url = f"http://{host}/player_api.php?username={usr}&password={pwd}&action=get_live_categories"
        lista = json.loads(http_get(api_url, headers=headers))
        json_text = '{"SetViewMode":"503","items":['
        for i, item in enumerate(lista):
            cat_id = item.get("category_id", "")
            name = item.get("category_name", "")
            if i > 0:
                json_text += ','
            json_text += (f'{{"title":"[COLOR orange]=*= {name} =*=[/COLOR]",'
                          f'"myresolve":"m3uPlus@@1_@|@_{name}_@|@_{cat_id}",'
                          f'"thumbnail":"https://static.vecteezy.com/system/resources/thumbnails/065/914/783/small/stylized-3d-rendering-of-a-file-folder-icon-for-data-management-free-png.png",'
                          f'"fanart":"https://www.stadiotardini.it/wp-content/uploads/2016/12/mandrakata.jpg",'
                          f'"info":"by MandraKodi"}}')
        json_text += ']}'

    elif mode == "1":
        par_sess = win.getProperty("sessionVar1")
        cat_id = arr_in[2]
        arr_sess = par_sess.split("_@|@_")
        host, usr, pwd = arr_sess[1], arr_sess[2], arr_sess[3]
        api_url = f"http://{host}/player_api.php?username={usr}&password={pwd}&action=get_live_streams&category_id={cat_id}"
        lista = json.loads(http_get(api_url, headers=headers))
        json_text = '{"SetViewMode":"503","items":['
        for i, item in enumerate(lista):
            stream_id = item.get("stream_id", "")
            link_url = f"http://{host}/live/{usr}/{pwd}/{stream_id}.m3u8"
            name = item.get("name", "")
            icon = item.get("stream_icon") or "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8f/Microsoft_Stream.svg/512px-Microsoft_Stream.svg.png"
            if i > 0:
                json_text += ','
            json_text += (f'{{"title":"[COLOR lime]{name}[/COLOR]","link":"{link_url}",'
                          f'"thumbnail":"{icon}",'
                          f'"fanart":"https://www.stadiotardini.it/wp-content/uploads/2016/12/mandrakata.jpg",'
                          f'"info":"by MandraKodi"}}')
        json_text += ']}'

    return json_text if json_text else None

# ===========================================================================
# DISPATCH  resolver
# ===========================================================================

def dispatch_resolver(tipo, param):
    """
    Restituisce una tupla di 3 elementi:
      ('url', url_string, is_ffmpeg_bool)   per stream diretti
      ('json', json_string, None)            per sub-menu
      ('error', messaggio, None)             per errori
    """
    tipo = tipo.lower()

    # ---- stream diretti ----
    if tipo == 'amstaff':
        return ('url', param, False)
    elif tipo in ('ffmpeg', 'ffmpeg_noref'):
        return ('url', param, True)
    elif tipo == 'vavooplay':
        url = resolve_vavoo(param)
        return ('url', url, False) if url else ('error', 'Vavoo: risoluzione fallita', None)
    elif tipo == 'freeshot':
        url = resolve_freeshot(param)
        return ('url', url, True) if url else ('error', f'freeshot: URL non trovato per {param}', None)
    elif tipo == 'mediahosting':
        url = resolve_mediahosting(param)
        return ('url', url, True) if url else ('error', f'mediahosting: URL non trovato per {param}', None)
    elif tipo == 'streamtp':
        url = resolve_streamtp(param)
        return ('url', url, True) if url else ('error', f'streamtp: URL non trovato per {param}', None)
    elif tipo == 'tvapp':
        url = resolve_tvapp(param)
        return ('url', url, True) if url else ('error', f'tvapp: URL non trovato per {param}', None)
    elif tipo == 'skytv':
        url = resolve_skytv(param)
        return ('url', url, True) if url else ('error', f'skyTV: URL non trovato per {param}', None)
    elif tipo == 'antenacode':
        return ('url', resolve_antenacode(param), True)
    elif tipo == 'antena':
        url = resolve_antena(param)
        return ('url', url, True) if url else ('error', 'antena: URL non trovato', None)
    elif tipo == 'koolto':
        return ('url', resolve_koolto(param), True)
    elif tipo == 'pulive':
        url = resolve_pulive(param)
        return ('url', url, True) if url else ('error', f'pulive: URL non trovato per {param}', None)
    elif tipo == 'vudeo':
        url = resolve_vudeo(param)
        return ('url', url, False) if url else ('error', f'vudeo: non trovato per {param}', None)
    elif tipo == 'voe':
        url = resolve_voe(param)
        return ('url', url, False) if url else ('error', f'voe: non trovato per {param}', None)
    elif tipo in ('sib', 'sibnet'):
        url = resolve_sibnet(param)
        return ('url', url, False) if url else ('error', f'sibNet: non trovato per {param}', None)
    elif tipo in ('stape', 'streamtape'):
        url = resolve_streamtape(param)
        return ('url', url, False) if url else ('error', 'streamTape: URL non trovato', None)
    elif tipo == 'markky':
        url = resolve_markky(param)
        return ('url', url, False) if url else ('error', 'markky: URL non trovato', None)
    elif tipo == 'daddy':
        url = resolve_daddy(param)
        return ('url', url, True) if url else ('error', 'daddy: URL non trovato', None)
    elif tipo in ('lvtv', 'livetv'):
        url = resolve_livetv(param)
        return ('url', url, True) if url else ('error', 'livetv: URL non trovato', None)
    elif tipo == 'hunter':
        url = resolve_hunterjs(param)
        return ('url', url, False) if url else ('error', 'hunterjs: URL non trovato', None)
    elif tipo in ('scom', 'scommunity'):
        url = resolve_scommunity(param)
        return ('url', url, False) if url else ('error', 'scommunity: URL non trovato', None)
    elif tipo in ('scws', 'scws2', 'moviesc'):
        url = resolve_scws(param)
        return ('url', url, False) if url else ('error', 'scws: URL non trovato', None)
    elif tipo == 'gaga':
        url = resolve_gaga(param)
        return ('url', url, False) if url else ('error', 'gaga: jsunpack non disponibile', None)
    elif tipo == 'wigi':
        url = resolve_wigi(param)
        return ('url', url, False) if url else ('error', 'wigi: jsunpack non disponibile', None)
    elif tipo == 'prodata':
        url = resolve_prodata(param)
        return ('url', url, False) if url else ('error', 'proData: jsunpack non disponibile', None)
    elif tipo == 'wikisport':
        url = resolve_wikisport(param)
        return ('url', url, True) if url else ('error', 'wikisport: URL non trovato', None)
    elif tipo in ('sansat', 'vividmosaica'):
        url = resolve_vividmosaica(param)
        return ('url', url, True) if url else ('error', 'sansat/vividmosaica: URL non trovato', None)
    elif tipo == 'daily':
        url = resolve_daily(param)
        return ('url', url, False) if url else ('error', f'daily: URL non trovato per {param}', None)
    # ---- sub-menu (JSON) ----
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
# HELPERS  ListItem
# ===========================================================================

def _auto_headers_for_url(url_lower, token=''):
    if "dazn" in url_lower or "dai.google.com" in url_lower:
        host = "https://www.dazn.com"
        if token:
            ua = urllib.parse.quote_plus("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36")
            return f'{token}&referer={host}/&origin={host}&user-agent={ua}'
        ua = urllib.parse.quote("Mozilla/5.0 (Web0S; Linux/SmartTV) AppleWebKit/537.41 (KHTML, like Gecko) Large Screen Safari/537.41 LG Browser/7.00.00(LGE; WEBOS1; 05.06.10; 1); webOS.TV-2014; LG NetCast.TV-2013 Compatible (LGE, WEBOS1, wireless)")
        return f'User-Agent={ua}&Referer={host}/&Origin={host}'
    elif "lba-ew" in url_lower:
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:143.0) Gecko/20100101 Firefox/143.0"
        host = "https://www.lbatv.com"
        return f'User-Agent={ua}&Referer={host}/&Origin={host}&verifypeer=false'
    elif "discovery" in url_lower:
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0"
        host = "https://www.discoveryplus.com"
        return f'User-Agent={ua}&Referer={host}/&Origin={host}&verifypeer=false'
    elif "nowitlin" in url_lower:
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
        host = "https://www.nowtv.it"
        return f'User-Agent={ua}&Referer={host}/&Origin={host}&verifypeer=false'
    elif "vodafone.pt" in url_lower:
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0"
        host = "http://rr.cdn.vodafone.pt"
        return f'User-Agent={ua}&Referer={host}/&Origin={host}&verifypeer=false'
    elif "clarovideo.com" in url_lower:
        ua = urllib.parse.quote_plus("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 OPR/124.0.0.0")
        host = "https://clarovideo.com"
        return f'User-Agent={ua}&Referer={host}/&Origin={host}&verifypeer=false'
    elif "starzplayarabia" in url_lower:
        ua = urllib.parse.quote("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 OPR/120.0.0.0")
        return f'User-Agent={ua}&verifypeer=false'
    elif "vavoo" in url_lower:
        ua = "Mozilla/5.0 (X11; Linux armv7l) AppleWebKit/537.36 (KHTML, like Gecko) QtWebEngine/5.9.7 Chrome/56.0.2924.122 Safari/537.36 Sky_STB_ST412_2018/1.0.0 (Sky, EM150UK,)"
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
                padded = license_key + '=' * ((4 - len(license_key) % 4) % 4)
                decoded = base64.b64decode(padded).decode('utf-8').replace('{', '').replace('}', '').replace('"', '')
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

def _build_listitem_ffmpeg(url, use_referer=True):
    if use_referer and '|' not in url:
        parts = url.split('/')
        if len(parts) >= 3:
            origin  = parts[0] + '//' + parts[2]
            referer = origin + '/'
            ua = "Mozilla/5.0 (iPad; CPU OS 133 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
            final_url = f"{url}|Referer={referer}&Origin={origin}&Connection=keep-alive&User-Agent={ua}"
        else:
            final_url = url
    else:
        final_url = url
    li = xbmcgui.ListItem(path=final_url)
    li.setProperty('inputstream', 'inputstream.ffmpegdirect')
    li.setMimeType('application/x-mpegURL')
    li.setProperty('inputstream.ffmpegdirect.manifest_type',      'hls')
    li.setProperty('inputstream.ffmpegdirect.is_realtime_stream', 'true')
    return li

# ===========================================================================
# MAIN  run()  —  identica struttura all'originale
# ===========================================================================

def run():
    handle = int(sys.argv[1])
    params = dict(urllib.parse.parse_qsl(sys.argv[2][1:]))

    # -----------------------------------------------------------------------
    # AZIONE: PLAY  — stream diretto (playlist.json o amstaff risolto)
    # -----------------------------------------------------------------------
    if params.get('action') == 'play':
        original_url = params.get('url', '')
        license_key  = params.get('license', '')
        url          = original_url
        url_lower    = url.lower()

        if original_url and "vavoo" in original_url:
            with urllib.request.urlopen(original_url) as response:
                url = response.geturl()
            url_lower = url.lower()

        # --- LOGICA AUTOMATICA HEADERS ---
        auto_headers = None
        token = ""

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
            ua = "Mozilla/5.0 (X11; Linux armv7l) AppleWebKit/537.36 (KHTML, like Gecko) QtWebEngine/5.9.7 Chrome/56.0.2924.122 Safari/537.36 Sky_STB_ST412_2018/1.0.0 (Sky, EM150UK,)"
            host = "https://vavoo.to"
            auto_headers = f'User-Agent={ua}&Referer={host}/&Origin={host}&Connection=keep-alive'
            logga("Auto-Header VAVOO rilevato")

        # --- SELEZIONE MANUALE SE NON AUTOMATICO ---
        if auto_headers:
            selected_headers = auto_headers
        else:
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
        li.setProperty('inputstream.adaptive.stream_headers',   selected_headers)
        li.setProperty('inputstream.adaptive.manifest_headers', selected_headers)

        # DRM: logica org.w3.clearkey
        if license_key:
            li.setProperty('inputstream.adaptive.drm_legacy', f"org.w3.clearkey|{license_key}")

        # MIMETYPE
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
        logga(f"mandra_play tipo={tipo} param={param[:60]}")

        result_type, result_data, extra = dispatch_resolver(tipo, param)

        if result_type == 'url':
            url        = result_data
            is_ffmpeg  = extra if extra is not None else False
            if is_ffmpeg:
                li = _build_listitem_ffmpeg(url, use_referer=('noref' not in tipo))
            else:
                headers_str = _auto_headers_for_url(url.lower()) or AMSTAFF_HEADERS
                lic = params.get('lic', '')
                li = _build_listitem_adaptive(url, headers_str, lic)
            xbmcplugin.setResolvedUrl(handle, True, li)

        elif result_type == 'json':
            try:
                data = json.loads(result_data)
                items = data.get('items', [])
                _render_mandra_items(handle, items)
                xbmcplugin.endOfDirectory(handle)
            except Exception as e:
                logga(f"mandra_play JSON render error: {e}")
                xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem())

        else:
            xbmcgui.Dialog().notification("Errore", result_data,
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
    # NAVIGAZIONE PLAYLIST NORMALE  —  identica all'originale
    # -----------------------------------------------------------------------
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
            li.setArt({'icon': 'DefaultFolder.png'})
            query = {'action': 'category', 'category': cat}
            plugin_url = f"{sys.argv[0]}?{urllib.parse.urlencode(query)}"
            xbmcplugin.addDirectoryItem(handle, plugin_url, li, isFolder=True)

        # Voce MandraKodi
        li_m = xbmcgui.ListItem(label="📺 MandraKodi")
        li_m.setArt({'icon': 'DefaultFolder.png'})
        plugin_url = f"{sys.argv[0]}?{urllib.parse.urlencode({'action': 'mandra_sub', 'url': URL_MANDRA})}"
        xbmcplugin.addDirectoryItem(handle, plugin_url, li_m, isFolder=True)

    elif action == 'category':
        # SOTTOMENU: Mostra solo i canali della categoria cliccata
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


# ===========================================================================
# RENDER  items MandraKodi
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

        # Separatore / intestazione
        if link.lower() == 'ignore':
            li = xbmcgui.ListItem(label=f"── {title} ──")
            li.setArt({'thumb': thumb, 'fanart': fanart})
            li.setInfo('video', {'title': title, 'plot': info_str})
            xbmcplugin.addDirectoryItem(handle, '', li, isFolder=False)
            continue

        # Sottocartella (livello successivo)
        if ext_link:
            li = xbmcgui.ListItem(label=title)
            li.setArt({'thumb': thumb, 'fanart': fanart})
            li.setInfo('video', {'title': title, 'plot': info_str})
            query      = {'action': 'mandra_sub', 'url': ext_link}
            plugin_url = f"{sys.argv[0]}?{urllib.parse.urlencode(query)}"
            xbmcplugin.addDirectoryItem(handle, plugin_url, li, isFolder=True)
            continue

        # Stream tramite myresolve
        if myresolve:
            tipo, param, lic = parse_myresolve(myresolve)
            is_folder_type = tipo in FOLDER_RESOLVER_TYPES

            li = xbmcgui.ListItem(label=title)
            li.setArt({'thumb': thumb, 'fanart': fanart})
            li.setInfo('video', {'title': title, 'plot': info_str})

            if is_folder_type:
                query = {'action': 'mandra_play', 'tipo': tipo, 'param': param}
                plugin_url = f"{sys.argv[0]}?{urllib.parse.urlencode(query)}"
                xbmcplugin.addDirectoryItem(handle, plugin_url, li, isFolder=True)
            elif param:
                li.setProperty('IsPlayable', 'true')
                query = {'action': 'mandra_play', 'tipo': tipo, 'param': param}
                if lic:
                    query['lic'] = lic
                plugin_url = f"{sys.argv[0]}?{urllib.parse.urlencode(query)}"
                xbmcplugin.addDirectoryItem(handle, plugin_url, li, isFolder=False)
            else:
                li2 = xbmcgui.ListItem(label=f"[{tipo.upper()}] {title}")
                li2.setArt({'thumb': thumb, 'fanart': fanart})
                li2.setInfo('video', {'title': title, 'plot': f"Tipo non supportato: {tipo}"})
                xbmcplugin.addDirectoryItem(handle, '', li2, isFolder=False)
            continue

        # Link diretto
        if link and link != 'ignore' and not link.startswith('acestream://'):
            li = xbmcgui.ListItem(label=title)
            li.setArt({'thumb': thumb, 'fanart': fanart})
            li.setInfo('video', {'title': title, 'plot': info_str})
            li.setProperty('IsPlayable', 'true')
            query      = {'action': 'play', 'url': link, 'license': ''}
            plugin_url = f"{sys.argv[0]}?{urllib.parse.urlencode(query)}"
            xbmcplugin.addDirectoryItem(handle, plugin_url, li, isFolder=False)
            continue

        # AceStream (non supportato)
        if link.startswith('acestream://'):
            li = xbmcgui.ListItem(label=f"[ACE] {title}")
            li.setArt({'thumb': thumb, 'fanart': fanart})
            li.setInfo('video', {'title': title, 'plot': 'AceStream non supportato'})
            xbmcplugin.addDirectoryItem(handle, '', li, isFolder=False)
            continue

        logga(f"Item senza azione riconoscibile: '{title}'")


if __name__ == '__main__':
    run()
