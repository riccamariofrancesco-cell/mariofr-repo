<div align="center">

# 📺 MarioFR Stream
### Il tuo addon Kodi per lo streaming italiano

![Version](https://img.shields.io/badge/version-1.0.41--stable-brightgreen?style=for-the-badge)
![Kodi](https://img.shields.io/badge/Kodi-19%2B-1f90d1?style=for-the-badge&logo=kodi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.x-3776ab?style=for-the-badge&logo=python&logoColor=white)
![License](https://img.shields.io/badge/license-Personal%20Use-green?style=for-the-badge)

[📥 Download](#-installazione) · [🌐 Sito Web](https://mariofr.com/kodi) · [📋 Changelog](#-changelog)

</div>

---

## ✨ Cosa include

| Sezione | Descrizione |
|--------|-------------|
| 📋 **EPG** | Guida TV con ricerca intelligente su tutti i canali — trova il canale giusto in un click |
| 📡 **DVB-T2 (zappr)** | Canali del digitale terrestre italiano via zappr.stream |
| 🌐 **Playlist** | Canali organizzati per categoria: Sport, Cinema, News, Intrattenimento e altro |
| 🔵 **Sky Italia** | Resolver integrato con decrittazione XOR e controllo scadenza link automatico |
| 🟣 **EUROTV** | Supporto completo per il gruppo vavoo.to / kool.to / oha.to / huhu.to con selezione del provider al volo |
| 📺 **MandraKodi** | Collegamento diretto all'addon MandraKodi ufficiale |

---

## 🚀 Installazione

> **Prerequisiti:** Kodi 19 (Matrix) o superiore

### 1 — Abilita le sorgenti sconosciute

`Impostazioni` → `Sistema` → `Componenti aggiuntivi` → attiva **Sorgenti sconosciute**

### 2 — Installa i plugin InputStream

Dal repository ufficiale Kodi assicurati di avere installati e **attivati**:

- ✅ `InputStream Adaptive`
- ✅ `InputStream FFmpegDirect`

### 3 — Scarica il repository

Vai su [`zips/repository.mariofr/`](zips/repository.mariofr/) e scarica:

```
repository.mariofr.zip
```

### 4 — Installa tramite zip

`Componenti aggiuntivi` → `Installa da file zip` → seleziona il file scaricato

### 5 — Installa l'addon dal repository

`Componenti aggiuntivi` → `Installa da repository` → **MarioFR Repository** → installa:

- 📦 `MarioFR Stream` (addon video)
- ⚙️ `MarioFR Autoexecute Service`

### 6 — Abilita gli aggiornamenti automatici

Su **entrambi** i componenti abilitare l'opzione **Aggiornamento automatico** per ricevere sempre l'ultima versione senza reinstallare manualmente.

---

## 🎮 Come funziona il player

Quando apri un canale HLS (.m3u8), l'addon ti mostra un popup per scegliere il metodo di riproduzione:

```
┌─────────────────────────────────┐
│      Scegli player              │
│  ▶ FFMPEG Direct (consigliato)  │
│  ▶ InputStream Adaptive         │
└─────────────────────────────────┘
```

Per i canali **EUROTV** (vavoo e affini) puoi scegliere il provider:

```
┌────────────────────────────────┐
│  EUROTV - Scegli provider      │
│  • vavoo.to                    │
│  • kool.to                     │
│  • oha.to                      │
│  • huhu.to                     │
└────────────────────────────────┘
```

---

## 📋 Changelog

### v1.0.41-stable *(2026-09-07)*
- 🔄 Resolver **EUROTV/vavoo** aggiornato a MandraKodi v1.2.252: device type desktop/electron, app version `1.3.1`, nuovo User-Agent `electron-fetch`, fallback TS via `lokke.app`
- 🔄 Resolver **Sky Italia**: aggiunto controllo scadenza automatico tramite campo `fine` — avviso notifica se il link è scaduto
- 🔄 **DVB-T2 zappr**: fix gestione `licensedetails` come oggetto dict `{kid: key}` (allineato a MandraKodi v1.2.252)

### v1.0.40-bigrelease-beta
- 🆕 Dialog interattivo per la scelta del player (FFMPEG Direct / InputStream Adaptive)
- 🆕 Gruppo **EUROTV**: supporto per kool.to, oha.to, huhu.to oltre a vavoo.to
- 🆕 Resolver **Sky Italia** con decrittazione XOR integrata
- 🆕 **EPG** con ricerca fuzzy multi-livello (trova "SPORT 24 EXTRA VAVOO 6" cercando "Sky Sport 24")
- 🆕 **DVB-T2 (zappr)**: digitale terrestre italiano completo
- ♻️ Rimosso tutto il codice legacy MandraKodi (~800 righe) — MandraKodi ora si apre come addon esterno
- ♻️ `setInfo()` sostituito con `InfoTagVideo` (API Kodi moderna)
- 🐛 Fix rilevamento URL Sky con doppio encoding Kodi (`sky%40@`)
- 🐛 Fix `xbmc.Player().play()` — firma corretta con path + listitem

---

## ⚙️ Requisiti tecnici

```
Kodi                   19 (Matrix) o superiore
Python                 3.x (incluso in Kodi 19+)
InputStream Adaptive   ✅ richiesto
InputStream FFmpegDirect ✅ richiesto
```

---

## ⚖️ Disclaimer

> MarioFR Stream **non ospita, archivia o distribuisce** alcun contenuto multimediale sui propri server.
> Funziona esclusivamente come strumento di ricerca e indicizzazione che aggrega informazioni
> pubblicamente disponibili da servizi di terze parti.
>
> Gli utenti sono responsabili di verificare di avere il diritto di accedere ai contenuti
> attraverso le proprie reti locali. Non siamo responsabili dell'utilizzo che gli utenti
> fanno dei contenuti individuati.

---

<div align="center">

Fatto con ❤️ da **MarioFR** · [mariofr.com/kodi](https://mariofr.com/kodi)

</div>
