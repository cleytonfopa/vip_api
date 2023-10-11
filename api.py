import sys
from flask import Flask, request
from joblib import load
from utils import f, clean_DF, calculate_recency, calculate_scores
import pandas as pd
import numpy as np
import datetime

app = Flask(__name__)

@app.route("/predict_vip", methods=["POST"])
def predict():
    # catching json:
    json_ = request.get_json()
    # convert to DF:
    df = pd.DataFrame(json_)
    # cleaning:
    df = clean_DF(df)    
    # Calculanto agregados por dia:
    bet_by_day = (
      df
      .groupby(["Username", "registration_dt", "ftd_value","age", "date"])
      .agg(
        n_bets=("turnover", lambda x: np.sum(x>0)), 
        turnover=("turnover", np.sum),  
        ggr=("ggr", np.sum)
        )
      .reset_index()
    )
    bet_by_day
    # selecionando variáveis:
    bet_by_day = bet_by_day[["registration_dt", "date", "Username", "ftd_value", "age", "n_bets", "turnover", "ggr"]]
    bet_by_day = bet_by_day.sort_values(by=["registration_dt", "Username"])
    # numero máximo de dias de atividade na plataforma:
    max_days_sample=(bet_by_day["date"].max() - bet_by_day["registration_dt"].min()).days + 1
    # Criando as datas correntes para todos os usuários
    bet_by_day = (
      bet_by_day
      .groupby("Username")
      .apply(f,min_days=max_days_sample)
      .reset_index(drop=True)
    )
    # Filtrando para a data máxima de apostas da base:
    dt_max_bet = df["date"].max()
    bet_by_day = bet_by_day.query("date <= @dt_max_bet")
    # calculating covariates:
    rfm_df = calculate_scores(bet_by_day, bet_by_day["date"].max())
    # adding user info:
    rfm_df = rfm_df.merge(
        bet_by_day[["Username", "age", "ftd_value"]].drop_duplicates(),
        on="Username"
    ) 
    ## predicting:
    vars_ = [
        'recency_value', 'frequency_value', 'revenue_value', 'turnover_value',
       'ticket_medio', 'overall_score', 'ftd_value', 'age'
    ]
    # predicting
    rfm_df["vip_proba"] = clf.predict_proba(rfm_df[vars_])[:, 1]
    rfm_df["vip_proba"] = np.where(rfm_df["vip_proba"] == 1, .999, rfm_df["vip_proba"])
    rfm_df["vip_proba"] = rfm_df["vip_proba"].round(3)
    # returning:
    return rfm_df[["Username", "vip_proba"]].to_json(orient="records")


if __name__ == '__main__':
    # If you don't provide any port the port will be set to 500
    try:
        port = int(sys.argv[1])
    except:
        port = 1234
    # loading models:
    clf = load("clf_vip_model.joblib")
    # running debug mode:
    app.run(port=port, debug=True)

