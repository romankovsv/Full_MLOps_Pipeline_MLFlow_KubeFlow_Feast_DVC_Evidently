from minio import Minio
import pandas as pd  # Updated imports for KFP v2
import argparse


def write_data(
    minio_host: str,
    access_key: str,
    secret_key: str,
    bucket_name: str,
    file_name: str,
    input_data_path: str,  # Updated type hint for KFP v2
):
    client = Minio(
        endpoint=minio_host, access_key=access_key, secret_key=secret_key, secure=False
    )

    # Load input data from the artifact path
    input_data = pd.read_parquet(
        input_data_path
    )  # KFP v2 uses `.path` for artifact inputs
    input_data.to_parquet(file_name, index=False)

    # Upload the file to MinIO
    client.fput_object(bucket_name, file_name, file_name)


def main():
    parser = argparse.ArgumentParser(description="Upload data to MinIO.")
    parser.add_argument("--minio_host", type=str, help="MinIO host URL")
    parser.add_argument("--access_key", type=str, help="MinIO access key")
    parser.add_argument("--secret_key", type=str, help="MinIO secret key")
    parser.add_argument("--bucket_name", type=str, help="MinIO bucket name")
    parser.add_argument("--file_name", type=str, help="Name of the file to upload")
    parser.add_argument("--input_data_path", type=str, help="Path to the input data")

    args = parser.parse_args()

    write_data(
        minio_host=args.minio_host,
        access_key=args.access_key,
        secret_key=args.secret_key,
        bucket_name=args.bucket_name,
        file_name=args.file_name,
        input_data_path=args.input_data_path,
    )


if __name__ == "__main__":
    main()