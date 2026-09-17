; installer.iss
; ---------------------------------------------------------------------
; Instalador de Windows de verdad para Blackjack Pro (Fase 21) -- en vez
; de repartir solo el .exe "onefile" suelto (lo que hacia la Fase 11),
; esto genera un setup.exe con acceso directo en el menu inicio (y,
; opcionalmente, en el escritorio) y su propio desinstalador registrado
; en "Aplicaciones y caracteristicas".
;
; No requiere permisos de administrador (PrivilegesRequired=lowest): se
; instala en la carpeta de programas del propio usuario, no en
; Archivos de programa.
;
; IMPORTANTE: el instalador solo conoce el .exe que el mismo copia --
; nunca toca la carpeta saves\ (perfiles, historial, logros), que
; BlackjackPro.exe crea por su cuenta la primera vez que se abre, al
; lado de donde este el .exe (ver engine/profile_store.py). Por eso
; desinstalar el juego NUNCA borra las partidas guardadas: no estan en
; la lista de archivos que Inno Setup sabe que instalo.
;
; Requiere tener Inno Setup instalado (gratis): https://jrsoftware.org/isdl.php
; No se compila a mano: usa build_installer.bat, que genera antes el
; .exe con PyInstaller (si hace falta) y luego llama a ISCC.exe sobre
; este script.
; ---------------------------------------------------------------------

#define MyAppName "Blackjack Pro"
#define MyAppVersion "1.3.0"
#define MyAppPublisher "Maruku"
#define MyAppExeName "BlackjackPro.exe"

[Setup]
AppId={{4F1B8C2E-7A3D-4E5F-9B1C-2D6A8E4F0C7B}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppSupportURL=https://github.com/Marukunai/blackjack-pro
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=dist_installer
OutputBaseFilename=BlackjackPro_Setup
SetupIconFile=assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\BlackjackPro.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
