# PaddleOCR 3.x on Marvin

```bash
module purge
module load Miniforge3
eval "$(conda shell.bash hook)"
conda create -n harvest-paddle python=3.10 -y
conda activate harvest-paddle
```

Install the PaddlePaddle build matching the CUDA version exposed inside the selected Slurm GPU
job, following the official Paddle installation selector. Then install the project and PaddleOCR:

```bash
pip install -U pip
pip install -e '.[base,paddle]'
python -c "from paddleocr import TableRecognitionPipelineV2; print('Paddle ready')"
```

PaddleOCR 3.x is required; version 2.x examples use an incompatible API.
