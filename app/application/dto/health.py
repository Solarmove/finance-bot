from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ReadinessResult:
    checks: dict[str, str]

    @property
    def is_ready(self) -> bool:
        return bool(self.checks) and all(value == "ok" for value in self.checks.values())
