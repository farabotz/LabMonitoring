param([Parameter(Mandatory=$true)][int]$ProcessId, [int]$Seconds=60, [Parameter(Mandatory=$true)][string]$OutputCsv)
$ErrorActionPreference='Stop'
$samples=@()
$previous=Get-Process -Id $ProcessId
$previousCpu=$previous.CPU
$last=[DateTime]::UtcNow
for ($i=0; $i -lt $Seconds; $i++) {
    Start-Sleep -Seconds 1
    $process=Get-Process -Id $ProcessId
    $at=[DateTime]::UtcNow
    $cpu=100*($process.CPU-$previousCpu)/($at-$last).TotalSeconds/[Environment]::ProcessorCount
    $samples += [pscustomobject]@{timestamp_utc=$at.ToString('o');process_id=$ProcessId;cpu_percent_total_machine=$cpu;rss_mb=$process.WorkingSet64/1MB}
    $previousCpu=$process.CPU
    $last=$at
}
$samples | Export-Csv -LiteralPath $OutputCsv -NoTypeInformation -Encoding utf8
