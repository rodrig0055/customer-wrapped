"""Classification rules: who counts as a consumer, what counts as a funeral or otherwise
sensitive order, which addresses are unmailable, and how a greeting name is cleaned.

compute.py imports everything from here, so the send list and the card engine can never disagree.
These rules were validated against a real table of 1.3 million orders; the comments keep the
numbers that justified each one.
"""
import os
import re

# Below this lifetime spend no money figure is shown anywhere: "$3 spent making people feel loved"
# is worse than showing nothing.
SPEND_FLOOR = float(os.environ.get("SPEND_FLOOR", 20))

# Your own domains: staff and corporate-order mailboxes are not customers.
OWN_DOMAINS = {d.strip().lower() for d in os.environ.get("OWN_DOMAINS", "acmeflorals.example").split(",") if d.strip()}
# Extra domains to treat as personal mailboxes (the demo's customers are all @example.com).
EXTRA_CONSUMER_DOMAINS = {d.strip().lower() for d in os.environ.get("EXTRA_CONSUMER_DOMAINS", "example.com").split(",") if d.strip()}

# --------------------------------------------------------------------------
# CONSUMER vs BUSINESS.
# The old rule was "any domain not in a 27-entry free-mail list is a business".
# That discarded ~5,600 obvious individuals: students, government staff, and
# anyone on regional or ISP webmail.
# --------------------------------------------------------------------------
FREE_MAIL = {
 'gmail.com','googlemail.com','yahoo.com','yahoo.co.uk','ymail.com','rocketmail.com',
 'hotmail.com','hotmail.co.uk','outlook.com','live.com','msn.com',
 'icloud.com','me.com','mac.com','aol.com','protonmail.com','proton.me','gmx.com','gmx.net','mail.com',
 'yandex.com','zoho.com','sbcglobal.net'}

# Regional webmail, ISP mailboxes and privacy providers: all individuals.
CONSUMER_WEBMAIL = {
 'yahoo.ca','yahoo.com.au','yahoo.com.sg','yahoo.co.jp','yahoo.com.hk','yahoo.co.nz','yahoo.co.in',
 'yahoo.com.tw','yahoo.it','yahoo.de','yahoo.fr','yahoo.es','yahoo.com.mx','yahoo.com.br','yahoo.gr',
 'yahoo.dk','yahoo.se','yahoo.no','yahoo.ie','yahoo.com.vn','yahoo.co.id','myyahoo.com','yahoo.com.kw',
 'naver.com','daum.net','hanmail.net','qq.com','163.com','126.com','sina.com','sina.cn','foxmail.com',
 'gmx.de','gmx.at','gmx.ch','gmx.us','gmx.co.uk','web.de','t-online.de','freenet.de','arcor.de','bluewin.ch',
 'orange.fr','wanadoo.fr','free.fr','laposte.net','sfr.fr','libero.it','virgilio.it','alice.it','tiscali.it',
 'hotmail.fr','hotmail.de','hotmail.it','hotmail.es','hotmail.ca','hotmail.com.au','hotmail.co.jp',
 'hotmail.sg','hotmail.co.th','hotmail.com.br','live.com.au','live.co.uk','live.ca','live.nl','live.de',
 'live.se','live.jp','live.hk','live.com.sg','live.com.pt','outlook.co.id','outlook.es','outlook.fr',
 'outlook.de','outlook.it','outlook.jp','outlook.sa','outlook.com.au','outlook.pt','outlook.dk','outlook.my',
 'outlook.in','outlook.sg','outlook.com.vn','outlook.co.nz','outlook.kr','aol.co.uk','aol.de','aol.fr',
 'comcast.net','verizon.net','att.net','bellsouth.net','cox.net','charter.net','earthlink.net','juno.com',
 'optonline.net','roadrunner.com','rr.com','shaw.ca','sympatico.ca','rogers.com','telus.net','videotron.ca',
 'btinternet.com','sky.com','virginmedia.com','talktalk.net','ntlworld.com','blueyonder.co.uk','bigpond.com',
 'bigpond.net.au','optusnet.com.au','iinet.net.au','tpg.com.au','xtra.co.nz','mail.ru','rambler.ru','bk.ru',
 'inbox.ru','list.ru','ukr.net','seznam.cz','wp.pl','onet.pl','o2.pl','interia.pl','abv.bg','mynet.com',
 'uol.com.br','bol.com.br','terra.com.br','singnet.com.sg','pacific.net.sg','starhub.net.sg','duck.com','duckduckgo.com',
 'fastmail.com','fastmail.fm','hushmail.com','tutanota.com','tuta.io','pm.me','protonmail.ch','mailfence.com',
 'zohomail.com','hey.com','posteo.de','mailbox.org','aim.com','rediffmail.com','indiatimes.com','lycos.com',
 'excite.com','netzero.net','frontier.com','windstream.net','centurylink.net','email.com','asia.com',
 'europe.com','iname.com','dr.com','engineer.com','doctor.com','mail.co.uk'}

EDU_RE = re.compile(r'(\.edu(\.[a-z]{2})?$|\.ac\.[a-z]{2}$|\.k12\.|student|alumni)')
GOV_RE = re.compile(r'(\.gov(\.[a-z]{2})?$|\.mil$)')

def domain(email):
    return email.split('@', 1)[1].lower().strip() if '@' in email else ''

def is_consumer(email):
    """True when this address belongs to a person we can send a personal recap to."""
    e = email.lower().strip()
    d = domain(e)
    if d in OWN_DOMAINS:                            # own staff + corporate-orders@
        return False
    if d in FREE_MAIL or d in CONSUMER_WEBMAIL or d in EXTRA_CONSUMER_DOMAINS:
        return True
    if EDU_RE.search(d) or GOV_RE.search(d):        # students, teachers, civil servants
        return True
    return False

# --------------------------------------------------------------------------
# UNMAILABLE ADDRESSES.
# --------------------------------------------------------------------------
SYNTAX_RE = re.compile(r"^[A-Za-z0-9!#$%&'*+/=?^_`{|}~.-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
ROLE_RE = re.compile(
 r'^(info|sales|admin|support|contact|noreply|no-reply|donotreply|postmaster|webmaster|abuse|marketing|'
 r'hr|careers|jobs|billing|accounts?|accounting|finance|orders?|inquiry|enquiry|help|team|office|reception|'
 r'purchasing|procurement)([._-]|$)', re.I)
DISPOSABLE = {
 'mailinator.com','yopmail.com','guerrillamail.com','10minutemail.com','tempmail.com','trashmail.com',
 'sharklasers.com','getnada.com','maildrop.cc','throwawaymail.com','temp-mail.org','dispostable.com',
 'fakeinbox.com','mytemp.email','emailondeck.com','tempr.email','moakt.com','mohmal.com'}

# Typos of the big providers are syntactically valid, so nothing else catches them.
# On one real list, gmail.con alone accounted for 2,063 addresses.
_TYPO_TARGETS = ['gmail.com','yahoo.com','hotmail.com','outlook.com','icloud.com',
                 'ymail.com','aol.com','live.com','protonmail.com']
_typo_cache = {}
def _levenshtein(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]

def is_typo_domain(d):
    """Misspelled free-mail domain, e.g. gmail.con / gmai.com / yahoo.con."""
    if d in _typo_cache:
        return _typo_cache[d]
    out = False
    if d not in FREE_MAIL and d not in CONSUMER_WEBMAIL and d not in EXTRA_CONSUMER_DOMAINS:
        for target in _TYPO_TARGETS:
            dist = _levenshtein(d, target)
            if dist == 0:
                out = False
                break
            if dist <= (1 if len(target) <= 10 else 2) and d[:1] == target[:1]:
                out = True
                break
    _typo_cache[d] = out
    return out

_correct_cache = {}
def correct_domain(d):
    """Best-guess correction for a misspelled free-mail domain, or None.

    Only corrects when the answer is UNAMBIGUOUS: exactly one candidate sits at the
    minimum edit distance, that distance is small relative to the domain length, and
    the first character matches. Anything with a tie is left alone rather than guessed,
    because a wrong correction mails a stranger instead of simply bouncing.
    """
    if d in _correct_cache:
        return _correct_cache[d]
    out = None
    if d not in FREE_MAIL and d not in CONSUMER_WEBMAIL:
        scored = []
        for target in _TYPO_TARGETS:
            dist = _levenshtein(d, target)
            limit = 1 if len(target) <= 8 else 2
            if 0 < dist <= limit and d[:1] == target[:1]:
                scored.append((dist, target))
        if scored:
            best = min(s[0] for s in scored)
            winners = [t for dist, t in scored if dist == best]
            if len(winners) == 1:
                out = winners[0]
    _correct_cache[d] = out
    return out

def is_scrubbed(email, user_id=None):
    """Anonymization artifact from a deleted account: the local part is just digits,
    and for 84 of them it is literally the account's own user_id."""
    local = email.split('@', 1)[0]
    if local.isdigit():
        return True
    return bool(user_id) and local == str(user_id).strip()

def mailability(email, user_id=None):
    """Return None when the address is fine, else a short reason string."""
    e = (email or '').strip()
    le = e.lower()
    if not SYNTAX_RE.match(e) or ' ' in e or le.count('@') != 1 or '..' in le:
        return 'invalid_syntax'
    d = domain(le)
    if d in DISPOSABLE:
        return 'disposable'
    if is_typo_domain(d):
        return 'typo_domain'
    if is_scrubbed(le, user_id):
        return 'scrubbed_account'
    if ROLE_RE.match(le.split('@', 1)[0]):
        return 'role_address'
    return None

# --------------------------------------------------------------------------
# FUNERAL AND SYMPATHY.  Policy: excluded from every stat and from the campaign.
# The old product pattern caught 2,066 orders and missed 5,939, because the
# catalogue names sympathy products euphemistically ("In Loving Memory",
# "Beautiful Farewell", "Memorial Meadows"). It also mis-flagged Christmas wreaths.
# --------------------------------------------------------------------------
FUNERAL_PRODUCT_RE = re.compile(
 r'wreath|funeral|sympath|condol|bereav|libing|inurn|farewell|memorial|tribute|'
 r'rest in peace|in loving memory|eternal peace|eternal rest|peaceful journey|'
 r'standing spray|requiem|last respect')
# Guard: seasonal and novelty products that legitimately contain "wreath" or "memorial".
NOT_FUNERAL_RE = re.compile(r'christmas|yuletide|holiday|advent|noel|santa|pet memorial|topper|cake|glasses|party')

FUNERAL_MSG_RE = re.compile(
 r'condolence|condole|rest in peace|deepest sympath|heartfelt sympath|with sympathy|our sympath|'
 r'sorry for your loss|in loving memory|eternal rest|eternal repose|forever in our hearts|'
 r'until we meet again|gone too soon')

def is_funeral_product(name):
    n = (name or '').lower()
    return bool(FUNERAL_PRODUCT_RE.search(n)) and not NOT_FUNERAL_RE.search(n)

def is_funeral_message(msg):
    return bool(FUNERAL_MSG_RE.search((msg or '').lower()))

# --------------------------------------------------------------------------
# OTHER SENSITIVE OCCASIONS.  Funeral was the only case the policy covered, but
# the same reasoning applies to these. Small volumes, disproportionate harm.
# Illness and get-well are deliberately NOT here: existing policy keeps them
# as generic gifting.
# --------------------------------------------------------------------------
SENSITIVE_MSG_RE = re.compile(
 r'miscarriage|still ?born|lost the baby|angel baby|rainbow bridge|'
 r'divorce|annulment|break ?up|broke up with|goodbye forever')

def is_sensitive_message(msg):
    return bool(SENSITIVE_MSG_RE.search((msg or '').lower()))

# --------------------------------------------------------------------------
# GREETING NAME.  A billing first name is usually populated but is not usable
# raw. On one real table: 15,014 are ALL CAPS, 15,852 all lowercase, 110,813 hold two or
# more words, 142 are placeholders, and 20 contain an email or an IG handle.
# --------------------------------------------------------------------------
PLACEHOLDER_NAMES = {
 'test','qa','na','n/a','none','asd','asdf','x','xx','xxx','abc','sample','dummy','user','customer',
 'guest','unknown','fname','firstname','me','myself','...','-','.','delete','dontuse',
 # function words that turn up as a first token and read absurdly after "Hi"
 'the','your','my','and','for','to','from','of','a','an'}
# Honorifics: skip past them to the real name ("Dr. Maria Santos" -> "Maria"),
# rather than greeting somebody as "Hi Dr,".
NAME_PARTICLES = {'mc','mac','de','del','dela','delos','della','di','da','la','le','san','santa','sta','st'}
HONORIFICS = {'mr','mrs','ms','miss','sir','maam',"ma'am",'madam','dr','doc','engr','atty','prof',
              'rev','fr','sr','br','hon','capt','col','gen','ptr','arch','arc'}

def clean_first_name(raw):
    """Return a greeting-safe first name, or '' when there is nothing usable.

    Callers should fall back to a name-free greeting on ''.
    """
    s = (raw or '').strip()
    if not s:
        return ''
    if '@' in s or 'instagram' in s.lower() or 'http' in s.lower():
        return ''
    s = re.split(r'[,&/(]| and ', s)[0].strip()          # "Mama, Sophia & Mykey" -> "Mama"
    if not s:
        return ''
    # Walk past honorifics to the first token that is an actual name.
    token = ''
    for cand in s.split():
        if re.search(r'\d', cand):       # 'b1g5', 'c4rrrrr': a handle, not a name
            return ''
        cand = re.sub(r"[^A-Za-zÀ-ɏ'\-]", '', cand)
        if not cand:
            continue
        if cand.lower().rstrip('.') in HONORIFICS:
            continue
        token = cand
        break
    if len(token) < 2:
        return ''
    if token.lower() in PLACEHOLDER_NAMES:
        return ''
    # "Mc Arthur" / "Dela Cruz" split across tokens: greeting just "Hi Mc," reads broken,
    # so re-attach the next token. A bare particle with nothing after it stays as-is
    # (Van and Mac are genuine nicknames).
    if token.lower() in NAME_PARTICLES:
        rest = s.split()
        try:
            i = next(idx for idx, t in enumerate(rest) if re.sub(r"[^A-Za-zÀ-ɏ'\-]", '', t).lower() == token.lower())
            nxt = re.sub(r"[^A-Za-zÀ-ɏ'\-]", '', rest[i + 1]) if i + 1 < len(rest) else ''
        except StopIteration:
            nxt = ''
        if nxt and not re.search(r'\d', nxt) and nxt.lower() not in PLACEHOLDER_NAMES:
            # title-case both halves here and return: the shared title-casing below
            # would lowercase the attached word ("Mc arthur")
            return (token[0].upper() + token[1:].lower() + ' '
                    + nxt[0].upper() + nxt[1:].lower())
    # Title-case, but keep genuinely mixed-case names like McKenzie or O'Brien sane.
    out = token[0].upper() + token[1:].lower()
    for sep in ("'", "-"):
        if sep in out:
            out = sep.join(p[:1].upper() + p[1:] for p in out.split(sep))
    if out.lower().startswith('mc') and len(out) > 2:
        out = 'Mc' + out[2:3].upper() + out[3:]
    return out

