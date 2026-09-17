from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

DATA_FILE = ROOT / "data" / "acentria_dashboard_data.csv"


def load_data():

    if DATA_FILE.exists():

        df = pd.read_csv(DATA_FILE)

        df["period"] = pd.to_datetime(df["period"])

        return df

    return pd.DataFrame()