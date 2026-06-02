#!/usr/bin/env bash
# Download real historical football data (with Pinnacle opening + closing odds
# and results) for backtesting, from the public-domain jokecamp/FootballData
# mirror of football-data.co.uk. Season 2019-2020 is the one that carries the
# closing-odds columns (PSC*) needed to measure real CLV.
#
#   bash scripts/fetch_sample_data.sh
#   python run.py backtest --data "data/*.csv" --commission 0.02 --stake 10
#   python run.py backtest --data "data/*.csv" --validate
set -u
mkdir -p data
BASE="https://raw.githubusercontent.com/jokecamp/FootballData/master/football-data.co.uk/england/2019-2020"
fetch() { curl -sSL --max-time 40 -o "data/$2" "$BASE/$1" && echo "  got $2 ($(wc -l < "data/$2") rows)"; }
echo "Fetching England 2019-2020 (Premier + Championship + League 1 + League 2)..."
fetch "Premier.csv"      e_pl_1920.csv
fetch "Championship.csv" e_ch_1920.csv
fetch "League%201.csv"   e_l1_1920.csv
fetch "League%202.csv"   e_l2_1920.csv
echo "Done. ~1770 matches with Pinnacle opening + closing odds."
