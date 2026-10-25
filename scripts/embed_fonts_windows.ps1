param(
 [Parameter(Mandatory=$true)][string]$InputPptx,
 [Parameter(Mandatory=$true)][string]$OutputPptx
)
# Uses an existing PowerPoint installation. This script does not install fonts.
$ErrorActionPreference='Stop'
$taskInput=(Resolve-Path -LiteralPath $InputPptx).Path
$taskOutput=[System.IO.Path]::GetFullPath($OutputPptx)
if($taskInput -eq $taskOutput){throw 'Choose a different output file.'}
if(Test-Path -LiteralPath $taskOutput){throw 'Output exists; choose a new file.'}
[System.IO.Directory]::CreateDirectory([System.IO.Path]::GetDirectoryName($taskOutput)) | Out-Null
$taskApp=New-Object -ComObject PowerPoint.Application
$taskDoc=$null
$taskAlerts=$taskApp.DisplayAlerts
try {
 $taskApp.DisplayAlerts=1
 $taskDoc=$taskApp.Presentations.Open($taskInput,$false,$false,$false)
 $taskDoc.SaveAs($taskOutput,24,-1)
 Write-Output ('Saved '+$taskDoc.Slides.Count+' slides with PowerPoint font embedding requested.')
 Write-Output 'Run check_pptx.py --require-fonts and render the result before claiming success.'
} finally {
 if($null -ne $taskDoc){$taskDoc.Close();[void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($taskDoc)}
 $taskApp.DisplayAlerts=$taskAlerts
 if($taskApp.Presentations.Count -eq 0){$taskApp.Quit()}
 [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($taskApp)
}
