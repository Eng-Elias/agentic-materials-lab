class BudgetExceededError(RuntimeError):
    pass


class Oracle:
    def __init__(self, labels, budget: int):
        if budget < 0:
            raise ValueError("budget must be non-negative")
        self.__labels = dict(labels)
        self.__budget = int(budget)
        self.__revealed: set[str] = set()

    def reveal(self, ids) -> dict[str, float]:
        ids = [str(i) for i in ids]
        if not ids:
            return {}
        if len(ids) > self.__budget:
            raise BudgetExceededError(
                f"requested {len(ids)} reveals with only {self.__budget} budget remaining"
            )
        already = self.__revealed.intersection(ids)
        if already:
            raise ValueError(f"already revealed: {sorted(already)}")
        for i in ids:
            if i not in self.__labels:
                raise KeyError(f"unknown id: {i}")
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate ids within reveal request")
        self.__budget -= len(ids)
        self.__revealed.update(ids)
        return {i: self.__labels[i] for i in ids}

    def budget_remaining(self) -> int:
        return self.__budget

    def revealed_ids(self) -> frozenset[str]:
        return frozenset(self.__revealed)

    def count_revealed(self) -> int:
        return len(self.__revealed)

    def hits_found(self, top_set) -> int:
        return len(self.__revealed.intersection(top_set))

    def __repr__(self) -> str:
        return f"Oracle(revealed={len(self.__revealed)}, budget_remaining={self.__budget})"
