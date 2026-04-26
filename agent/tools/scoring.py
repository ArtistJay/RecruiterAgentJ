"""Scoring utilities for agentJ."""


def calculate_match_score(
    skills_val: float,
    exp_val: float,
    edu_val: float,
    loc_val: float,
    bonus_val: float
) -> float:
    """
    Match Score (0-100).
    Weights: Skills 40%, Exp 25%, Edu 15%, Loc 10%, Bonus 10%
    """
    score = (
        0.40 * skills_val
        + 0.25 * exp_val
        + 0.15 * edu_val
        + 0.10 * loc_val
        + 0.10 * bonus_val
    )
    return round(min(max(score, 0), 100), 2)


def calculate_interest_score(
    enthusiasm: float,
    availability: float,
    salary_align: float,
    role_fit: float,
    red_flags: float
) -> float:
    """
    Interest Score (0-100).
    Weights: Enthusiasm 30%, Availability 25%, Salary 20%, Fit 15%, Flags -10%
    """
    score = (
        0.30 * enthusiasm
        + 0.25 * availability
        + 0.20 * salary_align
        + 0.15 * role_fit
        - 0.10 * red_flags
    )
    return round(min(max(score, 0), 100), 2)


def calculate_combined_score(
    match_score: float,
    interest_score: float,
    match_weight: float = 0.6,
    interest_weight: float = 0.4
) -> float:
    """Combined score. Default: 60% match + 40% interest."""
    return round(
        (match_weight * match_score) + (interest_weight * interest_score), 2
    )


def get_recommendation(combined_score: float) -> str:
    """Map combined score to recruiter-friendly recommendation."""
    if combined_score >= 80:
        return "Strong Yes 🟢"
    elif combined_score >= 60:
        return "Yes 🟡"
    elif combined_score >= 40:
        return "Maybe 🟠"
    else:
        return "No 🔴"
