import requests
import os
from dotenv import load_dotenv
load_dotenv()
import os
from supabase import create_client
import pandas as pd
import datetime
from datetime import datetime
import logging
import argparse
import numpy as np
from bs4 import BeautifulSoup

def get_values(soup, data_dict, currency, fold):
    tbodies = soup.find("tbody")
    rows = tbodies.find_all("tr")
    for row in rows:
        td = row.find_all("td")
        key = td[0].find("span").get_text()
        values = [t.get_text() if t.get_text() != "-" else np.nan for t in td[1:]]
        if len(values) > 4:
            continue
        # if key == "Diluted Weighted Average Shares":
        #     data_dict[key] = [float(value) for value in values]
        #     continue
        try:
            if currency == "USD":
                if fold == "Billions":
                    values = [float(value) * rate * 1000000000 for value in values]
                else:
                    values = [float(value) * rate * 1000000 for value in values]
            else:
                if fold == "Billions":
                    values = [float(value) * 1000000000 for value in values]
                else:
                    values = [float(value) * 1000000 for value in values]
        except Exception as e:
            print(f"error di {symbol}, dengan error: {e}")
        # print("values: ", values)
        if key in expected_value:
            data_dict[key] = values

def get_dates_quarter(soup, symbol):
    data_dict = {"symbol" : [], "date" : []}
    period = soup.find("tr", class_ = "alignBottom")
    quarters = period.find_all("th")
    for quarter in quarters:
        try:
            year = quarter.find("span").get_text()
            day, month = quarter.find("div").get_text().split("/")
            date = str(year) + "-" + str(month) + "-" + str(day)
            data_dict["symbol"].append(symbol.upper() + ".JK")
            data_dict["date"].append(date)
        except:
            pass
    return data_dict

def get_dates_annual(soup, symbol):
    data_dict = {"symbol" : [], "date" : []}
    periods = soup.find_all("th")
    for index, period in enumerate(periods[1:]):
        data_dict["symbol"].append(symbol.upper() + ".JK")
        if period.get_text() == "":
            date = datetime.strptime(data_dict["date"][-1], '%Y-%m-%d').date()
            date = str(date.replace(year=date.year-1))
            data_dict["date"].append(date)
            continue
        try:
            year = period.find("span").get_text()
            day, month = period.find("div").get_text().split("/")
            date = str(year) + "-" + str(month) + "-" + str(day)
            data_dict["date"].append(date)
        except Exception as e:
            print(f"error pada {symbol}: {e}")
            pass
    return data_dict

def main(data_link, args):
    data_list = []
    for index, row in data_link.iterrows():
        if index == 4:
            break
        symbol = row["symbols"]
        link = row["href"]
        currency = row["currency"]
        fold = row["fold"]
        id = row["id"]
        # Income Statement
        is_url = f"https://www.investing.com{link}-income-statement"
        html_content = requests.get(is_url).text
        soup = BeautifulSoup(html_content, "html.parser")
        data_dict = get_dates_quarter(soup, symbol) if args.quarter else get_dates_annual(soup, symbol)
        get_values(soup, data_dict, currency, fold)
        # Balance Sheet
        bs_url = f"https://www.investing.com{link}-balance-sheet"
        html_content = requests.get(bs_url).text
        soup = BeautifulSoup(html_content, "html.parser")
        get_values(soup, data_dict, currency, fold)
        # Cash Flow
        bs_url = f"https://www.investing.com{link}-cash-flow"
        html_content = requests.get(bs_url).text
        soup = BeautifulSoup(html_content, "html.parser")
        get_values(soup, data_dict, currency, fold)
        not_avail = [na for na in expected_value if na not in data_dict.keys()]
        for na in not_avail:
            data_dict[na] = [np.nan, np.nan, np.nan, np.nan]
        data_list.append(pd.DataFrame(data_dict))
    df = pd.concat(data_list)
    return df

def fe_and_rename(df):
    df["total_debt"] = df["Current Port. of LT Debt/Capital Leases"] + df["Total Long Term Debt"]
    df["stackholders_equity"] = df["Total Liabilities & Shareholders' Equity"] - df["Total Liabilities"] - df["Minority Interest"]
    df["ebit"] = df["Net Income Before Taxes"] - df["Interest Expense (Income) - Net Operating"]
    df["total_non_current_assets"] = df["Total Assets"] - df["Total Current Assets"]
    df["ebitda"] = np.nan
    columns_rename = {
        "Cash From Operating Activities" : "net_operating_cash_flow",
        "Total Assets" : "total_assets",
        "Total Liabilities" : "total_liabilities",
        "Total Current Liabilities" : "total_current_liabilities",
        "Total Equity" : "total_equity",
        "Total Revenue" : "total_revenue",
        "Net Income" : "net_income",
        "Cash and Short Term Investments" : "cash_and_short_term_investments",
        "Cash & Equivalents" : "cash_only",
        "Cash & Due from Banks" : "total_cash_and_due_from_banks",
        "Diluted Weighted Average Shares" : "diluted_shares_outstanding",
        "Gross Profit" : "gross_income",
        "Net Income Before Taxes" : "pretax_income",
        "Provision for Income Taxes" : "income_taxes",
        "Free Cash Flow" : "free_cash_flow",
        "Interest Expense (Income) - Net Operating" : "interest_expense_non_operating",
        "Operating Income" : "operating_income"
    }
    data = df.rename(columns=columns_rename).drop(['Minority Interest', 'Current Port. of LT Debt/Capital Leases', 'Total Long Term Debt', "Total Liabilities & Shareholders' Equity", "Total Current Assets"], axis = 1)
    return data

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update financial data. If no argument is specified, the annual data will be updated.")
    parser.add_argument("-a", "--annual", action="store_true", default=False, help="Update annual financial data")
    parser.add_argument("-q", "--quarter", action="store_true", default=False, help="Update quarter financial data")

    args = parser.parse_args()
    if args.annual and args.quarter:
        print("Error: Please specify either -a or -q, not both.")
        raise SystemExit(1)
    
    data_link = pd.read_csv("investing_link.csv")

    expected_value = [
        # Income Statement
        "Total Revenue", "Net Income", "Diluted Weighted Average Shares",
        "Gross Profit", "Net Income Before Taxes", "Provision for Income Taxes",
        "Interest Expense (Income) - Net Operating", "Operating Income",
        "Cash & Due from Banks",

        # Balance Sheet
        "Total Assets", "Total Liabilities", "Total Current Liabilities", 
        "Total Equity", "Current Port. of LT Debt/Capital Leases", 
        "Total Long Term Debt", "Total Liabilities & Shareholders' Equity", 
        "Minority Interest", "Cash and Short Term Investments", 
        "Cash & Equivalents", "Total Current Assets",

        # Cash FLow
        "Cash From Operating Activities", "Free Cash Flow"
    ]
    url_currency = 'https://raw.githubusercontent.com/supertypeai/sectors_get_conversion_rate/master/conversion_rate.json'

    response = requests.get(url_currency)
    data = response.json()
    rate = float(data['USD']['IDR'])

    url_supabase = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    supabase = create_client(url_supabase, key)

    data = main(data_link, args)
    data = fe_and_rename(data)
    data.to_csv("quarter.csv", index = False) if args.quarter else data.to_csv("annual.csv", index = False)