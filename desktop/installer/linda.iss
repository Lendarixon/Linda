; Linda-Pro installer (Inno Setup 6). Per-user install: no administrator rights needed, installs to %LOCALAPPDATA%\Programs\Linda-Pro.
; Build:  tools\InnoSetup\ISCC.exe installer\linda.iss   (after tools\build_app.py)
; Silent update (used by the app itself):  Linda-Setup.exe /SILENT /SUPPRESSMSGBOXES /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS
; Corporate rollout (тихая установка по сети): Linda-Setup.exe /SILENT /SUPPRESSMSGBOXES /NORESTART /TASKS="" /DIR="C:\Program Files\Linda-Pro" [/MODELSET=lite|pro|both]
;   Policies for all users: %PROGRAMDATA%\Linda-Pro\enterprise.json (org_name, disable_export, disable_history,
;   require_license, audit_retention_days, max_batch_files, allowed_dirs) — читается приложением при старте.
#ifdef TestInstall
  #define AppName "Linda-Pro (test)"
#else
  #define AppName "Linda-Pro"
#endif
#ifndef AppVersion
  #define AppVersion "2.0.5.2"
#endif

[Setup]
#ifdef TestInstall
; test builds (ISCC /DTestInstall=1) use another AppId and name so that installing/uninstalling them never touches a real installation, its shortcuts or its registry entry
AppId={{E57A11B0-7E57-4E57-9E57-7E57E57E57E5}
#else
AppId={{B6D1E7F4-5E1C-4B8E-9D2A-4C8F0A11D0A1}
#endif
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Linda
AppPublisherURL=https://github.com/Lendarixon/Linda
AppSupportURL=mailto:lindapro.support@proton.me
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
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

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "polish"; MessagesFile: "compiler:Languages\Polish.isl"

[CustomMessages]
english.ModelsTitle=Models folder
english.ModelsDesc=Where should the detector models be stored?
english.ModelsSub=The models take from 0.7 GB (Lite) to about 3.7 GB (both versions); the cache needs some more. You can choose another drive. Click Next to continue.
english.ModelsLow=There is not enough free space on this drive (about 6 GB needed). Choose another folder?
english.ModelsRel=Please choose a folder on this computer (for example D:\Linda).
english.CtxMenu=Check in Linda-Pro
english.CtxMenuTask=Add "Check in Linda-Pro" to the Explorer context menu (.docx, .pdf, .txt, .md)
english.CtxMenuGroup=Explorer:
english.UninstallModels=Also delete the downloaded models, settings and licence key (about 3 GB) from this computer?
russian.ModelsTitle=Папка для моделей
russian.ModelsDesc=Где хранить модели детектора?
russian.ModelsSub=Модели занимают около 3 ГБ (с кэшем до 6 ГБ). Можно выбрать другой диск. Нажмите «Далее», чтобы продолжить.
russian.ModelsLow=На этом диске мало места (нужно около 6 ГБ). Выбрать другую папку?
russian.ModelsRel=Укажите папку на этом компьютере (например, D:\Linda).
russian.CtxMenu=Проверить в Linda-Pro
russian.CtxMenuTask=Добавить «Проверить в Linda-Pro» в меню проводника (.docx, .pdf, .txt, .md)
russian.CtxMenuGroup=Проводник:
russian.UninstallModels=Удалить также скачанные модели, настройки и ключ лицензии (около 3 ГБ) с этого компьютера?
polish.ModelsTitle=Folder modeli
polish.ModelsDesc=Gdzie przechowywać modele detektora?
polish.ModelsSub=Modele zajmują około 3 GB (z pamięcią podręczną do 6 GB). Możesz wybrać inny dysk. Kliknij Dalej, aby kontynuować.
polish.ModelsLow=Na tym dysku jest za mało miejsca (potrzeba około 6 GB). Wybrać inny folder?
polish.ModelsRel=Podaj folder na tym komputerze (na przykład D:\Linda).
polish.CtxMenu=Sprawdź w Linda-Pro
polish.CtxMenuTask=Dodaj „Sprawdź w Linda-Pro” do menu Eksploratora (.docx, .pdf, .txt, .md)
polish.CtxMenuGroup=Eksplorator:
polish.UninstallModels=Usunąć także pobrane modele, ustawienia i klucz licencji (około 3 GB) z tego komputera?

english.SetsTitle=What to install
english.SetsDesc=Linda-Pro comes in two versions. Choose what to put on this computer.
english.SetsSub=Not sure? Choose Lite. You can add or remove either version later in Settings.
english.SetsLite=Linda-Pro Lite (about 0.7 GB): light and fast, works on any computer, even without a graphics card. Slightly less accurate.
english.SetsPro=Linda-Pro (about 3 GB): the most accurate; best with a modern graphics card, slow on a weak computer.
english.SetsBoth=Both (about 3.7 GB): the app picks the suitable one by itself.
russian.SetsTitle=Что установить
russian.SetsDesc=Linda-Pro выпускается в двух версиях. Выберите, что поставить на этот компьютер.
russian.SetsSub=Не уверены? Выберите Lite. Любую версию можно добавить или убрать позже в настройках.
russian.SetsLite=Linda-Pro Lite (около 0,7 ГБ): лёгкая и быстрая, работает на любом компьютере, даже без видеокарты. Чуть менее точная.
russian.SetsPro=Linda-Pro (около 3 ГБ): самая точная; лучше всего с современной видеокартой, на слабом компьютере медленная.
russian.SetsBoth=Обе (около 3,7 ГБ): программа сама выберет подходящую.
polish.SetsTitle=Co zainstalować
polish.SetsDesc=Linda-Pro występuje w dwóch wersjach. Wybierz, co zainstalować na tym komputerze.
polish.SetsSub=Nie jesteś pewien? Wybierz Lite. Każdą wersję można później dodać lub usunąć w ustawieniach.
polish.SetsLite=Linda-Pro Lite (około 0,7 GB): lekka i szybka, działa na każdym komputerze, nawet bez karty graficznej. Nieco mniej dokładna.
polish.SetsPro=Linda-Pro (około 3 GB): najdokładniejsza; najlepsza z nowoczesną kartą graficzną, na słabym komputerze wolna.
polish.SetsBoth=Obie (około 3,7 GB): program sam wybierze odpowiednią.

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"
Name: "ctxmenu"; Description: "{cm:CtxMenuTask}"; GroupDescription: "{cm:CtxMenuGroup}"

[Files]
Source: "..\dist\Linda-Pro\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\Linda-Pro.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\Linda-Pro.exe"; Tasks: desktopicon

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
Filename: "{app}\Linda-Pro.exe"; Description: "Start Linda-Pro"; Flags: nowait postinstall skipifsilent
; silent self-update of the app passes /RELAUNCH=1 so the new version starts by itself
Filename: "{app}\Linda-Pro.exe"; Flags: nowait; Check: ShouldRelaunch

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
// Models, settings and the licence are kept in %LOCALAPPDATA%\Linda-Pro (the models may live in a folder chosen on the Models page).
var
  ModelsPage: TInputDirWizardPage;
  SetsPage: TInputOptionWizardPage;

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

procedure InitializeWizard;
var
  Start: String;
begin
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
  SaveStringToFile(DataDir + '\installer_choice.json', '{"model_sets": ' + Sets + '}', False);
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;
  // the app updates itself silently: keep the folder chosen earlier
  if (PageID = ModelsPage.ID) and WizardSilent then Result := True;
  if (PageID = SetsPage.ID) and WizardSilent then Result := True;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  FreeMB, TotalMB: Cardinal;
  Dir: String;
begin
  Result := True;
  if CurPageID = ModelsPage.ID then
  begin
    Dir := Trim(ModelsPage.Values[0]);
    if (Length(Dir) < 3) or (Pos(':', Dir) <> 2) then
    begin
      MsgBox(CustomMessage('ModelsRel'), mbError, MB_OK);
      Result := False;
      Exit;
    end;
    if GetSpaceOnDisk(Copy(Dir, 1, 3), True, FreeMB, TotalMB) then
      if FreeMB < Cardinal(2048 + (SetsPage.SelectedValueIndex * 2048)) then
        if MsgBox(CustomMessage('ModelsLow'), mbConfirmation, MB_YESNO) = IDYES then
          Result := False;
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
      if ExpandConstant('{param:MODELSET|}') <> '' then SaveSetsChoice;
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
