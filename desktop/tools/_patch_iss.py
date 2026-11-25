# -*- coding: utf-8 -*-
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "installer/linda.iss"
s = p.read_text(encoding="utf-8")


def rep(a, b):
    global s
    assert a in s, a[:80]
    s = s.replace(a, b, 1)


MSG = {
    "english": {
        "SetsTitle": "What to install", "SetsDesc": "Linda-Pro comes in two versions. Choose what to put on this computer.",
        "SetsSub": "Not sure? Choose Lite. You can add or remove either version later in Settings.",
        "SetsLite": "Linda-Pro Lite (about 0.7 GB): light and fast, works on any computer, even without a graphics card. Slightly less accurate.",
        "SetsPro": "Linda-Pro (about 3 GB): the most accurate; best with a modern graphics card, slow on a weak computer.",
        "SetsBoth": "Both (about 3.7 GB): the app picks the suitable one by itself.",
    },
    "russian": {
        "SetsTitle": "Что установить", "SetsDesc": "Linda-Pro выпускается в двух версиях. Выберите, что поставить на этот компьютер.",
        "SetsSub": "Не уверены? Выберите Lite. Любую версию можно добавить или убрать позже в настройках.",
        "SetsLite": "Linda-Pro Lite (около 0,7 ГБ): лёгкая и быстрая, работает на любом компьютере, даже без видеокарты. Чуть менее точная.",
        "SetsPro": "Linda-Pro (около 3 ГБ): самая точная; лучше всего с современной видеокартой, на слабом компьютере медленная.",
        "SetsBoth": "Обе (около 3,7 ГБ): программа сама выберет подходящую.",
    },
    "polish": {
        "SetsTitle": "Co zainstalować", "SetsDesc": "Linda-Pro występuje w dwóch wersjach. Wybierz, co zainstalować na tym komputerze.",
        "SetsSub": "Nie jesteś pewien? Wybierz Lite. Każdą wersję można później dodać lub usunąć w ustawieniach.",
        "SetsLite": "Linda-Pro Lite (około 0,7 GB): lekka i szybka, działa na każdym komputerze, nawet bez karty graficznej. Nieco mniej dokładna.",
        "SetsPro": "Linda-Pro (około 3 GB): najdokładniejsza; najlepsza z nowoczesną kartą graficzną, na słabym komputerze wolna.",
        "SetsBoth": "Obie (około 3,7 GB): program sam wybierze odpowiednią.",
    },
}
block = ""
for lang, kv in MSG.items():
    block += "".join(f"{lang}.{k}={v}\n" for k, v in kv.items())
rep("\n[Tasks]\n", "\n" + block + "\n[Tasks]\n")
# the models page text must not promise a fixed size any more
rep("english.ModelsSub=The models take about 3 GB (up to 6 GB with the cache). You can choose another drive. Click Next to continue.",
    "english.ModelsSub=The models take from 0.7 GB (Lite) to about 3.7 GB (both versions); the cache needs some more. You can choose another drive. Click Next to continue.")
rep("var\n  ModelsPage: TInputDirWizardPage;", "var\n  ModelsPage: TInputDirWizardPage;\n  SetsPage: TInputOptionWizardPage;")
rep("  ModelsPage.Values[0] := Start;\nend;", """  ModelsPage.Values[0] := Start;
  // which model sets to put on this computer; the app reads the choice on its first start and downloads only those
  SetsPage := CreateInputOptionPage(wpSelectDir, CustomMessage('SetsTitle'), CustomMessage('SetsDesc'), CustomMessage('SetsSub'), True, False);
  SetsPage.Add(CustomMessage('SetsLite'));
  SetsPage.Add(CustomMessage('SetsPro'));
  SetsPage.Add(CustomMessage('SetsBoth'));
  SetsPage.SelectedValueIndex := 0;
end;

// lite / pro / both: the page's choice, or /MODELSET=... for silent installs
function ChosenSets: String;
var
  P: String;
begin
  P := LowerCase(ExpandConstant('{param:MODELSET|}'));
  if (P = 'lite') or (P = 'pro') or (P = 'both') then
    Result := P
  else if SetsPage.SelectedValueIndex = 1 then
    Result := 'pro'
  else if SetsPage.SelectedValueIndex = 2 then
    Result := 'both'
  else
    Result := 'lite';
end;

procedure SaveSetsChoice;
var
  Sets: String;
begin
  if ChosenSets = 'lite' then Sets := '["lite"]'
  else if ChosenSets = 'pro' then Sets := '["pro"]'
  else Sets := '["pro", "lite"]';
  ForceDirectories(DataDir);
  SaveStringToFile(DataDir + '\\installer_choice.json', '{"model_sets": ' + Sets + '}', False);
end;""")
rep("  if (PageID = ModelsPage.ID) and WizardSilent then Result := True;", "  if (PageID = ModelsPage.ID) and WizardSilent then Result := True;\n  if (PageID = SetsPage.ID) and WizardSilent then Result := True;")
rep("      if FreeMB < 6144 then", "      if FreeMB < Cardinal(2048 + (SetsPage.SelectedValueIndex * 2048)) then")
rep("    if not WizardSilent then\n      SaveModelsDir(Trim(ModelsPage.Values[0]))\n    else\n    begin\n      Dir := ExpandConstant('{param:MODELSDIR|}');\n      if Dir <> '' then SaveModelsDir(Dir);\n    end;",
    "    if not WizardSilent then\n    begin\n      SaveModelsDir(Trim(ModelsPage.Values[0]));\n      SaveSetsChoice;\n    end\n    else\n    begin\n      Dir := ExpandConstant('{param:MODELSDIR|}');\n      if Dir <> '' then SaveModelsDir(Dir);\n      if ExpandConstant('{param:MODELSET|}') <> '' then SaveSetsChoice;\n    end;")
rep("; Corporate rollout (тихая установка по сети): Linda-Setup.exe /SILENT /SUPPRESSMSGBOXES /NORESTART /TASKS=\"\" /DIR=\"C:\\Program Files\\Linda-Pro\"", "; Corporate rollout (тихая установка по сети): Linda-Setup.exe /SILENT /SUPPRESSMSGBOXES /NORESTART /TASKS=\"\" /DIR=\"C:\\Program Files\\Linda-Pro\" [/MODELSET=lite|pro|both]")
p.write_text(s, encoding="utf-8")
print("iss patched")
