#!/bin/bash
#SBATCH --job-name=harvest_ttd
#SBATCH --partition=mlgpu_devel
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=01:00:00
#SBATCH --output=runs/slurm/%x_%j.out
#SBATCH --error=runs/slurm/%x_%j.err

set -euo pipefail

REPO_DIR=${REPO_DIR:-"$HOME/project_harvest/HARVEST"}
WORKSPACE=${HARVEST_WORKSPACE:-/lustre/scratch/data/s6oraydi_hpc-project_harvest}
SOURCE_PDF=${HARVEST_SOURCE_PDF:-"$WORKSPACE/s6oraydi_work/old/data/0000765723_D0001.pdf"}
OUTPUT_ROOT=${HARVEST_TABLE_DETECTION_OUTPUT_ROOT:-"$WORKSPACE/s6oraydi_work/results/table_detection"}
PAGE_RANGE=${HARVEST_TABLE_DETECTION_PAGES:-20-45}
DPI=${HARVEST_TABLE_DETECTION_DPI:-180}
THRESHOLD=${HARVEST_TABLE_DETECTION_THRESHOLD:-0.50}
MODEL_NAME=${HARVEST_TABLE_DETECTION_MODEL:-microsoft/table-transformer-detection}
DEVICE=${HARVEST_TABLE_DETECTION_DEVICE:-cuda}
PADDING=${HARVEST_TABLE_DETECTION_PADDING:-8}
ANNOTATIONS=${HARVEST_TABLE_DETECTION_ANNOTATIONS:-}
HF_HOME=${HARVEST_HF_HOME:-"$WORKSPACE/.cache/huggingface"}
JOB_SCRATCH=${SLURM_TMPDIR:-${TMPDIR:-/tmp}}/harvest_table_detection_${SLURM_JOB_ID:-manual}
FINAL_DIR="$OUTPUT_ROOT/${SLURM_JOB_ID:-manual}"
LOCAL_PDF="$JOB_SCRATCH/$(basename "$SOURCE_PDF")"
RUN_DIR="$JOB_SCRATCH/run"

mkdir -p "$REPO_DIR/runs/slurm" "$JOB_SCRATCH" "$FINAL_DIR" "$HF_HOME"
test -f "$SOURCE_PDF"
cp "$SOURCE_PDF" "$LOCAL_PDF"

module purge
module load Miniforge3
eval "$(conda shell.bash hook)"
conda activate harvest-table-transformer

export HF_HOME
export TRANSFORMERS_CACHE="$HF_HOME"
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-8}

cd "$REPO_DIR"

COMMAND=(
  python scripts/table_detection/detect_tables_pdf.py
  --pdf "$LOCAL_PDF"
  --output-dir "$RUN_DIR"
  --pages "$PAGE_RANGE"
  --dpi "$DPI"
  --model "$MODEL_NAME"
  --threshold "$THRESHOLD"
  --device "$DEVICE"
  --bbox-padding "$PADDING"
)

if [[ -n "$ANNOTATIONS" ]]; then
  COMMAND+=(--annotations "$ANNOTATIONS")
fi

"${COMMAND[@]}"

cp -a "$RUN_DIR/." "$FINAL_DIR/"
sha256sum "$SOURCE_PDF" > "$FINAL_DIR/source_pdf.sha256"

echo "Final results: $FINAL_DIR"
