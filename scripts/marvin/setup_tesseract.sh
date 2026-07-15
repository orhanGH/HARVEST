#!/bin/bash
set -euo pipefail

REPO_DIR=${1:-"$HOME/project_harvest/HARVEST"}
ENV_NAME=${HARVEST_ENV_NAME:-harvest-tesseract}

module purge
module load Miniforge3
eval "$(conda shell.bash hook)"
cd "$REPO_DIR"

if conda env list | awk '{print $1}' | grep -qx "$ENV_NAME"; then
    conda env update -n "$ENV_NAME" -f "$REPO_DIR/environments/tesseract.yml" --prune
else
    conda env create -n "$ENV_NAME" -f environments/tesseract.yml
fi

conda activate "$ENV_NAME"
python -m pip install -e "${REPO_DIR}[base]"
python -c "import cv2, fitz, pytesseract, yaml; print('Python dependencies: OK')"
tesseract --version | head -n 1
tesseract --list-langs
