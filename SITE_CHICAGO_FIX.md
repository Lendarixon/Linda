# SITE_CHICAGO_FIX — Chicago-humans Assay 1.5.0 cell (2026-11-21)

## Cross-measurement (chicago_human, n=1992, caches read-only, eval/cache)
Old 1.3.1 shipped threshold (routing_131b.json EN thr_sensitive) = -0.109193.
1%-cap threshold (bench_150.json chicago_thr_1pct) = -0.345396.

| assay | @ old 1.3.1 thr (-0.1092) | @ 1% cap (-0.3454) |
|---|---|---|
| Assay 1.3.1 | 0.20% (4/1992, CI [0.08,0.52]) | 1.00% (20/1992, CI [0.65,1.55]) |
| Assay 1.5.0 | 0.20% (4/1992, CI [0.08,0.52]) | 1.00% (20/1992, CI [0.65,1.55]) |

The two assay versions are score-identical on this set (1.5.0 changed token-markup
heads only; EN routing byte-identical). The 1.00% cell was purely a threshold
artifact: the 1%-cap threshold was fit on this very set.

## Decision
Show the comparable number: Assay 1.5.0 Chicago-humans cell = 0.20% (same as
1.3.1 at the shipped threshold), with footnote 1 disclosing the 1%-cap figure
(1.00%, 20/1992). Edited results.html, results-ru.html, results-pl.html
(history table cell + explanatory note + footnote). Committed locally on gh-pages.
