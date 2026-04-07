import mlflow
from mlflow.tracking import MlflowClient
import pandas as pd
import pickle
from pathlib import Path
import argparse
import os


def perform_inference(
    minio_host: str,
    access_key: str,
    secret_key: str,
    model_name: str,
    model_type: str,
    model_stage: str,
    mlflow_host: str,
    input_data: str,  # KFP v2 input artifact
    data_output: str,  # KFP v2 output artifact
):
    os.environ["AWS_ACCESS_KEY_ID"] = access_key
    os.environ["AWS_SECRET_ACCESS_KEY"] = secret_key
    if not minio_host.startswith("http"):
        os.environ["AWS_ENDPOINT_URL"] = "http://" + minio_host
    else:
        os.environ["AWS_ENDPOINT_URL"] = minio_host
    mlflow.set_tracking_uri(mlflow_host)
    mlflow_client = MlflowClient(mlflow_host)
    model_run_id = None
    for model in mlflow_client.search_model_versions(f"name='{model_name}'"):
        if model.current_stage == model_stage:
            model_run_id = model.run_id
            break

    if not model_run_id:
        raise ValueError(
            f"No model found in stage {model_stage} for model {model_name}."
        )

    mlflow.artifacts.download_artifacts(
        f"runs:/{model_run_id}/column_list.pkl", dst_path="column_list"
    )
    input_data_df = pd.read_parquet(input_data)
    input_data_df.drop(columns=["user_id", "event_timestamp"], inplace=True)

    with open("column_list/column_list.pkl", "rb") as f:
        col_list = pickle.load(f)
    input_data_df = pd.get_dummies(
        input_data_df, drop_first=True, sparse=False, dtype=float
    )
    input_data_df = input_data_df.reindex(columns=col_list, fill_value=0)

    if model_type == "sklearn":
        model = mlflow.sklearn.load_model(
            model_uri=f"models:/{model_name}/{model_stage}"
        )
    elif model_type == "xgboost":
        model = mlflow.xgboost.load_model(
            model_uri=f"models:/{model_name}/{model_stage}"
        )
    elif model_type == "tensorflow":
        model = mlflow.tensorflow.load_model(
            model_uri=f"models:/{model_name}/{model_stage}"
        )
    else:
        raise NotImplementedError(f"Model type '{model_type}' is not supported.")

    predicted_classes = [x[1] for x in model.predict_proba(input_data_df)]
    input_data_df["Predicted_Income_Class"] = predicted_classes
    Path(data_output).parent.mkdir(parents=True, exist_ok=True)
    input_data_df.to_parquet(data_output)


def main():
    parser = argparse.ArgumentParser(
        description="Run inference using a specified model."
    )
    parser.add_argument("--minio_host", type=str, required=True, help="Minio host URL")
    parser.add_argument(
        "--access_key", type=str, required=True, help="Minio access key"
    )
    parser.add_argument(
        "--secret_key", type=str, required=True, help="Minio secret key"
    )
    parser.add_argument("--model_name", required=True, help="Name of the model.")
    parser.add_argument(
        "--model_type",
        required=True,
        help="Type of the model (e.g., sklearn, xgboost, tensorflow).",
    )
    parser.add_argument(
        "--model_stage",
        required=True,
        help="Stage of the model (e.g., production, staging).",
    )
    parser.add_argument("--mlflow_host", required=True, help="MLflow tracking URI.")
    parser.add_argument(
        "--input_data", required=True, help="Path to the input data artifact."
    )
    parser.add_argument(
        "--data_output", required=True, help="Path to the output data artifact."
    )

    args = parser.parse_args()

    perform_inference(
        minio_host=args.minio_host,
        access_key=args.access_key,
        secret_key=args.secret_key,
        model_name=args.model_name,
        model_type=args.model_type,
        model_stage=args.model_stage,
        mlflow_host=args.mlflow_host,
        input_data=args.input_data,
        data_output=args.data_output,
    )


if __name__ == "__main__":
    main()