from pathlib import Path


class RunPaths:
    """Stable artifact paths shared by the modular pipeline."""

    def __init__(self, run_dir: str | Path):
        self.root = Path(run_dir)

    def stage(self, name: str) -> Path:
        path = self.root / name
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def pages_manifest(self) -> Path:
        return self.root / "ingest" / "pages.jsonl"

    @property
    def processed_manifest(self) -> Path:
        return self.root / "preprocess" / "processed_pages.jsonl"
