import os
from distutils.util import strtobool
import opendp.smartnoise.core as sn
from tests import (TEST_PUMS_PATH, TEST_PUMS_NAMES,
                   TEST_EDUC_PATH, TEST_EDUC_NAMES)

# Used to skip showing plots, etc.
#
IS_CI_BUILD = strtobool(os.environ.get('IS_CI_BUILD', 'False'))


def test_multilayer_analysis(run=True):
    with sn.Analysis() as analysis:
        PUMS = sn.Dataset(path=TEST_PUMS_PATH, column_names=TEST_PUMS_NAMES)

        age = sn.to_float(PUMS['age'])
        sex = sn.to_bool(PUMS['sex'], true_label="TRUE")

        age_clamped = sn.clamp(age, lower=0., upper=150.)
        age_resized = sn.resize(age_clamped, number_rows=1000)

        race = sn.to_float(PUMS['race'])
        mean_age = sn.dp_mean(
            data=race,
            privacy_usage={'epsilon': .65},
            data_lower=0.,
            data_upper=100.,
            data_rows=500
        )
        analysis.release()

        sex_plus_22 = sn.add(
            sn.to_float(sex),
            22.,
            left_rows=1000, left_lower=0., left_upper=1.)

        sn.dp_mean(
            age_resized / 2. + sex_plus_22,
            privacy_usage={'epsilon': .1},
            data_lower=mean_age - 5.2,
            data_upper=102.,
            data_rows=500) + 5.

        sn.dp_variance(
            data=sn.to_float(PUMS['educ']),
            privacy_usage={'epsilon': .15},
            data_rows=1000,
            data_lower=0.,
            data_upper=12.
        )

        # sn.dp_raw_moment(
        #     sn.to_float(PUMS['married']),
        #     privacy_usage={'epsilon': .15},
        #     data_rows=1000000,
        #     data_lower=0.,
        #     data_upper=12.,
        #     order=3
        # )
        #
        # sn.dp_covariance(
        #     left=sn.to_float(PUMS['age']),
        #     right=sn.to_float(PUMS['married']),
        #     privacy_usage={'epsilon': .15},
        #     left_rows=1000,
        #     right_rows=1000,
        #     left_lower=0.,
        #     left_upper=1.,
        #     right_lower=0.,
        #     right_upper=1.
        # )

    if run:
        analysis.release()

    return analysis


def test_dp_linear_stats(run=True):
    with sn.Analysis() as analysis:
        dataset_pums = sn.Dataset(path=TEST_PUMS_PATH, column_names=TEST_PUMS_NAMES)


        age = dataset_pums['age']
        analysis.release()

        num_records = sn.dp_count(
            age,
            privacy_usage={'epsilon': .5},
            lower=0,
            upper=10000
        )
        analysis.release()

        print("number of records:", num_records.value)

        vars = sn.to_float(dataset_pums[["age", "income"]])

        covariance = sn.dp_covariance(
            data=vars,
            privacy_usage={'epsilon': .5},
            data_lower=[0., 0.],
            data_upper=[150., 150000.],
            data_rows=num_records)
        print("covariance released")

        num_means = sn.dp_mean(
            data=vars,
            privacy_usage={'epsilon': .5},
            data_lower=[0., 0.],
            data_upper=[150., 150000.],
            data_rows=num_records)

        analysis.release()
        print("covariance:\n", covariance.value)
        print("means:\n", num_means.value)

        age = sn.to_float(age)

        age_variance = sn.dp_variance(
            age,
            privacy_usage={'epsilon': .5},
            data_lower=0.,
            data_upper=150.,
            data_rows=num_records)

        analysis.release()

        print("age variance:", age_variance.value)

        # If I clamp, impute, resize, then I can reuse their properties for multiple statistics
        clamped_age = sn.clamp(age, lower=0., upper=100.)
        imputed_age = sn.impute(clamped_age)
        preprocessed_age = sn.resize(imputed_age, number_rows=num_records)

        # properties necessary for mean are statically known
        mean = sn.dp_mean(
            preprocessed_age,
            privacy_usage={'epsilon': .5}
        )

        # properties necessary for variance are statically known
        variance = sn.dp_variance(
            preprocessed_age,
            privacy_usage={'epsilon': .5}
        )

        # sum doesn't need n, so I pass the data in before resizing
        age_sum = sn.dp_sum(
            imputed_age,
            privacy_usage={'epsilon': .5}
        )

        # mean with lower, upper properties propagated up from prior bounds
        transformed_mean = sn.dp_mean(
            -(preprocessed_age + 2.),
            privacy_usage={'epsilon': .5}
        )

        analysis.release()
        print("age transformed mean:", transformed_mean.value)

        # releases may be pieced together from combinations of smaller components
        custom_mean = sn.laplace_mechanism(
            sn.mean(preprocessed_age),
            privacy_usage={'epsilon': .5})

        custom_maximum = sn.laplace_mechanism(
            sn.maximum(preprocessed_age),
            privacy_usage={'epsilon': .5})

        custom_maximum = sn.laplace_mechanism(
            sn.maximum(preprocessed_age),
            privacy_usage={'epsilon': .5})

        custom_quantile = sn.laplace_mechanism(
            sn.quantile(preprocessed_age, alpha=.5),
            privacy_usage={'epsilon': 500})

        income = sn.to_float(dataset_pums['income'])
        income_max = sn.laplace_mechanism(
            sn.maximum(income, data_lower=0., data_upper=1000000.),
            privacy_usage={'epsilon': 10})

        # releases may also be postprocessed and reused as arguments to more components
        age_sum + custom_maximum * 23.

        analysis.release()
        print("laplace quantile:", custom_quantile.value)

        age_histogram = sn.dp_histogram(
            sn.to_int(age, lower=0, upper=100),
            edges=list(range(0, 100, 25)),
            null_value=150,
            privacy_usage={'epsilon': 2.}
        )

        sex_histogram = sn.dp_histogram(
            sn.to_bool(dataset_pums['sex'], true_label="1"),
            privacy_usage={'epsilon': 2.}
        )

        education_histogram = sn.dp_histogram(
            dataset_pums['educ'],
            categories=["5", "7", "10"],
            null_value="-1",
            privacy_usage={'epsilon': 2.}
        )

        analysis.release()

        print("age histogram: ", age_histogram.value)
        print("sex histogram: ", sex_histogram.value)
        print("education histogram: ", education_histogram.value)

    if run:
        analysis.release()

        # get the mean computed when release() was called
        print(mean.value)
        print(variance.value)

    return analysis


def test_dp_count(run=True):
    with sn.Analysis() as analysis:
        dataset_pums = sn.Dataset(path=TEST_PUMS_PATH, column_names=TEST_PUMS_NAMES)


        count = sn.dp_count(
            dataset_pums['sex'] == '1',
            privacy_usage={'epsilon': 0.5})

    if run:
        analysis.release()
        print(count.value)

    return analysis


def test_raw_dataset(run=True):
    with sn.Analysis() as analysis:
        data = sn.to_float(sn.Dataset(value=[1., 2., 3., 4., 5.]))

        sn.dp_mean(
            data=data,
            privacy_usage={'epsilon': 1},
            data_lower=0.,
            data_upper=10.,
            data_rows=10,
            data_columns=1)

    if run:
        analysis.release()

    return analysis


def test_everything(run=True):
    with sn.Analysis() as analysis:
        data = sn.Dataset(path=TEST_PUMS_PATH, column_names=TEST_PUMS_NAMES)

        age_int = sn.to_int(data['age'], 0, 150)
        sex = sn.to_bool(data['sex'], "1")
        educ = sn.to_float(data['educ'])
        race = data['race']
        income = sn.to_float(data['income'])
        married = sn.to_bool(data['married'], "1")

        numerics = sn.to_float(data[['age', 'income']])

        # intentionally busted component
        # print("invalid component id ", (sex + "a").component_id)

        # broadcast scalar over 2d, broadcast scalar over 1d, columnar broadcasting, left and right mul
        numerics * 2. + 2. * educ

        # add different values for each column
        numerics + [[1., 2.]]

        # index into first column
        age = sn.index(numerics, indices=0)
        income = sn.index(numerics, mask=[False, True])

        # boolean ops and broadcasting
        mask = sex & married | (~married ^ False) | (age > 50.) | (age_int == 25)

        # numerical clamping
        sn.clamp(numerics, 0., [150., 150_000.])
        sn.clamp(data['educ'], categories=[str(i) for i in range(8, 10)], null_value="-1")

        sn.count(mask)
        sn.covariance(age, income)
        sn.digitize(educ, edges=[1., 3., 10.], null_value=-1)

        # checks for safety against division by zero
        income / 2.
        income / sn.clamp(educ, 5., 20.)

        sn.dp_count(data, privacy_usage={"epsilon": 0.5})
        sn.dp_count(mask, privacy_usage={"epsilon": 0.5})

        sn.dp_histogram(mask, privacy_usage={"epsilon": 0.5})
        age = sn.impute(sn.clamp(age, 0., 150.))
        sn.dp_maximum(age, privacy_usage={"epsilon": 0.5})
        sn.dp_minimum(age, privacy_usage={"epsilon": 0.5})
        sn.dp_median(age, privacy_usage={"epsilon": 0.5})

        age_n = sn.resize(age, number_rows=800)
        sn.dp_mean(age_n, privacy_usage={"epsilon": 0.5})
        sn.dp_raw_moment(age_n, order=3, privacy_usage={"epsilon": 0.5})

        sn.dp_sum(age, privacy_usage={"epsilon": 0.5})
        sn.dp_variance(age_n, privacy_usage={"epsilon": 0.5})

        sn.filter(income, mask)
        race_histogram = sn.histogram(race, categories=["1", "2", "3"], null_value="3")
        sn.histogram(income, edges=[0., 10000., 50000.], null_value=-1)

        sn.dp_histogram(married, privacy_usage={"epsilon": 0.5})

        sn.gaussian_mechanism(race_histogram, privacy_usage={"epsilon": 0.5, "delta": .000001})
        sn.laplace_mechanism(race_histogram, privacy_usage={"epsilon": 0.5, "delta": .000001})

        sn.raw_moment(educ, order=3)

        sn.log(sn.clamp(educ, 0.001, 50.))
        sn.maximum(educ)
        sn.mean(educ)
        sn.minimum(educ)

        educ % 2.
        educ ** 2.

        sn.quantile(educ, .32)

        sn.resize(educ, number_rows=1200, lower=0., upper=50.)
        sn.resize(race, number_rows=1200, categories=["1", "2"], weights=[1, 2])
        sn.resize(data[["age", "sex"]], 1200, categories=[["1", "2"], ["a", "b"]], weights=[1, 2])
        sn.resize(
            data[["age", "sex"]], 1200,
            categories=[["1", "2"], ["a", "b", "c"]],
            weights=[[1, 2], [3, 7, 2]])

        sn.sum(educ)
        sn.variance(educ)

    if run:
        analysis.release()

    return analysis


def test_histogram():
    import numpy as np

    # establish data information

    data = np.genfromtxt(TEST_PUMS_PATH, delimiter=',', names=True)
    education_categories = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17"]

    income = list(data[:]['income'])
    income_edges = list(range(0, 100_000, 10_000))

    print('actual', np.histogram(income, bins=income_edges)[0])

    with sn.Analysis() as analysis:
        data = sn.Dataset(path=TEST_PUMS_PATH, column_names=TEST_PUMS_NAMES)
        income = sn.to_int(data['income'], lower=0, upper=0)
        sex = sn.to_bool(data['sex'], true_label="1")

        income_histogram = sn.dp_histogram(
            income,
            edges=income_edges,
            privacy_usage={'epsilon': 1.})

    analysis.release()

    print("Income histogram Geometric DP release:   " + str(income_histogram.value))


def test_covariance():
    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt

    data = np.genfromtxt(TEST_PUMS_PATH, delimiter=',', names=True)

    with sn.Analysis() as analysis:
        wn_data = sn.Dataset(path=TEST_PUMS_PATH, column_names=TEST_PUMS_NAMES)
        # get full covariance matrix
        cov = sn.dp_covariance(data=sn.to_float(wn_data['age', 'sex', 'educ', 'income', 'married']),
                               privacy_usage={'epsilon': 10},
                               data_lower=[0., 0., 1., 0., 0.],
                               data_upper=[100., 1., 16., 500_000., 1.],
                               data_rows=1000)
    analysis.release()

    # store DP covariance and correlation matrix
    dp_cov = cov.value
    print(dp_cov)
    dp_corr = dp_cov / np.outer(np.sqrt(np.diag(dp_cov)), np.sqrt(np.diag(dp_cov)))

    # get non-DP covariance/correlation matrices
    age = list(data[:]['age'])
    sex = list(data[:]['sex'])
    educ = list(data[:]['educ'])
    income = list(data[:]['income'])
    married = list(data[:]['married'])
    non_dp_cov = np.cov([age, sex, educ, income, married])
    non_dp_corr = non_dp_cov / np.outer(np.sqrt(np.diag(non_dp_cov)), np.sqrt(np.diag(non_dp_cov)))

    print('Non-DP Covariance Matrix:\n{0}\n\n'.format(pd.DataFrame(non_dp_cov)))
    print('Non-DP Correlation Matrix:\n{0}\n\n'.format(pd.DataFrame(non_dp_corr)))
    print('DP Correlation Matrix:\n{0}'.format(pd.DataFrame(dp_corr)))

    # skip plot step
    if IS_CI_BUILD:
        return

    plt.imshow(non_dp_corr - dp_corr, interpolation='nearest')
    plt.colorbar()
    plt.show()


def test_properties():
    with sn.Analysis():
        # load data
        data = sn.Dataset(path=TEST_PUMS_PATH, column_names=TEST_PUMS_NAMES)

        # establish data
        age_dt = sn.cast(data['age'], 'FLOAT')

        # ensure data are non-null
        non_null_age_dt = sn.impute(age_dt, distribution='Uniform', lower=0., upper=100.)
        clamped = sn.clamp(age_dt, lower=0., upper=100.)

        # create potential for null data again
        potentially_null_age_dt = non_null_age_dt / 0.

        # print('original properties:\n{0}\n\n'.format(age_dt.properties))
        print('properties after imputation:\n{0}\n\n'.format(non_null_age_dt.nullity))
        print('properties after nan mult:\n{0}\n\n'.format(potentially_null_age_dt.nullity))

        print("lower", clamped.lower)
        print("upper", clamped.upper)
        print("releasable", clamped.releasable)
        # print("props", clamped.properties)
        print("data_type", clamped.data_type)
        print("categories", clamped.categories)


def test_reports():
    with sn.Analysis() as analysis:
        # load data
        data = sn.Dataset(path=TEST_PUMS_PATH, column_names=TEST_PUMS_NAMES)
        # get mean of age
        age_mean = sn.dp_mean(
            data=sn.to_float(data['age']),
            privacy_usage={'epsilon': .65},
            data_lower=0.,
            data_upper=100.,
            data_rows=1000)
        print("Pre-Release\n")
        print("DP mean of age: {0}".format(age_mean.value))
        print("Privacy usage: {0}\n\n".format(analysis.privacy_usage))

        # TODO: uncomment when reports fix is merged
        # assert len(analysis.report()) == 1
