# Downloads the data used by the notebook and saves it as CSV files in data/.
# The notebook only reads the CSV files, so this script does not need to be run again.
#
# Sources:
#   - Lockheed Martin 10-K figures: SEC EDGAR "company facts" API (free, no key)
#   - Monthly prices of LMT and of the S&P 500 total return index: Yahoo Finance (yfinance)
#   - 10-year US Treasury yield: FRED, series DGS10

import pandas as pd
import requests
import yfinance as yf

YEARS = [2021, 2022, 2023, 2024, 2025]

# Each line of the CSV: our column name -> the XBRL tag Lockheed Martin uses in its 10-K.
# A list means: use the first tag that has a value for that year.
TAGS = {
    # Income statement
    "revenue": ["Revenues"],
    "ebit": ["OperatingIncomeLoss"],
    "pretax_income": ["IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest"],
    "income_tax": ["IncomeTaxExpenseBenefit"],
    "interest_expense": ["InterestExpenseNonoperating", "InterestExpense"],
    # Cash flow statement
    "depreciation_amortization": ["DepreciationAndAmortization"],
    "capex": ["PaymentsToAcquireProductiveAssets"],
    # Balance sheet: working capital
    "receivables": ["ReceivablesNetCurrent"],
    "contract_assets": ["ContractWithCustomerAssetNetCurrent"],
    "inventories": ["InventoryNet"],
    "payables": ["AccountsPayableCurrent"],
    "contract_liabilities": ["ContractWithCustomerLiabilityCurrent"],
    # Balance sheet: equity bridge
    "cash": ["CashAndCashEquivalentsAtCarryingValue"],
    "total_debt": ["LongTermDebt"],
    "pension_liability": ["DefinedBenefitPensionPlanLiabilitiesNoncurrent"],
    "shares_outstanding": ["CommonStockSharesOutstanding"],
}


def get_10k_data():
    url = "https://data.sec.gov/api/xbrl/companyfacts/CIK0000936468.json"
    headers = {"User-Agent": "student DCF project"}
    facts = requests.get(url, headers=headers).json()["facts"]["us-gaap"]

    table = {}
    for column, tags in TAGS.items():
        table[column] = {}
        for year in YEARS:
            for tag in tags:
                if tag not in facts:
                    continue
                unit = list(facts[tag]["units"])[0]
                rows = facts[tag]["units"][unit]
                # Keep the full-year value (or year-end balance) reported in a 10-K
                rows = [r for r in rows if r["form"] == "10-K" and r["end"] == f"{year}-12-31"
                        and ("start" not in r or r["start"] == f"{year}-01-01")]
                if rows:
                    latest = max(rows, key=lambda r: r["filed"])  # latest filing wins
                    table[column][year] = latest["val"]
                    break

    df = pd.DataFrame(table)
    df.index.name = "year"
    # Dollars to millions of dollars, shares to millions of shares
    df = df / 1_000_000
    return df


def get_prices():
    tickers = {"LMT": "lmt", "^SP500TR": "sp500_total_return"}
    prices = pd.DataFrame()
    for ticker, name in tickers.items():
        data = yf.download(ticker, start="2020-12-01", end="2026-01-01", interval="1mo",
                           auto_adjust=True, progress=False)
        prices[name] = data["Close"][ticker]
    # Yahoo labels each month by its first day; the price is the last close of that month
    prices.index = prices.index.to_period("M")
    prices.index.name = "month"
    return prices.round(2)


def get_risk_free_rate():
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10&cosd=2025-12-01&coed=2025-12-31"
    rates = pd.read_csv(url).dropna()
    return rates


if __name__ == "__main__":
    get_10k_data().to_csv("data/lmt_10k.csv")
    get_prices().to_csv("data/monthly_prices.csv")
    print(get_risk_free_rate().tail(3))
