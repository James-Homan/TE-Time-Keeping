import io
import pandas as pd

def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    """Return CSV bytes for a dataframe (UTF-8 BOM to help Excel)."""
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")
