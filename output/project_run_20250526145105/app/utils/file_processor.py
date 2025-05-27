import io
import pandas as pd
from typing import List, Dict, Tuple, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FileProcessingError(Exception):
    """Custom exception for file processing errors."""
    pass

class FileProcessor:
    """
    Utility class for processing uploaded files (CSV/Excel) and generating
    various downloadable files (Moengage, Unique, Duplicate, Error).
    """

    @staticmethod
    def process_uploaded_customer_offers_file(
        file_content: bytes, file_extension: str
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Parses an uploaded customer offers file (CSV or Excel), performs basic
        column-level validation, and separates valid records from errors.

        Args:
            file_content: The raw bytes content of the uploaded file.
            file_extension: The extension of the file (e.g., 'csv', 'xlsx').

        Returns:
            A tuple containing:
            - A list of dictionaries for valid records.
            - A list of dictionaries for error records, each including an 'Error Desc' column.

        Raises:
            FileProcessingError: If the file type is unsupported or parsing fails.
        """
        df = pd.DataFrame()
        try:
            if file_extension.lower() == 'csv':
                df = pd.read_csv(io.BytesIO(file_content))
            elif file_extension.lower() in ['xls', 'xlsx']:
                df = pd.read_excel(io.BytesIO(file_content))
            else:
                raise FileProcessingError(f"Unsupported file type: {file_extension}")
        except Exception as e:
            logger.error(f"Error parsing uploaded file: {e}")
            raise FileProcessingError(f"Failed to parse file: {e}")

        # Define expected columns for customer offer uploads (FR43)
        # These are example columns. Actual columns would be derived from the
        # "attached Excel files" mentioned in BRD Ambiguity 1.
        # Based on DB schema and FRs, key identifiers and offer details are crucial.
        expected_columns = [
            "mobile_number", "pan_number", "aadhaar_ref_number", "ucid_number",
            "product_type", "offer_amount", "offer_interest_rate", "offer_tenure",
            "offer_start_date", "offer_end_date"
        ]

        valid_records = []
        error_records = []

        # Basic column validation (FR1, NFR3)
        # If critical columns are missing, we'll treat all rows as errors for now.
        # A more granular approach could process rows with partial data if business logic allows.
        missing_columns = [col for col in expected_columns if col not in df.columns]
        if missing_columns:
            logger.warning(f"Uploaded file is missing expected columns: {', '.join(missing_columns)}")
            for index, row in df.iterrows():
                error_row = row.to_dict()
                error_row['Error Desc'] = f"Missing required columns: {', '.join(missing_columns)}"
                error_records.append(error_row)
            return [], error_records

        # Iterate through rows for data validation
        for index, row in df.iterrows():
            record = row.to_dict()
            errors = []

            # Example validation: Check for presence of at least one primary identifier
            if not any(record.get(col) for col in ["mobile_number", "pan_number", "aadhaar_ref_number", "ucid_number"]):
                errors.append("At least one of Mobile Number, PAN, Aadhaar, or UCID is required.")

            # Example validation: product_type must be present
            if not record.get("product_type"):
                errors.append("Product Type is required.")

            # Example validation: Date format for offer start/end dates
            for date_col in ["offer_start_date", "offer_end_date"]:
                if record.get(date_col):
                    try:
                        # Attempt to convert to datetime to validate format
                        pd.to_datetime(record[date_col])
                    except ValueError:
                        errors.append(f"Invalid date format for {date_col}.")

            # Add more specific validations as per BRD (e.g., numeric checks for amount/rate/tenure)
            for num_col in ["offer_amount", "offer_interest_rate", "offer_tenure"]:
                if record.get(num_col) is not None:
                    try:
                        # Convert to float/int and check for non-negative values if applicable
                        float(record[num_col])
                        if float(record[num_col]) < 0:
                            errors.append(f"{num_col} cannot be negative.")
                    except ValueError:
                        errors.append(f"Invalid numeric format for {num_col}.")

            if errors:
                record['Error Desc'] = "; ".join(errors)
                error_records.append(record)
            else:
                # Clean up data types if necessary, e.g., convert pandas NaT/NaN to None
                for key, value in record.items():
                    if pd.isna(value):
                        record[key] = None
                valid_records.append(record)

        logger.info(f"File processed: {len(valid_records)} valid records, {len(error_records)} error records.")
        return valid_records, error_records

    @staticmethod
    def generate_moengage_file(data: List[Dict[str, Any]]) -> bytes:
        """
        Generates a CSV file in Moengage format from a list of campaign-ready data.
        (FR39, FR54, FR55)

        Args:
            data: A list of dictionaries, where each dictionary represents a customer
                  record formatted for Moengage. The keys in these dictionaries
                  are expected to be the column headers required by Moengage.

        Returns:
            The CSV file content as bytes.
        """
        if not data:
            logger.warning("No data provided to generate Moengage file.")
            return b""

        df = pd.DataFrame(data)

        # Ensure all columns are strings to avoid issues with mixed types in CSV
        # This is a common practice for Moengage uploads to prevent data type mismatches.
        for col in df.columns:
            df[col] = df[col].astype(str)

        output = io.StringIO()
        df.to_csv(output, index=False, encoding='utf-8')
        return output.getvalue().encode('utf-8')

    @staticmethod
    def generate_unique_data_file(data: List[Dict[str, Any]]) -> bytes:
        """
        Generates a CSV file containing unique customer data. (FR41)

        Args:
            data: A list of dictionaries, where each dictionary represents a unique
                  customer record.

        Returns:
            The CSV file content as bytes.
        """
        if not data:
            logger.warning("No data provided to generate unique data file.")
            return b""

        df = pd.DataFrame(data)
        output = io.StringIO()
        df.to_csv(output, index=False, encoding='utf-8')
        return output.getvalue().encode('utf-8')

    @staticmethod
    def generate_duplicate_data_file(data: List[Dict[str, Any]]) -> bytes:
        """
        Generates a CSV file containing duplicate customer data. (FR40)

        Args:
            data: A list of dictionaries, where each dictionary represents a duplicate
                  customer record.

        Returns:
            The CSV file content as bytes.
        """
        if not data:
            logger.warning("No data provided to generate duplicate data file.")
            return b""

        df = pd.DataFrame(data)
        output = io.StringIO()
        df.to_csv(output, index=False, encoding='utf-8')
        return output.getvalue().encode('utf-8')

    @staticmethod
    def generate_error_file(errors: List[Dict[str, Any]]) -> bytes:
        """
        Generates a CSV file containing error records with an 'Error Desc' column. (FR42, FR46)

        Args:
            errors: A list of dictionaries, where each dictionary is an error record
                    including the original data and an 'Error Desc' column.

        Returns:
            The CSV file content as bytes.
        """
        if not errors:
            logger.warning("No error data provided to generate error file.")
            return b""

        df = pd.DataFrame(errors)
        # Ensure 'Error Desc' is the last column for better readability if it exists
        if 'Error Desc' in df.columns:
            cols = [col for col in df.columns if col != 'Error Desc'] + ['Error Desc']
            df = df[cols]

        output = io.StringIO()
        df.to_csv(output, index=False, encoding='utf-8')
        return output.getvalue().encode('utf-8')