$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$literature = Join-Path $root 'literature'

$inputs = @(
  (Join-Path $literature 'papers_arxiv.jsonl'),
  (Join-Path $literature 'papers.jsonl'),
  'E:\Github\MatrAIx\personas\literature\papers.jsonl'
)

$records = @{}

foreach ($path in $inputs) {
  if (-not (Test-Path $path)) { continue }
  foreach ($line in Get-Content $path) {
    if (-not $line.Trim()) { continue }
    $entry = $line | ConvertFrom-Json
    $doi = $entry.doi
    $arxiv = $entry.arxiv_id
    if ($arxiv) {
      $arxiv = ($arxiv -replace '^https?://arxiv.org/abs/', '') -replace 'v\d+$', ''
      $entry.arxiv_id = $arxiv
      $entry.url = "https://arxiv.org/abs/$arxiv"
      $entry.pdf_url = "https://arxiv.org/pdf/$arxiv"
    }
    $titleKey = (($entry.title -as [string]).ToLower() -replace '[^a-z0-9]+', ' ').Trim()
    $key = if ($doi) {
      "doi:$($doi.ToLower())"
    } elseif ($arxiv) {
      "arxiv:$($arxiv.ToLower())"
    } else {
      "title:$titleKey"
    }

    if (-not $records.ContainsKey($key)) {
      $entry.id = $key
      $records[$key] = $entry
    } else {
      $existing = $records[$key]
      $existing.discovered_by = @($existing.discovered_by + $entry.discovered_by | Where-Object { $_ } | Select-Object -Unique)
      $existing.categories = @($existing.categories + $entry.categories | Where-Object { $_ } | Select-Object -Unique)
      if (-not $existing.abstract -and $entry.abstract) { $existing.abstract = $entry.abstract }
      if (-not $existing.doi -and $entry.doi) { $existing.doi = $entry.doi }
      if (-not $existing.semantic_scholar_id -and $entry.semantic_scholar_id) { $existing.semantic_scholar_id = $entry.semantic_scholar_id }
      if (-not $existing.citation_count -and $entry.citation_count) { $existing.citation_count = $entry.citation_count }
    }
  }
}

$selected = @(
  $records.Values |
    Sort-Object @{Expression = { if ($_.coding.relevance_score) { [int]$_.coding.relevance_score } else { 0 } }; Descending = $true },
                @{Expression = { if ($_.year) { [int]$_.year } else { 0 } }; Descending = $true } |
    Select-Object -First 100
)

$jsonlPath = Join-Path $literature 'papers_merged_top100.jsonl'
if (Test-Path $jsonlPath) { Remove-Item -LiteralPath $jsonlPath }
foreach ($entry in $selected) {
  ($entry | ConvertTo-Json -Depth 10 -Compress) | Add-Content -Path $jsonlPath -Encoding UTF8
}

$csvRows = foreach ($entry in $selected) {
  [pscustomobject]@{
    id = $entry.id
    title = $entry.title
    year = $entry.year
    authors = (@($entry.authors) -join '; ')
    venue = $entry.venue
    doi = $entry.doi
    arxiv_id = $entry.arxiv_id
    url = $entry.url
    citation_count = $entry.citation_count
    status = $entry.status
    relevance_score = $entry.coding.relevance_score
    discovered_by = (@($entry.discovered_by) -join ' | ')
  }
}
$csvPath = Join-Path $literature 'papers_merged_top100.csv'
$csvRows | Export-Csv -NoTypeInformation -Encoding UTF8 -Path $csvPath

$bibPath = Join-Path $root 'references.bib'
$bib = @()
foreach ($entry in $selected) {
  $authorText = if ($entry.authors) { (@($entry.authors) -join ' and ') } else { 'Unknown' }
  $baseKey = if ($entry.arxiv_id) {
    'arxiv' + (($entry.arxiv_id -replace '[^0-9]', '') | Select-Object -First 1)
  } else {
    (($entry.title -replace '[^A-Za-z0-9 ]', '').Split(' ') | Where-Object { $_ } | Select-Object -First 3) -join ''
  }
  if (-not $baseKey) { $baseKey = 'paper' }
  $key = $baseKey
  $i = 2
  while ($bib -match "@.*\{$key,") {
    $key = "$baseKey$i"
    $i++
  }
  $bib += "@misc{$key,"
  $bib += "  title = {$($entry.title)},"
  $bib += "  author = {$authorText},"
  if ($entry.year) { $bib += "  year = {$($entry.year)}," }
  if ($entry.arxiv_id) { $bib += "  eprint = {$($entry.arxiv_id)}," }
  if ($entry.doi) { $bib += "  doi = {$($entry.doi)}," }
  if ($entry.url) { $bib += "  url = {$($entry.url)}," }
  $bib += "}"
  $bib += ""
}
$bib | Set-Content -Encoding UTF8 -Path $bibPath

$summaryPath = Join-Path $literature 'corpus_summary.md'
$summary = @(
  '# Literature Corpus Summary',
  '',
  "Merged records available before top-100 trim: $($records.Count)",
  "Records retained in top-100 screening corpus: $($selected.Count)",
  '',
  'Primary files:',
  '- `papers_merged_top100.jsonl`: canonical flexible metadata and coding file.',
  '- `papers_merged_top100.csv`: spreadsheet-friendly screening file.',
  '- `../references.bib`: generated BibTeX starter bibliography.',
  '',
  'Notes:',
  '- Records are candidates for screening, not final inclusion decisions.',
  '- `coding` fields are intentionally nullable so a writing agent can add extraction metadata paper by paper.',
  '- Search logs are preserved in `search_log.md` and `search_log_arxiv.md`.'
)
$summary | Set-Content -Encoding UTF8 -Path $summaryPath

Write-Output "Merged $($records.Count) records; wrote top $($selected.Count) to $jsonlPath"
