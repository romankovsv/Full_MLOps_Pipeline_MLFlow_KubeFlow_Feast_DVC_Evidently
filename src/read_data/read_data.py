from minio import Minio
import pandas as pd
import os
import argparse
from pathlib import Path


def get_data(
    minio_host: str,
    access_key: str,
    secret_key: str,
    bucket_name: str,
    file_name: str,
    data_output_path: str,
):
    """
    Downloads a file from Minio, reads it as a DataFrame, and saves it as a parquet file.

    Args:
        minio_host (str): Minio host URL.
        access_key (str): Minio access key.
        secret_key (str): Minio secret key.
        bucket_name (str): Minio bucket name.
        file_name (str): File name to download.
        data_output_path (str): Path to save the output Dataset.
    """
    # Initialize Minio client
    client = Minio(
        endpoint=minio_host, access_key=access_key, secret_key=secret_key, secure=False
    )

    # Ensure the file will be downloaded to a temp directory
    local_temp_file = os.path.join("/tmp", file_name)

    # Download the file from Minio
    print(f"Downloading {file_name} from bucket {bucket_name}...")
    client.fget_object(bucket_name, file_name, local_temp_file)

    # Load the Parquet file into a DataFrame
    print(f"Reading the downloaded file {local_temp_file}...")
    df = pd.read_parquet(local_temp_file)

    # Save the DataFrame as a parquet file in the specified output path
    print(f"Saving the processed data to {data_output_path}...")
    Path(data_output_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(data_output_path)

    print("Data saved successfully.")


def main():
    # Set up argument parsing
    parser = argparse.ArgumentParser(
        description="Download data from Minio and save as a Dataset."
    )
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
        "--data_output_path",
        type=str,
        required=True,
        help="Output path for the Dataset",
    )

    args = parser.parse_args()

    # Call the get_data function with parsed arguments
    get_data(
        minio_host=args.minio_host,
        access_key=args.access_key,
        secret_key=args.secret_key,
        bucket_name=args.bucket_name,
        file_name=args.file_name,
        data_output_path=args.data_output_path,
    )


if __name__ == "__main__":
    main()