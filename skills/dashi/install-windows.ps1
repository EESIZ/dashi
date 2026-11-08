# Dashi on Windows: the Linux build runs inside WSL, and Windows Claude apps reach it through wsl.exe.
#
#   powershell -ExecutionPolicy Bypass -File install-windows.ps1 [-Distro Ubuntu] [-Desktop] [-NoClaudeCode]
#
# -Distro        WSL distribution to use (default: the WSL default distribution)
# -Desktop       also add dashi to Claude Desktop's config (a backup of the old config is kept)
# -NoClaudeCode  skip `claude mcp add` for Claude Code on Windows
param([string]$Distro = "", [switch]$Desktop, [switch]$NoClaudeCode)
$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$D = @(); if ($Distro) { $D = @("-d", $Distro) }

function Wsl([string]$Script, [string[]]$ScriptArgs = @()) {
    # Runs a bash login shell in WSL so PATH includes ~/.local/bin (uv, claude).
    $out = & wsl.exe @D -- bash -lc $Script "dashi" @ScriptArgs
    if ($LASTEXITCODE -ne 0) { throw "WSL command failed ($LASTEXITCODE): $Script" }
    return ($out -join "`n").Trim()
}

if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
    throw "WSL is not installed. In an administrator PowerShell run: wsl --install -d Ubuntu  (then reboot and run this script again)."
}
& wsl.exe @D -- true 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "No usable WSL distribution. Run: wsl --install -d Ubuntu  (or pass -Distro <name>; list with: wsl -l -v)."
}
$arch = Wsl 'uname -m'
if ($arch -ne "x86_64") { throw "Dashi binaries need x86_64 Linux; this WSL reports $arch." }
$uv = Wsl 'command -v uv || true'
if (-not $uv) {
    throw "uv is missing inside WSL. Open WSL and run: curl -LsSf https://astral.sh/uv/install.sh | sh   then run this script again."
}

# Copy the skill into the WSL home (Linux file system: faster and keeps file modes).
$src = Wsl 'wslpath -a "$1"' @($Here)
$target = Wsl 'printf %s "$HOME/.local/share/dashi-skill"'
Wsl 'set -e; t="$1"; s="$2"; case "$t" in /*/.local/share/dashi-skill) ;; *) echo "unexpected target $t" >&2; exit 1;; esac; [ -d "$s" ] || exit 1; mkdir -p "$(dirname "$t")"; rm -rf "$t.new"; cp -r "$s" "$t.new"; rm -rf "$t.new/.venv"; if [ -d "$t" ]; then rm -rf "$t.old"; mv "$t" "$t.old"; fi; mv "$t.new" "$t"' @($target, $src) | Out-Null
Write-Host "Installing inside WSL: $target"
& wsl.exe @D -- bash -lc 'sh "$1/install.sh"' "dashi" $target
if ($LASTEXITCODE -ne 0) { throw "install.sh failed inside WSL." }

$py = "$target/.venv/bin/python"; $server = "$target/scripts/dashi.py"
$launch = "exec '$py' '$server'"
$mcpArgs = @() + $D + @("--", "bash", "-lc", $launch)

if (-not $NoClaudeCode) {
    if (Get-Command claude -ErrorAction SilentlyContinue) {
        & claude mcp remove --scope user dashi 2>$null | Out-Null
        & claude mcp add --scope user dashi -- wsl.exe @mcpArgs
        if ($LASTEXITCODE -ne 0) { throw "claude mcp add failed." }
        $skills = Join-Path $env:USERPROFILE ".claude\skills\dashi"
        New-Item -ItemType Directory -Force -Path (Split-Path $skills) | Out-Null
        if (Test-Path $skills) { Remove-Item -Recurse -Force $skills }
        Copy-Item -Recurse -Path $Here -Destination $skills -Exclude ".venv"
        Write-Host "Claude Code: MCP 'dashi' registered and skill copied to $skills"
    } else {
        Write-Host "Claude Code for Windows was not found; skipped its registration."
    }
}

if ($Desktop) {
    $cfgPath = Join-Path $env:APPDATA "Claude\claude_desktop_config.json"
    New-Item -ItemType Directory -Force -Path (Split-Path $cfgPath) | Out-Null
    $cfg = [pscustomobject]@{}
    if (Test-Path $cfgPath) {
        Copy-Item $cfgPath "$cfgPath.bak" -Force
        $raw = Get-Content -Raw -Path $cfgPath
        if ($raw.Trim()) { $cfg = $raw | ConvertFrom-Json }
    }
    if (-not $cfg.mcpServers) { $cfg | Add-Member -NotePropertyName mcpServers -NotePropertyValue ([pscustomobject]@{}) -Force }
    $entry = [pscustomobject]@{ command = "wsl.exe"; args = $mcpArgs }
    $cfg.mcpServers | Add-Member -NotePropertyName dashi -NotePropertyValue $entry -Force
    [IO.File]::WriteAllText($cfgPath, ($cfg | ConvertTo-Json -Depth 20), (New-Object Text.UTF8Encoding $false))
    Write-Host "Claude Desktop: added 'dashi' to $cfgPath (restart Claude Desktop)."
}

$claudeInWsl = Wsl 'command -v claude || true'
if (-not $claudeInWsl -or $claudeInWsl -like "/mnt/*") {
    Write-Host ""
    Write-Host "Inspection tools work now. For compose (writing), install and log in to Claude Code inside WSL:"
    Write-Host "  wsl  ->  curl -fsSL https://claude.ai/install.sh | bash  ->  claude  (log in once)"
}
Write-Host "Done. In Claude Code run /mcp to reconnect."
