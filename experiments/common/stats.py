"""E7 (statistical rigor): every report.py in e2/e4/e5/e6 imports this module
so all quantitative tables get dispersion (95% CI) and, where two conditions
are compared, a hypothesis test + effect size — never just point values.
"""
import dataclasses
import math

import numpy as np
from scipy import stats as scipy_stats


@dataclasses.dataclass
class SummaryStats:
    n: int
    mean: float
    ci95_low: float
    ci95_high: float
    median: float
    iqr_low: float
    iqr_high: float
    is_normal: bool  # per Shapiro-Wilk, alpha=0.05
    shapiro_p: float


def summarize(values: list[float]) -> SummaryStats:
    """Mean + 95% CI (t-distribution) and median + IQR — report BOTH; which one
    is "the" number to lead with depends on the normality check (E7's own rule:
    median+IQR when Shapiro-Wilk rejects normality).
    """
    arr = np.asarray(values, dtype=float)
    n = len(arr)
    if n < 2:
        raise ValueError("summarize() needs at least 2 values to report a CI")

    mean = float(np.mean(arr))
    sem = float(scipy_stats.sem(arr))
    ci_low, ci_high = scipy_stats.t.interval(0.95, df=n - 1, loc=mean, scale=sem) if sem > 0 else (mean, mean)

    median = float(np.median(arr))
    q1, q3 = np.percentile(arr, [25, 75])

    # Shapiro-Wilk needs n>=3; treat smaller samples as "unknown / assume non-normal"
    if n >= 3:
        shapiro_stat, shapiro_p = scipy_stats.shapiro(arr)
        is_normal = shapiro_p > 0.05
    else:
        shapiro_p = float("nan")
        is_normal = False

    return SummaryStats(
        n=n,
        mean=mean,
        ci95_low=float(ci_low),
        ci95_high=float(ci_high),
        median=median,
        iqr_low=float(q1),
        iqr_high=float(q3),
        is_normal=is_normal,
        shapiro_p=float(shapiro_p),
    )


@dataclasses.dataclass
class ComparisonResult:
    test_used: str  # "t-test" | "mann-whitney-u"
    statistic: float
    p_value: float
    effect_size_name: str  # "cohens_d" | "cliffs_delta"
    effect_size: float
    significant_at_05: bool


def _cohens_d(a: np.ndarray, b: np.ndarray) -> float:
    n1, n2 = len(a), len(b)
    pooled_std = math.sqrt(((n1 - 1) * a.std(ddof=1) ** 2 + (n2 - 1) * b.std(ddof=1) ** 2) / (n1 + n2 - 2))
    if pooled_std == 0:
        return 0.0
    return float((a.mean() - b.mean()) / pooled_std)


def _cliffs_delta(a: np.ndarray, b: np.ndarray) -> float:
    """Non-parametric effect size: P(a > b) - P(a < b), each pair compared once."""
    gt = sum(1 for x in a for y in b if x > y)
    lt = sum(1 for x in a for y in b if x < y)
    return (gt - lt) / (len(a) * len(b))


def compare(sample_a: list[float], sample_b: list[float], label_a: str = "A", label_b: str = "B") -> ComparisonResult:
    """E3 (proposed vs. monolith) / E5 (PCM vs. compressed) use this: picks
    t-test+Cohen's d when both samples look normal (Shapiro-Wilk), else
    Mann-Whitney U + Cliff's delta.
    """
    a, b = np.asarray(sample_a, dtype=float), np.asarray(sample_b, dtype=float)
    if len(a) < 3 or len(b) < 3:
        raise ValueError("compare() needs at least 3 values per sample for a meaningful test")

    a_normal = scipy_stats.shapiro(a).pvalue > 0.05
    b_normal = scipy_stats.shapiro(b).pvalue > 0.05

    if a_normal and b_normal:
        stat, p = scipy_stats.ttest_ind(a, b, equal_var=False)  # Welch's t-test
        return ComparisonResult(
            test_used="t-test",
            statistic=float(stat),
            p_value=float(p),
            effect_size_name="cohens_d",
            effect_size=_cohens_d(a, b),
            significant_at_05=p < 0.05,
        )

    stat, p = scipy_stats.mannwhitneyu(a, b, alternative="two-sided")
    return ComparisonResult(
        test_used="mann-whitney-u",
        statistic=float(stat),
        p_value=float(p),
        effect_size_name="cliffs_delta",
        effect_size=_cliffs_delta(a, b),
        significant_at_05=p < 0.05,
    )


def repeat_sync(fn, n: int) -> list:
    """Run a synchronous callable n times, returning every result. Exceptions
    propagate — a failed run should stop the benchmark, not be silently dropped
    (E7 requires n>=10 independent runs; silently dropping failures would
    understate real error rates).
    """
    return [fn() for _ in range(n)]


async def repeat_async(fn, n: int) -> list:
    return [await fn() for _ in range(n)]
