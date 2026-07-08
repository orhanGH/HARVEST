# Chandra install idea

module purge
module load Miniforge3
eval "$(conda shell.bash hook)"
conda create -n harvest-chandra python=3.11 -y
conda activate harvest-chandra

pip install -U pip
pip install "chandra-ocr[hf]" pandas tqdm pillow beautifulsoup4 lxml

Use GPU Slurm job for inference.
Do not run Chandra model inference on login node.
