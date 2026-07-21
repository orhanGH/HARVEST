# Surya OCR 2 on Marvin

```bash
module purge
module load Miniforge3
eval "$(conda shell.bash hook)"
conda create -n harvest-surya python=3.11 -y
conda activate harvest-surya
pip install -U pip
pip install -e '.[base,surya]'
surya_ocr --help
surya_table --help
```

Surya 2 uses a vLLM backend on NVIDIA GPUs or `llama.cpp` on CPU. The adapter calls both
`surya_ocr` and `surya_table`, reusing the same staged table images. Configure the backend with
the official `SURYA_INFERENCE_*` environment variables.
