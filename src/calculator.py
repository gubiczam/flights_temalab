import pandas as pd
import numpy as np

def calculate_reliability(df: pd.DataFrame) -> pd.DataFrame:
    df['is_delayed'] = (df['arr_delay'] > 15).astype(int)

    stats = df.groupby(['origin', 'dest', 'carrier', 'name', 'napszak']).agg(
        osszes_jarat=('id', 'count'),
        kesett_jaratok=('is_delayed', 'sum'),
        atlagos_keses=('arr_delay', 'mean')
    ).reset_index()

    stats['kesesi_esely'] = (stats['kesett_jaratok'] / stats['osszes_jarat']) * 100
    stats['kesesi_esely'] = stats['kesesi_esely'].round(1)
    stats['atlagos_keses'] = stats['atlagos_keses'].round(1)
    
    stats['score'] = (100 - stats['kesesi_esely']).round(1)

    return stats.sort_values(by=['origin', 'dest', 'score'], ascending=[True, True, False])
if __name__ == "__main__":
    from data_loader import load_and_clean_data
    
    df = load_and_clean_data()
    
    result = calculate_reliability(df)
    
    print("\nRanglista JFK -> LAX útvonalon:")
    print(result[result['dest'] == 'LAX'].head(5))