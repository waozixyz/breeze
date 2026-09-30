; inbe-setup.nsi — Inner Breeze Windows installer.
;
; Built by `make windows-setup` (see Makefile), which passes:
;   -DVERSION=<x.y.z> -DWIN64_EXE=<path> -DOUT=<path>
; Inner Breeze runs on 64-bit Windows only. /S silent installs work (winget
; relies on them).

!ifndef VERSION
!error "VERSION must be defined (-DVERSION=1.2.3)"
!endif
!ifndef WIN64_EXE
!error "WIN64_EXE must be defined"
!endif
!ifndef OUT
!error "OUT must be defined"
!endif

Unicode true
SetCompressor /SOLID lzma
Name "Inner Breeze"
OutFile "${OUT}"
InstallDir "$PROGRAMFILES64\Inner Breeze"
InstallDirRegKey HKLM "Software\Inner Breeze" "InstallDir"
RequestExecutionLevel admin

!include "MUI2.nsh"
!include "x64.nsh"

!define ARP "Software\Microsoft\Windows\CurrentVersion\Uninstall\Inner Breeze"

!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

Function .onInit
    ${IfNot} ${RunningX64}
        MessageBox MB_OK|MB_ICONSTOP "Inner Breeze requires 64-bit Windows." /SD IDOK
        Abort
    ${EndIf}
FunctionEnd

Section "Inner Breeze"
    SetOutPath "$INSTDIR"
    File "${WIN64_EXE}"

    Var /GLOBAL ExeName
    StrCpy $ExeName "inbe-windows-x86_64.exe"

    CreateDirectory "$SMPROGRAMS\Inner Breeze"
    CreateShortcut "$SMPROGRAMS\Inner Breeze\Inner Breeze.lnk" "$INSTDIR\$ExeName"
    CreateShortcut "$DESKTOP\Inner Breeze.lnk" "$INSTDIR\$ExeName"

    WriteRegStr HKLM "Software\Inner Breeze" "InstallDir" "$INSTDIR"
    WriteRegStr HKLM "${ARP}" "DisplayName" "Inner Breeze"
    WriteRegStr HKLM "${ARP}" "DisplayVersion" "${VERSION}"
    WriteRegStr HKLM "${ARP}" "DisplayIcon" "$INSTDIR\$ExeName"
    WriteRegStr HKLM "${ARP}" "UninstallString" '"$INSTDIR\uninstall.exe"'
    WriteRegDWORD HKLM "${ARP}" "NoModify" 1
    WriteRegDWORD HKLM "${ARP}" "NoRepair" 1
    WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd

Section "Uninstall"
    Delete "$INSTDIR\inbe-windows-x86_64.exe"
    ; Installs from before 64-bit only releases also carried this file.
    Delete "$INSTDIR\inbe-windows-i686.exe"
    Delete "$INSTDIR\uninstall.exe"
    Delete "$SMPROGRAMS\Inner Breeze\Inner Breeze.lnk"
    RMDir "$SMPROGRAMS\Inner Breeze"
    Delete "$DESKTOP\Inner Breeze.lnk"
    RMDir "$INSTDIR"
    DeleteRegKey HKLM "${ARP}"
    DeleteRegKey HKLM "Software\Inner Breeze"
SectionEnd
