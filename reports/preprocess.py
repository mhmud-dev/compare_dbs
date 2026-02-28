import pandas as pd
import os


BASE_PATH = "../benchmark_results"
POSTGRES_PATH = f"{BASE_PATH}/postgres"
MARIADB_PATH = f"{BASE_PATH}/mariadb"


def get_datafame(db):
    all_files = []
    path = MARIADB_PATH
    if db != "mariadb":
        path = POSTGRES_PATH
    for _, _, files in os.walk(path):
        all_files.extend(files)
    csv_files = []
    for csv_file in all_files:
        if csv_file.find(".csv") != -1 and csv_file.find("disk") == -1:
            csv_files.append(os.path.join(path, csv_file))
    df = None
    for csv in csv_files:
        if df is None:
            df = pd.read_csv(csv)
        else:
            tmp = pd.read_csv(csv)
            df = pd.concat([df, tmp], ignore_index=True)
    df["database_type"] = db
    return df


def preprocess():
    mariadb = get_datafame("mariadb")
    postgres = get_datafame("postgres")
    df = pd.concat([mariadb, postgres], ignore_index=True)
    df.drop("timestamp", axis=1, inplace=True)
    df["batch_size"] = df["test_name"].apply(
        lambda x: int(x.split("_")[-1]) if "batch" in x else None
    )
    df["concurrent_workers"] = df["test_name"].apply(
        lambda x: int(x.split("_")[-1]) if "concurrent" in x else None
    )
    out_file = BASE_PATH + "/data.csv"
    df.to_csv(out_file, index=False)
