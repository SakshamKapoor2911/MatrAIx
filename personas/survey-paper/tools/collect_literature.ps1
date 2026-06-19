$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$queries = @(
  'synthetic persona generation large language models',
  'persona generation large language model agents',
  'synthetic personas LLM agents social simulation',
  'population aligned persona generation LLM social simulation',
  'socially grounded persona framework user simulation LLM',
  'LLM generated persona promise catch',
  'virtual survey respondents large language models',
  'synthetic respondents large language models',
  'language models simulate human samples silicon sampling',
  'demographic prompting large language models persona',
  'role-playing language agents persona survey',
  'role playing large language models persona benchmark',
  'persona adherence benchmark large language models',
  'persona drift language models dialogs',
  'LLMs replace human participants misportray flatten identity groups',
  'Whose opinions do language models reflect demographic groups',
  'LLM social simulation agents persona survey',
  'generative agents human behavior simulation personas',
  'large language model based social simulation agents survey',
  'user simulation large language models persona',
  'data driven personas HCI survey',
  'personas requirements engineering systematic mapping',
  'synthetic population agent based model survey population synthesis',
  'statistical matching data fusion conditional independence survey',
  'population synthesis microsimulation iterative proportional fitting review'
)

$root = Split-Path -Parent $PSScriptRoot
$literature = Join-Path $root 'literature'
New-Item -ItemType Directory -Force -Path $literature | Out-Null

$results = @{}
$searchLog = @()

foreach ($query in $queries) {
  $encoded = [System.Uri]::EscapeDataString($query)
  $uri = "https://api.semanticscholar.org/graph/v1/paper/search?query=$encoded&limit=20&fields=title,year,authors,url,externalIds,abstract,venue,publicationDate,citationCount,openAccessPdf"
  try {
    $response = Invoke-RestMethod -Uri $uri -TimeoutSec 30
    $count = if ($response.data) { $response.data.Count } else { 0 }
    $searchLog += [pscustomobject]@{
      query = $query
      source = 'Semantic Scholar Graph API'
      retrieved = $count
      timestamp = (Get-Date).ToString('s')
    }

    foreach ($paper in $response.data) {
      if (-not $paper.title) { continue }
      $doi = $null
      $arxiv = $null
      if ($paper.externalIds) {
        $doi = $paper.externalIds.DOI
        $arxiv = $paper.externalIds.ArXiv
      }

      $normalizedTitle = $paper.title.ToLower() -replace '[^a-z0-9]+', ' '
      $key = if ($doi) {
        "doi:$($doi.ToLower())"
      } elseif ($arxiv) {
        "arxiv:$($arxiv.ToLower())"
      } else {
        "title:$normalizedTitle"
      }

      if (-not $results.ContainsKey($key)) {
        $authors = @()
        if ($paper.authors) {
          $authors = @($paper.authors | ForEach-Object { $_.name })
        }

        $url = $paper.url
        if ($arxiv) {
          $url = "https://arxiv.org/abs/$arxiv"
        } elseif ($doi) {
          $url = "https://doi.org/$doi"
        }

        $pdfUrl = $null
        if ($paper.openAccessPdf) {
          $pdfUrl = $paper.openAccessPdf.url
        }

        $results[$key] = [ordered]@{
          id = $key
          title = $paper.title
          year = $paper.year
          authors = $authors
          venue = $paper.venue
          publication_date = $paper.publicationDate
          doi = $doi
          arxiv_id = $arxiv
          semantic_scholar_id = $paper.paperId
          url = $url
          pdf_url = $pdfUrl
          citation_count = $paper.citationCount
          abstract = $paper.abstract
          discovered_by = @($query)
          categories = @()
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
    Start-Sleep -Milliseconds 250
  } catch {
    $searchLog += [pscustomobject]@{
      query = $query
      source = 'Semantic Scholar Graph API'
      retrieved = 0
      timestamp = (Get-Date).ToString('s')
      error = $_.Exception.Message
    }
  }
}

$needles = @(
  'persona', 'personas', 'role-playing', 'role playing', 'survey respondent',
  'synthetic respondent', 'virtual respondent', 'human simulation',
  'simulate human', 'social simulation', 'generative agent', 'user simulation',
  'population synthesis', 'synthetic population', 'statistical matching',
  'data fusion', 'microsimulation', 'demographic', 'opinion', 'identity group',
  'psychometric', 'values', 'personality'
)

$scored = foreach ($entry in $results.Values) {
  $text = (($entry.title + ' ' + $entry.abstract) -as [string]).ToLower()
  $score = 0
  foreach ($needle in $needles) {
    if ($text.Contains($needle)) { $score++ }
  }
  if ($text.Contains('large language model') -or $text.Contains('llm')) { $score += 2 }
  if ($text.Contains('persona generation') -or $text.Contains('synthetic persona')) { $score += 3 }

  $entry.coding.relevance_score = $score
  if ($score -ge 5) {
    $entry.status = 'included_for_initial_screen'
  } else {
    $entry.status = 'candidate_low_relevance'
  }
  $entry
}

$selected = @(
  $scored |
    Sort-Object @{Expression = { $_.coding.relevance_score }; Descending = $true },
                @{Expression = { $_.citation_count }; Descending = $true } |
    Select-Object -First 120
)

$jsonlPath = Join-Path $literature 'papers.jsonl'
if (Test-Path $jsonlPath) {
  Remove-Item -LiteralPath $jsonlPath
}
foreach ($entry in $selected) {
  ($entry | ConvertTo-Json -Depth 10 -Compress) | Add-Content -Path $jsonlPath -Encoding UTF8
}

$csvRows = foreach ($entry in $selected) {
  [pscustomobject]@{
    id = $entry.id
    title = $entry.title
    year = $entry.year
    authors = ($entry.authors -join '; ')
    venue = $entry.venue
    doi = $entry.doi
    arxiv_id = $entry.arxiv_id
    url = $entry.url
    citation_count = $entry.citation_count
    status = $entry.status
    relevance_score = $entry.coding.relevance_score
    discovered_by = ($entry.discovered_by -join ' | ')
  }
}
$csvRows | Export-Csv -NoTypeInformation -Encoding UTF8 -Path (Join-Path $literature 'papers_index.csv')

$md = @()
$md += '# Search Log'
$md += ''
$md += "Search date: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')"
$md += ''
$md += 'Source: Semantic Scholar Graph API, seeded with the GitHub issue plan and personas/PLAN.md related-work categories.'
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
$md += "Initial deduplicated records written: $($selected.Count)"
$md += ''
$md += 'Files:'
$md += '- `papers.jsonl`: flexible metadata/coding records, one JSON object per paper.'
$md += '- `papers_index.csv`: spreadsheet-friendly index for screening.'
$md | Set-Content -Encoding UTF8 -Path (Join-Path $literature 'search_log.md')

Write-Output "Wrote $($selected.Count) records to $jsonlPath"
