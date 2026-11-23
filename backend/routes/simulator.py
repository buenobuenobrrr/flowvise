"""Portfolio simulation routes — extracted from server.py.

Endpoints:
  POST /api/simulation/simple        — deterministic compound-interest projection
  POST /api/simulation/monte-carlo   — stochastic Monte-Carlo distribution

Behavior is byte-identical to the original server.py implementation.
"""
import math
import random
from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from core import get_current_user

router = APIRouter()

MONTE_CARLO_CHART_PATHS = 200
MONTE_CARLO_MAX_POINTS = 60


class SimulationRequest(BaseModel):
    initial_investment: float
    monthly_contribution: float = 0
    years: int = 10
    expected_return: float = 0.07  # 7% annual
    risk_level: str = "moderate"  # conservative, moderate, aggressive


class MonteCarloRequest(BaseModel):
    initial_investment: float
    monthly_contribution: float = 0
    years: int = 10
    expected_return: float = 0.07
    volatility: float = 0.15
    simulations: int = 500


def _run_monte_carlo_finals(
    num_sims: int, initial: float, months: int,
    monthly_return: float, monthly_vol: float, contribution: float,
) -> List[float]:
    """Run Monte Carlo simulations and return sorted final balances."""
    results = []
    for _ in range(num_sims):
        balance = initial
        for _ in range(months):
            monthly_r = random.gauss(monthly_return, monthly_vol)
            balance = max(0, balance * (1 + monthly_r) + contribution)
        results.append(balance)
    results.sort()
    return results


def _run_monte_carlo_paths(
    initial: float, months: int, monthly_return: float,
    monthly_vol: float, contribution: float, years: int,
) -> List[Dict[str, Any]]:
    """Run representative paths and compute percentile timeline for charting."""
    sample_paths = []
    random.seed(42)  # Reproducible for chart
    for _ in range(MONTE_CARLO_CHART_PATHS):
        path = []
        balance = initial
        for m in range(months + 1):
            if m % max(1, months // MONTE_CARLO_MAX_POINTS) == 0:
                path.append(round(balance, 2))
            if m < months:
                monthly_r = random.gauss(monthly_return, monthly_vol)
                balance = max(0, balance * (1 + monthly_r) + contribution)
        sample_paths.append(path)

    num_points = len(sample_paths[0])
    timeline = []
    for i in range(num_points):
        values = sorted(p[i] for p in sample_paths)
        n = len(values)
        timeline.append({
            "point": i,
            "year": round(i * years / max(1, num_points - 1), 2),
            "p10": round(values[int(n * 0.1)], 2),
            "p25": round(values[int(n * 0.25)], 2),
            "p50": round(values[int(n * 0.5)], 2),
            "p75": round(values[int(n * 0.75)], 2),
            "p90": round(values[int(n * 0.9)], 2),
        })
    return timeline


@router.post("/simulation/simple")
async def simple_simulation(
    req: SimulationRequest,
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Simple compound interest projection."""
    monthly_rate = req.expected_return / 12
    months = req.years * 12

    timeline = []
    balance = req.initial_investment
    total_invested = req.initial_investment

    for month in range(months + 1):
        year = month / 12
        timeline.append({
            "month": month,
            "year": round(year, 2),
            "balance": round(balance, 2),
            "invested": round(total_invested, 2),
            "gains": round(balance - total_invested, 2),
        })
        if month < months:
            balance = balance * (1 + monthly_rate) + req.monthly_contribution
            total_invested += req.monthly_contribution

    final = timeline[-1]
    return {
        "timeline": timeline[::max(1, len(timeline) // 60)],  # max 60 data points
        "summary": {
            "final_balance": final["balance"],
            "total_invested": final["invested"],
            "total_gains": final["gains"],
            "return_pct": round((final["balance"] / final["invested"] - 1) * 100, 1)
                if final["invested"] > 0 else 0,
            "years": req.years,
            "annual_return": req.expected_return * 100,
        },
    }


@router.post("/simulation/monte-carlo")
async def monte_carlo_simulation(
    req: MonteCarloRequest,
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Monte Carlo simulation with multiple random scenarios."""
    monthly_return = req.expected_return / 12
    monthly_vol = req.volatility / math.sqrt(12)
    months = req.years * 12
    num_sims = min(req.simulations, 1000)

    all_final_values = _run_monte_carlo_finals(
        num_sims, req.initial_investment, months,
        monthly_return, monthly_vol, req.monthly_contribution,
    )
    percentile_timeline = _run_monte_carlo_paths(
        req.initial_investment, months, monthly_return,
        monthly_vol, req.monthly_contribution, req.years,
    )

    total_invested = req.initial_investment + req.monthly_contribution * months
    profit_count = sum(1 for v in all_final_values if v > total_invested)
    prob_profit = profit_count / num_sims

    n = len(all_final_values)
    return {
        "percentile_timeline": percentile_timeline,
        "summary": {
            "simulations_run": num_sims,
            "years": req.years,
            "total_invested": round(total_invested, 2),
            "worst_case": round(all_final_values[int(n * 0.05)], 2),
            "p10": round(all_final_values[int(n * 0.1)], 2),
            "median": round(all_final_values[int(n * 0.5)], 2),
            "p90": round(all_final_values[int(n * 0.9)], 2),
            "best_case": round(all_final_values[int(n * 0.95)], 2),
            "probability_of_profit": round(prob_profit * 100, 1),
            "expected_return_pct": req.expected_return * 100,
            "volatility_pct": req.volatility * 100,
        },
    }
