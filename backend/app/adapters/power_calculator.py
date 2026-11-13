import math
from itertools import product
from uuid import UUID

import scipy
import statsmodels
from scipy.stats import norm
from statsmodels.stats.power import FTestAnovaPower, TTestIndPower, TTestPower

from app.domain.experiment import ExperimentPlan
from app.domain.preparation import (
    PowerAnalysis,
    PowerAnalysisRequest,
    PowerScenario,
    PowerTestType,
    TestAlternative,
)
from app.domain.preparation_ports import PowerCalculationError
from app.domain.project import GenerationMetadata


class StatsmodelsPowerCalculator:
    """Calculate supported sample sizes with versioned deterministic methods."""

    method_version = "power-v1"

    def calculate(
        self,
        project_id: UUID,
        plan: ExperimentPlan,
        plan_hash: str,
        request: PowerAnalysisRequest,
    ) -> PowerAnalysis:
        primary = self._scenario(
            request,
            request.effect_size,
            request.target_power,
        )
        effects = request.sensitivity_effect_sizes or [
            request.effect_size * 0.75,
            request.effect_size,
            request.effect_size * 1.25,
        ]
        powers = request.sensitivity_powers or sorted(
            {request.target_power, min(0.95, request.target_power + 0.1)}
        )
        sensitivity: list[PowerScenario] = []
        seen: set[tuple[float, float]] = set()
        for effect_size, target_power in product(effects, powers):
            key = (round(effect_size, 10), round(target_power, 10))
            if key == (
                round(request.effect_size, 10),
                round(request.target_power, 10),
            ) or key in seen:
                continue
            seen.add(key)
            sensitivity.append(self._scenario(request, effect_size, target_power))
        return PowerAnalysis(
            project_id=project_id,
            source_plan_id=plan.id,
            source_plan_hash=plan_hash,
            request=request,
            primary_result=primary,
            sensitivity_results=sensitivity,
            method=self._method_label(request.test_type),
            package_versions={
                "statsmodels": statsmodels.__version__,
                "scipy": scipy.__version__,
            },
            generation=GenerationMetadata(
                generator="deterministic",
                model=None,
                prompt_version=self.method_version,
            ),
        )

    def _scenario(
        self,
        request: PowerAnalysisRequest,
        effect_size: float,
        target_power: float,
    ) -> PowerScenario:
        try:
            nominal_per_group = self._nominal_group_sizes(
                request,
                effect_size,
                target_power,
            )
        except (RuntimeError, TypeError, ValueError, ZeroDivisionError) as error:
            raise PowerCalculationError(f"Power calculation failed: {error}") from error
        adjusted_per_group = [
            math.ceil(value / (1 - request.attrition_rate))
            for value in nominal_per_group
        ]
        return PowerScenario(
            effect_size=effect_size,
            target_power=target_power,
            nominal_total_n=sum(nominal_per_group),
            adjusted_total_n=sum(adjusted_per_group),
            nominal_per_group=nominal_per_group,
            adjusted_per_group=adjusted_per_group,
        )

    @staticmethod
    def _nominal_group_sizes(
        request: PowerAnalysisRequest,
        effect_size: float,
        target_power: float,
    ) -> list[int]:
        directional_effect = (
            -effect_size
            if request.alternative is TestAlternative.SMALLER
            else effect_size
        )
        if request.test_type is PowerTestType.INDEPENDENT_T:
            n_group_one = TTestIndPower().solve_power(
                effect_size=directional_effect,
                nobs1=None,
                alpha=request.alpha,
                power=target_power,
                ratio=request.allocation_ratio,
                alternative=request.alternative.value,
            )
            group_one = max(2, math.ceil(float(n_group_one)))
            group_two = max(2, math.ceil(group_one * request.allocation_ratio))
            return [group_one, group_two]
        if request.test_type is PowerTestType.PAIRED_T:
            participants = TTestPower().solve_power(
                effect_size=directional_effect,
                nobs=None,
                alpha=request.alpha,
                power=target_power,
                alternative=request.alternative.value,
            )
            return [max(2, math.ceil(float(participants)))]
        if request.test_type is PowerTestType.ONE_WAY_ANOVA:
            total = FTestAnovaPower().solve_power(
                effect_size=effect_size,
                nobs=None,
                alpha=request.alpha,
                power=target_power,
                k_groups=request.groups,
            )
            per_group = max(2, math.ceil(float(total) / request.groups))
            return [per_group] * request.groups
        if request.test_type is PowerTestType.CORRELATION:
            alpha_tail = (
                request.alpha / 2
                if request.alternative is TestAlternative.TWO_SIDED
                else request.alpha
            )
            z_alpha = norm.ppf(1 - alpha_tail)
            z_power = norm.ppf(target_power)
            fisher_z = math.atanh(effect_size)
            participants = ((z_alpha + z_power) / fisher_z) ** 2 + 3
            return [max(4, math.ceil(float(participants)))]
        raise ValueError(f"Unsupported test type: {request.test_type}")

    @staticmethod
    def _method_label(test_type: PowerTestType) -> str:
        return {
            PowerTestType.INDEPENDENT_T: "statsmodels TTestIndPower.solve_power",
            PowerTestType.PAIRED_T: "statsmodels TTestPower.solve_power",
            PowerTestType.ONE_WAY_ANOVA: "statsmodels FTestAnovaPower.solve_power",
            PowerTestType.CORRELATION: "Fisher z normal approximation using scipy.stats.norm",
        }[test_type]
