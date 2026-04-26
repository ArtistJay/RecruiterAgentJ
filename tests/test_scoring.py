"""Unit tests for scoring utilities."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.tools.scoring import (
    calculate_match_score,
    calculate_interest_score,
    calculate_combined_score,
    get_recommendation,
)


def test_match_score_perfect():
    score = calculate_match_score(100, 100, 100, 100, 100)
    assert score == 100.0, f"Expected 100, got {score}"


def test_match_score_zero():
    score = calculate_match_score(0, 0, 0, 0, 0)
    assert score == 0.0, f"Expected 0, got {score}"


def test_match_score_weights():
    # Only skills (40%) at 100, rest 0
    score = calculate_match_score(100, 0, 0, 0, 0)
    assert score == 40.0, f"Expected 40, got {score}"


def test_interest_score_clamp():
    # Max red flags should clamp to 0
    score = calculate_interest_score(0, 0, 0, 0, 100)
    assert score == 0.0, f"Expected 0 (clamped), got {score}"


def test_interest_score_perfect():
    score = calculate_interest_score(100, 100, 100, 100, 0)
    assert score == 100.0, f"Expected 100, got {score}"


def test_combined_score():
    score = calculate_combined_score(80, 60)
    expected = round(0.6 * 80 + 0.4 * 60, 2)
    assert score == expected, f"Expected {expected}, got {score}"


def test_combined_custom_weights():
    score = calculate_combined_score(80, 60, match_weight=0.5, interest_weight=0.5)
    expected = round(0.5 * 80 + 0.5 * 60, 2)
    assert score == expected, f"Expected {expected}, got {score}"


def test_recommendations():
    assert get_recommendation(85) == "Strong Yes 🟢"
    assert get_recommendation(65) == "Yes 🟡"
    assert get_recommendation(45) == "Maybe 🟠"
    assert get_recommendation(20) == "No 🔴"


if __name__ == "__main__":
    tests = [
        test_match_score_perfect,
        test_match_score_zero,
        test_match_score_weights,
        test_interest_score_clamp,
        test_interest_score_perfect,
        test_combined_score,
        test_combined_custom_weights,
        test_recommendations,
    ]

    passed = 0
    for t in tests:
        try:
            t()
            print(f"  ✅ {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  ❌ {t.__name__}: {e}")
        except Exception as e:
            print(f"  ❌ {t.__name__}: {e}")

    print(f"\n{'='*40}")
    print(f"  {passed}/{len(tests)} tests passed")
