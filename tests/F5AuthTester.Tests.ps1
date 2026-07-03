BeforeAll {
    Import-Module "$PSScriptRoot/../powershell/F5AuthTester.psd1" -Force
}

Describe 'F5AuthTester module' {
    It 'exports Get-F5AuthStatus' {
        Get-Command -Module F5AuthTester -Name 'Get-F5AuthStatus' | Should -Not -BeNullOrEmpty
    }

    It 'exports Invoke-F5AuthRun' {
        Get-Command -Module F5AuthTester -Name 'Invoke-F5AuthRun' | Should -Not -BeNullOrEmpty
    }

    It 'builds the status URI from BaseUrl and calls Invoke-RestMethod' {
        Mock -ModuleName F5AuthTester Invoke-RestMethod { return @{ report = @{ results = @() } } }
        $null = Get-F5AuthStatus -BaseUrl 'http://f5.test:8080/'
        Should -Invoke -ModuleName F5AuthTester Invoke-RestMethod -Times 1 -ParameterFilter {
            $Uri -eq 'http://f5.test:8080/api/status' -and $Method -eq 'Get'
        }
    }

    It 'posts to /api/run for Invoke-F5AuthRun' {
        Mock -ModuleName F5AuthTester Invoke-RestMethod { return @{ results = @() } }
        $null = Invoke-F5AuthRun -BaseUrl 'http://f5.test:8080'
        Should -Invoke -ModuleName F5AuthTester Invoke-RestMethod -Times 1 -ParameterFilter {
            $Uri -eq 'http://f5.test:8080/api/run' -and $Method -eq 'Post'
        }
    }
}
