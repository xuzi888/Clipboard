[Setup]
AppName=剪贴板管理器
; 注意：这里的版本号会被 sync_version.py 脚本自动从 main.py 同步更新，请务必保留此行
AppVersion=1.1.1
AppPublisher=xuzi
AppPublisherURL=https://github.com/xuzi888/Clipboard
AppSupportURL=https://github.com/xuzi888/Clipboard
AppUpdatesURL=https://github.com/xuzi888/Clipboard
VersionInfoCompany=xuzi
VersionInfoDescription=剪贴板管理器安装程序
VersionInfoCopyright=Copyright (C) xuzi
DefaultDirName={autopf}\剪贴板管理器
DefaultGroupName=剪贴板管理器
UninstallDisplayIcon={app}\剪贴板管理器.exe
Compression=lzma2
SolidCompression=yes
OutputDir=D:\daima\kjj\clipboard_manager\dist
OutputBaseFilename=剪贴板管理器安装程序
SetupIconFile=D:\daima\kjj\clipboard_manager\assets\app_logo.ico
PrivilegesRequired=lowest
LanguageDetectionMethod=uilanguage

[Languages]
Name: "chinesesimp"; MessagesFile: "ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "D:\daima\kjj\clipboard_manager\dist\剪贴板管理器\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\剪贴板管理器"; Filename: "{app}\剪贴板管理器.exe"
Name: "{autodesktop}\剪贴板管理器"; Filename: "{app}\剪贴板管理器.exe"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "KjjClipboardManager"; ValueData: """{app}\剪贴板管理器.exe"""; Flags: uninsdeletevalue

[Run]
Filename: "{app}\剪贴板管理器.exe"; Description: "{cm:LaunchProgram,剪贴板管理器}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{app}\剪贴板管理器.exe"; Parameters: "--quit"; Flags: runhidden waituntilterminated skipifdoesntexist

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  MsgBoxResult: Integer;
begin
  if CurUninstallStep = usUninstall then
  begin
    MsgBoxResult := MsgBox(
      '【 数据清理确认 】' + #13#10 + #13#10 + 
      '是否要彻底删除所有的用户数据？' + #13#10 + 
      '（包含：剪贴板历史记录、快捷短语、个性化设置等）' + #13#10 + #13#10 + 
      '▶ 选择“是(Y)”：执行彻底卸载，清空所有数据' + #13#10 + 
      '▶ 选择“否(N)”：仅卸载程序，保留数据以便下次使用',
      mbConfirmation, MB_YESNO or MB_DEFBUTTON2);
      
    if MsgBoxResult = idYes then
    begin
      DelTree(ExpandConstant('{app}\images'), True, False, False);
      DeleteFile(ExpandConstant('{app}\data.json'));
      DeleteFile(ExpandConstant('{app}\config.json'));
      // 也删除可能的备份文件或日志文件
      DeleteFile(ExpandConstant('{app}\data_backup.json'));
      DeleteFile(ExpandConstant('{app}\*.log'));
    end;
  end;
end;
