import math


def wilson(successes: int, n: int, z: float = 1.96) -> tuple[float, float] | tuple[None, None]:
    """95% Wilson score interval for a proportion, in percent."""
    if n == 0:
        return None, None
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return round(100 * max(0.0, centre - half), 1), round(100 * min(1.0, centre + half), 1)
