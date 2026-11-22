; Linda-Pro installer (Inno Setup 6). Per-user install: no administrator rights needed, installs to %LOCALAPPDATA%\Programs\Linda-Pro.
; Build:  tools\InnoSetup\ISCC.exe installer\linda.iss   (after tools\build_app.py)
; Silent update (used by the app itself):  Linda-Setup.exe /SILENT /SUPPRESSMSGBOXES /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS
; Corporate rollout (тихая установка по сети): Linda-Setup.exe /SILENT /SUPPRESSMSGBOXES /NORESTART /TASKS="" /DIR="C:\Program Files\Linda-Pro" [/MODELSET=lite|pro|both] [/PACKS=none|trace|lite|full|trace,humanizer-lite,humanizer-full] [/LICENSEKEY=ключ]
;   Silent без /MODELSET и /PACKS оставляет автовыбор: модель Loupe + пакеты по железу (WMI: VRAM>=8 ГБ -> Trace+Full, RAM>=8 ГБ -> Trace+Lite, иначе только детектор).
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
  #define AppVersion "2.5.0.1"
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
VersionInfoVersion={#AppVersion}
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
CloseApplications=force
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
english.ModelsSub=Models: ~0.3 GB (with cache ~0.5 GB). You can choose another drive.
english.ModelsSubFmt=Models: ~%1 GB (with cache ~%2 GB). You can choose another drive.
english.ModelsLow=Not enough free space on this drive (need ~%1 GB). Choose another folder?
english.ModelsRel=Please choose a folder on this computer (for example D:\Linda).
english.CtxMenu=Check in Linda
english.CtxMenuTask=Add "Check in Linda" to the Explorer context menu (.docx, .pdf, .txt, .md)
english.CtxMenuGroup=Explorer:
english.UninstallModels=Also delete the downloaded models, settings and licence key from this computer?
russian.ModelsTitle=Папка для моделей
russian.ModelsDesc=Где хранить модели детектора?
russian.ModelsSub=Модели: ~0,3 ГБ (с кэшем ~0,5 ГБ). Можно выбрать другой диск.
russian.ModelsSubFmt=Модели: ~%1 ГБ (с кэшем ~%2 ГБ). Можно выбрать другой диск.
russian.ModelsLow=На этом диске мало места (нужно ~%1 ГБ). Выбрать другую папку?
russian.ModelsRel=Укажите папку на этом компьютере (например, D:\Linda).
russian.CtxMenu=Проверить в Linda
russian.CtxMenuTask=Добавить «Проверить в Linda» в меню проводника (.docx, .pdf, .txt, .md)
russian.CtxMenuGroup=Проводник:
russian.UninstallModels=Удалить также скачанные модели, настройки и ключ лицензии с этого компьютера?
polish.ModelsTitle=Folder modeli
polish.ModelsDesc=Gdzie przechowywać modele detektora?
polish.ModelsSub=Modele: ~0,3 GB (z pamięcią podręczną ~0,5 GB). Możesz wybrać inny dysk.
polish.ModelsSubFmt=Modele: ~%1 GB (z pamięcią podręczną ~%2 GB). Możesz wybrać inny dysk.
polish.ModelsLow=Za mało wolnego miejsca na tym dysku (potrzeba ~%1 GB). Wybrać inny folder?
polish.ModelsRel=Podaj folder na tym komputerze (na przykład D:\Linda).
polish.CtxMenu=Sprawdź w Linda
polish.CtxMenuTask=Dodaj „Sprawdź w Linda” do menu Eksploratora (.docx, .pdf, .txt, .md)
polish.CtxMenuGroup=Eksplorator:
polish.UninstallModels=Usunąć także pobrane modele, ustawienia i klucz licencji z tego komputera?

english.LicTitle=Licence key
english.LicDesc=Do you have a licence key?
english.LicSub=Paid and gift keys both unlock Trace and Humanizer. Without a key the app installs in demo mode.
english.LicKey=I have a key:
english.LicKeyMode=I have a key (Confirm)
english.LicDemoMode=Continue in demo mode
english.LicDemoNote=Demo: text check, history, batch & compare. Key unlocks Trace & Humanizer (enter later in Licence).
english.LicNeedKey=Enter your key or choose demo mode.
english.LicWarnPacks=Without a key, Trace/Humanizer packs cannot be downloaded. Clear pack selection?
english.LicReuseMode=Use the licence key already on this computer
english.LicReuseNote=Found in %1 — will be copied here.
english.LicReuseNone=No licence key from an earlier installation was found on this computer.
english.UninstallKeep=Keep settings, downloaded models and the licence key on this computer?
english.UninstallKeepNote=A new installation will pick them up again. Choose No to delete all app data.
russian.LicTitle=Ключ лицензии
russian.LicDesc=Есть ли у вас ключ лицензии?
russian.LicSub=Подойдёт и платный, и подарочный ключ: они открывают Trace и Humanizer. Без ключа программа ставится в демо-режиме.
russian.LicKey=У меня есть ключ:
russian.LicKeyMode=У меня есть ключ (Подтвердить)
russian.LicDemoMode=Продолжить в демо-режиме
russian.LicDemoNote=Демо: проверка, история, пакеты и сравнение. Ключ открывает Trace и Humanizer (раздел «Лицензия»).
russian.LicNeedKey=Введите ключ или выберите демо-режим.
russian.LicWarnPacks=Без ключа пакеты Trace/Humanizer не скачаются. Снять выбор пакетов?
russian.LicReuseMode=Использовать ключ лицензии с этого компьютера
russian.LicReuseNote=Найден в %1 — будет скопирован сюда.
russian.LicReuseNone=Ключ от предыдущей установки на этом компьютере не найден.
russian.UninstallKeep=Сохранить настройки, скачанные модели и ключ лицензии на этом компьютере?
russian.UninstallKeepNote=Новая установка подхватит их снова. Выберите «Нет», чтобы удалить все данные.
polish.LicTitle=Klucz licencji
polish.LicDesc=Czy masz klucz licencji?
polish.LicSub=Płatny i podarunkowy klucz odblokowują Trace i Humanizer. Bez klucza program instaluje się w trybie demo.
polish.LicKey=Mam klucz:
polish.LicKeyMode=Mam klucz (Potwierdź)
polish.LicDemoMode=Kontynuuj w trybie demo
polish.LicDemoNote=Demo: sprawdzanie, historia, wsad i porównanie. Klucz otwiera Trace i Humanizer (sekcja Licencja).
polish.LicNeedKey=Wpisz klucz lub wybierz tryb demo.
polish.LicWarnPacks=Bez klucza pakiety Trace/Humanizer nie zostaną pobrane. Odznaczyć pakiety?
polish.LicReuseMode=Użyj klucza licencji z tego komputera
polish.LicReuseNote=Znaleziono w %1 — zostanie tu skopiowany.
polish.LicReuseNone=Na tym komputerze nie znaleziono klucza z wcześniejszej instalacji.
polish.UninstallKeep=Zachować ustawienia, pobrane modele i klucz licencji na tym komputerze?
polish.UninstallKeepNote=Nowa instalacja przejmie je ponownie. Wybierz Nie, aby usunąć wszystkie dane.

english.SetsTitle=What to install
english.SetsDesc=Choose which detector version to install.
english.SetsSub=Not sure? Choose Linda Loupe. You can change this later in Settings.
english.SetsLite=Linda Loupe (~0.3 GB) — fast, runs on any PC without a GPU
; EN uses dhi ONNX fp32 voices and PL/RU use l14m50 safetensors (~5.8 GB total on disk); lazy pool keeps one language loaded at a time, so ~4 GB VRAM, not 8.
english.SetsPro=Linda Assay (~5.8 GB) — most accurate; on a GPU it uses ~4 GB VRAM (fits 4 GB cards, slower on less)
english.SetsBoth=Both (~6.1 GB) — app picks the suitable one automatically (Assay uses ~4 GB VRAM on a GPU)
english.ReuseFound=Existing models (v%1) found in %2 — will be reused without re-downloading.
russian.SetsTitle=Что установить
russian.SetsDesc=Выберите версию детектора для установки.
russian.SetsSub=Не уверены? Выберите Linda Loupe. Версию можно сменить в настройках.
russian.SetsLite=Linda Loupe (~0,3 ГБ) — быстрая, работает на любом ПК без GPU
russian.SetsPro=Linda Assay (~5,8 ГБ) — самая точная; на видеокарте занимает ~4 ГБ VRAM (влезает в 4 ГБ, на меньших медленнее)
russian.SetsBoth=Обе (~6,1 ГБ) — программа сама выберет подходящую (Assay на GPU занимает ~4 ГБ VRAM)
russian.ReuseFound=Найдены готовые модели (v%1) в %2 — будут использованы без повторного скачивания.
polish.SetsTitle=Co zainstalować
polish.SetsDesc=Wybierz wersję detektora do zainstalowania.
polish.SetsSub=Nie jesteś pewien? Wybierz Linda Loupe. Zmienisz to później w ustawieniach.
polish.SetsLite=Linda Loupe (~0,3 GB) — szybka, działa na każdym PC bez GPU
polish.SetsPro=Linda Assay (~5,8 GB) — najdokładniejsza; na karcie graficznej zajmuje ~4 GB VRAM (mieści się w 4 GB, na mniejszych wolniej)
polish.SetsBoth=Obie (~6,1 GB) — program sam wybierze odpowiednią (Assay na GPU zajmuje ~4 GB VRAM)
polish.ReuseFound=Znaleziono gotowe modele (v%1) w %2 — zostaną użyte ponownie bez pobierania.

english.PackTitle=Licence packs
english.PackDesc=Select optional packs to install (requires a licence key).
english.PackSub=Defaults match this PC's hardware. Uncheck all for detector only.
english.PackTrace=Trace — source similarity check (~150 MB)
english.PackLite=Humanizer-Lite (0.6B, ~1.2 GB, CPU — any PC)
english.PackFull=Humanizer-Full (4B, ~8 GB, GPU 8+ GB)
russian.PackTitle=Пакеты лицензии
russian.PackDesc=Выберите дополнительные пакеты (нужен ключ лицензии).
russian.PackSub=Выбор ниже подобран под ваш ПК. Снимите всё, чтобы оставить только детектор.
russian.PackTrace=Trace — проверка схожести с источником (~150 МБ)
russian.PackLite=Humanizer-Lite (0,6B, ~1,2 ГБ, CPU — любой ПК)
russian.PackFull=Humanizer-Full (4B, ~8 ГБ, GPU 8+ ГБ)
polish.PackTitle=Pakiety licencji
polish.PackDesc=Wybierz opcjonalne pakiety (wymagany klucz licencji).
polish.PackSub=Domyślne dopasowano do sprzętu tego PC. Odznacz wszystko dla samego detektora.
polish.PackTrace=Trace — sprawdzanie podobieństwa źródeł (~150 MB)
polish.PackLite=Humanizer-Lite (0,6B, ~1,2 GB, CPU — każdy PC)
polish.PackFull=Humanizer-Full (4B, ~8 GB, GPU 8+ GB)

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
const
  TH32CS_SNAPPROCESS = $00000002;
  INVALID_HANDLE_VALUE = $FFFFFFFF;
  PROCESS_TERMINATE = $0001;
  SYNCHRONIZE = $00100000;
  WM_CLOSE = $0010;
  MAX_PATH = 260;

type
  TProcessEntry32W = record
    dwSize: DWORD;
    cntUsage: DWORD;
    th32ProcessID: DWORD;
    th32DefaultHeapID: DWORD;
    th32ModuleID: DWORD;
    cntThreads: DWORD;
    th32ParentProcessID: DWORD;
    pcPriClassBase: Longint;
    dwFlags: DWORD;
    szExeFile: array[0..MAX_PATH - 1] of Char;
  end;
  TDwordArray = array of DWORD;

var
  ModelsPage: TInputDirWizardPage;
  SetsPage: TInputOptionWizardPage;
  PacksPage: TInputOptionWizardPage;
  LicPage: TWizardPage;
  LicKeyRadio, LicDemoRadio, LicReuseRadio: TRadioButton;
  LicKeyEdit: TEdit;
  ExistingLicense: String;
  SetsReuseNote: TLabel;
  ReuseModelsFound: Boolean;
  SavedModelsVersion, SavedModelsSets, SavedModelsPath: String;
  CloseTargetPIDs: TDwordArray;
  ClosedWinCount: Integer;

function CreateToolhelp32Snapshot(dwFlags, th32ProcessID: DWORD): THandle;
  external 'CreateToolhelp32Snapshot@kernel32.dll stdcall';
function Process32FirstW(hSnapshot: THandle; var lppe: TProcessEntry32W): BOOL;
  external 'Process32FirstW@kernel32.dll stdcall';
function Process32NextW(hSnapshot: THandle; var lppe: TProcessEntry32W): BOOL;
  external 'Process32NextW@kernel32.dll stdcall';
function WinCloseHandle(hObject: THandle): BOOL;
  external 'CloseHandle@kernel32.dll stdcall';
function OpenProcess(dwDesiredAccess: DWORD; bInheritHandle: BOOL; dwProcessId: DWORD): THandle;
  external 'OpenProcess@kernel32.dll stdcall';
function TerminateProcess(hProcess: THandle; uExitCode: Cardinal): BOOL;
  external 'TerminateProcess@kernel32.dll stdcall';
function WaitForSingleObject(hHandle: THandle; dwMilliseconds: DWORD): DWORD;
  external 'WaitForSingleObject@kernel32.dll stdcall';
function GetCurrentProcessId: DWORD;
  external 'GetCurrentProcessId@kernel32.dll stdcall';
function EnumWindows(lpEnumFunc: LongWord; lParam: Longint): BOOL;
  external 'EnumWindows@user32.dll stdcall';
function GetWindowThreadProcessId(hWnd: LongWord; var lpdwProcessId: DWORD): DWORD;
  external 'GetWindowThreadProcessId@user32.dll stdcall';
function PostMessageW(hWnd: LongWord; Msg: Cardinal; wParam, lParam: Longint): BOOL;
  external 'PostMessageW@user32.dll stdcall';

function FindProcessesByName(ExeName: String): TDwordArray;
var
  Snap: THandle;
  PE: TProcessEntry32W;
  I, N: Integer;
  Name: String;
  SelfPID: DWORD;
begin
  SetArrayLength(Result, 0);
  SelfPID := GetCurrentProcessId;
  Snap := CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
  if Snap = INVALID_HANDLE_VALUE then
  begin
    Log('CloseRunningLindaProcesses: CreateToolhelp32Snapshot failed');
    Exit;
  end;
  try
    PE.dwSize := SizeOf(PE);
    if Process32FirstW(Snap, PE) then
    begin
      repeat
        Name := '';
        for I := 0 to MAX_PATH - 1 do
        begin
          if PE.szExeFile[I] = #0 then Break;
          Name := Name + PE.szExeFile[I];
        end;
        if (CompareText(Name, ExeName) = 0) and (PE.th32ProcessID <> SelfPID) then
        begin
          N := GetArrayLength(Result);
          SetArrayLength(Result, N + 1);
          Result[N] := PE.th32ProcessID;
        end;
      until not Process32NextW(Snap, PE);
    end;
  finally
    WinCloseHandle(Snap);
  end;
end;

function IsCloseTargetPID(PID: DWORD): Boolean;
var
  I: Integer;
begin
  Result := False;
  for I := 0 to GetArrayLength(CloseTargetPIDs) - 1 do
  begin
    if CloseTargetPIDs[I] = PID then
    begin
      Result := True;
      Exit;
    end;
  end;
end;

function EnumWindowsCloseProc(hWnd: LongWord; lParam: Longint): Longint;
var
  PID: DWORD;
begin
  PID := 0;
  GetWindowThreadProcessId(hWnd, PID);
  if (PID <> 0) and IsCloseTargetPID(PID) then
  begin
    if PostMessageW(hWnd, WM_CLOSE, 0, 0) then
      ClosedWinCount := ClosedWinCount + 1;
  end;
  Result := 1;
end;

procedure CloseRunningLindaProcesses;
var
  I, WaitStep, ResultCode: Integer;
  Remaining: TDwordArray;
  H: THandle;
begin
  CloseTargetPIDs := FindProcessesByName('Linda-Pro.exe');
  if GetArrayLength(CloseTargetPIDs) = 0 then
  begin
    Log('CloseRunningLindaProcesses: no running Linda-Pro.exe processes.');
    Exit;
  end;

  Log('CloseRunningLindaProcesses: found ' + IntToStr(GetArrayLength(CloseTargetPIDs)) + ' running Linda-Pro.exe process(es); sending WM_CLOSE.');
  ClosedWinCount := 0;
  EnumWindows(CreateCallback(@EnumWindowsCloseProc), 0);
  Log('CloseRunningLindaProcesses: posted WM_CLOSE to ' + IntToStr(ClosedWinCount) + ' window(s).');

  if ClosedWinCount > 0 then
  begin
    for WaitStep := 1 to 30 do
    begin
      Sleep(100);
      Remaining := FindProcessesByName('Linda-Pro.exe');
      if GetArrayLength(Remaining) = 0 then
      begin
        Log('CloseRunningLindaProcesses: all Linda-Pro.exe processes exited gracefully.');
        Exit;
      end;
    end;
  end;

  Remaining := FindProcessesByName('Linda-Pro.exe');
  for I := 0 to GetArrayLength(Remaining) - 1 do
  begin
    Log('CloseRunningLindaProcesses: terminating PID=' + IntToStr(Remaining[I]));
    H := OpenProcess(PROCESS_TERMINATE or SYNCHRONIZE, False, Remaining[I]);
    if H <> 0 then
    begin
      try
        if TerminateProcess(H, 1) then
          WaitForSingleObject(H, 2000)
        else
          Log('CloseRunningLindaProcesses: TerminateProcess failed for PID=' + IntToStr(Remaining[I]));
      finally
        WinCloseHandle(H);
      end;
    end
    else
      Log('CloseRunningLindaProcesses: OpenProcess failed for PID=' + IntToStr(Remaining[I]));
  end;

  Remaining := FindProcessesByName('Linda-Pro.exe');
  if GetArrayLength(Remaining) > 0 then
  begin
    Log('CloseRunningLindaProcesses: ' + IntToStr(GetArrayLength(Remaining)) + ' process(es) still running; invoking taskkill /F /IM Linda-Pro.exe');
    if Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /IM Linda-Pro.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
      Log('CloseRunningLindaProcesses: taskkill exit code=' + IntToStr(ResultCode))
    else
      Log('CloseRunningLindaProcesses: failed to launch taskkill, error=' + IntToStr(ResultCode));
  end;

  Remaining := FindProcessesByName('Linda-Pro.exe');
  Log('CloseRunningLindaProcesses: remaining Linda-Pro.exe count=' + IntToStr(GetArrayLength(Remaining)));
end;

// declared further down; needed by the licence-detection helpers
function DataDir: String; forward;

// A licence file counts only when it holds a key, is not revoked, and (if non-gift)
// has either a non-null expires_at or an explicit perpetual flag (matches licensing.py).
function LicenseFileUsable(F: String): Boolean;
var
  S: AnsiString;
  T: String;
  HasNullExp, IsGift, IsPerp: Boolean;
begin
  Result := False;
  if not FileExists(F) then Exit;
  if not LoadStringFromFile(F, S) then Exit;
  T := LowerCase(String(S));
  if not ((Pos('"key"', T) > 0) and (Pos('"status"', T) > 0) and (Pos('"revoked"', T) = 0)) then Exit;
  HasNullExp := (Pos('"expires_at": null', T) > 0) or (Pos('"expires_at":null', T) > 0);
  IsGift := Pos('"gift"', T) > 0;
  IsPerp := (Pos('"perpetual": true', T) > 0) or (Pos('"perpetual":true', T) > 0);
  if HasNullExp and (not IsGift) and (not IsPerp) then Exit;
  Result := True;
end;

// Walks the direct child folders of Parent matching Mask and returns the first
// Parent\<child>\<Leaf> that is a usable licence file ('' when there is none).
function ScanLicenseChildren(Parent, Mask, Leaf: String): String;
var
  FindRec: TFindRec;
begin
  Result := '';
  if not FindFirst(Parent + '\' + Mask, FindRec) then
    Exit;
  try
    repeat
      if (Result = '') then
        if LicenseFileUsable(Parent + '\' + FindRec.Name + '\' + Leaf) then
          Result := Parent + '\' + FindRec.Name + '\' + Leaf;
    until not FindNext(FindRec);
  finally
    FindClose(FindRec);
  end;
end;

// licence.json locations left behind by earlier Linda installations on THIS computer:
//   %LOCALAPPDATA%\Linda-Pro\license.json                     (EXE install, default data folder)
//   %LOCALAPPDATA%\Linda-Pro-*\license.json                   (older versioned data folders)
//   %LOCALAPPDATA%\Packages\<family>\LocalState\license.json  (MSIX/Store install)
// Returns the first usable file, or '' when there is none.
function FindExistingLicense: String;
var
  P: String;
begin
  Result := '';

  // same data folder this installer writes to (reinstall / in-place update)
  if LicenseFileUsable(DataDir + '\license.json') then
    Result := DataDir + '\license.json';

  // other EXE data folders (versioned, dev, beta builds)
  if Result = '' then
    Result := ScanLicenseChildren(ExpandConstant('{localappdata}'), 'Linda-Pro*', 'license.json');

  // MSIX / Store package profile (Packages\<family>\LocalState\license.json)
  if Result = '' then
    Result := ScanLicenseChildren(ExpandConstant('{localappdata}\Packages'), '*', 'LocalState\license.json');

  // explicit pointer that the app or a corporate rollout may leave behind
  if Result = '' then
  begin
    P := '';
    if RegQueryStringValue(HKEY_CURRENT_USER, 'Software\LindaPro', 'LastLicenseFile', P) then
      if LicenseFileUsable(P) then Result := P;
  end;
end;

function ReuseChosen: Boolean;
begin
  Result := Assigned(LicReuseRadio) and LicReuseRadio.Checked;
end;

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
  Result := (LicenseKey <> '') or ReuseChosen;
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
function HasPackToken(P, Tok: String): Boolean;
begin
  Result := Pos(',' + Tok + ',', ',' + P + ',') > 0;
end;

function ExplicitPacks: Boolean;
var
  P: String;
begin
  P := LowerCase(Trim(ExpandConstant('{param:PACKS|}')));
  Result := (P = 'none') or (P = 'trace') or (P = 'lite') or (P = 'full')
    or HasPackToken(P, 'trace') or HasPackToken(P, 'humanizer-lite') or HasPackToken(P, 'humanizer-full');
end;

function DataDir: String;
begin
  Result := ExpandConstant('{localappdata}\{#AppName}');
end;

// Folder chosen in a specific models_location.json file, or '' when absent.
function ReadModelsPath(LocFile: String): String;
var
  Raw: AnsiString;
  S: String;
  P, Q: Integer;
begin
  Result := '';
  if LoadStringFromFile(LocFile, Raw) then
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

// Folder chosen earlier (models_location.json), or '' for the default.
function SavedModelsDir: String;
begin
  Result := ReadModelsPath(DataDir + '\models_location.json');
end;

function HasSubDirMask(Mask: String): Boolean;
var
  FindRec: TFindRec;
begin
  Result := False;
  if not FindFirst(Mask, FindRec) then Exit;
  try
    repeat
      if (FindRec.Attributes and $10) <> 0 then
      begin
        Result := True;
        Break;
      end;
    until not FindNext(FindRec);
  finally
    FindClose(FindRec);
  end;
end;

function ExtractJsonField(S, Key: String): String;
var
  P, Q: Integer;
  Sub: String;
begin
  Result := '';
  P := Pos('"' + Key + '"', S);
  if P <= 0 then Exit;
  Sub := Copy(S, P + Length(Key) + 2, Length(S));
  P := Pos(':', Sub);
  if P <= 0 then Exit;
  Sub := Copy(Sub, P + 1, Length(Sub));
  P := Pos('"', Sub);
  if P <= 0 then Exit;
  Sub := Copy(Sub, P + 1, Length(Sub));
  Q := Pos('"', Sub);
  if Q <= 0 then Exit;
  Sub := Copy(Sub, 1, Q - 1);
  StringChangeEx(Sub, '\\', '\', True);
  Result := Sub;
end;

function ParseVerSeg(var S: String): Integer;
var
  P, I: Integer;
  Tok, Digits: String;
begin
  Result := 0;
  if S = '' then Exit;
  P := Pos('.', S);
  if P > 0 then
  begin
    Tok := Copy(S, 1, P - 1);
    S := Copy(S, P + 1, Length(S));
  end
  else
  begin
    Tok := S;
    S := '';
  end;
  Digits := '';
  for I := 1 to Length(Tok) do
  begin
    if (Tok[I] >= '0') and (Tok[I] <= '9') then
      Digits := Digits + Tok[I]
    else if Digits <> '' then
      Break;
  end;
  if Digits <> '' then
    Result := StrToIntDef(Digits, 0);
end;

function CompareVersionStr(A, B: String): Integer;
var
  VA, VB: Integer;
begin
  Result := 0;
  while (A <> '') or (B <> '') do
  begin
    VA := ParseVerSeg(A);
    VB := ParseVerSeg(B);
    if VA > VB then
    begin
      Result := 1;
      Exit;
    end;
    if VA < VB then
    begin
      Result := -1;
      Exit;
    end;
  end;
end;

procedure ConsiderSavedModelsCandidate(ProfileDir, CandidateDir: String;
  var BestVer, BestSets, BestDir: String; var BestHasFiles: Boolean);
var
  Raw: AnsiString;
  S, Ver, LowChoice, Sets: String;
  HasPro, HasLite, HasFiles, Better: Boolean;
begin
  if (CandidateDir = '') or (not FileExists(CandidateDir + '\manifest.json')) then Exit;
  if not LoadStringFromFile(CandidateDir + '\manifest.json', Raw) then Exit;
  S := String(Raw);
  Ver := ExtractJsonField(S, 'version');
  if Ver = '' then Exit;
  HasPro := HasSubDirMask(CandidateDir + '\models\essay_dhi*') or HasSubDirMask(CandidateDir + '\models\linda_essay*');
  HasLite := HasSubDirMask(CandidateDir + '\models\linda_speed*');
  HasFiles := HasPro or HasLite;
  if not HasFiles then
  begin
    if FileExists(ProfileDir + '\settings.json') and LoadStringFromFile(ProfileDir + '\settings.json', Raw) then
    begin
      LowChoice := LowerCase(String(Raw));
      if Pos('"model_sets"', LowChoice) > 0 then
      begin
        HasPro := Pos('"pro"', LowChoice) > 0;
        HasLite := Pos('"lite"', LowChoice) > 0;
      end;
    end;
    if (not HasPro) and (not HasLite) and FileExists(ProfileDir + '\installer_choice.json') and LoadStringFromFile(ProfileDir + '\installer_choice.json', Raw) then
    begin
      LowChoice := LowerCase(String(Raw));
      HasPro := Pos('"pro"', LowChoice) > 0;
      HasLite := Pos('"lite"', LowChoice) > 0;
    end;
  end;
  if (not HasPro) and (not HasLite) then
  begin
    LowChoice := LowerCase(S);
    HasPro := Pos('"pro"', LowChoice) > 0;
    HasLite := Pos('"lite"', LowChoice) > 0;
  end;
  if HasPro and HasLite then Sets := 'both'
  else if HasPro then Sets := 'pro'
  else Sets := 'lite';

  Better := False;
  if BestVer = '' then
    Better := True
  else if HasFiles and (not BestHasFiles) then
    Better := True
  else if HasFiles = BestHasFiles then
  begin
    if CompareVersionStr(Ver, BestVer) > 0 then
      Better := True;
  end;
  if Better then
  begin
    BestVer := Ver;
    BestSets := Sets;
    BestDir := CandidateDir;
    BestHasFiles := HasFiles;
  end;
end;

// A test build (ISCC /DTestInstall=1) has its own AppId and data dir and must never
// adopt another Linda profile's models: on a real machine the owner's production
// profile is always present, so a "fresh install" test would silently test the
// reuse path instead of the download path.
function AllowForeignProfileReuse: Boolean;
begin
#ifdef TestInstall
  Result := False;
#else
  // Silent self-update (/SILENT) runs through the same code and relies on reuse, so
  // this is deliberately NOT gated on WizardSilent.
  Result := True;
#endif
end;

// A folder only counts as a Linda profile if it carries at least one profile marker.
// Without this, any stray `%LOCALAPPDATA%\Linda-Pro*` folder (leftover of a manual
// copy, a half-deleted install) can be picked as the reuse source.
function IsLindaProfile(P: String): Boolean;
begin
  Result := FileExists(P + '\license.json') or FileExists(P + '\settings.json')
    or FileExists(P + '\installer_choice.json') or FileExists(P + '\models_location.json');
end;

// Scans DataDir, %LOCALAPPDATA%\Linda-Pro*\ and %LOCALAPPDATA%\Packages\*Linda*\LocalState\
// for models_location.json and manifest.json, picking the newest manifest version.
// Foreign profiles are only consulted by production builds (see AllowForeignProfileReuse).
function FindSavedModels(var OutVersion, OutSets, OutDir: String): Boolean;
var
  Dir, LocalApp, PkgDir, P, Loc: String;
  FindRec: TFindRec;
  BestHasFiles: Boolean;
begin
  Result := False;
  OutVersion := '';
  OutSets := '';
  OutDir := '';
  BestHasFiles := False;

  // 1. Current install DataDir (models_location.json target, then DataDir itself)
  Dir := SavedModelsDir;
  if Dir <> '' then
    ConsiderSavedModelsCandidate(DataDir, Dir, OutVersion, OutSets, OutDir, BestHasFiles);
  ConsiderSavedModelsCandidate(DataDir, DataDir, OutVersion, OutSets, OutDir, BestHasFiles);

  // 2. Other EXE data folders: %LOCALAPPDATA%\Linda-Pro*\
  LocalApp := ExpandConstant('{localappdata}');
  if AllowForeignProfileReuse and FindFirst(LocalApp + '\Linda-Pro*', FindRec) then
  begin
    try
      repeat
        if ((FindRec.Attributes and $10) <> 0) and (FindRec.Name <> '.') and (FindRec.Name <> '..') then
        begin
          P := LocalApp + '\' + FindRec.Name;
          if (CompareText(RemoveBackslashUnlessRoot(P), RemoveBackslashUnlessRoot(DataDir)) <> 0)
             and IsLindaProfile(P) then
          begin
            Loc := ReadModelsPath(P + '\models_location.json');
            if Loc <> '' then
              ConsiderSavedModelsCandidate(P, Loc, OutVersion, OutSets, OutDir, BestHasFiles);
            ConsiderSavedModelsCandidate(P, P, OutVersion, OutSets, OutDir, BestHasFiles);
          end;
        end;
      until not FindNext(FindRec);
    finally
      FindClose(FindRec);
    end;
  end;

  // 3. Store / MSIX packages: %LOCALAPPDATA%\Packages\*Linda*\LocalState\
  PkgDir := LocalApp + '\Packages';
  if AllowForeignProfileReuse and FindFirst(PkgDir + '\*Linda*', FindRec) then
  begin
    try
      repeat
        if ((FindRec.Attributes and $10) <> 0) and (FindRec.Name <> '.') and (FindRec.Name <> '..') then
        begin
          P := PkgDir + '\' + FindRec.Name + '\LocalState';
          if DirExists(P) then
          begin
            Loc := ReadModelsPath(P + '\models_location.json');
            if Loc <> '' then
              ConsiderSavedModelsCandidate(P, Loc, OutVersion, OutSets, OutDir, BestHasFiles);
            ConsiderSavedModelsCandidate(P, P, OutVersion, OutSets, OutDir, BestHasFiles);
          end;
        end;
      until not FindNext(FindRec);
    finally
      FindClose(FindRec);
    end;
  end;

  Result := OutVersion <> '';
end;

function DetectSavedModels(var OutVersion, OutSets, OutDir: String): Boolean;
begin
  Result := FindSavedModels(OutVersion, OutSets, OutDir);
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

// Independent pack checkboxes (Trace, Humanizer-Lite, Humanizer-Full) or /PACKS=... for silent installs.
// Demo mode (or no key without explicit /PACKS) installs the detector only.
function PackTraceSelected: Boolean;
var
  P: String;
begin
  P := LowerCase(Trim(ExpandConstant('{param:PACKS|}')));
  if ExplicitPacks then
    Result := (P = 'trace') or (P = 'lite') or (P = 'full') or HasPackToken(P, 'trace')
  else if DemoMode or (not HasLicenseKey) then
    Result := False
  else
    Result := Assigned(PacksPage) and PacksPage.Values[0];
end;

function PackLiteSelected: Boolean;
var
  P: String;
begin
  P := LowerCase(Trim(ExpandConstant('{param:PACKS|}')));
  if ExplicitPacks then
    Result := (P = 'lite') or (P = 'full') or HasPackToken(P, 'humanizer-lite')
  else if DemoMode or (not HasLicenseKey) then
    Result := False
  else
    Result := Assigned(PacksPage) and PacksPage.Values[1];
end;

function PackFullSelected: Boolean;
var
  P: String;
begin
  P := LowerCase(Trim(ExpandConstant('{param:PACKS|}')));
  if ExplicitPacks then
    Result := (P = 'full') or HasPackToken(P, 'humanizer-full')
  else if DemoMode or (not HasLicenseKey) then
    Result := False
  else
    Result := Assigned(PacksPage) and PacksPage.Values[2];
end;

function AnyPackSelected: Boolean;
begin
  Result := PackTraceSelected or PackLiteSelected or PackFullSelected;
end;

function ChosenPacks: String;
var
  S: String;
begin
  S := '';
  if PackTraceSelected then S := 'trace';
  if PackLiteSelected then
  begin
    if S <> '' then S := S + ',';
    S := S + 'humanizer-lite';
  end;
  if PackFullSelected then
  begin
    if S <> '' then S := S + ',';
    S := S + 'humanizer-full';
  end;
  if S = '' then S := 'none';
  Result := S;
end;

// extra disk space for the licence packs, in MB (Trace ~150, Lite ~1200, Full ~8000)
function PacksExtraMB: Integer;
begin
  Result := 0;
  if PackTraceSelected then Result := Result + 150;
  if PackLiteSelected then Result := Result + 1200;
  if PackFullSelected then Result := Result + 8000;
end;

function PacksJson: String;
var
  S: String;
begin
  S := '';
  if PackTraceSelected then S := '"trace"';
  if PackLiteSelected then
  begin
    if S <> '' then S := S + ', ';
    S := S + '"humanizer-lite"';
  end;
  if PackFullSelected then
  begin
    if S <> '' then S := S + ', ';
    S := S + '"humanizer-full"';
  end;
  Result := '[' + S + ']';
end;

function HumanizerVariant: String;
begin
  if PackFullSelected and (not PackLiteSelected) then
    Result := 'full'
  else if PackLiteSelected and (not PackFullSelected) then
    Result := 'lite'
  else
    Result := 'auto';
end;

// lite / pro / both: the page's choice, or /MODELSET=... for silent installs
function ChosenSets: String;
var
  P: String;
begin
  P := LowerCase(ExpandConstant('{param:MODELSET|}'));
  if (P = 'lite') or (P = 'pro') or (P = 'both') then
    Result := P
  else if Assigned(SetsPage) and (SetsPage.SelectedValueIndex = 1) then
    Result := 'pro'
  else if Assigned(SetsPage) and (SetsPage.SelectedValueIndex = 2) then
    Result := 'both'
  else
    Result := 'lite';
end;

function TotalModelsGB(WithCache: Boolean): Double;
var
  S: String;
  GB: Double;
begin
  S := ChosenSets;
  if S = 'pro' then GB := 5.8
  else if S = 'both' then GB := 6.1
  else GB := 0.3;
  if PackTraceSelected then GB := GB + 0.15;
  if PackLiteSelected then GB := GB + 1.2;
  if PackFullSelected then GB := GB + 8.0;
  if WithCache then GB := GB * 1.5;
  Result := GB;
end;

function FormatGB(V: Double): String;
begin
  Result := Format('%.1f', [V]);
  if (ActiveLanguage = 'russian') or (ActiveLanguage = 'polish') then
    StringChangeEx(Result, '.', ',', True)
  else
    StringChangeEx(Result, ',', '.', True);
end;

procedure UpdateModelsSub;
begin
  if not Assigned(ModelsPage) then Exit;
  ModelsPage.SubCaptionLabel.Caption := FmtMessage(CustomMessage('ModelsSubFmt'), [FormatGB(TotalModelsGB(False)), FormatGB(TotalModelsGB(True))]);
end;

procedure SelectionChanged(Sender: TObject);
begin
  UpdateModelsSub;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if Assigned(ModelsPage) and (CurPageID = ModelsPage.ID) then
    UpdateModelsSub;
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
  begin
    LicKeyRadio.Checked := True;
    // typing a key overrides the "reuse" choice
    if Assigned(LicReuseRadio) and LicReuseRadio.Checked then
      LicReuseRadio.Checked := False;
  end;
end;

// Copies the key found on this computer into the new install's data folder, so the
// app starts already licensed. Never overwrites a key the new install already has.
// Returns True when a licence file is in place afterwards.
function CopyExistingLicense: Boolean;
begin
  Result := False;
  if ExistingLicense = '' then
    Exit;
  if CompareText(ExistingLicense, DataDir + '\license.json') = 0 then
  begin
    Result := True;   // already in the right place (reinstall / in-place update)
    Exit;
  end;
  if FileExists(DataDir + '\license.json') then
  begin
    Result := True;   // do not clobber a newer key
    Exit;
  end;
  ForceDirectories(DataDir);
  Result := CopyFile(ExistingLicense, DataDir + '\license.json', False);
end;

procedure InitializeWizard;
var
  Start: String;
  VramGB, RamGB: Double;
  DefTrace, DefLite, DefFull: Boolean;
  LicPrompt, LicNote, LicReuseNote: TLabel;
  Y: Integer;
begin
  // licence key FIRST, right after the agreement: reuse an existing key, enter a new one, or demo
  LicPage := CreateCustomPage(wpLicense, CustomMessage('LicTitle'), CustomMessage('LicDesc'));
  ExistingLicense := FindExistingLicense;
  LicPrompt := TLabel.Create(LicPage);
  LicPrompt.Parent := LicPage.Surface;
  LicPrompt.Caption := CustomMessage('LicKey');
  LicPrompt.Left := 0; LicPrompt.Top := 0; LicPrompt.Width := LicPage.SurfaceWidth;
  Y := LicPrompt.Top + 22;

  // reuse an existing key from an earlier install: offered only when one was found
  LicReuseRadio := TRadioButton.Create(LicPage);
  LicReuseRadio.Parent := LicPage.Surface;
  LicReuseRadio.Caption := CustomMessage('LicReuseMode');
  LicReuseRadio.Left := 0; LicReuseRadio.Top := Y; LicReuseRadio.Width := LicPage.SurfaceWidth;
  LicReuseRadio.Visible := ExistingLicense <> '';
  // fixed-height label under the radio: AutoSize would reflow over the controls below
  LicReuseNote := TLabel.Create(LicPage);
  LicReuseNote.Parent := LicPage.Surface;
  LicReuseNote.Caption := '';
  if ExistingLicense <> '' then
    LicReuseNote.Caption := FmtMessage(CustomMessage('LicReuseNote'), [ExtractFileDir(ExistingLicense)]);
  LicReuseNote.Left := 16; LicReuseNote.Top := Y + 20;
  LicReuseNote.Width := LicPage.SurfaceWidth - 16;
  LicReuseNote.WordWrap := True; LicReuseNote.AutoSize := False; LicReuseNote.Height := 42;
  LicReuseNote.Visible := ExistingLicense <> '';
  if ExistingLicense <> '' then
    Y := Y + 66;

  LicKeyRadio := TRadioButton.Create(LicPage);
  LicKeyRadio.Parent := LicPage.Surface;
  LicKeyRadio.Caption := CustomMessage('LicKeyMode');
  LicKeyRadio.Left := 0; LicKeyRadio.Top := Y; LicKeyRadio.Width := LicPage.SurfaceWidth;
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
  LicReuseRadio.OnClick := @LicModeChanged;
  if ExistingLicense <> '' then
  begin
    // an existing key is the friendliest default: offer to carry it over
    LicReuseRadio.Checked := True;
    LicKeyRadio.Checked := False;
    LicDemoRadio.Checked := False;
  end
  else
  begin
    LicKeyRadio.Checked := LicKeyEdit.Text <> '';
    LicDemoRadio.Checked := LicKeyEdit.Text = '';
  end;
  LicModeChanged(nil);
  // scan for saved models before ModelsPage so we default to the folder where they live
  ReuseModelsFound := FindSavedModels(SavedModelsVersion, SavedModelsSets, SavedModelsPath);
  ModelsPage := CreateInputDirPage(wpSelectDir, CustomMessage('ModelsTitle'), CustomMessage('ModelsDesc'), CustomMessage('ModelsSub'), False, '');
  ModelsPage.Add('');
  Start := ExpandConstant('{param:MODELSDIR|}');
  if Start = '' then Start := SavedModelsDir;
  if (Start = '') and ReuseModelsFound and (SavedModelsPath <> '') then Start := SavedModelsPath;
  if Start = '' then Start := DataDir;
  ModelsPage.Values[0] := Start;
  // which model sets to put on this computer; the app reads the choice on its first start and downloads only those
  SetsPage := CreateInputOptionPage(wpSelectDir, CustomMessage('SetsTitle'), CustomMessage('SetsDesc'), CustomMessage('SetsSub'), True, False);
  SetsPage.Add(CustomMessage('SetsLite'));
  SetsPage.Add(CustomMessage('SetsPro'));
  SetsPage.Add(CustomMessage('SetsBoth'));
  if ReuseModelsFound and (SavedModelsSets = 'pro') then
    SetsPage.SelectedValueIndex := 1
  else if ReuseModelsFound and (SavedModelsSets = 'both') then
    SetsPage.SelectedValueIndex := 2
  else
    SetsPage.SelectedValueIndex := 0;
  SetsPage.CheckListBox.OnClickCheck := @SelectionChanged;
  SetsPage.CheckListBox.Height := ScaleY(90);
  SetsReuseNote := TLabel.Create(SetsPage);
  SetsReuseNote.Parent := SetsPage.Surface;
  SetsReuseNote.Left := 0;
  SetsReuseNote.Top := SetsPage.CheckListBox.Top + SetsPage.CheckListBox.Height + ScaleY(8);
  SetsReuseNote.Width := SetsPage.SurfaceWidth;
  SetsReuseNote.WordWrap := True;
  SetsReuseNote.AutoSize := True;
  SetsReuseNote.Font.Style := [fsBold];
  SetsReuseNote.Font.Color := $00206818;
  SetsReuseNote.Visible := ReuseModelsFound;
  if ReuseModelsFound then
    SetsReuseNote.Caption := FmtMessage(CustomMessage('ReuseFound'), [SavedModelsVersion, SavedModelsPath]);
  // licence packs (2.5.0.1): independent checkboxes preselected from hardware
  DefTrace := False;
  DefLite := False;
  DefFull := False;
  try
    VramGB := DetectVramGB;
    RamGB := DetectRamGB;
    if VramGB >= 8 then
    begin
      DefTrace := True;
      DefFull := True;
    end
    else if RamGB >= 8 then
    begin
      DefTrace := True;
      DefLite := True;
    end;
  except
  end;
  PacksPage := CreateInputOptionPage(SetsPage.ID, CustomMessage('PackTitle'), CustomMessage('PackDesc'), CustomMessage('PackSub'), False, False);
  PacksPage.Add(CustomMessage('PackTrace'));
  PacksPage.Add(CustomMessage('PackLite'));
  PacksPage.Add(CustomMessage('PackFull'));
  PacksPage.Values[0] := DefTrace;
  PacksPage.Values[1] := DefLite;
  PacksPage.Values[2] := DefFull;
  PacksPage.CheckListBox.OnClickCheck := @SelectionChanged;
  UpdateModelsSub;
end;

procedure SaveSetsChoice;
var
  Sets, UILang, Key, ReuseJson, VerEsc, ReuseSetsJson: String;
begin
  if ChosenSets = 'lite' then Sets := '["lite"]'
  else if ChosenSets = 'pro' then Sets := '["pro"]'
  else Sets := '["pro", "lite"]';
  UILang := 'en';
  if ActiveLanguage = 'russian' then UILang := 'ru'
  else if ActiveLanguage = 'polish' then UILang := 'pl';
  Key := LicenseKey;
  // reuse mode: copy the found licence.json instead of stuffing the key into the choice file
  if (Key = '') and ReuseChosen then
    CopyExistingLicense;
  StringChangeEx(Key, '\', '\\', True);
  StringChangeEx(Key, '"', '\"', True);
  ReuseJson := 'false';
  VerEsc := '';
  ReuseSetsJson := '[]';
  if ReuseModelsFound and (ChosenSets = SavedModelsSets) and
     (WizardSilent or (CompareText(RemoveBackslashUnlessRoot(Trim(ModelsPage.Values[0])), RemoveBackslashUnlessRoot(SavedModelsPath)) = 0)) then
  begin
    ReuseJson := 'true';
    ReuseSetsJson := Sets;
    VerEsc := SavedModelsVersion;
    StringChangeEx(VerEsc, '\', '\\', True);
    StringChangeEx(VerEsc, '"', '\"', True);
  end;
  ForceDirectories(DataDir);
  SaveStringToFile(DataDir + '\installer_choice.json',
    '{"model_sets": ' + Sets +
    ', "language": "' + UILang +
    '", "packs": ' + PacksJson +
    ', "humanizer_variant": "' + HumanizerVariant +
    '", "license_key": "' + Key +
    '", "reuse_models": ' + ReuseJson +
    ', "reuse_version": "' + VerEsc +
    '", "reuse_sets": ' + ReuseSetsJson + '}', False);
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
      if FreeMB < Cardinal(Round(TotalModelsGB(True) * 1024)) then
        if MsgBox(FmtMessage(CustomMessage('ModelsLow'), [FormatGB(TotalModelsGB(True))]), mbConfirmation, MB_YESNO) = IDYES then
          Result := False;
  end;
  // licence key page (first, right after the agreement): reuse, key (=confirm) or demo
  if (CurPageID = LicPage.ID) and (not LicDemoRadio.Checked) and (not LicReuseRadio.Checked)
     and (Trim(LicKeyEdit.Text) = '') then
  begin
    MsgBox(CustomMessage('LicNeedKey'), mbError, MB_OK);
    Result := False;
    Exit;
  end;
  // safety net: packs without a key are not downloaded — offer to clear pack checkboxes
  if (CurPageID = PacksPage.ID) and (not HasLicenseKey) and AnyPackSelected then
  begin
    if MsgBox(CustomMessage('LicWarnPacks'), mbConfirmation, MB_YESNO) = IDYES then
    begin
      PacksPage.Values[0] := False;
      PacksPage.Values[1] := False;
      PacksPage.Values[2] := False;
    end
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

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  CloseRunningLindaProcesses;
  Result := '';
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  Dir: String;
begin
  if CurStep = ssInstall then
    CloseRunningLindaProcesses;
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

// Data lives OUTSIDE the install folder (%LOCALAPPDATA%\Linda-Pro\ and the models
// folder chosen on the Models page), so [UninstallDelete] only removes {app}.
// Uninstall never silently deletes user data: keeping it is the default answer, and
// a new installation picks the same profile up again (including the licence key).
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Dir: String;
begin
  if (CurUninstallStep = usPostUninstall) and (not UninstallSilent) then
  begin
    if MsgBox(CustomMessage('UninstallKeep') + #13#10#13#10 + CustomMessage('UninstallKeepNote'), mbConfirmation, MB_YESNO or MB_DEFBUTTON1) = IDNO then
    begin
      Dir := SavedModelsDir;
      if Dir <> '' then
      begin
        DelTree(Dir + '\models', True, True, True);
        DelTree(Dir + '\onnx', True, True, True);
        DelTree(Dir + '\calibration', True, True, True);
        DelTree(Dir + '\staging', True, True, True);
        DelTree(Dir + '\packs', True, True, True);
        DeleteFile(Dir + '\manifest.json');
        DeleteFile(Dir + '\manifest.json.sig');
        RemoveDir(Dir);
      end;
      DelTree(DataDir, True, True, True);
    end;
  end;
end;
