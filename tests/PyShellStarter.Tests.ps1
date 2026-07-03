BeforeAll {
    Import-Module "$PSScriptRoot/../powershell/PyShellStarter.psd1" -Force
}

Describe 'Get-Greeting' {
    It 'returns the default greeting' {
        Get-Greeting | Should -Be 'Hello, world!'
    }

    It 'returns a greeting with the given name' {
        Get-Greeting -Name 'Claude' | Should -Be 'Hello, Claude!'
    }
}
