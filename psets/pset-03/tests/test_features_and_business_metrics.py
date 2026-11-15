import unittest

import numpy as np
import pandas as pd

from src.business_metrics import (
    calibrate_pairwise_interval,
    coelution_proxy_metrics,
)
from src.pipeline import _mobile_phase_features, _molecule_features


class FeatureAndBusinessMetricTests(unittest.TestCase):
    def test_mobile_phase_parser_extracts_both_phases(self):
        features = _mobile_phase_features(
            "A[H2O=95;MeOH=5;ACN=0] B[H2O=5;MeOH=95;ACN=0]"
        )

        self.assertEqual(features["elu_a_h2o"], 95.0)
        self.assertEqual(features["elu_b_meoh"], 95.0)
        self.assertEqual(features["elu_a_acn"], 0.0)

    def test_molecule_descriptors_use_rdkit_supported_ring_count(self):
        features = _molecule_features("CCO")

        self.assertEqual(features["mol_ring_count"], 0.0)
        self.assertTrue(np.isfinite(features["mol_weight"]))

    def test_pair_interval_and_coelution_proxy_are_finite(self):
        actual = np.array([1.0, 1.2, 2.0, 2.2])
        predicted = np.array([1.05, 1.15, 2.05, 2.15])
        conditions = pd.Series(["method-a", "method-a", "method-b", "method-b"])
        compounds = pd.Series(["compound-a", "compound-b", "compound-c", "compound-d"])
        interval = calibrate_pairwise_interval(
            actual,
            predicted,
            conditions,
            compounds,
            coverage=0.95,
        )
        metrics = coelution_proxy_metrics(
            actual,
            predicted,
            conditions,
            compounds,
            interval,
        )

        self.assertEqual(interval["coverage"], 0.95)
        self.assertEqual(metrics["coelution_labels_are_proxy"], 1)
        self.assertEqual(metrics["comparison_pairs"], 2)
        self.assertTrue(np.isfinite(metrics["pairwise_prediction_interval_coverage"]))

    def test_pair_metrics_accept_nonconsecutive_input_indices(self):
        index = [3, 8, 12, 21]
        actual = pd.Series([1.0, 1.2, 2.0, 2.2], index=index)
        predicted = pd.Series([1.05, 1.15, 2.05, 2.15], index=index)
        conditions = pd.Series(["method-a", "method-a", "method-b", "method-b"], index=index)
        compounds = pd.Series(
            ["compound-a", "compound-b", "compound-c", "compound-d"],
            index=index,
        )

        interval = calibrate_pairwise_interval(
            actual, predicted, conditions, compounds, coverage=0.95
        )
        metrics = coelution_proxy_metrics(
            actual, predicted, conditions, compounds, interval
        )

        self.assertEqual(metrics["comparison_pairs"], 2)
        self.assertTrue(np.isfinite(metrics["pairwise_prediction_interval_coverage"]))


if __name__ == "__main__":
    unittest.main()
