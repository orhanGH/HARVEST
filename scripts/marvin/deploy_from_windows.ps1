param(
    [string]$ArchivePath = "$env:USERPROFILE\Downloads\HARVEST_OCR_implementation_v3.zip",
    [string]$IdentityFile = "$env:USERPROFILE\.ssh\marvin_ed25519",
    [string]$Remote = "s6oraydi_hpc@marvin.hpc.uni-bonn.de"
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path -LiteralPath $ArchivePath)) {
    throw "Archive not found: $ArchivePath"
}
if (-not (Test-Path -LiteralPath $IdentityFile)) {
    throw "SSH key not found: $IdentityFile"
}

$RemoteArchive = "HARVEST_OCR_implementation_v3.zip"
& scp -i $IdentityFile $ArchivePath "${Remote}:~/$RemoteArchive"
if ($LASTEXITCODE -ne 0) { throw "SCP upload failed." }

$RemoteScript = @'
set -euo pipefail
module purge
module load Miniforge3
mkdir -p "$HOME/project_harvest/_archive"
if [ -d "$HOME/project_harvest/HARVEST" ]; then
    stamp=$(date +%Y%m%d_%H%M%S)
    mv "$HOME/project_harvest/HARVEST" "$HOME/project_harvest/_archive/HARVEST_$stamp"
fi
python -m zipfile -e "$HOME/HARVEST_OCR_implementation_v3.zip" "$HOME/project_harvest"
cd "$HOME/project_harvest/HARVEST"
bash scripts/marvin/setup_tesseract.sh
mkdir -p runs/slurm
SOURCE_PDF=/lustre/scratch/data/s6oraydi_hpc-project_harvest/s6oraydi_work/old/data/0000765723_D0001.pdf
test -f "$SOURCE_PDF"
HARVEST_SOURCE_PDF="$SOURCE_PDF" sbatch --export=ALL scripts/slurm/run_marvin_tesseract.sbatch
'@

& ssh -t -i $IdentityFile $Remote $RemoteScript
if ($LASTEXITCODE -ne 0) { throw "Remote setup or Slurm submission failed." }
