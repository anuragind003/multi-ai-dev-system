import io
import pandas as pd
from flask import current_app

def generate_file_for_download(df: pd.DataFrame, filename: str, file_format: str):
    """
    Generates a file (CSV or Excel) from a pandas DataFrame into a BytesIO buffer.
    This function prepares the buffer, mimetype, and attachment filename for Flask's send_file.

    Args:
        df (pd.DataFrame): The DataFrame to convert.
        filename (str): The desired base filename for the download (e.g., "report").
        file_format (str): The desired file format ('csv' or 'excel').

    Returns:
        tuple: A tuple containing (BytesIO buffer, mimetype, attachment_filename).
               The buffer contains the file content, mimetype is for HTTP header,
               and attachment_filename is the suggested name for the downloaded file.

    Raises:
        ValueError: If an unsupported file format is requested.
        Exception: For any other errors during file generation.
    """
    buffer = io.BytesIO()
    mimetype = ''
    attachment_filename = filename

    try:
        if file_format.lower() == 'csv':
            df.to_csv(buffer, index=False, encoding='utf-8')
            mimetype = 'text/csv'
            if not attachment_filename.lower().endswith('.csv'):
                attachment_filename += '.csv'
        elif file_format.lower() == 'excel':
            # Ensure openpyxl is installed for Excel support
            df.to_excel(buffer, index=False, engine='openpyxl')
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            if not (attachment_filename.lower().endswith('.xls') or attachment_filename.lower().endswith('.xlsx')):
                attachment_filename += '.xlsx' # Default to .xlsx
        else:
            current_app.logger.error(f"Unsupported file format requested for download: {file_format}")
            raise ValueError("Unsupported file format. Must be 'csv' or 'excel'.")
    except Exception as e:
        current_app.logger.exception(f"Error generating file for download (format: {file_format}, filename: {filename}): {e}")
        raise

    buffer.seek(0) # Rewind the buffer to the beginning
    return buffer, mimetype, attachment_filename

def parse_uploaded_file_to_dataframe(file_content_bytes: bytes, original_filename: str) -> pd.DataFrame:
    """
    Parses the content of an uploaded file (CSV or Excel) into a pandas DataFrame.
    Infers the file type from the original_filename's extension.

    Args:
        file_content_bytes (bytes): The raw bytes content of the uploaded file.
        original_filename (str): The original name of the uploaded file, used to infer format.

    Returns:
        pd.DataFrame: A pandas DataFrame containing the parsed data.

    Raises:
        ValueError: If the file type is unsupported, the file is empty, or parsing fails.
    """
    logger = current_app.logger
    file_extension = original_filename.split('.')[-1].lower()
    df = pd.DataFrame()

    try:
        if file_extension == 'csv':
            df = pd.read_csv(io.BytesIO(file_content_bytes))
            logger.info(f"Successfully parsed CSV file: {original_filename}")
        elif file_extension in ['xls', 'xlsx']:
            df = pd.read_excel(io.BytesIO(file_content_bytes))
            logger.info(f"Successfully parsed Excel file: {original_filename}")
        else:
            logger.error(f"Unsupported file extension for upload: {file_extension} from {original_filename}")
            raise ValueError(f"Unsupported file type: .{file_extension}. Only CSV and Excel files are supported.")

        if df.empty:
            logger.warning(f"Uploaded file '{original_filename}' is empty after parsing.")
            raise ValueError("Uploaded file is empty or contains no valid data.")

    except pd.errors.EmptyDataError:
        logger.warning(f"Uploaded file '{original_filename}' is empty.")
        raise ValueError("Uploaded file is empty.")
    except Exception as e:
        logger.exception(f"Error parsing uploaded file '{original_filename}': {e}")
        raise ValueError(f"Error parsing file '{original_filename}': {e}")

    return df