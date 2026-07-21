#!/bin/bash
#SBATCH --job-name=harvest_effocr
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=runs/slurm/%x_%j.out
#SBATCH --error=runs/slurm/%x_%j.err

set -euo pipefail

REGIONS=${1:?Usage: sbatch run_effocr.sbatch REGIONS_MANIFEST [OUTPUT_DIR]}
OUTPUT_DIR=${2:-runs/effocr}
WORKSPACE=${WORKSPACE:-/lustre/scratch/data/s6oraydi_hpc-project_harvest}

mkdir -p runs/slurm "$OUTPUT_DIR" "$WORKSPACE/models/effocr"

module purge
module load Miniforge3
eval "$(conda shell.bash hook)"
conda activate harvest-effocr

python scripts/ocr_models/effocr/run_effocr_ocr.py \
  --regions-manifest "$REGIONS" \
  --output-dir "$OUTPUT_DIR" \
  --model-dir "$WORKSPACE/models/effocr" \
  --device cpu \
  --region-type cell
