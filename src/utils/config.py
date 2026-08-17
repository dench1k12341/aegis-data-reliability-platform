from pathlib import Path
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config" / "settings.yaml"


def load_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def get_simulation_config(config: dict) -> dict:
    mode = config["simulation"]["mode"]

    if mode not in {"dev", "full"}:
        raise ValueError(
            f"Unsupported simulation mode: {mode}. "
            "Expected 'dev' or 'full'."
        )

    return config["simulation"][mode]