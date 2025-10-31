# Kheiven D'Haiti — crawler
import httpx
from selectolax.parser import HTMLParser


def _main_text(html: str) -> str:
    tree = HTMLParser(html)
    # prefer <article>, else largest texty node heuristic
    art = tree.css_first("article")
    if art:
        return art.text(separator="\n").strip()
    best = ""
    for node in tree.css("p, div"):
        t = node.text(separator=" ").strip()
        if len(t) > len(best):
            best = t
    return best.strip()


def grab(url: str, timeout=20.0) -> str:
    with httpx.Client(
        follow_redirects=True, timeout=timeout, headers={"User-Agent": "sagemtl/0.0.1"}
    ) as c:
        r = c.get(url)
        r.raise_for_status()
        return _main_text(r.text)
