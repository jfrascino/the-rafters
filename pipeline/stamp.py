#!/usr/bin/env python3
"""Cache-busting: fingerprint every JS module and the stylesheet by content hash.

Writes an import map into site/index.html that remaps each module URL to `…?v=<hash>`, so browsers
(and GitHub Pages' 10-minute cache) always load matching versions of app.js, the views and helpers.
Run before every deploy (deploy.sh and the GitHub Action do).
"""
import hashlib, os, re, json

SITE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'site')


def h(path):
    return hashlib.sha1(open(path, 'rb').read()).hexdigest()[:10]


def main():
    idx = os.path.join(SITE, 'index.html')
    html = open(idx).read()
    imports = {}
    for root, _, files in os.walk(os.path.join(SITE, 'js')):
        for fn in sorted(files):
            if fn.endswith('.js'):
                full = os.path.join(root, fn)
                rel = './' + os.path.relpath(full, SITE).replace(os.sep, '/')
                imports[rel] = f'{rel}?v={h(full)}'
    block = '<script type="importmap" id="stamp">\n' + json.dumps({'imports': imports}, indent=1) + '\n</script>'
    if 'id="stamp"' in html:
        html = re.sub(r'<script type="importmap" id="stamp">.*?</script>', lambda _: block, html, flags=re.S)
    else:
        html = html.replace('</head>', block + '\n</head>', 1)
    css = os.path.join(SITE, 'css', 'app.css')
    html = re.sub(r'css/app\.css\?v=[\w]+', f'css/app.css?v={h(css)}', html)
    html = re.sub(r'js/app\.js\?v=[\w]+', f"js/app.js?v={h(os.path.join(SITE, 'js', 'app.js'))}", html)
    open(idx, 'w').write(html)
    print(f'stamped {len(imports)} modules + stylesheet')


if __name__ == '__main__':
    main()
