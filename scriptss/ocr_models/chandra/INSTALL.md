# Chandra OCR 2 on Marvin

```bash
module purge
module load Miniforge3
eval "$(conda shell.bash hook)"
conda create -n harvest-chandra python=3.11 -y
conda activate harvest-chandra
pip install -U pip
pip install -e '.[base,chandra]'
chandra --help
```

Use `--method hf` for a self-contained smoke test. For production throughput, launch the official
vLLM service and select `--method vllm`. Run inference only inside a GPU Slurm job.
