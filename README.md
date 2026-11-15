# reddit-idea-scraper

Besplatni tjedni skener Reddita koji traži:
- **pritužbe** ("mrzim kad...", "frustrira me...")
- **feature-request-ove** ("trebao bih app koji...", "zašto ne postoji...")
- **direktna pitanja za app** ("postoji li app koji...")

u tri skupine subreddita:
- hrvatski (`r/croatia`, `r/zagreb`, `r/askcroatia`)
- poslovne-ideje subovi (`r/SomebodyMakeThis`, `r/Entrepreneur`, `r/AppIdeas`, `r/startups`, `r/SideProject`)
- shopping/financije (`r/frugal`, `r/personalfinance`, `r/deals`)

Svaki pogodak je obilježen i s `cjenko_relevant` stupcem (da/ne) — grubi
heuristički signal spominje li post cijene/kupovinu/trgovine, dakle je
li to nešto što bi Cjenko Akcije mogao pokriti, ili je to prilika za
potpuno novu app.

Sve besplatno: Redditov službeni read-only API (preko `praw`) + GitHub
Actions (besplatni free-tier minuti, isti pattern kao `prices-crawl.yml`
u `akcija-hr`).

## Postavljanje (jednom, ~5 min)

1. **Redditov API ključ (besplatno, bez kartice):**
   - Idi na https://www.reddit.com/prefs/apps dok si ulogiran na svom Reddit računu.
   - Klikni "create another app..." (dolje).
   - Tip: **script**
   - Name: npr. `cjenko-idea-scanner`
   - redirect uri: `http://localhost:8080` (mora biti upisano nešto, nije bitno što)
   - Klikni "create app".
   - Dobiješ dva podatka:
     - `client_id` — niz slova/brojeva ispod naziva app-a (ispod "personal use script")
     - `client_secret` — piše "secret"

2. **Dodaj ih kao GitHub Secrets u ovaj repo:**
   - Repo → Settings → Secrets and variables → Actions → "New repository secret"
   - `REDDIT_CLIENT_ID` = client_id s koraka 1
   - `REDDIT_CLIENT_SECRET` = secret s koraka 1

3. **Gotovo.** Workflow se sam pokreće svaki ponedjeljak. Za ručno
   pokretanje: repo → Actions → "Tjedni Reddit skener ideja" → "Run workflow".

## Izlaz

- `data/latest.csv` — svi pogoci iz zadnjeg pokretanja (sirova tablica)
- `data/history.csv` — kumulativna povijest, dedupliciano po post ID-u
- `data/summary.md` — sažetak na vrhu: top pogoci po kategoriji, koliko
  je Cjenko-relevantno, najčešće riječi u naslovima (grubi signal tema)

## Prilagodba

Sve ključne riječi, subreddit liste i broj postova po subredditu su u
`scraper/config.py` — slobodno dodaj/oduzmi subreddite ili fraze.
