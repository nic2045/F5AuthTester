function Get-Greeting {
    [CmdletBinding()]
    param(
        [Parameter()]
        [string]$Name = 'world'
    )

    return "Hello, $Name!"
}

Export-ModuleMember -Function Get-Greeting
