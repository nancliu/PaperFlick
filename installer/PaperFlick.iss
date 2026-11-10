; PaperFlick Windows installer (Inno Setup 6)
#define MyAppName        "PaperFlick（纸闪）"
#define MyAppVersion     "1.0.0"
#define MyAppPublisher   "nancliu"
#define MyAppURL         "https://github.com/nancliu/PaperFlick"
#define MyAppExeName     "PaperFlick.exe"
#define MyRepoRoot       ".."
#define MySourceDir      MyRepoRoot + "\dist\PaperFlick.dist"
#define MyOutputDir      MyRepoRoot + "\output"
#define MyIconPath       MyRepoRoot + "\icons\PaperFlick.ico"

[Setup]
AppId={{099E2B2A-3C82-485E-A3B3-724A2E72D6D3}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\PaperFlick
DefaultGroupName={#MyAppName}
DisableDirPage=no
DisableProgramGroupPage=no
PrivilegesRequired=admin
OutputDir={#MyOutputDir}
OutputBaseFilename=PaperFlick-Setup-1.0.0
WizardStyle=modern
SetupIconFile={#MyIconPath}
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "{#MySourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[UninstallDelete]
Type: filesandordirs; Name: "{app}\*"

[Icons]
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
