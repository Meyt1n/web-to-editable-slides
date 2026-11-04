param(
 [Parameter(Mandatory=$true)][string]$InputPptx,
 [Parameter(Mandatory=$true)][string]$OutputVideo,
 [int]$SecondsPerSlide=6,
 [int]$TimeoutSeconds=240,
 [int]$FrameRate=12,
 [string]$FontMap
)
# Video preview preserves element animation; it is not proof of live click timing.
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'powerpoint_session.ps1')
$taskInput=(Resolve-Path -LiteralPath $InputPptx).Path
$taskOutput=[System.IO.Path]::GetFullPath($OutputVideo)
if(Test-Path -LiteralPath $taskOutput){throw 'Choose a new video output file.'}
if([System.IO.Path]::GetExtension($taskOutput) -ne '.mp4'){throw 'Output must be an MP4 file.'}
if($SecondsPerSlide -lt 1 -or $TimeoutSeconds -lt 10){throw 'Invalid video duration or timeout.'}
if($FrameRate -lt 1 -or $FrameRate -gt 60){throw 'FrameRate must be between 1 and 60.'}
[System.IO.Directory]::CreateDirectory([System.IO.Path]::GetDirectoryName($taskOutput)) | Out-Null
$taskApp=$null
$taskDoc=$null
$taskFontFiles=@()
try {
 $taskFontFiles=@(Register-SlideFonts $FontMap)
 $taskApp=New-SlidePowerPoint
 $taskDoc=$taskApp.Presentations.Open($taskInput,-1,0,0)
 $taskDoc.CreateVideo($taskOutput,-1,$SecondsPerSlide,720,$FrameRate,80)
 $taskDeadline=[DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
 do {
  Start-Sleep -Milliseconds 500
  $taskStatus=[int]$taskDoc.CreateVideoStatus
  if($taskStatus -eq 4){throw 'PowerPoint video creation failed.'}
  if([DateTime]::UtcNow -gt $taskDeadline){throw 'PowerPoint video creation timed out.'}
 } while($taskStatus -ne 3)
 if(-not (Test-Path -LiteralPath $taskOutput)){throw 'PowerPoint reported completion without an output file.'}
 Write-Output ('Exported animation video: '+$taskOutput)
} finally {
 try {
  if($null -ne $taskDoc){$taskDoc.Close();[void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($taskDoc)}
  if($null -ne $taskApp){
   if($taskApp.Presentations.Count -eq 0){$taskApp.Quit()}
   [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($taskApp)
  }
 } finally {Remove-SlideFonts $taskFontFiles}
}
