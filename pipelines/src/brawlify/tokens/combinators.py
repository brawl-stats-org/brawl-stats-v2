"""Recipe shapes: a path string, or an arithmetic node whose operands are recipes.

Percent(p, b)   p% of b               Frank: 10% of 13600 = 1360
Share(v, b)     v as a % of b         Colt: 3/27 = 11%
Ratio(n, b)     how much bigger n is  Buzz: 2400/1800 = +33%
Loss(n, b)      how much smaller n is Byron: 304/380 = 20%
Div(a, b)       a / b, truncated      Brock: 2050/150 = 13
Delta(a, b)     a - b                 8-Bit: 50 - 35 = 15
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from brawlify.tokens.primitives import Roots, as_number, truncate

if TYPE_CHECKING:
    from brawlify.tokens.walker import Walker


@dataclass(frozen=True)
class Percent:
    percent: "Recipe"
    base: "Recipe"

    def evaluate(self, roots: Roots, walker: "Walker") -> float | None:
        percent, base = evaluate_both(self.percent, self.base, roots, walker)
        if percent is None or base is None:
            return None
        return percent * base / 100


@dataclass(frozen=True)
class Share:
    value: "Recipe"
    base: "Recipe"

    def evaluate(self, roots: Roots, walker: "Walker") -> float | None:
        value, base = evaluate_both(self.value, self.base, roots, walker)
        if value is None or not base:
            return None
        return truncate(value / base * 100)


@dataclass(frozen=True)
class Ratio:
    new: "Recipe"
    base: "Recipe"

    def evaluate(self, roots: Roots, walker: "Walker") -> float | None:
        new, base = evaluate_both(self.new, self.base, roots, walker)
        if new is None or not base:
            return None
        return truncate((new / base - 1) * 100)


@dataclass(frozen=True)
class Loss:
    new: "Recipe"
    base: "Recipe"

    def evaluate(self, roots: Roots, walker: "Walker") -> float | None:
        bigger = Ratio(self.new, self.base).evaluate(roots, walker)
        return None if bigger is None else abs(bigger)


@dataclass(frozen=True)
class Div:
    a: "Recipe"
    b: "Recipe"

    def evaluate(self, roots: Roots, walker: "Walker") -> float | None:
        a, b = evaluate_both(self.a, self.b, roots, walker)
        if a is None or not b:
            return None
        return truncate(a / b)


@dataclass(frozen=True)
class Delta:
    a: "Recipe"
    b: "Recipe"

    def evaluate(self, roots: Roots, walker: "Walker") -> float | None:
        a, b = evaluate_both(self.a, self.b, roots, walker)
        if a is None or b is None:
            return None
        return a - b


Recipe = str | Percent | Share | Ratio | Loss | Div | Delta


def value_of(recipe: Recipe | None, roots: Roots, walker: "Walker") -> float | None:
    """The number a recipe produces, or None when any part of it cannot be walked."""
    if recipe is None:
        return None
    if isinstance(recipe, str):
        return as_number(walker.resolve(recipe, roots))
    return recipe.evaluate(roots, walker)


def evaluate_both(
    left: Recipe, right: Recipe, roots: Roots, walker: "Walker"
) -> tuple[float | None, float | None]:
    return value_of(left, roots, walker), value_of(right, roots, walker)
