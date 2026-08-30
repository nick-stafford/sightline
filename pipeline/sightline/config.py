"""Cohort definition and the XBRL tag -> line item mapping."""

from pathlib import Path

PIPELINE_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = PIPELINE_DIR.parent
CACHE_DIR = PIPELINE_DIR / "cache"
SQL_DIR = PIPELINE_DIR / "sql"
DB_PATH = PIPELINE_DIR / "sightline.duckdb"
WEB_DATA_DIR = PROJECT_DIR / "web" / "public" / "data"

# SEC wants a real contact address in the User-Agent and <= 10 req/sec.
SEC_USER_AGENT = "Sightline Research (nicholas.alexander.stafford@gmail.com)"
SEC_DELAY = 0.2

# Athletic and outdoor apparel/footwear. Sticking to one sector keeps the peer
# comparison honest -- comparing Nike's margins to a grocer's would be noise.
# These eight all file 10-Ks under us-gaap with history back to 2018.
#
# Note: Arc'teryx is owned by Amer Sports (NYSE: AS), which reports under IFRS
# as a foreign private issuer and only listed in 2024. On Holding (ONON) is the
# same. Neither has us-gaap tags, so they can't go through this pipeline
# without a separate IFRS mapping.
COHORT = [
    {"ticker": "VFC", "name": "VF Corporation", "cik": "0000103379",
     "brands": "The North Face, Vans, Timberland"},
    {"ticker": "NKE", "name": "Nike", "cik": "0000320187",
     "brands": "Nike, Jordan, Converse"},
    {"ticker": "DECK", "name": "Deckers Outdoor", "cik": "0000910521",
     "brands": "Hoka, Ugg, Teva"},
    {"ticker": "LULU", "name": "Lululemon Athletica", "cik": "0001397187",
     "brands": "Lululemon"},
    {"ticker": "COLM", "name": "Columbia Sportswear", "cik": "0001050797",
     "brands": "Columbia, Sorel, prAna"},
    {"ticker": "UAA", "name": "Under Armour", "cik": "0001336917",
     "brands": "Under Armour"},
    {"ticker": "CROX", "name": "Crocs", "cik": "0001334036",
     "brands": "Crocs, HeyDude"},
    {"ticker": "YETI", "name": "YETI Holdings", "cik": "0001670592",
     "brands": "YETI"},
]

# The company the page is about. The other seven are the peer group -- they
# exist so YETI's ratios can be ranked against comparable businesses instead of
# being reported in a vacuum.
DEFAULT_TICKER = "YETI"

# YETI IPO'd in late 2018 but its S-1 backfilled FY2017, which is the first
# year with a complete set of statements.
START_YEAR = 2017

# Companies don't all use the same us-gaap tag for the same line item, and they
# switch tags between filings. So each line item gets a list of tags in priority
# order and we fill in missing years from further down the list.
#
# "duration" = reported over a period (income statement, cash flow)
# "instant"  = reported at a point in time (balance sheet)
LINE_ITEMS = {
    # Income statement
    "revenue": ("duration", "Revenue", [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
    ]),
    "cogs": ("duration", "Cost of Sales", [
        "CostOfGoodsAndServicesSold",
        "CostOfRevenue",
        "CostOfGoodsSold",
    ]),
    "gross_profit": ("duration", "Gross Profit", ["GrossProfit"]),
    "sga": ("duration", "SG&A", [
        "SellingGeneralAndAdministrativeExpense",
        "OperatingExpenses",
    ]),
    "operating_income": ("duration", "Operating Income", ["OperatingIncomeLoss"]),
    "interest_expense": ("duration", "Interest Expense", [
        "InterestExpense",
        "InterestExpenseDebt",
        "InterestExpenseNonoperating",
        "InterestAndDebtExpense",
        "InterestIncomeExpenseNet",
    ]),
    "pretax_income": ("duration", "Pre-Tax Income", [
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
    ]),
    "tax_expense": ("duration", "Income Tax Expense", ["IncomeTaxExpenseBenefit"]),
    "net_income": ("duration", "Net Income", ["NetIncomeLoss", "ProfitLoss"]),
    "eps_diluted": ("duration", "Diluted EPS", ["EarningsPerShareDiluted"]),
    "shares_diluted": ("duration", "Diluted Shares", [
        "WeightedAverageNumberOfDilutedSharesOutstanding",
    ]),

    # Balance sheet
    "cash": ("instant", "Cash & Equivalents", [
        "CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
    ]),
    "receivables": ("instant", "Accounts Receivable", [
        "AccountsReceivableNetCurrent",
        "ReceivablesNetCurrent",
    ]),
    # Nike tags inventory as finished goods rather than the generic InventoryNet.
    "inventory": ("instant", "Inventory", [
        "InventoryNet",
        "InventoryFinishedGoodsNetOfReserves",
    ]),
    "current_assets": ("instant", "Total Current Assets", ["AssetsCurrent"]),
    # After the 2019 lease standard (ASC 842) several companies moved to the
    # combined PP&E-plus-finance-lease-right-of-use tag, so both are needed to
    # get an unbroken series.
    "ppe_net": ("instant", "Property & Equipment, Net", [
        "PropertyPlantAndEquipmentNet",
        "PropertyPlantAndEquipmentAndFinanceLeaseRightOfUseAssetAfterAccumulatedDepreciationAndAmortization",
    ]),
    "total_assets": ("instant", "Total Assets", ["Assets"]),
    "accounts_payable": ("instant", "Accounts Payable", [
        "AccountsPayableCurrent",
        "AccountsPayableTradeCurrent",
        "AccountsPayableAndAccruedLiabilitiesCurrent",
    ]),
    "current_liabilities": ("instant", "Total Current Liabilities", ["LiabilitiesCurrent"]),
    "long_term_debt": ("instant", "Long-Term Debt", [
        "LongTermDebtNoncurrent",
        "LongTermDebt",
        "LongTermDebtAndCapitalLeaseObligations",
    ]),
    "total_liabilities": ("instant", "Total Liabilities", ["Liabilities"]),
    "retained_earnings": ("instant", "Retained Earnings", ["RetainedEarningsAccumulatedDeficit"]),
    "equity": ("instant", "Total Equity", [
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ]),

    # Cash flow
    "operating_cash_flow": ("duration", "Cash from Operations", [
        "NetCashProvidedByUsedInOperatingActivities",
        "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
    ]),
    "capex": ("duration", "Capital Expenditures", [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsToAcquireProductiveAssets",
        "PaymentsForCapitalImprovements",  # VF Corp uses this one
    ]),
    "depreciation_amortization": ("duration", "Depreciation & Amortization", [
        "DepreciationDepletionAndAmortization",
        "DepreciationAmortizationAndAccretionNet",
        "DepreciationAndAmortization",
    ]),
    "dividends_paid": ("duration", "Dividends Paid", [
        "PaymentsOfDividendsCommonStock",
        "PaymentsOfDividends",
    ]),
}
