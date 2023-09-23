from typing import Optional
from omegaconf import DictConfig, OmegaConf
import hydra

@hydra.main(version_base=None, config_path="./conf", config_name="config")
def my_app(cfg: Optional[DictConfig] = None) -> None:
    print(OmegaConf.to_yaml(cfg))

if __name__ == "__main__":
    my_app()
