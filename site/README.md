# Linda website source

The public site is generated from `build_site.py`, `i18n/`, `content/`, `assets/` and `static/`.

From this folder, run `python build_site.py`, `python check_i18n.py` and `python check_links.py`. The generated `public/` tree is deployed to the repository's `gh-pages` branch. Keep older standalone pages when deploying; this update does not delete existing pages.

Application release 2.0.6.2; model pack 1.3.4. Store package 2.0.6002.0 is prepared for submission; Store availability requires submission and review. The online demo processes text on Modal servers; desktop inference stays local.
