$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$queries = @(
  'all:"synthetic persona"',
  'all:"persona generation"',
  'all:"large language model" AND all:persona',
  'all:"LLM" AND all:persona',
  'all:"synthetic respondent"',
  'all:"virtual survey respondent"',
  'all:"silicon sampling"',
  'all:"role-playing" AND all:"language agent"',
  'all:"role playing" AND all:"large language model"',
  'all:"social simulation" AND all:"large language model"',
  'all:"generative agents"',
  'all:"user simulation" AND all:"large language model"',
  'all:"population synthesis" AND all:"agent-based"',
  'all:"statistical matching" AND all:"data fusion"'
)

$root = Split-Path -Parent $PSScriptRoot
$literature = Join-Path $root 'literature'
New-Item -ItemType Directory -Force -Path $literature | Out-Null

$results = @{}
$searchLog = @()

foreach ($query in $queries) {
  $encoded = [System.Uri]::EscapeDataString($query)
  $uri = "https://export.arxiv.org/api/query?search_query=$encoded&start=0&max_results=30&sortBy=relevance&sortOrder=descending"
  try {
    $entries = @(Invoke-RestMethod -Uri $uri -TimeoutSec 30)
    $searchLog += [pscustomobject]@{
      query = $query
      source = 'arXiv API'
      retrieved = $entries.Count
      timestamp = (Get-Date).ToString('s')
    }

    foreach ($entry in $entries) {
      if (-not $entry.title) { continue }
      $id = (($entry.id -as [string]) -replace '^https?://arxiv.org/abs/', '') -replace 'v\d+$', ''
      $authors = @()
      if ($entry.author) {
        $authors = @($entry.author | ForEach-Object { $_.name })
      }
      $key = "arxiv:$($id.ToLower())"
      if (-not $results.ContainsKey($key)) {
        $results[$key] = [ordered]@{
          id = $key
          title = (($entry.title -as [string]) -replace '\s+', ' ').Trim()
          year = if ($entry.published) { [int]($entry.published.Substring(0, 4)) } else { $null }
          authors = $authors
          venue = 'arXiv'
          publication_date = if ($entry.published) { $entry.published.Substring(0, 10) } else { $null }
          doi = $null
          arxiv_id = $id
          semantic_scholar_id = $null
          url = "https://arxiv.org/abs/$id"
          pdf_url = "https://arxiv.org/pdf/$id"
          citation_count = $null
          abstract = (($entry.summary -as [string]) -replace '\s+', ' ').Trim()
          discovered_by = @($query)
          categories = @('arxiv_search')
          relevance_notes = ''
          coding = [ordered]@{
            persona_type = $null
            representation = $null
            generation_method = $null
            grounding_data = $null
            theoretical_grounding = $null
            sampling_design = $null
            evaluation_type = $null
            bias_or_harm_analysis = $null
            reproducibility_artifacts = $null
            limitations = $null
            relevance_score = $null
          }
          status = 'candidate'
        }
      } else {
        $results[$key].discovered_by += $query
      }
    }
    Start-Sleep -Seconds 3
  } catch {
    $searchLog += [pscustomobject]@{
      query = $query
      source = 'arXiv API'
      retrieved = 0
      timestamp = (Get-Date).ToString('s')
      error = $_.Exception.Message
    }
  }
}

$needles = @(
  'persona', 'personas', 'role-playing', 'role playing', 'survey respondent',
  'synthetic respondent', 'virtual respondent', 'silicon sampling',
  'human simulation', 'simulate human', 'social simulation', 'generative agent',
  'user simulation', 'population synthesis', 'synthetic population',
  'statistical matching', 'data fusion', 'microsimulation', 'demographic',
  'opinion', 'identity group', 'psychometric', 'values', 'personality'
)

$selected = foreach ($entry in $results.Values) {
  $text = (($entry.title + ' ' + $entry.abstract) -as [string]).ToLower()
  $score = 0
  foreach ($needle in $needles) {
    if ($text.Contains($needle)) { $score++ }
  }
  if ($text.Contains('large language model') -or $text.Contains('llm')) { $score += 2 }
  if ($text.Contains('persona generation') -or $text.Contains('synthetic persona')) { $score += 3 }
  $entry.coding.relevance_score = $score
  if ($score -ge 4) {
    $entry.status = 'included_for_initial_screen'
  } else {
    $entry.status = 'candidate_low_relevance'
  }
  $entry
}

$jsonlPath = Join-Path $literature 'papers_arxiv.jsonl'
if (Test-Path $jsonlPath) {
  Remove-Item -LiteralPath $jsonlPath
}
foreach ($entry in ($selected | Sort-Object @{Expression = { $_.coding.relevance_score }; Descending = $true } | Select-Object -First 120)) {
  ($entry | ConvertTo-Json -Depth 10 -Compress) | Add-Content -Path $jsonlPath -Encoding UTF8
}

$md = @()
$md += '# arXiv Search Log'
$md += ''
$md += "Search date: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')"
$md += ''
$md += '## Queries'
foreach ($log in $searchLog) {
  $line = "- ``$($log.query)`` -> $($log.retrieved) records"
  if ($log.error) {
    $line += " (error: $($log.error))"
  }
  $md += $line
}
$md += ''
$md += "Initial arXiv records written: $((Get-Content $jsonlPath -ErrorAction SilentlyContinue | Measure-Object -Line).Lines)"
$md | Set-Content -Encoding UTF8 -Path (Join-Path $literature 'search_log_arxiv.md')

Write-Output "Wrote arXiv records to $jsonlPath"
