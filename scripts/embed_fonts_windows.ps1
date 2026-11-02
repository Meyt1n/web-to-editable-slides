param(
 [Parameter(Mandatory=$true)][string]$InputPptx,
 [Parameter(Mandatory=$true)][string]$OutputPptx,
 [string]$FontMap
)
# Uses PowerPoint. Optional -FontMap registers supplied fonts temporarily; no persistent installation.
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'powerpoint_session.ps1')
$taskInput=(Resolve-Path -LiteralPath $InputPptx).Path
$taskOutput=[System.IO.Path]::GetFullPath($OutputPptx)
if($taskInput -eq $taskOutput){throw 'Choose a different output file.'}
if(Test-Path -LiteralPath $taskOutput){throw 'Output exists; choose a new file.'}
[System.IO.Directory]::CreateDirectory([System.IO.Path]::GetDirectoryName($taskOutput)) | Out-Null
$taskFontFiles=@()
$taskApp=$null
$taskDoc=$null
try {
 $taskFontFiles=@(Register-SlideFonts $FontMap)
 $taskApp=New-SlidePowerPoint
 $taskAlerts=$taskApp.DisplayAlerts
 $taskApp.DisplayAlerts=1
 $taskDoc=$taskApp.Presentations.Open($taskInput,$false,$false,$false)
 $taskDoc.SaveAs($taskOutput,24,-1)
 Write-Output ('Saved '+$taskDoc.Slides.Count+' slides with PowerPoint font embedding requested.')
 Write-Output 'Inspect font declarations and render the result. Compressed EOT may be structurally unverified even when PowerPoint wrote it.'
} finally {
 try {
 if($null -ne $taskDoc){$taskDoc.Close();[void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($taskDoc)}
 if($null -ne $taskApp){
  $taskApp.DisplayAlerts=$taskAlerts
  if($taskApp.Presentations.Count -eq 0){$taskApp.Quit()}
  [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($taskApp)
 }
 } finally {
  Remove-SlideFonts $taskFontFiles
 }
}
