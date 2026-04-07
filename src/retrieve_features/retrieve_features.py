from feast import FeatureStore
import pandas as pd
from pathlib import Path
from minio import Minio
from feast.repo_config import FeastConfigError
from pydantic import ValidationError
import argparse
import os


def init_feature_store(
    minio_host: str, access_key: str, secret_key: str, bucket_name: str, file_name: str
) -> FeatureStore:
   
    client = Minio(
        minio_host, access_key=access_key, secret_key=secret_key, secure=False
    )
    client.fget_object(bucket_name, file_name, "feature_store.yaml")
    config_path = Path("./") / "feature_store.yaml"
    try:
        print("http://" + minio_host)
        os.environ["AWS_ACCESS_KEY_ID"] = access_key
        os.environ["AWS_SECRET_ACCESS_KEY"] = secret_key
        os.environ["FEAST_S3_ENDPOINT_URL"] = "http://" + minio_host
        os.environ["S3_ENDPOINT_URL"] = "http://" + minio_host
        os.environ["AWS_ENDPOINT_URL"] = "http://" + minio_host
        store = FeatureStore(repo_path=".")
    except ValidationError as e:
        raise FeastConfigError(e, config_path)
    return store


def get_features(
    minio_host: str,
    access_key: str,
    secret_key: str,
    bucket_name: str,
    file_name: str,
    entity_df: str,
    feature_list: str,
    data_output: str,
):
    store = init_feature_store(
        minio_host, access_key, secret_key, bucket_name, file_name
    )
    print("Feature store initialized")
    feature_list = feature_list.split(",")
    print("Requested features:", feature_list)
    print(entity_df)
    entity_df = pd.read_parquet(entity_df)
    print("Entity DataFrame head:")
    print(entity_df.head())
    feature_df = store.get_historical_features(
        entity_df=entity_df,
        features=feature_list,
    ).to_df()
    print("Retrieved historical features:")
    print(feature_df.head())
    Path(data_output).parent.mkdir(parents=True, exist_ok=True)
    feature_df.to_parquet(data_output)


def main():
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Retrieve features from Feast")
    parser.add_argument("--minio_host", type=str, required=True, help="Minio host URL")
    parser.add_argument(
        "--access_key", type=str, required=True, help="Minio access key"
    )
    parser.add_argument(
        "--secret_key", type=str, required=True, help="Minio secret key"
    )
    parser.add_argument(
        "--bucket_name", type=str, required=True, help="Minio bucket name"
    )
    parser.add_argument(
        "--file_name", type=str, required=True, help="File name to download"
    )
    parser.add_argument(
        "--entity_df", type=str, required=True, help="Input path for the Dataset"
    )
    parser.add_argument(
        "--feature_list", type=str, required=True, help="List of features to retrieve"
    )
    parser.add_argument(
        "--data_output", type=str, required=True, help="Output path for the Dataset"
    )
    args = parser.parse_args()

    # Call the get_features function with parsed arguments
    get_features(
        minio_host=args.minio_host,
        access_key=args.access_key,
        secret_key=args.secret_key,
        bucket_name=args.bucket_name,
        file_name=args.file_name,
        entity_df=args.entity_df,
        feature_list=args.feature_list,
        data_output=args.data_output,
    )


if __name__ == "__main__":
    main()