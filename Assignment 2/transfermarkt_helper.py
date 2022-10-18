from bs4 import BeautifulSoup
import requests
import pandas as pd
import numpy as np
import re
import datetime as dt
from time import sleep

seed = 0
rng = np.random.default_rng(seed)

MAX_RETRIES = 5

SUMMER_2018_DATE = dt.date(2018, 6, 1)

headers = {'User-Agent':
           'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.106 Safari/537.36',
           'Connection': 'keep-alive'}

# "a" is a placeholder, can be anything, technically is player name but doesn't matter
base_url = 'https://www.transfermarkt.com/a/marktwertverlauf/spieler/'

columns = ['player_name', 'transfermarkt_player_id',
           'date', 'market_value_in_gbp']


def get_market_value_history_of_player(transfermarkt_player_id, retry_count=0):
    '''
    Takes a Transfermarkt player ID
    Returns a tuple of player name and a "list of dictionaries" of the market value history of the player according to Transfermarkt
    Each element of the list represents a single datapoint of market value history
    Dictionary keys:
        "y" = market value in GBP
        "verein" = club
        "age" = age in years
        "mw" = shorthand market valuation
        "datum_mw" = date as readable string
        "x" = date in epoch notation
        "marker" = url for icon used by Transfermarkt line chart

    If no market value exists, returns None
    '''
    tree = requests.get(base_url + str(transfermarkt_player_id),
                        headers=headers, timeout=300)
    soup = BeautifulSoup(tree.content, 'html.parser')

    try:
        script = soup.find('script', text=re.compile('Highcharts.Chart')).text
        player_name = soup.find('title').text.partition(' - ')[0]

        chart_data = script.split("'data':[")[1]
        ending_string = '}}]'
        chart_data = chart_data[:chart_data.find(ending_string) + 1]

        delim = '},'
        market_values = [eval(e + delim[0])
                         for e in chart_data.split(delim) if e[:5] == "{'y':"]

    except AttributeError:
        player_name = None
        market_values = None

    except ConnectionResetError as e:
        if retry_count == MAX_RETRIES:
            raise e
        sleep_time = rng.uniform(1, 3)
        sleep(sleep_time)
        get_market_value_history_of_player(
            transfermarkt_player_id, retry_count + 1)

    return player_name, market_values


def get_latest_market_value(transfermarkt_player_id, maximum_date=dt.date.today(), wait_seconds_max=1, as_pandas=False, market_value_only=False):
    '''
    Takes a Transfermarkt player ID, and optionally a date (defaulting to today)
    Returns the most recent Transfermarkt valuation of the player prior to the date parameter
    If no market value exists (or none before the date parameter), returns None
    Market values are in British Pounds ("GBP")
    '''

    if wait_seconds_max > 1:
        sleep_time = rng.uniform(1, wait_seconds_max)
        sleep(sleep_time)

    player_name, market_values = get_market_value_history_of_player(
        transfermarkt_player_id)

    if market_values:

        data_points_earlier_than_max_date = [data_point for data_point in market_values if dt.date.fromtimestamp(
            int(str(data_point['x'])[:-3])) < maximum_date]

        if data_points_earlier_than_max_date:
            market_vals_clean = [(player_name, transfermarkt_player_id, dt.date.fromtimestamp(
                int(str(data_point['x'])[:-3])), data_point['y']) for data_point in market_values]

            if maximum_date:
                market_vals_clean = [
                    [record for record in market_vals_clean if record[2] < maximum_date][-1]]

            if as_pandas:
                market_vals_clean = pd.DataFrame(
                    market_vals_clean, columns=columns)

            if market_value_only:
                market_vals_clean = market_vals_clean[3]

        else:
            market_vals_clean = None

    else:
        market_vals_clean = None

    return market_vals_clean


if __name__ == "__main__":
    messi_market_values = get_market_value_history_of_player(28003)
    print("Lionel Messi's market value history - first five data points from Transfermarkt")
    for data_point in messi_market_values[1][0:5]:
        print(data_point['datum_mw'] +
              ' (' + data_point['verein'] + '): ' + data_point['mw'])
