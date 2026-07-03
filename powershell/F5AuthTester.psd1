@{
    RootModule        = 'F5AuthTester.psm1'
    ModuleVersion     = '0.2.0'
    GUID              = 'b7d4e8a2-3c19-4f6a-8e57-2a9c1d0b6f34'
    Author            = 'f5authtester'
    Description       = 'PowerShell helper for the F5AuthTester dashboard: query SSO-variant health from the running web API.'
    PowerShellVersion = '5.1'
    FunctionsToExport = @('Get-F5AuthStatus', 'Invoke-F5AuthRun')
    CmdletsToExport   = @()
    VariablesToExport = @()
    AliasesToExport   = @()
}
