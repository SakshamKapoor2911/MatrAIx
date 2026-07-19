$ErrorActionPreference = "Stop"

$schemaDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$dimensionsPath = Join-Path $schemaDir "dimensions.json"
$taxonomyPath = Join-Path $schemaDir "persona_taxonomy.json"
$csvPath = Join-Path $schemaDir "persona_taxonomy_mapping.csv"

$dimensionsDocument = Get-Content -Raw $dimensionsPath | ConvertFrom-Json
$taxonomy = Get-Content -Raw $taxonomyPath | ConvertFrom-Json
$dimensions = @($dimensionsDocument.dimensions)

if ($dimensions.Count -eq 0) {
    throw "dimensions.json must contain a non-empty dimensions array"
}

$dimensionsById = @{}
$dimensionsByCategory = @{}

foreach ($attribute in $dimensions) {
    if ($dimensionsById.ContainsKey($attribute.id)) {
        throw "Duplicate attribute ID in dimensions.json: $($attribute.id)"
    }
    $dimensionsById[$attribute.id] = $attribute

    if (-not $dimensionsByCategory.ContainsKey($attribute.category)) {
        $dimensionsByCategory[$attribute.category] = [System.Collections.Generic.List[object]]::new()
    }
    $dimensionsByCategory[$attribute.category].Add($attribute)
}

$script:rows = [System.Collections.Generic.List[object]]::new()
$script:assignmentsByAttribute = @{}
$script:mappedSchemaCategories = @{}
$script:layerCounts = @(0, 0, 0)

function Resolve-LeafAttributes {
    param([Parameter(Mandatory)]$Node)

    $mapping = $Node.mapping
    $schemaCategories = @($mapping.schema_categories)
    if ($null -eq $mapping -or $schemaCategories.Count -eq 0) {
        throw "Layer 3 node $($Node.id) must define mapping.schema_categories"
    }

    foreach ($category in $schemaCategories) {
        $script:mappedSchemaCategories[$category] = $true
        if (-not $dimensionsByCategory.ContainsKey($category)) {
            throw "Unknown schema category on $($Node.id): $category"
        }
    }

    $resolved = [System.Collections.Generic.List[object]]::new()

    if ($mapping.mode -eq "all_in_categories") {
        foreach ($category in $schemaCategories) {
            foreach ($attribute in $dimensionsByCategory[$category]) {
                $resolved.Add($attribute)
            }
        }
        return @($resolved)
    }

    if ($mapping.mode -eq "explicit_attributes") {
        $attributeIds = @($mapping.attribute_ids)
        if ($attributeIds.Count -eq 0) {
            throw "Explicit mapping $($Node.id) must define attribute_ids"
        }

        $localIds = @{}
        foreach ($attributeId in $attributeIds) {
            if ($localIds.ContainsKey($attributeId)) {
                throw "Duplicate attribute ID inside $($Node.id): $attributeId"
            }
            $localIds[$attributeId] = $true

            if (-not $dimensionsById.ContainsKey($attributeId)) {
                throw "Unknown attribute ID on $($Node.id): $attributeId"
            }

            $attribute = $dimensionsById[$attributeId]
            if ($schemaCategories -notcontains $attribute.category) {
                throw "$attributeId has category $($attribute.category), which is not allowed by $($Node.id)"
            }
            $resolved.Add($attribute)
        }
        return @($resolved)
    }

    throw "Unsupported mapping mode on $($Node.id): $($mapping.mode)"
}

function Visit-TaxonomyNode {
    param(
        [Parameter(Mandatory)]$Node,
        [Parameter(Mandatory)][int]$Depth,
        [AllowEmptyCollection()][object[]]$Path = @()
    )

    if ($Depth -lt 1 -or $Depth -gt 3) {
        throw "Node $($Node.id) is at unsupported depth $Depth"
    }
    $script:layerCounts[$Depth - 1] += 1

    $nextPath = @($Path) + @($Node)
    $hasChildren = $null -ne $Node.PSObject.Properties["children"]
    $children = if ($hasChildren) { @($Node.children) } else { @() }

    if ($hasChildren) {
        if ($Depth -eq 3) {
            throw "Layer 3 node $($Node.id) cannot have children"
        }
        if ($null -ne $Node.mapping) {
            throw "Non-leaf node $($Node.id) cannot define a mapping"
        }

        $childCount = ($children | Measure-Object -Property expected_count -Sum).Sum
        if ([int]$childCount -ne [int]$Node.expected_count) {
            throw "$($Node.id) expects $($Node.expected_count) attributes but its children sum to $childCount"
        }

        foreach ($child in $children) {
            Visit-TaxonomyNode -Node $child -Depth ($Depth + 1) -Path $nextPath
        }
        return
    }

    if ($Depth -ne 3) {
        throw "Leaf node $($Node.id) must be at Layer 3, not Layer $Depth"
    }

    $attributes = @(Resolve-LeafAttributes -Node $Node)
    if ($attributes.Count -ne [int]$Node.expected_count) {
        throw "$($Node.id) expects $($Node.expected_count) attributes but resolves to $($attributes.Count)"
    }

    $layer1 = $nextPath[0]
    $layer2 = $nextPath[1]
    $layer3 = $nextPath[2]

    foreach ($attribute in $attributes) {
        if ($script:assignmentsByAttribute.ContainsKey($attribute.id)) {
            $previous = $script:assignmentsByAttribute[$attribute.id]
            throw "Attribute $($attribute.id) is assigned to both $previous and $($layer3.id)"
        }
        $script:assignmentsByAttribute[$attribute.id] = $layer3.id

        $script:rows.Add([pscustomobject][ordered]@{
            attribute_index = $attribute.index
            attribute_id = $attribute.id
            attribute_label = $attribute.label
            schema_category = $attribute.category
            layer_1_id = $layer1.id
            layer_1 = $layer1.label
            layer_2_id = $layer2.id
            layer_2 = $layer2.label
            layer_3_id = $layer3.id
            layer_3 = $layer3.label
        })
    }
}

foreach ($layer1Node in @($taxonomy.hierarchy)) {
    Visit-TaxonomyNode -Node $layer1Node -Depth 1 -Path @()
}

$missingAttributeIds = @(
    $dimensions |
        Where-Object { -not $script:assignmentsByAttribute.ContainsKey($_.id) } |
        ForEach-Object { $_.id }
)
if ($missingAttributeIds.Count -gt 0) {
    throw "Unassigned attributes: $($missingAttributeIds -join ', ')"
}

if ($script:rows.Count -ne [int]$taxonomy.expected_attribute_count) {
    throw "Expected $($taxonomy.expected_attribute_count) rows but generated $($script:rows.Count)"
}

$expectedLayerCounts = @(
    $taxonomy.expected_structure.layer_1_groups,
    $taxonomy.expected_structure.layer_2_groups,
    $taxonomy.expected_structure.layer_3_groups
)
for ($index = 0; $index -lt $expectedLayerCounts.Count; $index += 1) {
    if ($script:layerCounts[$index] -ne [int]$expectedLayerCounts[$index]) {
        throw "Expected $($expectedLayerCounts[$index]) Layer $($index + 1) groups but found $($script:layerCounts[$index])"
    }
}

$actualSchemaCategories = @($dimensionsByCategory.Keys)
$missingSchemaCategories = @(
    $actualSchemaCategories | Where-Object { -not $script:mappedSchemaCategories.ContainsKey($_) }
)
$unknownSchemaCategories = @(
    $script:mappedSchemaCategories.Keys | Where-Object { -not $dimensionsByCategory.ContainsKey($_) }
)
if ($missingSchemaCategories.Count -gt 0 -or $unknownSchemaCategories.Count -gt 0) {
    throw "Schema category mismatch; missing=[$($missingSchemaCategories -join ', ')], unknown=[$($unknownSchemaCategories -join ', ')]"
}
if ($actualSchemaCategories.Count -ne [int]$taxonomy.expected_structure.schema_categories) {
    throw "Expected $($taxonomy.expected_structure.schema_categories) schema categories but found $($actualSchemaCategories.Count)"
}

$sortedRows = @(
    $script:rows | Sort-Object `
        @{ Expression = { [int]$_.attribute_index }; Ascending = $true }, `
        @{ Expression = { $_.attribute_id }; Ascending = $true }
)
$csvLines = @($sortedRows | ConvertTo-Csv -NoTypeInformation)
$utf8WithoutBom = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllLines($csvPath, $csvLines, $utf8WithoutBom)

Write-Output "Generated $($sortedRows.Count) rows across $($actualSchemaCategories.Count) schema categories."
Write-Output "Validated Layer 1/2/3 group counts: $($script:layerCounts -join ' / ')."
Write-Output "Wrote $csvPath."
