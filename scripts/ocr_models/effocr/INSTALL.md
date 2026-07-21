# EfficientOCR installation on Marvin

The maintained package is `efficient_ocr` (underscore in Python), not the older
research repository named `effocr`.

```bash
module purge
module load Miniforge3
eval "$(conda shell.bash hook)"

conda create -n harvest-effocr python=3.10 -y
conda activate harvest-effocr

python -m pip install --upgrade pip
python -m pip install "efficient_ocr==0.1.1"
```

The first inference downloads pretrained ONNX artifacts from Hugging Face into
the directory passed with `--model-dir`. Put that directory in the HARVEST
workspace, not in `$HOME`.

Before scheduling a full job, verify the manifest without loading models:

```bash
python scripts/ocr_models/effocr/run_effocr_ocr.py \
  --regions-manifest "$WORKSPACE/runs/regions/cells.jsonl" \
  --output-dir "$WORKSPACE/runs/effocr" \
  --model-dir "$WORKSPACE/models/effocr" \
  --validate-only
```

EfficientOCR's pretrained ONNX path is CPU-oriented. Use the CPU Slurm script
first. GPU use should be benchmarked rather than assumed to be faster.
