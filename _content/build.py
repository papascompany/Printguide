#!/usr/bin/env python3
"""본문 이미지/동영상 URL을 CDN URL로 치환 -> data/ready/*.json + 미리보기 HTML data/preview/."""
import json, re, html as _html
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).parent
POSTS = ROOT / "data" / "posts"
READY = ROOT / "data" / "ready"
PREVIEW = ROOT / "data" / "preview"
READY.mkdir(parents=True, exist_ok=True)
PREVIEW.mkdir(parents=True, exist_ok=True)
blob_map = json.loads((ROOT / "data" / "blob_map.json").read_text())
cats = json.loads((ROOT / "data" / "categories.json").read_text())["mylogCategoryList"]
name_of = {str(c["categoryNo"]): c["categoryName"] for c in cats}

NAVER = re.compile(r"pstatic\.net|naver\.(com|net)")
BRAND = "(주)파파스컴퍼니"
# 글자 사이가 인라인 태그/공백/제로폭문자로 쪼개진 브랜드명 보정 (URL 미손상: 단어 사이 구분 필수)
_SEP = r"(?:</?[^>]{0,60}>|[\s​])"
SPLIT_BRAND = [
    re.compile(rf"쿡{_SEP}*더{_SEP}*디자인"),
    re.compile(rf"cook{_SEP}+the{_SEP}+design", re.IGNORECASE),
]


def fix_split_brand(html: str) -> str:
    for pat in SPLIT_BRAND:
        html = pat.sub(BRAND, html)
    return html
PAGE = """<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title>
<style>body{{max-width:760px;margin:24px auto;padding:0 16px;font-family:-apple-system,Segoe UI,Roboto,sans-serif;line-height:1.7}}
img,video{{max-width:100%;height:auto}}.meta{{color:#888;font-size:14px;margin-bottom:24px}}</style></head><body>
<a href="../../index.html">← 목록</a><h1>{title}</h1>
<div class="meta">{date} · {cat} · <a href="{src}" target="_blank">원본</a></div>{body}</body></html>"""

n = leftover = 0
for f in sorted(POSTS.glob("*.json")):
    d = json.loads(f.read_text())
    naver2cdn = {u: blob_map[loc] for u, loc in d.get("image_local", {}).items() if loc in blob_map}
    soup = BeautifulSoup(d["content_html"], "lxml")
    # naver URL 품은 data-* 속성 제거(inert)
    for el in soup.find_all(True):
        for a in list(el.attrs):
            v = el.attrs[a]
            sv = " ".join(v) if isinstance(v, list) else str(v)
            if a == "data-linkdata" or (NAVER.search(sv) and a not in ("src", "href")):
                del el.attrs[a]
    for img in soup.select("img"):
        for j in ("data-lazy-src", "data-src", "data-linkdata", "srcset"):
            img.attrs.pop(j, None)
        cdn = naver2cdn.get(img.get("src", ""))
        if cdn:
            img["src"] = cdn
            a = img.find_parent("a")
            if a and a.has_attr("href") and NAVER.search(a["href"] or ""):
                a["href"] = cdn
    for el in soup.select("video, source"):
        cdn = naver2cdn.get(el.get("src", ""))
        if cdn:
            el["src"] = cdn
    # CDN 매핑 안 된 네이버 이미지(원본 삭제·404) 는 깨진 아이콘 대신 제거
    for img in soup.select("img"):
        if NAVER.search(img.get("src", "")):
            comp = img.find_parent("div", class_="se-image") or img
            comp.decompose()
    # 본문 속 네이버 하이퍼링크 정리: 링크는 풀고 텍스트만 남김(네이버 의존 제거)
    for a in soup.select("a[href]"):
        if NAVER.search(a.get("href", "")):
            a.unwrap()
    # 평문으로 적힌 네이버 URL 토큰 제거(브랜드 치환으로 변형된 형태 포함)
    BARE = re.compile(r"https?://[^\s<]*(?:naver\.(?:com|net)|pstatic\.net)[^\s<]*")
    for t in list(soup.find_all(string=NAVER)):
        new = BARE.sub("", str(t))
        if new != str(t):
            t.replace_with(new)
    body = soup.body.decode_contents() if soup.body else str(soup)
    body = fix_split_brand(body)
    leftover += len(NAVER.findall(body))

    cat = name_of.get(str(d.get("categoryNo", "")), "")
    rec = {"logNo": d["logNo"], "title": d["title"], "date": d.get("date", ""),
           "addDate": d.get("addDate", ""), "categoryNo": d.get("categoryNo", ""),
           "category": cat, "source_url": d.get("url", ""), "content_html": body}
    (READY / f"{d['logNo']}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2))
    (PREVIEW / f"{d['logNo']}.html").write_text(PAGE.format(
        title=_html.escape(d["title"]), date=d.get("date") or d.get("addDate", ""),
        cat=_html.escape(cat), src=d.get("url", ""), body=body))
    n += 1

print(f"data/ready/ + data/preview/ {n}개 생성. 잔여 네이버 참조 {leftover}")
