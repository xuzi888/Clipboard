; *** Inno Setup version 6.1.0+ Chinese (Simplified) messages ***
;
; Maintained by:
;   KngStr (KngStr@gmail.com)
;   W.X. (wx042@126.com)
;
; History:
;   2021-08-01: Update for Inno Setup 6.1.0+
;   2020-05-18: Update for Inno Setup 6.0.5+

[LangOptions]
LanguageName=Simplified Chinese
LanguageID=$0804
LanguageCodePage=936

[Messages]
; *** Application titles
SetupAppTitle=安装程序
SetupWindowTitle=安装 - %1
UninstallAppTitle=卸载
UninstallAppFullTitle=%1 卸载

; *** Misc. common
InformationTitle=信息
ConfirmTitle=确认
ErrorTitle=错误

; *** SetupLdr messages
SetupLdrStartupMessage=现在将安装 %1。是否继续？
LdrCannotCreateTemp=无法创建临时文件。安装已中止
LdrCannotExecTemp=无法在临时目录中执行文件。安装已中止
HelpTextNote=

; *** Startup error messages
LastErrorMessage=%1.%n%n错误 %2: %3
SetupFileMissing=安装目录中缺失文件 %1。请更正此问题或获取新的程序副本。
SetupFileCorrupt=安装文件已损坏。请获取新的程序副本。
SetupFileCorruptOrWrongVer=安装文件已损坏，或是与此版本的安装程序不兼容。请更正此问题或获取新的程序副本。
InvalidParameter=向命令行传递了无效参数：%n%n%1
SetupAlreadyRunning=安装程序已在运行。
WindowsVersionNotSupported=此程序不支持您正在运行的 Windows 版本。
WindowsServicePackRequired=此程序需要 %1 Service Pack %2 或更高版本。
NotOnThisPlatform=此程序无法在 %1 下运行。
OnlyOnThisPlatform=此程序只能在 %1 下运行。
OnlyOnTheseArchitectures=此程序只能在为以下处理器架构设计的 Windows 版本上安装：%n%n%1
WinVersionTooLowError=此程序需要 %1 版本 %2 或更高。
WinVersionTooHighError=此程序无法在 %1 版本 %2 或更高上安装。
AdminPrivilegesRequired=在安装此程序时您必须以管理员身份登录。
PowerUserPrivilegesRequired=在安装此程序时您必须以管理员身份或是具有高级用户权限的组的成员登录。
SetupAppRunningError=安装程序检测到 %1 正在运行。%n%n请现在关闭它的所有实例，然后单击“确定”继续，或单击“取消”退出。
UninstallAppRunningError=卸载程序检测到 %1 正在运行。%n%n请现在关闭它的所有实例，然后单击“确定”继续，或单击“取消”退出。

; *** Startup questions
PrivilegesRequiredOverrideTitle=选择安装模式
PrivilegesRequiredOverrideInstruction=选择安装模式
PrivilegesRequiredOverrideText1=%1 支持为所有用户安装（需要管理员权限），或仅为您自己安装。
PrivilegesRequiredOverrideText2=%1 支持仅为您自己安装，或为所有用户安装（需要管理员权限）。
PrivilegesRequiredOverrideAllUsers=为所有用户安装(&A)
PrivilegesRequiredOverrideAllUsersRecommended=为所有用户安装(&A) (推荐)
PrivilegesRequiredOverrideCurrentUser=仅为我安装(&M)
PrivilegesRequiredOverrideCurrentUserRecommended=仅为我安装(&M) (推荐)

; *** Misc. errors
ErrorCreatingDir=安装程序无法创建目录“%1”
ErrorTooManyFilesInDir=无法在目录“%1”中创建文件，因为其中的文件太多

; *** Setup common
ExitSetupTitle=退出安装程序
ExitSetupMessage=安装尚未完成。如果您现在退出，程序将不会被安装。%n%n您可以稍后再次运行安装程序来完成安装。%n%n退出安装程序吗？
AboutSetupMenuItem=关于安装程序(&A)...
AboutSetupTitle=关于安装程序
AboutSetupMessage=%1 版本 %2%n%3%n%n%1 主页：%n%4
AboutSetupNote=
TranslatorNote=

; *** Buttons
ButtonBack=< 上一步(&B)
ButtonNext=下一步(&N) >
ButtonInstall=安装(&I)
ButtonOK=确定
ButtonCancel=取消
ButtonYes=是(&Y)
ButtonYesToAll=全是(&A)
ButtonNo=否(&N)
ButtonNoToAll=全否(&O)
ButtonFinish=完成(&F)
ButtonBrowse=浏览(&B)...
ButtonWizardBrowse=浏览(&B)...
ButtonWizard=向导(&W)
ButtonNewFolder=新建文件夹(&M)

; *** "Select Language" dialog messages
SelectLanguageTitle=选择安装语言
SelectLanguageLabel=请选择在安装期间使用的语言。

; *** Common wizard text
ClickNext=单击“下一步”继续，或单击“取消”退出安装程序。
BeveledLabel=
BrowseDialogTitle=浏览文件夹
BrowseDialogLabel=在下面的列表中选择目标文件夹，然后单击“确定”。
NewFolderName=新建文件夹

; *** "Welcome" wizard page
WelcomeLabel1=欢迎使用 [name] 安装向导
WelcomeLabel2=现在将安装 [name/ver] 到您的电脑中。%n%n推荐您在继续安装前关闭所有其它应用程序。

; *** "Password" wizard page
WizardPassword=密码
PasswordLabel1=此安装受密码保护。
PasswordLabel3=请提供密码，然后单击“下一步”继续。密码区分大小写。
PasswordEditLabel=密码(&P)：
IncorrectPassword=您输入的密码不正确。请重试。

; *** "License Agreement" wizard page
WizardLicense=许可协议
LicenseLabel=在继续之前请阅读以下重要信息。
LicenseLabel3=请仔细阅读以下许可协议。在继续安装前，您必须同意这些协议条款。
LicenseAccepted=我同意此协议(&A)
LicenseNotAccepted=我拒绝此协议(&D)

; *** "Information" wizard pages
WizardInfoBefore=信息
InfoBeforeLabel=在继续之前请阅读以下重要信息。
InfoBeforeClickLabel=当您准备好继续安装时，单击“下一步”。
WizardInfoAfter=信息
InfoAfterLabel=在继续之前请阅读以下重要信息。
InfoAfterClickLabel=当您准备好继续安装时，单击“下一步”。

; *** "User Information" wizard page
WizardUserInfo=用户信息
UserInfoDesc=请输入您的信息。
UserInfoName=用户名(&U)：
UserInfoOrg=组织(&O)：
UserInfoSerial=序列号(&S)：
UserInfoNameRequired=您必须输入名字。

; *** "Select Destination Location" wizard page
WizardSelectDir=选择目标位置
SelectDirDesc=您想将 [name] 安装在什么地方？
SelectDirLabel3=安装程序将安装 [name] 到以下文件夹中。
SelectDirBrowseLabel=单击“下一步”继续。如果您想选择其它文件夹，单击“浏览”。
DiskSpaceMBLabel=至少需要有 [mb] MB 的可用磁盘空间。
CannotInstallToNetworkDrive=无法安装到网络驱动器。
CannotInstallToUNCPath=无法安装到 UNC 路径。
InvalidPath=您必须输入含驱动器盘符的完整路径，例如：%n%nC:\APP%n%n或 UNC 路径，例如：%n%n\\server\share
InvalidDrive=您选择的驱动器或 UNC 共享不存在或无法访问。请选择其它位置。
DiskSpaceWarningTitle=磁盘空间不足
DiskSpaceWarning=安装程序至少需要 %1 KB 可用磁盘空间才能安装，但选定驱动器上只有 %2 KB 可用空间。%n%n您仍要继续吗？
DirNameTooLong=文件夹名称或路径太长。
InvalidDirName=文件夹名称无效。
BadDirName32=文件夹名称不能包含以下任何字符：%n%n%1
DirExistsTitle=文件夹已存在
DirExists=文件夹：%n%n%1%n%n已存在。您仍想安装到该文件夹中吗？
DirDoesntExistTitle=文件夹不存在
DirDoesntExist=文件夹：%n%n%1%n%n不存在。您想要创建此文件夹吗？

; *** "Select Components" wizard page
WizardSelectComponents=选择组件
SelectComponentsDesc=您想安装哪些组件？
SelectComponentsLabel2=选择您想要安装的组件；清除您不想安装的组件。当您准备好继续时，单击“下一步”。
FullInstallation=完全安装
CompactInstallation=精简安装
CustomInstallation=自定义安装
NoUninstallWarningTitle=组件存在
NoUninstallWarning=安装程序检测到以下组件已在您的电脑中安装：%n%n%1%n%n取消选择这些组件将不会卸载它们。%n%n您仍要继续吗？
ComponentSize1=%1 KB
ComponentSize2=%1 MB
ComponentsDiskSpaceMBLabel=当前选择至少需要 [mb] MB 的可用磁盘空间。

; *** "Select Additional Tasks" wizard page
WizardSelectTasks=选择附加任务
SelectTasksDesc=您想执行哪些附加任务？
SelectTasksLabel2=选择您想在安装 [name] 时执行的附加任务，然后单击“下一步”。

; *** "Select Start Menu Folder" wizard page
WizardSelectProgramGroup=选择开始菜单文件夹
SelectStartMenuFolderDesc=您想在哪里放置程序的快捷方式？
SelectStartMenuFolderLabel3=安装程序将在以下开始菜单文件夹中创建程序的快捷方式。
SelectStartMenuFolderBrowseLabel=单击“下一步”继续。如果您想选择其它文件夹，单击“浏览”。
MustEnterGroupName=您必须输入文件夹名称。
GroupNameTooLong=文件夹名称或路径太长。
InvalidGroupName=文件夹名称无效。
BadGroupName=文件夹名称不能包含以下任何字符：%n%n%1
NoProgramGroupCheck2=不创建开始菜单文件夹(&D)

; *** "Ready to Install" wizard page
WizardReady=准备安装
ReadyLabel1=安装程序已准备好在您的电脑中安装 [name]。
ReadyLabel2a=单击“安装”继续安装，或者如果您想要回顾或更改任何设置，请单击“上一步”。
ReadyLabel2b=单击“安装”继续安装。
ReadyMemoUserInfo=用户信息：
ReadyMemoDir=目标位置：
ReadyMemoType=安装类型：
ReadyMemoComponents=选定组件：
ReadyMemoGroup=开始菜单文件夹：
ReadyMemoTasks=附加任务：

; *** "Preparing to Install" wizard page
WizardPreparing=正在准备安装
PreparingDesc=安装程序正在准备在您的电脑中安装 [name]。
PreviousInstallNotCompleted=前一次安装/卸载未完成。您需要重新启动电脑才能完成那次安装。%n%n重启电脑后，再次运行安装程序来完成 [name] 的安装。
CannotContinue=安装无法继续。请单击“取消”退出。
ApplicationsFound=以下应用程序正在使用需要由安装程序更新的文件。建议您允许安装程序自动关闭这些应用程序。
ApplicationsFound2=以下应用程序正在使用需要由安装程序更新的文件。建议您允许安装程序自动关闭这些应用程序。安装完成后，安装程序将尝试重启这些应用程序。
CloseApplications=自动关闭应用程序(&A)
DontCloseApplications=不关闭应用程序(&D)
ErrorCloseApplications=安装程序无法自动关闭所有应用程序。建议您在继续前手动关闭所有使用需更新文件的应用程序。

; *** "Installing" wizard page
WizardInstalling=正在安装
InstallingLabel=请稍候，安装程序正在您的电脑中安装 [name]。

; *** "Setup Completed" wizard page
FinishedHeadingLabel=完成 [name] 安装向导
FinishedLabelNoIcons=安装程序已在您的电脑中安装了 [name]。
FinishedLabel=安装程序已在您的电脑中安装了 [name]。您可以通过选择已安装的快捷方式来启动应用程序。
ClickFinish=单击“完成”退出安装程序。
FinishedRestartLabel=为完成 [name] 的安装，安装程序必须重新启动您的电脑。您想现在就重启吗？
FinishedRestartMessage=为完成 [name] 的安装，安装程序必须重新启动您的电脑。%n%n您想现在就重启吗？
ShowReadmeCheck=是，我想查看自述文件
YesRadio=是，现在重新启动电脑(&Y)
NoRadio=否，我将稍后重新启动电脑(&N)
; used for example as 'Run MyProg.exe'
RunEntryExec=运行 %1
; used for example as 'View Readme.txt'
RunEntryShellExec=查看 %1

; *** "Setup Needs the Next Disk" stuff
SetupNeedsDisk=安装程序需要下一张磁盘
NeedDiskPage1=请插入磁盘 %1 并单击“确定”。
NeedDiskPage2=如果您要找的文件不在该磁盘中，或者是位于不是下边所示的其它文件夹中，请输入正确路径或单击“浏览”。
PathTitle=路径(&P)：
ErrorFileTitle=文件未找到
ErrorFilename=%1 不存在。
ErrorFilename2=由于缺少包含这些文件的安装包，该文件未能找到：%n%n%1%n%n请插入正确的磁盘或选择正确的文件夹。
ErrorFilename3=由于缺少包含这些文件的安装包，该文件未能找到：%n%n%1%n%n请确认所有的安装包在相同的文件夹里，或者取消安装。
ErrorDiskTitle=插入的磁盘不正确
ErrorDiskMessage=该文件未能在这张磁盘中找到。请插入对应的磁盘或选择正确的文件夹。%n%n请插入磁盘 %1。

; *** Installation phase messages
; Not actually used, just for compatibility
ErrorReadingData=读取文件出错：
ErrorReadingData2=读取文件出错：
ErrorWritingData=写入文件出错：
ErrorCreatingPipe=创建管道出错。
ErrorReadingPipe=读取管道出错。
ErrorWritingPipe=写入管道出错。

; *** Uninstallation phase messages
UninstallNotFound=文件“%1”不存在。无法卸载。
UninstallOpenError=文件“%1”无法打开。无法卸载。
UninstallUnsupportedVer=该卸载记录文件的格式无法识别，此版本卸载程序无法处理。无法卸载。
UninstallUnknownEntry=在卸载记录中遇到未知的条目 (%1)。
ConfirmUninstall=您确实要完全移除 %1 及其所有组件吗？
UninstallOnlyOnWin64=此程序只能在 64 位 Windows 下卸载。
OnlyAdminCanUninstall=该安装只能被具有管理员权限的用户卸载。
UninstallStatusLabel=请稍候，正从您的电脑中移除 %1。
UninstalledAll=%1 已成功从您的电脑中移除。
UninstalledMost=%1 卸载完成。%n%n某些元素无法被移除。您可以手动删除它们。
UninstalledAndNeedsRestart=为完成 %1 的卸载，您的电脑必须重新启动。%n%n您想现在就重启吗？
UninstallDataCorrupted="%1" 文件已损坏。无法卸载。

; *** Uninstallation phase messages
ConfirmDeleteSharedFileTitle=移除共享文件吗？
ConfirmDeleteSharedFile2=系统中存在一些共享文件，似乎已不再被任何程序使用。您想让卸载程序移除这些共享文件吗？%n%n如果任何程序仍在使用这些文件，并且它们被移除，那些程序可能无法正常运行。如果您不确定，选择“否”。将这些文件保留在系统中不会造成任何危害。
SharedFileNameLabel=文件名：
SharedFileLocationLabel=位置：
WizardUninstalling=卸载状态
StatusUninstalling=正在卸载 %1...

; *** Shutdown custom messages
ShutdownBlockReasonInstallingApp=正在安装 %1。
ShutdownBlockReasonUninstallingApp=正在卸载 %1。

; *** Status messages
StatusClosingApplications=正在关闭应用程序...
StatusCreateDirs=正在创建目录...
StatusExtractFiles=正在解压文件...
StatusCreateIcons=正在创建快捷方式...
StatusCreateIniEntries=正在创建 INI 条目...
StatusCreateRegistryEntries=正在创建注册表条目...
StatusRegisterFiles=正在注册文件...
StatusSavingUninstall=正在保存卸载信息...
StatusRunProgram=正在完成安装...
StatusRestartingApplications=正在重启应用程序...
StatusRollback=正在回滚更改...

; *** Misc. errors
ErrorInternal2=内部错误：%1
ErrorFunctionFailedNoCode=%1 失败
ErrorFunctionFailed=%1 失败；代码 %2
ErrorFunctionFailedWithMessage=%1 失败；代码 %2。%n%3
ErrorExecutingProgram=无法执行文件：%n%1

; *** Registry errors
ErrorRegOpenKey=打开注册表键出错：%n%1\%2
ErrorRegCreateKey=创建注册表键出错：%n%1\%2
ErrorRegWriteKey=写入注册表键出错：%n%1\%2

; *** INI errors
ErrorIniEntry=在文件“%1”中创建 INI 条目出错。

; *** File copying errors
FileAbortRetryIgnoreSkipNotRecommended=跳过此文件(&S) (不推荐)
FileAbortRetryIgnoreIgnoreNotRecommended=忽略此错误(&I) (不推荐)
SourceIsCorrupted=源文件已损坏
SourceDoesntExist=源文件“%1”不存在
ExistingFileReadOnly2=无法替换现有的文件，因为其被标记为只读。
ExistingFileReadOnlyRetry=移除只读属性并重试(&R)
ExistingFileReadOnlyKeepExisting=保留现有文件(&K)
ErrorReadingExistingDest=尝试读取现有文件出错：
FileExists=文件已存在。%n%n您想让安装程序覆盖它吗？
ExistingFileNewer=现有的文件比安装程序尝试安装的文件更新。建议您保留现有文件。%n%n您想保留现有文件吗？
ErrorChangingAttr=尝试改变现有文件属性出错：
ErrorCreatingTemp=尝试在目标目录创建文件出错：
ErrorReadingSource=尝试读取源文件出错：
ErrorCopying=尝试复制文件出错：
ErrorReplacingExistingFile=尝试替换现有文件出错：
ErrorRestartReplace=RestartReplace 失败：
ErrorRenamingTemp=尝试重命名目标目录中的文件出错：
ErrorRegisterServer=无法注册 DLL/OCX：%1
ErrorRegSvr32Failed=RegSvr32 失败并返回退出代码 %1
ErrorRegisterTypeLib=无法注册类型库：%1

; *** Post-installation errors
ErrorOpeningReadme=尝试打开自述文件出错。
ErrorRestartingComputer=安装程序无法重启电脑。请手动重启。

; *** Uninstaller messages
UninstallNotFound=文件“%1”不存在。无法卸载。
UninstallOpenError=文件“%1”无法打开。无法卸载。
UninstallUnsupportedVer=该卸载记录文件的格式无法识别，此版本卸载程序无法处理。无法卸载。
UninstallUnknownEntry=在卸载记录中遇到未知的条目 (%1)。
ConfirmUninstall=您确实要完全移除 %1 及其所有组件吗？
UninstallOnlyOnWin64=此程序只能在 64 位 Windows 下卸载。
OnlyAdminCanUninstall=该安装只能被具有管理员权限的用户卸载。
UninstallStatusLabel=请稍候，正从您的电脑中移除 %1。
UninstalledAll=%1 已成功从您的电脑中移除。
UninstalledMost=%1 卸载完成。%n%n某些元素无法被移除。您可以手动删除它们。
UninstalledAndNeedsRestart=为完成 %1 的卸载，您的电脑必须重新启动。%n%n您想现在就重启吗？
UninstallDataCorrupted="%1" 文件已损坏。无法卸载。

; *** Uninstallation phase messages
ConfirmDeleteSharedFileTitle=移除共享文件吗？
ConfirmDeleteSharedFile2=系统中存在一些共享文件，似乎已不再被任何程序使用。您想让卸载程序移除这些共享文件吗？%n%n如果任何程序仍在使用这些文件，并且它们被移除，那些程序可能无法正常运行。如果您不确定，选择“否”。将这些文件保留在系统中不会造成任何危害。
SharedFileNameLabel=文件名：
SharedFileLocationLabel=位置：
WizardUninstalling=卸载状态
StatusUninstalling=正在卸载 %1...

; *** Shutdown custom messages
ShutdownBlockReasonInstallingApp=正在安装 %1。
ShutdownBlockReasonUninstallingApp=正在卸载 %1。

; The custom messages below aren't used by Setup itself, but if you make
; use of them in your scripts, you'll want to translate them.

[CustomMessages]

NameAndVersion=%1 版本 %2
AdditionalIcons=附加快捷方式：
CreateDesktopIcon=创建桌面快捷方式(&D)
CreateQuickLaunchIcon=创建快速启动栏快捷方式(&Q)
ProgramOnTheWeb=%1 网站
UninstallProgram=卸载 %1
LaunchProgram=运行 %1
AssocFileExtension=将 %1 与 %2 文件扩展名关联(&A)
AssocingFileExtension=正在将 %1 与 %2 文件扩展名关联...
AutoStartProgramGroupDescription=启动：
AutoStartProgram=在 Windows 启动时自动运行 %1
AddonHostProgramNotFound=未在您选择的文件夹中找到 %1。%n%n您仍要继续吗？

