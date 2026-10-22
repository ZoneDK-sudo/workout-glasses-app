# Copies Workout Counter (glasses) and Workout Tracker (phone) into your copy of
# MemoMind's plugin-open-platform SDK, then you build with `py build.py`.
# Usage:  .\install.ps1                      (SDK at $HOME\plugin-open-platform)
#         .\install.ps1 -Sdk D:\path\to\plugin-open-platform
param([string]$Sdk = "$HOME\plugin-open-platform")
$ErrorActionPreference = "Stop"
if (-not (Test-Path "$Sdk\GlassSDK") -or -not (Test-Path "$Sdk\PhoneSDK")) {
    throw "Couldn't find the SDK at '$Sdk'. Clone https://github.com/memomind-open/plugin-open-platform first, or pass -Sdk <path>."
}
Copy-Item -Recurse -Force "$PSScriptRoot\glasses\situp_counter" "$Sdk\GlassSDK\examples\"
Copy-Item -Recurse -Force "$PSScriptRoot\phone\situp-tracker" "$Sdk\PhoneSDK\examples\"
# The phone plugin needs MemoMind's web SDK file; take it from your own SDK copy.
New-Item -ItemType Directory -Force "$Sdk\PhoneSDK\examples\situp-tracker\vendor" | Out-Null
Copy-Item -Force "$Sdk\PhoneSDK\examples\fighter-controller\vendor\gm-plugin-web-sdk.esm.js" "$Sdk\PhoneSDK\examples\situp-tracker\vendor\"
Write-Host "Installed. Now run:  cd $Sdk ; py build.py"
