# PowerPoint can briefly reject COM activation while a preceding instance exits.
# Retry only transient activation errors; never kill user PowerPoint processes.
function New-SlidePowerPoint {
 for($taskAttempt=0;$taskAttempt -lt 4;$taskAttempt++){
  try {return New-Object -ComObject PowerPoint.Application}
  catch {
   if($taskAttempt -eq 3 -or $_.Exception.ToString() -notmatch '800706ba|80080005|8001010a'){throw}
   Start-Sleep -Milliseconds (750*($taskAttempt+1))
  }
 }
}

function Register-SlideFonts([string]$FontMap) {
 if(-not $FontMap){return}
 if(-not ('SlideSessionFonts' -as [type])){Add-Type -TypeDefinition @'
using System; using System.Runtime.InteropServices;
public static class SlideSessionFonts {
 [DllImport("gdi32.dll", CharSet=CharSet.Unicode)] public static extern int AddFontResourceEx(string file,uint flags,IntPtr reserved);
 [DllImport("gdi32.dll", CharSet=CharSet.Unicode)] public static extern bool RemoveFontResourceEx(string file,uint flags,IntPtr reserved);
 [DllImport("user32.dll", SetLastError=true)] private static extern IntPtr SendMessageTimeout(IntPtr hwnd,uint msg,UIntPtr wParam,IntPtr lParam,uint flags,uint timeout,out UIntPtr result);
 public static void Notify(){UIntPtr result; SendMessageTimeout(new IntPtr(0xffff),0x001D,UIntPtr.Zero,IntPtr.Zero,2,1000,out result);}
}
'@
 }
 $taskMapPath=(Resolve-Path -LiteralPath $FontMap).Path
 $taskFontMap=Get-Content -Raw -LiteralPath $taskMapPath | ConvertFrom-Json
 $taskLoaded=@()
 try {
  foreach($taskFont in $taskFontMap.PSObject.Properties.Value){
   $taskFontPath=(Resolve-Path -LiteralPath (Join-Path ([System.IO.Path]::GetDirectoryName($taskMapPath)) $taskFont)).Path
   if([SlideSessionFonts]::AddFontResourceEx($taskFontPath,0,[IntPtr]::Zero) -eq 0){throw ('Cannot load session font: '+$taskFontPath)}
   $taskLoaded+=,$taskFontPath
  }
  [SlideSessionFonts]::Notify()
 } catch {Remove-SlideFonts $taskLoaded;throw}
 Write-Host ('Temporarily loaded '+$taskLoaded.Count+' supplied font files; no persistent installation.')
 return $taskLoaded
}

function Remove-SlideFonts([string[]]$Files) {
 if(-not $Files -or $Files.Count -eq 0){return}
 $taskRemoved=0
 foreach($taskFontPath in $Files){
  if([SlideSessionFonts]::RemoveFontResourceEx($taskFontPath,0,[IntPtr]::Zero)){$taskRemoved++}
  else{Write-Warning ('Session font removal failed: '+$taskFontPath)}
 }
 [SlideSessionFonts]::Notify()
 Write-Host ('Removed '+$taskRemoved+' of '+$Files.Count+' temporary font registrations.')
}
