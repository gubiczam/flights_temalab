import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional  

def load_and_clean_data(file_path: Optional[str] = None) -> pd.DataFrame:
    target_path: Path
    
    if file_path is None:
        base_path = Path(__file__).resolve().parent.parent
        target_path = base_path / "data" / "raw" / "flights.csv"
    else:
        target_path = Path(file_path)
    
    if not target_path.exists():
        raise FileNotFoundError(f"Target path not exists: {target_path}")

    print(f"Adatok betöltése: {target_path} ...")
    df = pd.read_csv(target_path)

    initial_len = len(df)
    df = df.dropna(subset=['dep_time', 'arr_time', 'dep_delay', 'arr_delay'])
    print(f"Tisztítás kész: {initial_len - len(df)} db járat törlődött")

    conditions = [
        (df['hour'] >= 0) & (df['hour'] < 6),
        (df['hour'] >= 6) & (df['hour'] < 12),
        (df['hour'] >= 12) & (df['hour'] < 18),
        (df['hour'] >= 18) & (df['hour'] <= 24)
    ]
    choices = ['Hajnal', 'Délelőtt', 'Délután', 'Este']
    df['napszak'] = np.select(conditions, choices, default='Ismeretlen napszak')

    return df

if __name__ == "__main__":
    try:
        test_df = load_and_clean_data()
        print("\nSikeres a betöltés és a típusellenőrzés")
        print(test_df[['carrier', 'origin', 'dest', 'napszak', 'arr_delay']].head())
    except Exception as e:
        print(f"\nHiba történt: {e}")