param([Parameter(Mandatory=$true)][string]$OutputDirectory)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$demoNarration = @(
    'Salesforce Guard reviews security risks and upstream and downstream impact. This demonstration uses original fictional expense workflow fixtures. No customer application or live Salesforce organisation is included.',
    'Fifteen local signals need review. The report includes source locations, guidance and partial OWASP mappings. Findings are not automatically confirmed vulnerabilities.',
    'The impact explorer follows Apex references, record operations, possible Flow activation and asynchronous handoffs. Choose a component, direction and depth. Explicit, conditional and unresolved connections remain distinct.',
    'Here is the fictional expense Flow. Its scheduled path references an invocable action, which enqueues a background job. The fault connector has its own route. Click any connection for evidence and transaction context. The map does not prove runtime authorisation.',
    'The separate Salesforce Code Analyzer integration was run on the same fictional project. Its raw findings, engine versions and run receipt are retained. Graph uncertainty and scanner results are reported separately.',
    'These are recorded checks from the real Hermes runtime. Review and impact tools were allowed. Unrelated shell, Apex execution, deployment and messaging identities were blocked. A terminal probe was blocked before execution. The plugin is a restricted review environment, not an operating system sandbox.'
)
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
$speaker.Rate = 2
try {
    for ($segment = 0; $segment -lt $demoNarration.Count; $segment++) {
        $speaker.SetOutputToWaveFile((Join-Path $OutputDirectory "voice$segment.wav"))
        $speaker.Speak($demoNarration[$segment])
        $speaker.SetOutputToNull()
    }
} finally { $speaker.Dispose() }
