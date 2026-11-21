Prepare Linda Detector agreements for its next release. Work only in C:\Users\ninja\Desktop\Linda_2100_Dev. Do not build, publish, push or sign anything, and do not touch LocalDocs or the website.

Read NEXT_RELEASE_EULA.md in this folder first and follow its section "Что обязательно сделать при следующей разрешённой сборке", steps 1 and 2 only:

1. Compare the local installer/EULA.txt with the current file on main of the public repo: https://raw.githubusercontent.com/Lendarixon/Linda/main/desktop/installer/EULA.txt . Before changing the local file, copy it to work\eula_backup\EULA.txt. Then make the local file match main, without losing any newer local wording: if the local file has something main lacks, keep it out and list it in the report instead of merging by guess.
2. Find which EULA file the build script of this folder really reads and report the file and line. If it reads another copy, say so and do not edit that copy without listing it.

Also look in this folder for other notes about what must change before the next Detector release, for example PENDING_NEXT_RELEASE.md, NEXT_RELEASE*, and compare any other agreement or licence text shipped in the installer with the published documents in the repo's desktop folder. Only report these, do not edit them.

Do not change prices, device limits, refund terms or licence periods. Do not open private keys or files with keys.

Write the result to work\EULA_SYNC_REPORT.md in Russian: what changed, diff summary, which file the build reads, what else differs from the published documents, and what you could not check. Do not claim anything you did not verify.
