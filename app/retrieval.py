"""Email search: the naive baseline and the BM25 ranker the agent actually uses.

naive_search  - the first version: any query word that appears as a substring anywhere, results in inbox order.
bm25_search   - tokenise, drop stop words, light plural stemming, rank with BM25 (subject counts double).
"""
import math
import re
from collections import Counter

TOP_K = 5

STOPWORDS = frozenset("""
a an the and or of to in on at for from with by about as is are was were be been am do does did doing
i me my mine we our you your he she it its they them their this that these those there here
what when where which who whom why how any some all can could would should will shall may might must
have has had not no yes if then than so up down out over under again very just also please
tell show find give get got see look need want know
""".split())

_TOKEN = re.compile(r"[a-z0-9]+|[\u0e00-\u0e7f]+")


def _stem(token: str) -> str:
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def tokenize(text: str, use_stopwords: bool = True) -> list[str]:
    tokens = _TOKEN.findall(text.lower())
    if use_stopwords:
        tokens = [t for t in tokens if t not in STOPWORDS]
    return [_stem(t) for t in tokens]


def naive_search(emails: list[dict], query: str) -> list[str]:
    terms = [t for t in query.lower().split() if t]
    return [
        e["id"] for e in emails
        if any(t in f"{e['from']} {e['subject']} {e['body']}".lower() for t in terms)
    ]


def bm25_search(emails: list[dict], query: str, k: int | None = TOP_K,
                use_stopwords: bool = True, k1: float = 1.5, b: float = 0.75) -> list[str]:
    docs = []
    for e in emails:
        tokens = (tokenize(e["from"], use_stopwords)
                  + 2 * tokenize(e["subject"], use_stopwords)  # subject counts double
                  + tokenize(e["body"], use_stopwords))
        docs.append((e["id"], Counter(tokens), len(tokens)))
    n = len(docs)
    avgdl = (sum(length for _, _, length in docs) / n) if n else 0.0
    query_terms = set(tokenize(query, use_stopwords))
    df = {t: sum(1 for _, tf, _ in docs if t in tf) for t in query_terms}

    scored = []
    for position, (email_id, tf, length) in enumerate(docs):
        score = 0.0
        for t in query_terms:
            if t not in tf:
                continue
            idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
            score += idf * tf[t] * (k1 + 1) / (tf[t] + k1 * (1 - b + b * length / avgdl))
        if score > 0:
            scored.append((-score, position, email_id))
    scored.sort()
    ids = [email_id for _, _, email_id in scored]
    return ids if k is None else ids[:k]
