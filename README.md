# reddit-idea-scraper

Besplatni tjedni skener Reddita (v2) koji traži:
- **pritužbe** ("mrzim kad...", "frustrira me...", plus puno neformalnih varijanti)
- **feature-request-ove** ("trebao bih app koji...", "zašto ne postoji...")
- **direktna pitanja za app** ("postoji li app koji...")

Skenira i **postove** (najnovije + top tjedna, da ne promaši popularne
teme) i **komentare** (tu se krije najviše pravih pritužbi), rangira sve
po `composite_score` (glasovi + komentari + broj poklopljenih fraza), i
prati koje se fraze **ponavljaju kroz više tjedana** — to je jači signal
prave poslovne prilike nego jednokratan spomen.

u tri skupine subreddita:
- hrvatski (`r/croatia`, `r/zagreb`, `r/askcroatia`)
- poslovne-ideje subovi (`r/SomebodyMakeThis`, `r/Entrepreneur`, `r/AppIdeas`, `r/startups`, `r/SideProject`)
- shopping/financije (`r/frugal`, `r/personalfinance`, `r/deals`)

Svaki pogodak je obilježen i s `cjenko_relevant` stupcem (da/ne) — grubi
heuristički signal spominje li post cijene/kupovinu/trgovine, dakle je
li to nešto što bi Cjenko Akcije mogao pokriti, ili je to prilika za
potpuno novu app.

**Status: automatski Python scraper NE RADI.** Isprobano je:
1. Redditov službeni API preko PRAW-a — Reddit je 2026. zatvorio izradu
   novih "legacy API" aplikacija za obične korisnike (samo uz odobren
   moderacijski use-case); registracija nove app tiho ne uspijeva.
2. Javni, besplatni JSON feed (`reddit.com/r/<sub>/new.json`) bez
   ključa — Reddit vraća HTTP 403 "Blocked" na sve zahtjeve s GitHub
   Actions / cloud IP adresa (anti-bot zaštita na razini infrastrukture,
   ne nešto što user-agent ili delay mogu zaobići).

Oba pokušaja su ostala u repou (`scraper/`) kao referenca, i
`workflow_dispatch` i dalje radi za ručno eksperimentiranje, ali
**tjedni cron je isključen** jer bi uvijek vraćao 0 pogodaka.

**Kako tjedno istraživanje stvarno radi sada:** Claude (u zasebnoj
scheduled-task sesiji, izvan ovog repoa) svaki ponedjeljak sam
pretražuje web (WebSearch) za relevantne Reddit rasprave — to ne
izgleda kao bot pa nije blokirano — i šalje sažetak izravno u chat.
Nalazi se po mogućnosti commitaju natrag u `data/history.csv` ovog
repoa radi praćenja kroz vrijeme, preko GitHub API-ja.

## Postavljanje

Ništa nije potrebno postaviti na ovoj strani — nema secrets, nema API
ključa. Tjedni posao se odvija automatski kroz Claudeov scheduled task,
ne kroz GitHub Actions cron (vidi gore).

## Izlaz

- `data/latest.csv` — svi pogoci iz zadnjeg pokretanja (sirova tablica)
- `data/history.csv` — kumulativna povijest, dedupliciano po post ID-u
- `data/summary.md` — sažetak na vrhu: top pogoci po kategoriji, koliko
  je Cjenko-relevantno, najčešće riječi u naslovima (grubi signal tema)

## Prilagodba

Sve ključne riječi, subreddit liste i broj postova po subredditu su u
`scraper/config.py` — slobodno dodaj/oduzmi subreddite ili fraze.

## Napomena o ograničenjima javnog feeda

Javni `.json` feed vraća samo najnovije postove (ne pretražuje cijelu
povijest subreddita), i Reddit ga povremeno rate-limitira ako se zove
prečesto — skripta to sama čeka i nastavlja. Za tjedni ritam i
`POSTS_PER_SUBREDDIT = 300` ovo je više nego dovoljno da se ne
propuste novi postovi između dva pokretanja.
