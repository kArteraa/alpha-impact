from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parent
COMPANIES_CSV = FIXTURES_DIR / "df_Uid_data_hack.csv"
PAYMENTS_CSV = FIXTURES_DIR / "df_Uid_payment_hack.csv"
CLIENT = "U_901"
AMOUNTS = (1000000.0, 300000.0, 100000.0, 200000.0, 400000.0, 500000.0)
