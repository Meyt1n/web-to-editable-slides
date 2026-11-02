param(
 [Parameter(Mandatory=$true)][string]$InputPptx,
 [Parameter(Mandatory=$true)][string]$OutputDir,
 [int]$Width=1600,
 [string]$FontMap
)
# Export read-only; optional supplied fonts are session-only, never persistently installed.
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'powerpoint_session.ps1')
if($Width -lt 320 -or $Width -gt 7680){throw 'Width must be between 320 and 7680.'}
$taskInput=(Resolve-Path -LiteralPath $InputPptx).Path
$taskOutput=[System.IO.Path]::GetFullPath($OutputDir)
if(Test-Path -LiteralPath $taskOutput){throw 'Choose a new output directory.'}
[System.IO.Directory]::CreateDirectory($taskOutput) | Out-Null
$taskApp=$null
$taskDoc=$null
$taskFontFiles=@()
try {
 $taskFontFiles=@(Register-SlideFonts $FontMap)
 $taskApp=New-SlidePowerPoint
 $taskAlerts=$taskApp.DisplayAlerts
 $taskApp.DisplayAlerts=1
 $taskDoc=$taskApp.Presentations.Open($taskInput,-1,0,0)
 $taskHeight=[int][Math]::Round($Width*$taskDoc.PageSetup.SlideHeight/$taskDoc.PageSetup.SlideWidth)
 $taskPages=@()
 for($taskIndex=1;$taskIndex -le $taskDoc.Slides.Count;$taskIndex++){
  $taskSlide=$taskDoc.Slides.Item($taskIndex)
  $taskName=('{0:D2}.png' -f $taskIndex)
  $taskSlide.Export((Join-Path $taskOutput $taskName),'PNG',$Width,$taskHeight)
  $taskOverflow=@()
  foreach($taskShape in $taskSlide.Shapes){
   if($taskShape.HasTextFrame -and $taskShape.TextFrame.HasText){
    $taskRange=$taskShape.TextFrame2.TextRange
    if($taskRange.BoundHeight -gt $taskShape.Height+2 -or $taskRange.BoundWidth -gt $taskShape.Width+2){
     $taskOverflow+=@{shape=$taskShape.Name;text=$taskRange.Text;bounds=@($taskShape.Left,$taskShape.Top,$taskShape.Width,$taskShape.Height);text_width=$taskRange.BoundWidth;text_height=$taskRange.BoundHeight}
    }
   }
  }
  $taskPages+=@{index=$taskIndex;file=$taskName;shapes=$taskSlide.Shapes.Count;overflow_candidates=$taskOverflow}
 }
 $taskReport=@{renderer='Microsoft PowerPoint';version=$taskApp.Version;width=$Width;height=$taskHeight;slides=$taskPages;supplied_fonts=$taskFontFiles.Count;scope='Actual PPTX rendered; overflow candidates require visual review. No cross-application guarantee.'}
 $taskReport | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $taskOutput 'render-report.json') -Encoding utf8
 Write-Output ('Rendered '+$taskDoc.Slides.Count+' slides to '+$taskOutput)
} finally {
 try {
 if($null -ne $taskDoc){$taskDoc.Close();[void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($taskDoc)}
 if($null -ne $taskApp){
 $taskApp.DisplayAlerts=$taskAlerts
 if($taskApp.Presentations.Count -eq 0){$taskApp.Quit()}
 [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($taskApp)
 }
 } finally {Remove-SlideFonts $taskFontFiles}
}
