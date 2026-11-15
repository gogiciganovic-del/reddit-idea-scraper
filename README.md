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

**Bez Reddit API ključa.** Reddit je 2026. zatvorio izradu novih
"legacy API" aplikacija za obične korisnike (samo uz odobren
moderacijski use-case), pa ovaj skener umjesto toga koristi Redditove
javne, besplatne JSON feedove (`reddit.com/r/<sub>/new.json`), koji ne
traže prijavu ni ključ. Jedino se GitHub Actions runner (koji ima pun
pristup internetu) koristi za dohvat — ne vrti se lokalno ni u
ograničenom sandboxu.

Sve besplatno: bez API ključa, bez plaćanja, GitHub Actions free-tier
minuti (isti pattern kao `prices-crawl.yml` u `akcija-hr`).

## Postavljanje

Ništa nije potrebno postaviti — nema secrets, nema API ključa. Workflow
se sam pokreće svaki ponedjeljak preko GitHub Actions.

Za ručno pokretanje: repo → Actions → "Tjedni Reddit skener ideja" →
"Run workflow".

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
