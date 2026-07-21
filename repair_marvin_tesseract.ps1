param(
    [string]$IdentityFile = "$env:USERPROFILE\.ssh\marvin_ed25519",
    [string]$Remote = "s6oraydi_hpc@marvin.hpc.uni-bonn.de"
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path -LiteralPath $IdentityFile)) {
    throw "SSH key not found: $IdentityFile"
}

$RemoteScript = @'
set -euo pipefail

REPO_DIR="$HOME/project_harvest/HARVEST"
SOURCE_PDF=/lustre/scratch/data/s6oraydi_hpc-project_harvest/s6oraydi_work/old/data/0000765723_D0001.pdf

test -d "$REPO_DIR"
test -f "$REPO_DIR/environments/tesseract.yml"

# Conda resolves editable pip paths relative to environments/, not the repository root.
# Remove only the pip subsection; setup_tesseract.sh installs the project explicitly.
python - <<'PY'
from pathlib import Path

path = Path.home() / "project_harvest/HARVEST/environments/tesseract.yml"
lines = path.read_text(encoding="utf-8").splitlines()
for index, line in enumerate(lines):
    if line.strip() == "- pip:":
        lines = lines[:index]
        break
path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
print(f"Repaired {path}")
PY

cd "$REPO_DIR"
bash scripts/marvin/setup_tesseract.sh

test -f "$SOURCE_PDF"
mkdir -p runs/slurm
HARVEST_SOURCE_PDF="$SOURCE_PDF" \
    sbatch --export=ALL scripts/slurm/run_marvin_tesseract.sbatch
'@

# Encode the Bash program before sending it. Passing a multiline script as a
# Windows OpenSSH argument strips nested quotes; raw stdin can also retain CRLF.
$NormalizedScript = $RemoteScript -replace "`r`n", "`n"
$EncodedScript = [Convert]::ToBase64String(
    [Text.Encoding]::UTF8.GetBytes($NormalizedScript)
)
& ssh -i $IdentityFile $Remote "echo $EncodedScript | base64 --decode | bash"
if ($LASTEXITCODE -ne 0) {
    throw "Marvin repair or Slurm submission failed."
}
