Build Linda Detector 2.3.0.2. The only change from 2.3.0.1 is the corrected agreement already in installer/EULA.txt. Work from C:\Users\ninja\Desktop\Linda_2100_Dev. Read HANDOFF.md (the 26.10.2026 entries), NEXT_RELEASE_EULA.md, tools/release_2301.py, tools/build_store_2301.py, tools/publish_2301.py and qa tools first.

Do NOT publish, push, upload to GitHub or Hugging Face, or sign a manifest. Never open, print or copy private keys. Do not touch models, prices or app logic. Never start the app against the real user profile, and do not uninstall or overwrite the installed Linda. Do not touch C:\Users\ninja\Desktop\Linda_2.3.0.1 or Linda_2.3.0.1_Store: they are the published builds; use them only as read-only base.

Steps:
1. Copy the three tools to tools/release_2302.py, build_store_2302.py, publish_2302.py with VER 2.3.0.2, base = the 2.3.0.1 app, output folders Desktop\Linda_2.3.0.2 and Desktop\Linda_2.3.0.2_Store. Update any version constant and EXE stamp the 2.3.0.1 release updated, the same way. Keep it to version changes. If a full rebuild is not needed because the base app is already complete, use the lightest existing path that still gives a correct version stamp, and explain it.
2. Build the installer Linda-Setup.exe with its sha256.
3. Build the Store MSIX. Microsoft requires revision 0, and the last Store package was Version 2.3.1.0, so its manifest Version must be 2.3.2.0: file Linda-Pro_2.3.2.0_x64.msix. Identity from HANDOFF and the existing script: Lendarixon.Linda-ProPrivateAITextChecker, publisher CN=9B03426F-4B1A-417A-82A1-61A2A4CA04E1. No secrets, logs or per-machine config inside; check it by listing the archive.
4. Verify: the new EULA text is inside the installer output and is what Inno shows (the compile input hash equals installer/EULA.txt; extract if possible). Run the smoke QA adapted from tools/qa_smoke_2301.py if it can run with a temporary profile; otherwise say so. Check the app reports version 2.3.0.2. Check the MSIX manifest version.
5. publish_2302.py: release notes in EN, RU and PL, plainly: corrected licence agreement text, no feature changes. Make it able to run the GitHub step alone, without touching the Hugging Face manifest. Do not run it.
6. Write Desktop\Linda_2.3.0.2\RELEASE_RESULT.md in Russian: exact paths, sizes, SHA-256, what was verified and how, what was not, and text for Store "What's new" in EN, RU, PL.

Do not claim anything you did not run.
