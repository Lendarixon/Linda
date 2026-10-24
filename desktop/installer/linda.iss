; Linda-Pro installer (Inno Setup 6). Per-user install: no administrator rights needed, installs to %LOCALAPPDATA%\Programs\Linda-Pro.
; Build:  tools\InnoSetup\ISCC.exe installer\linda.iss   (after tools\build_app.py)
; Silent update (used by the app itself):  Linda-Setup.exe /SILENT /SUPPRESSMSGBOXES /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS
; Corporate rollout (тихая установка по сети): Linda-Setup.exe /SILENT /SUPPRESSMSGBOXES /NORESTART /TASKS="" /DIR="C:\Program Files\Linda-Pro" [/MODELSET=lite|pro|both] [/PACKS=none|trace|lite|full] [/LICENSEKEY=ключ]
;   Silent без /MODELSET и /PACKS оставляет автовыбор: модель Loupe + пакеты по железу (WMI: VRAM>=8 ГБ -> всё, RAM>=8 ГБ -> Lite, иначе только детектор).
;   Без ключа (и без явного /PACKS) ставится демо: только детектор, без пакетов Trace/Humanizer. Страница ключа идёт первой, сразу после соглашения.
;   Policies for all users: %PROGRAMDATA%\Linda-Pro\enterprise.json (org_name, disable_export, disable_history,
;   require_license, audit_retention_days, max_batch_files, allowed_dirs) — читается приложением при старте.
#ifdef TestInstall
  #define AppName "Linda-Pro (test)"
  #define DisplayAppName "Linda (test)"
#else
  #define AppName "Linda-Pro"
  #define DisplayAppName "Linda"
#endif
#ifndef AppVersion
  #define AppVersion "2.3.0.0"
#endif

[Setup]
#ifdef TestInstall
; test builds (ISCC /DTestInstall=1) use another AppId and name so that installing/uninstalling them never touches a real installation, its shortcuts or its registry entry
AppId={{E57A11B0-7E57-4E57-9E57-7E57E57E57E5}
SetupMutex=LindaProTestSetup,Global\LindaProTestSetup
#else
AppId={{B6D1E7F4-5E1C-4B8E-9D2A-4C8F0A11D0A1}
SetupMutex=LindaProSetup,Global\LindaProSetup
#endif
AppName={#DisplayAppName}
AppVersion={#AppVersion}
AppPublisher=Linda
AppPublisherURL=https://github.com/Lendarixon/Linda
AppSupportURL=mailto:lindapro.support@proton.me
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#DisplayAppName}
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=Linda-Setup
SetupIconFile=..\assets\linda.ico
UninstallDisplayIcon={app}\Linda-Pro.exe
Compression=lzma2/fast
SolidCompression=no
WizardStyle=modern
WizardImageFile=../assets/wizard.bmp
WizardSmallImageFile=../assets/wizard_small.bmp
WizardImageBackColor=$15110d
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
LicenseFile=..\installer\EULA.txt
CloseApplications=yes
RestartApplications=no
UsePreviousAppDir=yes
; Ignore the language remembered by older installers; use Windows display language.
; English is the first language and fallback. /LANG still allows an explicit choice.
UsePreviousLanguage=no
LanguageDetectionMethod=uilanguage
ShowLanguageDialog=auto

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "polish"; MessagesFile: "compiler:Languages\Polish.isl"

[CustomMessages]
english.ModelsTitle=Models folder
english.ModelsDesc=Where should the detector models be stored?
english.ModelsSub=The models take from 0.3 GB (Linda Loupe) to about 3 GB (both versions); the cache needs some more. You can choose another drive. Click Next to continue.
english.ModelsLow=There is not enough free space on this drive (about 6 GB needed). Choose another folder?
english.ModelsRel=Please choose a folder on this computer (for example D:\Linda).
english.CtxMenu=Check in Linda
english.CtxMenuTask=Add "Check in Linda" to the Explorer context menu (.docx, .pdf, .txt, .md)
english.CtxMenuGroup=Explorer:
english.UninstallModels=Also delete the downloaded models, settings and licence key (about 3 GB) from this computer?
russian.ModelsTitle=Папка для моделей
russian.ModelsDesc=Где хранить модели детектора?
russian.ModelsSub=Модели занимают около 3 ГБ (с кэшем до 6 ГБ). Можно выбрать другой диск. Нажмите «Далее», чтобы продолжить.
russian.ModelsLow=На этом диске мало места (нужно около 6 ГБ). Выбрать другую папку?
russian.ModelsRel=Укажите папку на этом компьютере (например, D:\Linda).
russian.CtxMenu=Проверить в Linda
russian.CtxMenuTask=Добавить «Проверить в Linda» в меню проводника (.docx, .pdf, .txt, .md)
russian.CtxMenuGroup=Проводник:
russian.UninstallModels=Удалить также скачанные модели, настройки и ключ лицензии (около 3 ГБ) с этого компьютера?
polish.ModelsTitle=Folder modeli
polish.ModelsDesc=Gdzie przechowywać modele detektora?
polish.ModelsSub=Modele zajmują około 3 GB (z pamięcią podręczną do 6 GB). Możesz wybrać inny dysk. Kliknij Dalej, aby kontynuować.
polish.ModelsLow=Na tym dysku jest za mało miejsca (potrzeba około 6 GB). Wybrać inny folder?
polish.ModelsRel=Podaj folder na tym komputerze (na przykład D:\Linda).
polish.CtxMenu=Sprawdź w Linda
polish.CtxMenuTask=Dodaj „Sprawdź w Linda” do menu Eksploratora (.docx, .pdf, .txt, .md)
polish.CtxMenuGroup=Eksplorator:
polish.UninstallModels=Usunąć także pobrane modele, ustawienia i klucz licencji (około 3 GB) z tego komputera?

english.LicTitle=Licence key
english.LicDesc=Do you have a licence key?
english.LicSub=Paid and gift keys both unlock Trace and Humanizer. Without a key the app installs in demo mode.
english.LicKey=I have a key:
english.LicKeyMode=I have a key (Confirm)
english.LicDemoMode=Continue in demo mode
english.LicDemoNote=Demo includes text checking, history, batch checking and document comparison. Not available: Humanizer (text rewriting) and Trace (similarity check). You can enter a key later in the app, under Licence.
english.LicNeedKey=Enter your key or choose demo mode.
english.LicWarnPacks=Without a key the Trace/Humanizer packs cannot be used or downloaded. Switch back to “Detector only”?
russian.LicTitle=Ключ лицензии
russian.LicDesc=Есть ли у вас ключ лицензии?
russian.LicSub=Подойдёт и платный, и подарочный ключ: они открывают Trace и Humanizer. Без ключа программа ставится в демо-режиме.
russian.LicKey=У меня есть ключ:
russian.LicKeyMode=У меня есть ключ (Подтвердить)
russian.LicDemoMode=Продолжить в демо-режиме
russian.LicDemoNote=Демо: доступны проверка текста, история, пакетная проверка и сравнение документов. Недоступны: Humanizer (переписывание текста) и Trace (проверка схожести). Ключ можно ввести позже в приложении в разделе «Лицензия».
russian.LicNeedKey=Введите ключ или выберите демо-режим.
russian.LicWarnPacks=Без ключа пакеты Trace/Humanizer недоступны и не будут скачиваться. Вернуться к варианту «Только детектор»?
polish.LicTitle=Klucz licencji
polish.LicDesc=Czy masz klucz licencji?
polish.LicSub=Płatny i podarunkowy klucz odblokowują Trace i Humanizer. Bez klucza program instaluje się w trybie demo.
polish.LicKey=Mam klucz:
polish.LicKeyMode=Mam klucz (Potwierdź)
polish.LicDemoMode=Kontynuuj w trybie demo
polish.LicDemoNote=Demo: dostępne sprawdzanie tekstu, historia, sprawdzanie plików i porównywanie dokumentów. Niedostępne: Humanizer (przeredagowanie tekstu) i Trace (sprawdzanie podobieństwa). Klucz można wpisać później w aplikacji w sekcji Licencja.
polish.LicNeedKey=Wpisz klucz lub wybierz tryb demo.
polish.LicWarnPacks=Bez klucza pakiety Trace/Humanizer są niedostępne i nie zostaną pobrane. Wrócić do opcji „Tylko detektor”?

english.SetsTitle=What to install
english.SetsDesc=Linda comes in two versions. Choose what to put on this computer.
english.SetsSub=Not sure? Choose Linda Loupe. You can add or remove either version later in Settings.
english.SetsLite=Linda Loupe (about 0.3 GB): light and fast, works on any computer, even without a graphics card. Slightly less accurate.
english.SetsPro=Linda Assay (about 3 GB): the most accurate; best with a modern graphics card, slow on a weak computer.
english.SetsBoth=Both (about 3.7 GB): the app picks the suitable one by itself.
russian.SetsTitle=Что установить
russian.SetsDesc=Linda выпускается в двух версиях. Выберите, что поставить на этот компьютер.
russian.SetsSub=Не уверены? Выберите Linda Loupe. Любую версию можно добавить или убрать позже в настройках.
russian.SetsLite=Linda Loupe (около 0,3 ГБ): лёгкая и быстрая, работает на любом компьютере, даже без видеокарты. Чуть менее точная.
russian.SetsPro=Linda Assay (около 3 ГБ): самая точная; лучше всего с современной видеокартой, на слабом компьютере медленная.
russian.SetsBoth=Обе (около 3,7 ГБ): программа сама выберет подходящую.
polish.SetsTitle=Co zainstalować
polish.SetsDesc=Linda występuje w dwóch wersjach. Wybierz, co zainstalować na tym komputerze.
polish.SetsSub=Nie jesteś pewien? Wybierz Linda Loupe. Każdą wersję można później dodać lub usunąć w ustawieniach.
polish.SetsLite=Linda Loupe (około 0,3 GB): lekka i szybka, działa na każdym komputerze, nawet bez karty graficznej. Nieco mniej dokładna.
polish.SetsPro=Linda Assay (około 3 GB): najdokładniejsza; najlepsza z nowoczesną kartą graficzną, na słabym komputerze wolna.
polish.SetsBoth=Obie (około 3,7 GB): program sam wybierze odpowiednią.

english.PackTitle=Licence packs
english.PackDesc=Which packs should be installed on this computer?
english.PackSub=Trace links findings to the source text. Humanizer rewrites flagged passages; Lite (0.6B, about 1.2 GB) runs on any PC, Full (4B, about 8 GB) needs a GPU with 8+ GB. The choice below was preselected from this computer's hardware. Trace and Humanizer need any licence key — you will be asked for it on the next page.
english.PackNone=Detector only
english.PackTrace=Detector + Trace (about 150 MB)
english.PackLite=Detector + Trace + Humanizer-Lite (0.6B, about 1.2 GB, any PC)
english.PackFull=Everything including Humanizer-Full (4B, about 8 GB, needs a GPU with 8+ GB)
english.PackWeak=(auto: weak hardware)
russian.PackTitle=Пакеты лицензии
russian.PackDesc=Какие пакеты поставить на этот компьютер?
russian.PackSub=Trace привязывает находки к исходному тексту. Humanizer переписывает помеченные фрагменты; Lite (0,6B, около 1,2 ГБ) работает на любом ПК, Full (4B, около 8 ГБ) нужен GPU с 8+ ГБ. Выбор ниже уже подставлен под железо этого компьютера. Для Trace и Humanizer нужен любой ключ лицензии — он спросится на следующей странице.
russian.PackNone=Только детектор
russian.PackTrace=Детектор + Trace (около 150 МБ)
russian.PackLite=Детектор + Trace + Humanizer-Lite (0,6B, около 1,2 ГБ, любой ПК)
russian.PackFull=Всё включая Humanizer-Full (4B, около 8 ГБ, нужен GPU с 8+ ГБ)
russian.PackWeak=(авто: слабое железо)
polish.PackTitle=Pakiety licencji
polish.PackDesc=Które pakiety zainstalować na tym komputerze?
polish.PackSub=Trace wiąże wyniki z tekstem źródłowym. Humanizer przepisuje oflagowane fragmenty; Lite (0,6B, około 1,2 GB) działa na każdym komputerze, Full (4B, około 8 GB) wymaga GPU z 8+ GB. Wybór poniżej wstępnie dopasowano do sprzętu tego komputera. Trace i Humanizer wymagają dowolnego klucza licencji — zapytamy o niego na następnej stronie.
polish.PackNone=Tylko detektor
polish.PackTrace=Detektor + Trace (około 150 MB)
polish.PackLite=Detektor + Trace + Humanizer-Lite (0,6B, około 1,2 GB, dowolny komputer)
polish.PackFull=Wszystko łącznie z Humanizer-Full (4B, około 8 GB, wymagany GPU z 8+ GB)
polish.PackWeak=(auto: słaby sprzęt)

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"
Name: "ctxmenu"; Description: "{cm:CtxMenuTask}"; GroupDescription: "{cm:CtxMenuGroup}"

[Files]
Source: "..\dist\Linda-Pro\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[InstallDelete]
; 2.0.5.2: продукт переименован в Linda - убрать ярлыки со старым именем
Type: files; Name: "{autoprograms}\{#AppName}.lnk"
Type: files; Name: "{autodesktop}\{#AppName}.lnk"

[Icons]
Name: "{autoprograms}\{#DisplayAppName}"; Filename: "{app}\Linda-Pro.exe"
Name: "{autodesktop}\{#DisplayAppName}"; Filename: "{app}\Linda-Pro.exe"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.docx\shell\LindaPro"; ValueType: string; ValueName: ""; ValueData: "{cm:CtxMenu}"; Flags: uninsdeletekey; Tasks: ctxmenu
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.docx\shell\LindaPro"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\Linda-Pro.exe"; Tasks: ctxmenu
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.docx\shell\LindaPro\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Linda-Pro.exe"" ""%1"""; Tasks: ctxmenu
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\LindaPro"; ValueType: string; ValueName: ""; ValueData: "{cm:CtxMenu}"; Flags: uninsdeletekey; Tasks: ctxmenu
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\LindaPro"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\Linda-Pro.exe"; Tasks: ctxmenu
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\LindaPro\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Linda-Pro.exe"" ""%1"""; Tasks: ctxmenu
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.txt\shell\LindaPro"; ValueType: string; ValueName: ""; ValueData: "{cm:CtxMenu}"; Flags: uninsdeletekey; Tasks: ctxmenu
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.txt\shell\LindaPro"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\Linda-Pro.exe"; Tasks: ctxmenu
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.txt\shell\LindaPro\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Linda-Pro.exe"" ""%1"""; Tasks: ctxmenu
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.md\shell\LindaPro"; ValueType: string; ValueName: ""; ValueData: "{cm:CtxMenu}"; Flags: uninsdeletekey; Tasks: ctxmenu
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.md\shell\LindaPro"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\Linda-Pro.exe"; Tasks: ctxmenu
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.md\shell\LindaPro\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Linda-Pro.exe"" ""%1"""; Tasks: ctxmenu

[Run]
Filename: "{app}\Linda-Pro.exe"; Description: "Start Linda"; Flags: nowait postinstall skipifsilent
; silent self-update of the app passes /RELAUNCH=1 so the new version starts by itself
Filename: "{app}\Linda-Pro.exe"; Flags: nowait; Check: ShouldRelaunch

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
// Models, settings and the licence are kept in %LOCALAPPDATA%\Linda-Pro (the models may live in a folder chosen on the Models page).
var
  ModelsPage: TInputDirWizardPage;
  SetsPage: TInputOptionWizardPage;
  PacksPage: TInputOptionWizardPage;
  LicPage: TWizardPage;
  LicKeyRadio, LicDemoRadio: TRadioButton;
  LicKeyEdit: TEdit;

// Licence key from the page (/LICENSEKEY=...) or the demo mode.
// Key page comes right after the licence agreement; demo mode means detector only.
function LicenseKey: String;
var
  K: String;
begin
  K := Trim(ExpandConstant('{param:LICENSEKEY|}'));
  if (K = '') and (not WizardSilent) and Assigned(LicKeyRadio) and LicKeyRadio.Checked then
    K := Trim(LicKeyEdit.Text);
  Result := K;
end;

function HasLicenseKey: Boolean;
begin
  Result := LicenseKey <> '';
end;

// Demo mode: key page answered with "demo" (or silent without /LICENSEKEY=).
// The packs page is skipped and only the detector is installed.
function DemoMode: Boolean;
begin
  if WizardSilent then
    Result := Trim(ExpandConstant('{param:LICENSEKEY|}')) = ''
  else if Assigned(LicDemoRadio) then
    Result := LicDemoRadio.Checked
  else
    Result := True;
end;

// explicit /PACKS=... (admin choice) bypasses the licence gate; the wizard default does not
function ExplicitPacks: Boolean;
var
  P: String;
begin
  P := LowerCase(ExpandConstant('{param:PACKS|}'));
  Result := (P = 'none') or (P = 'trace') or (P = 'lite') or (P = 'full');
end;

function DataDir: String;
begin
  Result := ExpandConstant('{localappdata}\{#AppName}');
end;

// Folder chosen earlier (models_location.json), or '' for the default.
function SavedModelsDir: String;
var
  Raw: AnsiString;
  S: String;
  P, Q: Integer;
begin
  Result := '';
  if LoadStringFromFile(DataDir + '\models_location.json', Raw) then
  begin
    S := String(Raw);
    P := Pos('"path"', S);
    if P > 0 then
    begin
      S := Copy(S, P + 6, Length(S));
      P := Pos('"', S);
      if P > 0 then
      begin
        S := Copy(S, P + 1, Length(S));
        Q := Pos('"', S);
        if Q > 0 then
        begin
          S := Copy(S, 1, Q - 1);
          StringChangeEx(S, '\\', '\', True);
          Result := S;
        end;
      end;
    end;
  end;
end;

// Total video memory in GB over all adapters (WMI Win32_VideoController), or -1 on any error.
function DetectVramGB: Double;
var
  Locator, Service, List, Item: Variant;
  I, Count: Integer;
  Total: Double;
  V: Variant;
begin
  Result := -1;
  try
    Locator := CreateOleObject('WbemScripting.SWbemLocator');
    Service := Locator.ConnectServer('.', 'root\CIMV2');
    List := Service.ExecQuery('SELECT AdapterRAM FROM Win32_VideoController');
    Count := List.Count;
    Total := 0;
    for I := 0 to Count - 1 do
    begin
      try
        Item := List.ItemIndex(I);
        V := Item.AdapterRAM;
        Total := Total + (1.0 * V);
      except
      end;
    end;
    if Total >= 0 then
      Result := Total / 1073741824;
  except
    Result := -1;
  end;
end;

// Total physical memory in GB (WMI Win32_ComputerSystem), or -1 on any error.
function DetectRamGB: Double;
var
  Locator, Service, List, Item: Variant;
  Total: Double;
  V: Variant;
begin
  Result := -1;
  try
    Locator := CreateOleObject('WbemScripting.SWbemLocator');
    Service := Locator.ConnectServer('.', 'root\CIMV2');
    List := Service.ExecQuery('SELECT TotalPhysicalMemory FROM Win32_ComputerSystem');
    Item := List.ItemIndex(0);
    V := Item.TotalPhysicalMemory;
    Total := 1.0 * V;
    if Total >= 0 then
      Result := Total / 1073741824;
  except
    Result := -1;
  end;
end;

// none / trace / lite / full: the page's choice, /PACKS=... for silent installs.
// Demo mode (or no key without explicit /PACKS) installs the detector only.
function ChosenPacks: String;
var
  P: String;
begin
  P := LowerCase(ExpandConstant('{param:PACKS|}'));
  if (P = 'none') or (P = 'trace') or (P = 'lite') or (P = 'full') then
    Result := P
  else if DemoMode or ((not HasLicenseKey) and (not ExplicitPacks)) then
    Result := 'none'
  else if PacksPage.SelectedValueIndex = 1 then
    Result := 'trace'
  else if PacksPage.SelectedValueIndex = 2 then
    Result := 'lite'
  else if PacksPage.SelectedValueIndex = 3 then
    Result := 'full'
  else
    Result := 'none';
end;

// extra disk space for the licence packs, in MB (Trace ~150, Lite ~1500, Full ~8500, cumulative)
function PacksExtraMB: Integer;
var
  P: String;
begin
  P := ChosenPacks;
  if P = 'full' then Result := 150 + 1500 + 8500
  else if P = 'lite' then Result := 150 + 1500
  else if P = 'trace' then Result := 150
  else Result := 0;
end;

function PacksJson: String;
begin
  if ChosenPacks = 'full' then Result := '["trace", "humanizer-lite", "humanizer-full"]'
  else if ChosenPacks = 'lite' then Result := '["trace", "humanizer-lite"]'
  else if ChosenPacks = 'trace' then Result := '["trace"]'
  else Result := '[]';
end;

function HumanizerVariant: String;
begin
  if ChosenPacks = 'full' then Result := 'full'
  else if ChosenPacks = 'lite' then Result := 'lite'
  else Result := 'auto';
end;

// licence page controls: the key field is active only in key mode
procedure LicModeChanged(Sender: TObject);
begin
  if Assigned(LicKeyEdit) and Assigned(LicKeyRadio) then
    LicKeyEdit.Enabled := LicKeyRadio.Checked;
end;

procedure LicKeyChanged(Sender: TObject);
begin
  if Assigned(LicKeyEdit) and Assigned(LicKeyRadio) and (Trim(LicKeyEdit.Text) <> '') then
    LicKeyRadio.Checked := True;
end;

procedure InitializeWizard;
var
  Start: String;
  VramGB, RamGB: Double;
  Presel: Integer;
  NoneCaption: String;
  LicPrompt, LicNote: TLabel;
begin
  // licence key FIRST, right after the agreement: key (=Подтвердить) or demo
  LicPage := CreateCustomPage(wpLicense, CustomMessage('LicTitle'), CustomMessage('LicDesc'));
  LicPrompt := TLabel.Create(LicPage);
  LicPrompt.Parent := LicPage.Surface;
  LicPrompt.Caption := CustomMessage('LicKey');
  LicPrompt.Left := 0; LicPrompt.Top := 0; LicPrompt.Width := LicPage.SurfaceWidth;
  LicKeyRadio := TRadioButton.Create(LicPage);
  LicKeyRadio.Parent := LicPage.Surface;
  LicKeyRadio.Caption := CustomMessage('LicKeyMode');
  LicKeyRadio.Left := 0; LicKeyRadio.Top := LicPrompt.Top + 22; LicKeyRadio.Width := LicPage.SurfaceWidth;
  LicKeyEdit := TEdit.Create(LicPage);
  LicKeyEdit.Parent := LicPage.Surface;
  LicKeyEdit.Left := 16; LicKeyEdit.Top := LicKeyRadio.Top + 22; LicKeyEdit.Width := LicPage.SurfaceWidth - 16;
  LicKeyEdit.Text := ExpandConstant('{param:LICENSEKEY|}');
  LicKeyEdit.OnChange := @LicKeyChanged;
  LicDemoRadio := TRadioButton.Create(LicPage);
  LicDemoRadio.Parent := LicPage.Surface;
  LicDemoRadio.Caption := CustomMessage('LicDemoMode');
  LicDemoRadio.Left := 0; LicDemoRadio.Top := LicKeyEdit.Top + 30; LicDemoRadio.Width := LicPage.SurfaceWidth;
  LicNote := TLabel.Create(LicPage);
  LicNote.Parent := LicPage.Surface;
  LicNote.Caption := CustomMessage('LicDemoNote');
  LicNote.Left := 16; LicNote.Top := LicDemoRadio.Top + 24; LicNote.Width := LicPage.SurfaceWidth - 16;
  LicNote.WordWrap := True; LicNote.AutoSize := True;
  LicDemoRadio.OnClick := @LicModeChanged; LicKeyRadio.OnClick := @LicModeChanged;
  LicKeyRadio.Checked := LicKeyEdit.Text <> '';
  LicDemoRadio.Checked := LicKeyEdit.Text = '';
  LicModeChanged(nil);
  ModelsPage := CreateInputDirPage(wpSelectDir, CustomMessage('ModelsTitle'), CustomMessage('ModelsDesc'), CustomMessage('ModelsSub'), False, '');
  ModelsPage.Add('');
  Start := ExpandConstant('{param:MODELSDIR|}');
  if Start = '' then Start := SavedModelsDir;
  if Start = '' then Start := DataDir;
  ModelsPage.Values[0] := Start;
  // which model sets to put on this computer; the app reads the choice on its first start and downloads only those
  SetsPage := CreateInputOptionPage(wpSelectDir, CustomMessage('SetsTitle'), CustomMessage('SetsDesc'), CustomMessage('SetsSub'), True, False);
  SetsPage.Add(CustomMessage('SetsLite'));
  SetsPage.Add(CustomMessage('SetsPro'));
  SetsPage.Add(CustomMessage('SetsBoth'));
  SetsPage.SelectedValueIndex := 0;
  // licence packs (2.2.0.0): preselect from the hardware, weak PCs default to the detector only
  Presel := 0;
  NoneCaption := CustomMessage('PackNone');
  try
    VramGB := DetectVramGB;
    RamGB := DetectRamGB;
    if VramGB >= 8 then Presel := 3
    else if RamGB >= 8 then Presel := 2
    else if RamGB >= 0 then
      NoneCaption := NoneCaption + ' ' + CustomMessage('PackWeak');
  except
    Presel := 0;
  end;
  PacksPage := CreateInputOptionPage(SetsPage.ID, CustomMessage('PackTitle'), CustomMessage('PackDesc'), CustomMessage('PackSub'), True, False);
  PacksPage.Add(NoneCaption);
  PacksPage.Add(CustomMessage('PackTrace'));
  PacksPage.Add(CustomMessage('PackLite'));
  PacksPage.Add(CustomMessage('PackFull'));
  PacksPage.SelectedValueIndex := Presel;
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
  Sets, UILang, Key: String;
begin
  if ChosenSets = 'lite' then Sets := '["lite"]'
  else if ChosenSets = 'pro' then Sets := '["pro"]'
  else Sets := '["pro", "lite"]';
  UILang := 'en';
  if ActiveLanguage = 'russian' then UILang := 'ru'
  else if ActiveLanguage = 'polish' then UILang := 'pl';
  Key := LicenseKey;
  StringChangeEx(Key, '\', '\\', True);
  StringChangeEx(Key, '"', '\"', True);
  ForceDirectories(DataDir);
  SaveStringToFile(DataDir + '\installer_choice.json', '{"model_sets": ' + Sets + ', "language": "' + UILang + '", "packs": ' + PacksJson + ', "humanizer_variant": "' + HumanizerVariant + '", "license_key": "' + Key + '"}', False);
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;
  // the app updates itself silently: keep the folder chosen earlier
  if (PageID = ModelsPage.ID) and WizardSilent then Result := True;
  if (PageID = SetsPage.ID) and WizardSilent then Result := True;
  if (PageID = PacksPage.ID) and WizardSilent then Result := True;
  if (PageID = LicPage.ID) and WizardSilent then Result := True;
  // demo mode needs no pack choice: only the detector is installed
  if (PageID = PacksPage.ID) and (not WizardSilent) and DemoMode then Result := True;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  FreeMB, TotalMB: Cardinal;
  Dir: String;
begin
  Result := True;
  if (CurPageID = ModelsPage.ID) or (CurPageID = PacksPage.ID) then
  begin
    Dir := Trim(ModelsPage.Values[0]);
    if (Length(Dir) < 3) or (Pos(':', Dir) <> 2) then
    begin
      MsgBox(CustomMessage('ModelsRel'), mbError, MB_OK);
      Result := False;
      Exit;
    end;
    if GetSpaceOnDisk(Copy(Dir, 1, 3), True, FreeMB, TotalMB) then
      if FreeMB < Cardinal(2048 + (SetsPage.SelectedValueIndex * 2048) + PacksExtraMB) then
        if MsgBox(CustomMessage('ModelsLow'), mbConfirmation, MB_YESNO) = IDYES then
          Result := False;
  end;
  // licence key page (first, right after the agreement): key (=confirm) or demo
  if (CurPageID = LicPage.ID) and (not LicDemoRadio.Checked) and (Trim(LicKeyEdit.Text) = '') then
  begin
    MsgBox(CustomMessage('LicNeedKey'), mbError, MB_OK);
    Result := False;
    Exit;
  end;
  // safety net: packs without a key are not downloaded — offer to reset to the detector only
  if (CurPageID = PacksPage.ID) and (not HasLicenseKey) and (ChosenPacks <> 'none') then
  begin
    if MsgBox(CustomMessage('LicWarnPacks'), mbConfirmation, MB_YESNO) = IDYES then
      PacksPage.SelectedValueIndex := 0
    else
    begin
      Result := False;
      Exit;
    end;
  end;
end;

procedure SaveModelsDir(Dir: String);
var
  Esc: String;
begin
  ForceDirectories(DataDir);
  if CompareText(RemoveBackslashUnlessRoot(Dir), DataDir) = 0 then
    DeleteFile(DataDir + '\models_location.json')
  else
  begin
    Esc := Dir;
    StringChangeEx(Esc, '\', '\\', True);
    SaveStringToFile(DataDir + '\models_location.json', '{"path": "' + Esc + '"}', False);
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  Dir: String;
begin
  if CurStep = ssPostInstall then
  begin
    if not WizardSilent then
    begin
      SaveModelsDir(Trim(ModelsPage.Values[0]));
      SaveSetsChoice;
    end
    else
    begin
      Dir := ExpandConstant('{param:MODELSDIR|}');
      if Dir <> '' then SaveModelsDir(Dir);
      // installer_choice записываем всегда: фиксирует решение установки
      // (наборы, язык, паки, ключ), приложение читает его только при пустых настройках
      SaveSetsChoice;
    end;
  end;
end;

function ShouldRelaunch: Boolean;
begin
  Result := ExpandConstant('{param:RELAUNCH|0}') = '1';
end;

// Ask before removing the models, settings and the licence on uninstall (about 3 GB).
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Dir: String;
begin
  if (CurUninstallStep = usPostUninstall) and (not UninstallSilent) then
    if MsgBox(CustomMessage('UninstallModels'), mbConfirmation, MB_YESNO) = IDYES then
    begin
      Dir := SavedModelsDir;
      if Dir <> '' then
      begin
        DelTree(Dir + '\models', True, True, True);
        DelTree(Dir + '\onnx', True, True, True);
        DelTree(Dir + '\calibration', True, True, True);
        DelTree(Dir + '\staging', True, True, True);
        DeleteFile(Dir + '\manifest.json');
        DeleteFile(Dir + '\manifest.json.sig');
        RemoveDir(Dir);
      end;
      DelTree(DataDir, True, True, True);
    end;
end;
