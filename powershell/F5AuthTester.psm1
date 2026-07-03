Set-StrictMode -Version Latest

function Get-F5AuthStatus {
    <#
    .SYNOPSIS
        Retrieves the latest SSO-variant health report from a running F5AuthTester instance.
    .DESCRIPTION
        Calls the /api/status endpoint of the F5AuthTester web app and returns the report as
        a PowerShell object. Use -Raw to get the untouched JSON payload instead.
    .PARAMETER BaseUrl
        Base URL of the F5AuthTester web app, e.g. http://localhost:8080.
    .PARAMETER Raw
        Return the raw JSON string instead of a parsed object.
    .EXAMPLE
        Get-F5AuthStatus -BaseUrl http://localhost:8080
    #>
    [CmdletBinding()]
    param(
        [Parameter()]
        [string]$BaseUrl = 'http://localhost:8080',

        [Parameter()]
        [switch]$Raw
    )

    $uri = ('{0}/api/status' -f $BaseUrl.TrimEnd('/'))
    $response = Invoke-RestMethod -Uri $uri -Method Get -ErrorAction Stop

    if ($Raw) {
        return ($response | ConvertTo-Json -Depth 10)
    }

    return $response
}

function Invoke-F5AuthRun {
    <#
    .SYNOPSIS
        Triggers a fresh check run on a running F5AuthTester instance and returns the report.
    .PARAMETER BaseUrl
        Base URL of the F5AuthTester web app, e.g. http://localhost:8080.
    .EXAMPLE
        Invoke-F5AuthRun -BaseUrl http://localhost:8080
    #>
    [CmdletBinding()]
    param(
        [Parameter()]
        [string]$BaseUrl = 'http://localhost:8080'
    )

    $uri = ('{0}/api/run' -f $BaseUrl.TrimEnd('/'))
    return (Invoke-RestMethod -Uri $uri -Method Post -ErrorAction Stop)
}

Export-ModuleMember -Function Get-F5AuthStatus, Invoke-F5AuthRun
