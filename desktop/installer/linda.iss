; Linda-Pro installer (Inno Setup 6). Per-user install: no administrator rights needed, installs to %LOCALAPPDATA%\Programs\Linda-Pro.
; Build:  tools\InnoSetup\ISCC.exe installer\linda.iss   (after tools\build_app.py)
; Silent update (used by the app itself):  Linda-Setup.exe /SILENT /SUPPRESSMSGBOXES /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS
#define AppName "Linda-Pro"
#ifndef AppVersion
  #define AppVersion "1.1.0"
#endif

[Setup]
AppId={{B6D1E7F4-5E1C-4B8E-9D2A-4C8F0A11D0A1}
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
RestartApplications=yes
UsePreviousAppDir=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"

[Files]
Source: "..\dist\Linda-Pro\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\Linda-Pro.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\Linda-Pro.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Linda-Pro.exe"; Description: "Start Linda-Pro"; Flags: nowait postinstall skipifsilent
; silent self-update of the app passes /RELAUNCH=1 so the new version starts by itself
Filename: "{app}\Linda-Pro.exe"; Flags: nowait; Check: ShouldRelaunch

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
function ShouldRelaunch: Boolean;
begin
  Result := ExpandConstant('{param:RELAUNCH|0}') = '1';
end;

// Models, settings and the licence are kept in %LOCALAPPDATA%\Linda-Pro. Ask before removing them on uninstall (2.9 GB).
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if (CurUninstallStep = usPostUninstall) and (not UninstallSilent) then
    if MsgBox('Also delete the downloaded models, settings and licence key (about 3 GB) from this computer?', mbConfirmation, MB_YESNO) = IDYES then
      DelTree(ExpandConstant('{localappdata}\Linda-Pro'), True, True, True);
end;
