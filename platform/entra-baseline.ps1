param(
    [switch]$Apply
)

$groups = @(
    "hf-makers",
    "hf-coordinators",
    "hf-finance",
    "hf-acct-north",
    "hf-acct-bright",
    "hf-pp-admins",
    "hf-sql-admins"
)

Write-Host "Harbor Entra groups"
foreach ($group in $groups) {
    if ($Apply) {
        $existing = az ad group list --display-name $group --query "[0].id" -o tsv
        if (-not $existing) {
            az ad group create --display-name $group --mail-nickname $group | Out-Null
            Write-Host "created $group"
        } else {
            Write-Host "exists  $group"
        }
    } else {
        Write-Host "would ensure $group"
    }
}

if (-not $Apply) {
    Write-Host "Dry run only. Re-run with -Apply to create missing groups."
}
