Unicode true
!include "MUI2.nsh"
!include "FileFunc.nsh"
Var ServerEndpoint
Var CaBundle
Var ConnectionArguments
Var ConnectionConfig
!ifndef APP
!error "APP wajib student atau admin"
!endif
!define PRODUCT "LabAccess-${APP}"
!define DIST "..\build\${APP}\entry_${APP}.dist"
Name "${PRODUCT} Pilot"
OutFile "..\dist\${PRODUCT}-Setup-0.1.0.exe"
InstallDir "$LOCALAPPDATA\Programs\${PRODUCT}"
RequestExecutionLevel user
SetCompressor /SOLID zlib
!insertmacro MUI_PAGE_LICENSE "..\docs\LICENSES.md"
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "Indonesian"

Function .onInit
  ; Direktori tetap per-user; /D tidak boleh mengarahkan uninstall ke folder sembarang.
  StrCpy $INSTDIR "$LOCALAPPDATA\Programs\${PRODUCT}"
  StrCpy $ConnectionConfig "$LOCALAPPDATA\LabAccess\connection-${APP}.ini"
  ReadINIStr $ServerEndpoint $ConnectionConfig "connection" "server"
  ReadINIStr $CaBundle $ConnectionConfig "connection" "ca"
  ${GetParameters} $0
  ClearErrors
  ; Delimiter spasi agar slash dalam https:// tidak dianggap opsi berikutnya.
  ${GetOptions} " $0" " /SERVER=" $1
  IfErrors +2
  StrCpy $ServerEndpoint $1
  ClearErrors
  ${GetOptions} " $0" " /CA=" $1
  IfErrors +2
  StrCpy $CaBundle $1
  StrCpy $ConnectionArguments ""
  StrCmp $ServerEndpoint "" +2
  StrCpy $ConnectionArguments '--server "$ServerEndpoint"'
  StrCmp $CaBundle "" +2
  StrCpy $ConnectionArguments '$ConnectionArguments --ca "$CaBundle"'
FunctionEnd

Section "Install"
  SetOutPath "$INSTDIR\app"
  File /r "${DIST}\*"
  SetOutPath "$INSTDIR"
  File "..\docs\LICENSES.md"
  File /r "..\third_party\licenses"
  FileOpen $0 "$INSTDIR\labaccess-${APP}.marker" w
  FileWrite $0 "LabAccess ${APP} 0.1.0"
  FileClose $0
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  CreateDirectory "$LOCALAPPDATA\LabAccess"
  WriteINIStr $ConnectionConfig "connection" "server" $ServerEndpoint
  WriteINIStr $ConnectionConfig "connection" "ca" $CaBundle
  CreateShortcut "$SMPROGRAMS\${PRODUCT}.lnk" "$INSTDIR\app\LabAccess-${APP}.exe" $ConnectionArguments
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT}" "DisplayName" "${PRODUCT} Pilot"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT}" "DisplayVersion" "0.1.0"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT}" "UninstallString" '$\"$INSTDIR\Uninstall.exe$\"'
SectionEnd

Section "Uninstall"
  GetFullPathName $0 "$LOCALAPPDATA\Programs\${PRODUCT}"
  GetFullPathName $1 "$INSTDIR"
  StrCmp $0 $1 0 unsafe
  IfFileExists "$INSTDIR\labaccess-${APP}.marker" 0 unsafe
  ; Target absolut diverifikasi; hanya subtree aplikasi milik installer ini.
  RMDir /r "$INSTDIR\app"
  RMDir /r "$INSTDIR\licenses"
  Delete "$INSTDIR\LICENSES.md"
  Delete "$INSTDIR\labaccess-${APP}.marker"
  Delete "$INSTDIR\Uninstall.exe"
  Delete "$SMPROGRAMS\${PRODUCT}.lnk"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT}"
  RMDir "$INSTDIR"
  ; DPAPI, database, model, user Windows dan data pekerjaan tidak disentuh.
  Goto done
unsafe:
  MessageBox MB_ICONSTOP "Lokasi uninstall tidak sesuai atau marker hilang. Tidak ada data dihapus."
  SetErrorLevel 1
done:
SectionEnd
