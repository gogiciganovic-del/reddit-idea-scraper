"""
Konfiguracija: subreddit liste i ključne riječi/fraze za prepoznavanje
pritužbi, feature-request-ova i "postoji li app koji..." pitanja.

Sve besplatno — koristi se samo Redditov besplatni službeni API (PRAW,
read-only app, bez OAuth login-a korisnika).
"""

# Tri skupine subreddita (sve tri aktivne, po dogovoru)
SUBREDDITS = {
    "hr": [  # hrvatski subovi — najrelevantniji za Cjenko Akcije
        "croatia",
        "zagreb",
        "askcroatia",
    ],
    "ideje": [  # subovi gdje ljudi direktno traže/predlažu app ideje
        "SomebodyMakeThis",
        "Entrepreneur",
        "AppIdeas",
        "startups",
        "SideProject",
    ],
    "shopping_finance": [  # šopinganje / štednja / osobne financije (eng.)
        "frugal",
        "personalfinance",
        "deals",
    ],
}

# Koliko najnovijih postova po subredditu provjeriti svaki tjedan.
# PRAW sam pazi na rate-limit (60 req/min za script app), ovo je sigurno.
POSTS_PER_SUBREDDIT = 300

# Ključne fraze po "kanti" (bucket) — hrvatski + engleski.
# Bucket = vrsta signala koji tražimo.
KEYWORDS = {
    "pritužba": [
        # hrvatski
        "frustrira me", "mrzim kad", "nervira me", "ljuti me",
        "najveći problem", "grozno je", "katastrofa je",
        "dokle više", "živcira me",
        # engleski
        "so annoying when", "i hate when", "drives me crazy",
        "biggest problem with", "frustrated with", "sick of",
    ],
    "feature_request": [
        "trebao bih app", "treba nam app", "kad bi samo postojala",
        "zašto ne postoji", "falio bi mi app",
        "wish there was an app", "someone should build",
        "why isn't there an app", "need an app that",
        "someone should make a",
    ],
    "traži_app": [
        "postoji li app", "znate li aplikaciju", "ima li neka app",
        "preporuka za app",
        "does anyone know an app", "is there an app that",
        "looking for an app", "any app that",
    ],
}

# Ako naslov/tekst sadrži i jednu od ovih riječi, obilježi kao
# potencijalno relevantno za Cjenko Akcije (cijene/kupovina/akcije).
CJENKO_RELEVANT_HINTS = [
    "cijena", "cijene", "cjenik", "trgovin", "kupovin", "akcij",
    "popust", "shopping", "price", "grocery", "supermarket",
    "discount", "deal", "lidl", "konzum", "kaufland", "spar", "dm ",
]
