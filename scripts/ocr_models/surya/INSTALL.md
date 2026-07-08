# Surya install idea

Surya may be more complicated because current Surya 2 backend can require vLLM on NVIDIA GPU or llama.cpp CPU backend.

Try only after Paddle and Chandra.

module purge
module load Miniforge3
eval "$(conda shell.bash hook)"
conda create -n harvest-surya python=3.11 -y
conda activate harvest-surya

pip install -U pip
pip install surya-ocr pandas tqdm pillow beautifulsoup4 lxml
