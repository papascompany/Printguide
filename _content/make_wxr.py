#!/usr/bin/env python3
"""
data/ready/*.json -> 워드프레스 가져오기(WXR, eXtended RSS) XML 생성.

사용:
  .venv/bin/python make_wxr.py                       # 발행(publish), CDN 이미지 URL 유지
  .venv/bin/python make_wxr.py --draft               # 초안으로
  .venv/bin/python make_wxr.py --image-base https://media.example.com/print
       # 본문 이미지의 jsDelivr 베이스를 다른 호스트로 치환(WP 미디어/R2 등으로 옮길 때)

출력: cookthedesign.wordpress.xml  (워드프레스 도구 > 가져오기 > WordPress 로 업로드)

카테고리 계층(대분류>하위)을 그대로 정의하고, 각 글을 원래 카테고리에 배치.
원본 발행일(KST) 보존. 이미지가 외부 URL이므로, 가져오기 후 'Auto Upload Images' 등
플러그인으로 워드프레스 미디어로 내재화하면 GitHub 레포를 비공개로 돌려도 됩니다.
"""
import json, glob, sys, re
from pathlib import Path
from datetime import datetime, timedelta

ROOT = Path(__file__).parent
cats = json.loads((ROOT / "data" / "categories.json").read_text())["mylogCategoryList"]
SITE_TITLE = "(주)파파스컴퍼니 인쇄/디자인"
SITE_LINK = "https://example.com"          # 새 워드프레스 주소로 바꿔도 됨(가져오기엔 영향 없음)
AUTHOR = "admin"
DEFAULT_DATE = "2026-06-16"                # 상대표기('6시간 전') 글 보정용

args = sys.argv[1:]
status = "draft" if "--draft" in args else "publish"
image_base = None
if "--image-base" in args:
    image_base = args[args.index("--image-base") + 1].rstrip("/")

CDN_PREFIX = re.compile(r"https://cdn\.jsdelivr\.net/gh/papascompany/Printguide@[0-9a-f]+")


def cdata(s: str) -> str:
    return "<![CDATA[" + (s or "").replace("]]>", "]]]]><![CDATA[>") + "]]>"


def slug(no) -> str:
    return f"cat-{no}"


def rfc822(d: str) -> str:
    dt = datetime.strptime(d, "%Y-%m-%d")
    return dt.strftime("%a, %d %b %Y 09:00:00 +0900")


# 카테고리 정의(구분선 제외)
cat_defs = []
name_of = {}
for c in cats:
    if c["categoryName"] == "구분선":
        continue
    no = c["categoryNo"]; name_of[str(no)] = c["categoryName"]
    parent = c["parentCategoryNo"]
    cat_defs.append(
        f"\t<wp:category>\n"
        f"\t\t<wp:term_id>{no}</wp:term_id>\n"
        f"\t\t<wp:category_nicename>{slug(no)}</wp:category_nicename>\n"
        f"\t\t<wp:category_parent>{slug(parent) if parent else ''}</wp:category_parent>\n"
        f"\t\t<wp:cat_name>{cdata(c['categoryName'])}</wp:cat_name>\n"
        f"\t</wp:category>")

items = []
posts = [json.loads(Path(f).read_text()) for f in glob.glob(str(ROOT / "data/ready/*.json"))]
posts.sort(key=lambda p: p.get("date") or DEFAULT_DATE)
for i, p in enumerate(posts, 1):
    date = p.get("date") or DEFAULT_DATE
    html = p["content_html"]
    if image_base:
        html = CDN_PREFIX.sub(image_base, html)
    gmt = (datetime.strptime(date, "%Y-%m-%d") - timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")
    catno = str(p.get("categoryNo", ""))
    catname = name_of.get(catno, p.get("category", ""))
    items.append(
        "\t<item>\n"
        f"\t\t<title>{cdata(p['title'])}</title>\n"
        f"\t\t<link>{SITE_LINK}/?p={p['logNo']}</link>\n"
        f"\t\t<pubDate>{rfc822(date)}</pubDate>\n"
        f"\t\t<dc:creator>{cdata(AUTHOR)}</dc:creator>\n"
        f"\t\t<guid isPermaLink=\"false\">naver-{p['logNo']}</guid>\n"
        f"\t\t<description></description>\n"
        f"\t\t<content:encoded>{cdata(html)}</content:encoded>\n"
        f"\t\t<excerpt:encoded>{cdata('')}</excerpt:encoded>\n"
        f"\t\t<wp:post_id>{p['logNo']}</wp:post_id>\n"
        f"\t\t<wp:post_date>{cdata(date + ' 09:00:00')}</wp:post_date>\n"
        f"\t\t<wp:post_date_gmt>{cdata(gmt)}</wp:post_date_gmt>\n"
        f"\t\t<wp:comment_status>{cdata('open')}</wp:comment_status>\n"
        f"\t\t<wp:ping_status>{cdata('open')}</wp:ping_status>\n"
        f"\t\t<wp:post_name>{cdata('post-' + p['logNo'])}</wp:post_name>\n"
        f"\t\t<wp:status>{cdata(status)}</wp:status>\n"
        f"\t\t<wp:post_parent>0</wp:post_parent>\n"
        f"\t\t<wp:menu_order>0</wp:menu_order>\n"
        f"\t\t<wp:post_type>{cdata('post')}</wp:post_type>\n"
        f"\t\t<wp:post_password>{cdata('')}</wp:post_password>\n"
        f"\t\t<wp:is_sticky>0</wp:is_sticky>\n"
        + (f"\t\t<category domain=\"category\" nicename=\"{slug(catno)}\">{cdata(catname)}</category>\n" if catname else "")
        + "\t</item>")

xml = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<rss version="2.0"\n'
    '\txmlns:excerpt="http://wordpress.org/export/1.2/excerpt/"\n'
    '\txmlns:content="http://purl.org/rss/1.0/modules/content/"\n'
    '\txmlns:wfw="http://wellformedweb.org/CommentAPI/"\n'
    '\txmlns:dc="http://purl.org/dc/elements/1.1/"\n'
    '\txmlns:wp="http://wordpress.org/export/1.2/">\n'
    '<channel>\n'
    f'\t<title>{SITE_TITLE}</title>\n'
    f'\t<link>{SITE_LINK}</link>\n'
    '\t<description>cookthedesign 블로그 백업 이전</description>\n'
    f'\t<pubDate>{rfc822(DEFAULT_DATE)}</pubDate>\n'
    '\t<language>ko</language>\n'
    '\t<wp:wxr_version>1.2</wp:wxr_version>\n'
    f'\t<wp:base_site_url>{SITE_LINK}</wp:base_site_url>\n'
    f'\t<wp:base_blog_url>{SITE_LINK}</wp:base_blog_url>\n'
    f'\t<wp:author><wp:author_id>1</wp:author_id><wp:author_login>{cdata(AUTHOR)}</wp:author_login>'
    f'<wp:author_email>admin@example.com</wp:author_email>'
    f'<wp:author_display_name>{cdata(AUTHOR)}</wp:author_display_name></wp:author>\n'
    + "\n".join(cat_defs) + "\n"
    + "\n".join(items) + "\n"
    '</channel>\n</rss>\n')

out = ROOT / "cookthedesign.wordpress.xml"
out.write_text(xml)
print(f"WXR 생성: {out.name}  글 {len(items)}개 · 상태 {status} · 이미지베이스 {'(치환)'+image_base if image_base else '(jsDelivr 유지)'}")
print(f"용량 {out.stat().st_size/1024/1024:.1f}MB")
