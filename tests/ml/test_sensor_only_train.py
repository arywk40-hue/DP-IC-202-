import unittest

import pandas as pd

from ml.sensor_only.train_model import build_split


class SensorOnlySplitTest(unittest.TestCase):
    def test_split_separates_future_validation_and_complete_locations(self):
        rows = []
        for location in ["A", "B", "C", "D", "E"]:
            for day in range(10):
                rows.append(
                    {
                        "location_name": location,
                        "last_updated": f"2026-01-{day + 1:02d}T00:00:00Z",
                    }
                )
        identifiers = pd.DataFrame(rows)
        train, validation, test, manifest = build_split(identifiers, 0.2, 0.2)

        self.assertFalse((train & validation).any())
        self.assertFalse((train & test).any())
        self.assertFalse((validation & test).any())
        self.assertEqual(manifest["holdout_locations"], ["E"])
        self.assertTrue(identifiers.loc[test, "location_name"].eq("E").all())
        train_max = pd.to_datetime(identifiers.loc[train, "last_updated"], utc=True).max()
        validation_min = pd.to_datetime(
            identifiers.loc[validation, "last_updated"], utc=True
        ).min()
        self.assertLess(train_max, validation_min)


if __name__ == "__main__":
    unittest.main()

