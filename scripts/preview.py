#!/usr/bin/env python3
"""Build _preview.html so the README can be checked before pushing.

Rather than approximating GitHub's markdown, this asks GitHub to render it:
POST /markdown returns the exact HTML the site would produce. Only the
surrounding page styling is approximated here.

Use mode=markdown, not mode=gfm. `gfm` is comment semantics, where every single
newline becomes a <br> — that double-spaces a document like this one, which
uses explicit <br> for its line breaks. README files are rendered without that.

Unauthenticated, so it is rate limited (60/hour) — plenty for checking a page.

Usage:
  python scripts/preview.py            # then serve, see scripts/README.md
"""
import json
import os
import sys
import urllib.error
import urllib.request

OUT = "_preview.html"

# Close enough to GitHub's own markdown body for judging layout and contrast.
CSS = """
body{margin:0}
.pane{padding:32px}
.light{background:#fff;color:#1f2328}
.dark{background:#0d1117;color:#e6edf3;color-scheme:dark}
.md{max-width:620px;margin:0 auto;
    font:16px/1.6 -apple-system,"Segoe UI",Helvetica,Arial,sans-serif}
.md img{max-width:100%}
.md p{margin:0 0 16px}
.md blockquote{margin:0 0 16px;padding:0 1em;
               border-left:.25em solid #d1d9e0;color:#59636e}
.dark .md blockquote{border-color:#3d444d;color:#9198a1}
.md a{color:#0969da;text-decoration:none}
.dark .md a{color:#4493f8}
.md samp,.md code{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,
                  monospace;font-size:13px}
.md div[align=center]{text-align:center}
.tag{font:11px ui-monospace,monospace;letter-spacing:1.4px;opacity:.45;
     max-width:620px;margin:0 auto 20px}
"""


def render(markdown):
    req = urllib.request.Request(
        "https://api.github.com/markdown",
        data=json.dumps({"text": markdown, "mode": "markdown"}).encode(),
        headers={"Accept": "application/vnd.github+json",
                 "Content-Type": "application/json",
                 "User-Agent": "readme-preview"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode()
    except urllib.error.HTTPError as e:
        sys.exit(f"GitHub returned {e.code}: {e.read().decode()[:200]}")


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, "README.md"), encoding="utf-8") as f:
        body = render(f.read())

    html = ("<!doctype html><meta charset='utf-8'><title>preview</title>"
            f"<style>{CSS}</style>")
    for cls, name in (("light", "LIGHT MODE"), ("dark", "DARK MODE")):
        html += (f"<div class='pane {cls}'><p class='tag'>{name}</p>"
                 f"<div class='md'>{body}</div></div>")

    out = os.path.join(root, OUT)
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"{OUT}: {len(html) // 1024} KB. Now serve it — browsers refuse "
          f"file:// subresources for image documents:\n"
          f"  python -m http.server 8731\n"
          f"  http://127.0.0.1:8731/{OUT}")


if __name__ == "__main__":
    main()
