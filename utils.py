# helper function to clean dataset:
def clean_DF(df):
    import pandas as pd
    # removing cancelled bets:
    df = df.query("Cancelled == 0")
    # fixing date columns:
    df["Reg_Date"] = pd.to_datetime(df["Reg_Date"])
    df["DOB"] = pd.to_datetime(df["DOB"])
    # date
    df["registration_dt"] = df["Reg_Date"].dt.date
    # idade:
    df["age"] = pd.to_datetime(df["registration_dt"]).dt.year - df["DOB"].dt.year
    # rename
    df.rename(columns={"Amount": "ftd_value"}, inplace=True)
    # columns:
    players_input = ["User_ID", "name", "Username",
                     "registration_dt", "ftd_value",
                     "deposit_dt", "age", "no-affiliate"]
    # fixing numerical values:
    df["Bet"] = df["Bet"].str.replace(",", ".").astype("float")
    df["Win"] = df["Win"].str.replace(",", ".").astype("float")
    df["Cancelled"] = df["Cancelled"].astype("int")
    # date features:
    df["Date_Time"] = pd.to_datetime(df["Date_Time"])
    df["date"] = df["Date_Time"].dt.date
    # ggr
    df["ggr"] = df["Bet"] - df["Win"]
    # renaming
    df.rename(columns={"Bet": "turnover"}, inplace=True)
    return df

# function to guarantee at least 180 days:
def f(x, min_days=181):
    import pandas as pd
    # convert to datetime
    x["date"] = pd.to_datetime(x["date"])
    x["registration_dt"] = pd.to_datetime(x["registration_dt"])
    # merge
    x = pd.merge(
        pd.DataFrame({"date": pd.date_range(x["registration_dt"].min(), periods=min_days)}),
        x,
        on="date",
        how="left"
    )
    # processing:
    if x.dropna().shape[0] == 0:
        x= x.dropna()
    else:    
       x["ftd_value"].fillna(x["ftd_value"].dropna().unique()[0], inplace=True)    
       x["age"].fillna(x["age"].dropna().unique()[0], inplace=True)
       x["Username"].fillna(x["Username"].dropna().unique()[0], inplace=True)
       #x["no-affiliate"].fillna(x["no-affiliate"].dropna().unique()[0], inplace=True)
       x["n_bets"].fillna(0, inplace=True)
       x["turnover"].fillna(0, inplace=True)
       x["ggr"].fillna(0, inplace=True)
       x["registration_dt"].fillna(x["registration_dt"].dropna().unique()[0], inplace=True)
       return x


# função para calcular Recency
def calculate_recency(df, date_max):
    import pandas as pd
    recency_value = date_max - df.query("n_bets > 0")["date"].max()
    # Se naT (nao houve nenhuma aposta):
    if pd.isnull(recency_value):
        recency_value = date_max - df["registration_dt"].max()
    recency_value = recency_value.days
    return recency_value

def calculate_scores(df, bet_date_max):
    import datetime
    import pandas as pd
    from scipy.stats.mstats import hmean
    # Recency:
    dt_max = datetime.datetime(bet_date_max.year, bet_date_max.month, bet_date_max.day)
    recency_df = (
        df
        .groupby("Username")
        .apply(
            calculate_recency,
            date_max=dt_max
        )
    )
    recency_df = recency_df.reset_index()
    recency_df.columns = ["Username", "recency_value"]
    # Frequency:
    frequency_df = df.groupby("Username")["n_bets"].sum()
    frequency_df = frequency_df.reset_index()
    frequency_df.columns = ["Username", "frequency_value"]
    # Monetary value:
    revenue_df = df.groupby("Username")["ggr"].sum()
    revenue_df = revenue_df.reset_index()
    revenue_df.columns = ["Username", "revenue_value"]
    # turnover value:
    turnover_df = df.groupby("Username")["turnover"].sum()
    turnover_df = turnover_df.reset_index()
    turnover_df.columns = ["Username", "turnover_value"]
    # merging:
    rfm_df = recency_df.merge(frequency_df, on="Username")
    rfm_df = rfm_df.merge(revenue_df, on="Username")
    rfm_df = rfm_df.merge(turnover_df, on="Username")
    # ticket_medio
    rfm_df["ticket_medio"] = rfm_df["turnover_value"] / rfm_df["frequency_value"]
    rfm_df["ticket_medio"] = rfm_df["ticket_medio"].fillna(0)
    # creating scores:
    rfm_df["revenue_score"] = (rfm_df["revenue_value"] - rfm_df["revenue_value"].min()) / (rfm_df["revenue_value"].max() - rfm_df["revenue_value"].min())
    rfm_df["frequency_score"] = (rfm_df["frequency_value"] - rfm_df["frequency_value"].min()) / (rfm_df["frequency_value"].max() - rfm_df["frequency_value"].min())
    rfm_df["recency_score"] = (rfm_df["recency_value"] - rfm_df["recency_value"].min()) / (rfm_df["recency_value"].max() - rfm_df["recency_value"].min())
    rfm_df["ticket_score"] = (rfm_df["ticket_medio"] - rfm_df["ticket_medio"].min()) / (rfm_df["ticket_medio"].max() - rfm_df["ticket_medio"].min())
    # overall score:
    # harmonic mean of scores
    vars_ = ["revenue_score", "frequency_score", "recency_score", "ticket_score"]
    rfm_df["overall_score"] = rfm_df[vars_].apply(hmean, axis=1)
    # final dataset:
    vars_ = [
        "Username",
        "recency_value",
        "frequency_value",
        "revenue_value",
        "turnover_value",
        "ticket_medio",
        "overall_score",
    ]
    return rfm_df[vars_]
