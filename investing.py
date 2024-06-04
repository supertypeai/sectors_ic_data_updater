import requests
import os
from dotenv import load_dotenv
load_dotenv()
import os
from supabase import create_client
import pandas as pd
import datetime
import logging
import numpy as np
from bs4 import BeautifulSoup

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

data_list = []

def get_values(soup, data_dict):
    n_values = len(data_dict["year"])
    info = soup.find(class_="arial_11 lightgrayFont bottomRemark").get_text()
    currency = "IDR" if "IDR" in info else "USD"
    fold = "Millions" if "Millions" in info else "Billions"
    tbodies = soup.find("tbody")
    rows = tbodies.find_all("tr")
    for row in rows:
        td = row.find_all("td")
        key = td[0].find("span").get_text()
        values = [t.get_text() if t.get_text() != "-" else np.nan for t in td[1:]]
        if len(values) > 4:
            continue
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

for symbol, link in zip(data_link["symbols"].tolist()[:5], data_link["href"].tolist()[:5]):
    # Income Statement
    is_url = f"https://www.investing.com{link}-income-statement"
    html_content = requests.get(is_url).text
    soup = BeautifulSoup(html_content, "html.parser")
    period = soup.find("tr", class_ = "alignBottom")
    quarters = period.find_all("th")
    data_dict = {"symbols" : [], "year" : []}
    for quarter in quarters:
        try:
            year = quarter.find("span").get_text()
            day, month = quarter.find("div").get_text().split("/")
            date = str(year) + "-" + str(month) + "-" + str(day)
            data_dict["symbols"].append(symbol.upper() + ".JK")
            data_dict["year"].append(date)
        except:
            pass
    get_values(soup, data_dict)
    # Balance Sheet
    bs_url = f"https://www.investing.com{link}-balance-sheet"
    html_content = requests.get(bs_url).text
    soup = BeautifulSoup(html_content, "html.parser")
    get_values(soup, data_dict)
    # Cash Flow
    bs_url = f"https://www.investing.com{link}-cash-flow"
    html_content = requests.get(bs_url).text
    soup = BeautifulSoup(html_content, "html.parser")
    get_values(soup, data_dict)
    not_avail = [na for na in expected_value if na not in data_dict.keys()]
    for na in not_avail:
        data_dict[na] = [np.nan, np.nan, np.nan, np.nan]
    data_list.append(pd.DataFrame(data_dict))

df = pd.concat(data_list)
df.to_csv("result.csv", index = False)