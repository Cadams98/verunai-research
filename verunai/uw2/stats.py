"""Exact one-sided sign test used to decide whether an update improved the model.

For each fresh evaluation example, compare the old and the new model. Only
*discordant* examples matter: a "win" is new-right/old-wrong and a "loss" is
the reverse. If an update does not truly help, a discordant example is a win
with probability at most 1/2, so the chance of seeing at least ``wins`` wins
among ``wins + losses`` discordant examples is at most the Binomial(n, 1/2)
upper tail. The update is accepted only when that tail is at most ``alpha``.

All arithmetic is exact integers; there is no floating-point rounding.
"""

from __future__ import annotations

from math import comb

Alpha = tuple[int, int]  # numerator, denominator
DEFAULT_ALPHA: Alpha = (1, 1024)


def tail_numerator(wins: int, losses: int) -> int:
    """Return the number of sign patterns with at least ``wins`` wins (out of 2**n)."""
    n = wins + losses
    return sum(comb(n, k) for k in range(wins, n + 1))


def improved(wins: int, losses: int, alpha: Alpha = DEFAULT_ALPHA) -> bool:
    """Return whether the paired evidence shows improvement at level ``alpha``.

    Args:
        wins: Examples the new model gets right and the old model gets wrong.
        losses: Examples the old model gets right and the new model gets wrong.
        alpha: False-acceptance limit as an exact fraction in (0, 1/2].

    Returns:
        ``True`` only if ``P[Binomial(wins+losses, 1/2) >= wins] <= alpha``.
    """
    numerator, denominator = alpha
    if (type(wins) is not int or type(losses) is not int or wins < 0 or losses < 0 or
            type(numerator) is not int or type(denominator) is not int or
            not 0 < 2 * numerator <= denominator):
        raise ValueError("invalid counts or alpha")
    if wins <= losses:
        return False
    return tail_numerator(wins, losses) * denominator <= numerator * 2 ** (wins + losses)
