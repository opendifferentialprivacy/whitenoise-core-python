from pprint import pprint

import pytest

import opendp.whitenoise.core as wn
from tests import TEST_PUMS_PATH, TEST_PUMS_NAMES


def dp_all(numeric, categorical, args):
    return {
        "covariance": wn.dp_covariance(left=numeric, right=numeric, **args),
        "histogram": wn.dp_histogram(categorical, **args),
        "maximum": wn.dp_maximum(numeric, **args),
        "mean": wn.dp_mean(numeric, **args),
        "median": wn.dp_median(numeric, **args),
        "minimum": wn.dp_minimum(numeric, **args),
        "quantile": wn.dp_quantile(numeric, .75, **args),
        "raw_moment": wn.dp_raw_moment(numeric, 2, **args),
        "sum": wn.dp_sum(numeric, **args),
        "variance": wn.dp_variance(numeric, **args)
    }

def dp_all_snapping(numeric, categorical, args):
    return {
        "covariance": wn.dp_covariance(left=numeric, right=numeric, **args),
        "histogram": wn.dp_histogram(categorical, **args),
        "maximum": wn.dp_maximum(numeric, **args),
        "mean": wn.dp_mean(numeric, **args),
        "median": wn.dp_median(numeric, **args),
        "minimum": wn.dp_minimum(numeric, **args),
        "quantile": wn.dp_quantile(numeric, .75, **args),
        # "raw_moment": wn.dp_raw_moment(numeric, 2, **args),
        "sum": wn.dp_sum(numeric, **args),
        "variance": wn.dp_variance(numeric, **args)
    }


def analytic_gaussian_similarity():
    analytic_gauss_estimates = []
    gauss_estimates = []
    with wn.Analysis(strict_parameter_checks=False):
        PUMS = wn.Dataset(path=TEST_PUMS_PATH, column_names=TEST_PUMS_NAMES)

        age = wn.impute(
            wn.to_float(PUMS['age']),
            data_lower=0.,
            data_upper=100.,
            data_rows=1000)

        for i in range(100):
            an_gauss_component = wn.dp_mean(
                age, mechanism="AnalyticGaussian",
                privacy_usage={"epsilon": 1.0, "delta": 1E-6})
            gauss_component = wn.dp_mean(
                age, mechanism="Gaussian",
                privacy_usage={"epsilon": 1.0, "delta": 1E-6})

            # this triggers an analysis.release (which also computes gauss_component)
            analytic_gauss_estimates.append(an_gauss_component.value)
            gauss_estimates.append(gauss_component.value)

    print(sum(analytic_gauss_estimates) / len(analytic_gauss_estimates))
    print(sum(gauss_estimates) / len(gauss_estimates))


def snapping_similarity():
    snapping_estimates = []
    laplace_estimates = []
    with wn.Analysis(strict_parameter_checks=False):
        PUMS = wn.Dataset(path=TEST_PUMS_PATH, column_names=TEST_PUMS_NAMES)

        age = wn.impute(
            wn.to_float(PUMS['age']),
            data_lower=0.,
            data_upper=100.,
            data_rows=1000)

        for i in range(100):
            snapping_component = wn.dp_mean(
                age, mechanism="snapping",
                privacy_usage={"epsilon": 1.0, "delta": 1E-6})
            laplace_component = wn.dp_mean(
                age, mechanism="laplace",
                privacy_usage={"epsilon": 1.0, "delta": 1E-6})

            snapping_estimates.append(snapping_component.value)
            laplace_estimates.append(laplace_component.value)

    print(sum(snapping_estimates) / len(snapping_estimates))
    print(sum(laplace_estimates) / len(laplace_estimates))


@pytest.mark.parametrize(
    "args,constructor",
    [
        pytest.param({
            "mechanism": "AnalyticGaussian",
            "privacy_usage": {"epsilon": 2.0, "delta": 1E-6}
        }, dp_all, id="AnalyticGaussian"),
        pytest.param({
            "mechanism": "Gaussian",
            "privacy_usage": {"epsilon": 1.0, "delta": 1E-6}
        }, dp_all, id="Gaussian"),
        pytest.param({
            "mechanism": "Laplace",
            "privacy_usage": {"epsilon": 2.0, "delta": 1E-6}
        }, dp_all, id="Laplace"),
        # pytest.param({
        #     "mechanism": "Snapping",
        #     "privacy_usage": {"epsilon": 2.0, "delta": 1E-6}
        # }, dp_all_snapping, id="Snapping"),

        pytest.param(
            {
                "mechanism": "Gaussian",
                "privacy_usage": {"epsilon": 1.0, "delta": 1E-6}
            },
            dp_all,
            id="Gaussian_large_epsilon",
            marks=pytest.mark.xfail(raises=AssertionError)),
    ],
)
def test_mechanism(args, constructor):
    with wn.Analysis() as analysis:
        PUMS = wn.Dataset(path=TEST_PUMS_PATH, column_names=TEST_PUMS_NAMES)
        categorical = wn.resize(
            wn.clamp(PUMS['sex'], categories=["0", "1"], null_value="0"),
            number_rows=1000)

        numeric = wn.impute(
            wn.to_float(PUMS['age']),
            data_lower=0.,
            data_upper=100.,
            data_rows=1000)

        all = constructor(numeric, categorical, args)

        analysis.release()
        all_values = {stat: all[stat].value for stat in all}
        print()
        pprint(all_values)

        for value in all_values.values():
            assert value is not None


def test_snapping():
    with wn.Analysis():
        PUMS = wn.Dataset(path=TEST_PUMS_PATH, column_names=TEST_PUMS_NAMES)

        statistic = wn.mean(
            wn.to_float(PUMS['age']),
            data_lower=0.,
            data_upper=100.,
            data_rows=1000)

        privatized = wn.snapping_mechanism(
            statistic,
            lower=30.,
            upper=70.,
            binding_probability=0.4,
            privacy_usage={"epsilon": 0.1})

        print(privatized.value)
        print(privatized.get_accuracy(0.5))
        necessary_usage = privatized.from_accuracy(4., 0.5)
        print("usage: ", necessary_usage)
        print("accuracy: ", privatized.get_accuracy(0.5, necessary_usage))