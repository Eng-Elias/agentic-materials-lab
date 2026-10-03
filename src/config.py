from dataclasses import dataclass


@dataclass
class RunConfig:
    seeds: int = 10
    budget: int = 300
    rounds: int = 6
    pool: int = 15000
    gap_min: float = 1.0
    gap_max: float = 2.0
    ehull_max: float | None = None
    out_dir: str = "results"
    cache_dir: str = "cache"

    @property
    def batch_size(self) -> int:
        return self.budget // self.rounds
