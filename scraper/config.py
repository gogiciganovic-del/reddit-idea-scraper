"""
Konfiguracija: subreddit liste i ključne riječi/fraze za prepoznavanje
pritužbi, feature-request-ova i "postoji li app koji..." pitanja.

Sve besplatno — koristi se samo Redditov javni, besplatni JSON feed
(bez API ključa, bez prijave).
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

# Koliko najnovijih postova/komentara po subredditu provjeriti svaki tjedan.
POSTS_PER_SUBREDDIT = 300
COMMENTS_PER_SUBREDDIT = 300
TOP_WEEK_PER_SUBREDDIT = 100  # dodatno: najpopularniji postovi tjedna

# Ključne fraze po "kanti" (bucket) — hrvatski + engleski.
# Namjerno širok popis (formalno + neformalno) da se ne promaši signal.
KEYWORDS = {
    "pritužba": [
        # hrvatski — formalno
        "frustrira me", "nervira me", "ljuti me", "najveći problem",
        "grozno je", "katastrofa je", "dokle više", "živcira me",
        "muka mi je od", "dosta mi je", "umara me",
        # hrvatski — neformalno/razgovorno
        "mrzim kad", "ide mi na živce", "iritira me", "ne podnosim kad",
        "izluđuje me", "kad me nešto", "najgore mi je kad",
        "fakat me nervira", "stvarno me nervira",
        # engleski
        "so annoying when", "i hate when", "drives me crazy",
        "biggest problem with", "frustrated with", "sick of",
        "really bugs me", "drives me nuts", "fed up with",
        "tired of dealing with", "such a pain", "such a hassle",
        "is so frustrating", "can't stand when", "annoys me",
    ],
    "feature_request": [
        "trebao bih app", "treba nam app", "kad bi samo postojala",
        "zašto ne postoji", "falio bi mi app", "fali mi aplikacija",
        "nedostaje mi app", "bilo bi super da postoji",
        "da bar postoji", "zašto nitko nije napravio",
        "wish there was an app", "someone should build",
        "why isn't there an app", "need an app that",
        "someone should make a", "i wish someone would make",
        "there should be an app for", "someone needs to build",
        "would be great if there was an app",
    ],
    "traži_app": [
        "postoji li app", "znate li aplikaciju", "ima li neka app",
        "preporuka za app", "zna li netko aplikaciju",
        "does anyone know an app", "is there an app that",
        "looking for an app", "any app that",
        "can't believe there's no app", "why does no app",
        "no app does this", "is there any app",
    ],
}

# Ako naslov/tekst sadrži i jednu od ovih riječi, obilježi kao
# potencijalno relevantno za Cjenko Akcije (cijene/kupovina/akcije).
CJENKO_RELEVANT_HINTS = [
    "cijena", "cijene", "cjenik", "trgovin", "kupovin", "akcij",
    "popust", "shopping", "price", "grocery", "supermarket",
    "discount", "deal", "lidl", "konzum", "kaufland", "spar", "dm ",
]

# Fraza se smatra "ponavljajućom temom" ako se pojavi u ovoliko ili
# više različitih tjedana kroz povijest — to je jači signal prave
# poslovne prilike nego jednokratan spomen.
RECURRING_MIN_WEEKS = 2
