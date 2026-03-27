from evidently.report import Report
from evidently.metric_preset import DataDriftPreset
import pandas as pd
import numpy as np

np.random.seed(42)

train_df = pd.DataFrame({
"age": np.random.normal(35, 10, 1000),
"income": np.random.normal(50000, 15000, 1000),
"city_code": np.random.choice([1, 2, 3], 1000, p=[0.5, 0.3, 0.2]),
})

prod_df = pd.DataFrame({
"age": np.random.normal(42, 12, 1000),
"income": np.random.normal(62000, 18000, 1000),
"city_code": np.random.choice([1, 2, 3], 1000, p=[0.3, 0.4, 0.3]),
})

report = Report(metrics=[DataDriftPreset()])
report.run(reference_data=train_df, current_data=prod_df)

report.save_html("evidently_drift_report.html")
print("Saved: evidently_drift_report.html")