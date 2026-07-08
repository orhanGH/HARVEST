# PaddleOCR install idea

Create environment:

module purge
module load Miniforge3
eval "$(conda shell.bash hook)"
conda create -n harvest-paddle python=3.10 -y
conda activate harvest-paddle

pip install -U pip
pip install paddleocr pandas tqdm pillow beautifulsoup4 lxml

Then test import:

python - <<'PY'
import paddleocr
print("paddleocr import ok")
PY
