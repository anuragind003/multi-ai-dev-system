import pandas as pd
from fastapi import UploadFile
from io import BytesIO
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FileParsingError(Exception):
    """Custom exception for file parsing errors."""
    pass

class FileParser:
    """
    Utility class for parsing uploaded customer offer files (CSV/Excel).
    Handles reading file content into a pandas DataFrame and basic structural validation.
    """

    # Define expected columns for customer offer uploads
    # These are the minimum required fields for initial processing and lead generation (FR43, FR44)
    # Additional offer_details fields can be dynamic and will be handled in subsequent validation/processing.
    REQUIRED_COLUMNS = [
        "mobile_number",
        "pan_number",
        "aadhaar_ref_number",
        "product_type", # Corresponds to offer.product_type
        "offer_start_date",
        "offer_end_date",
        # Common offer details that might be present in the upload
        "loan_amount",
        "tenure",
        "interest_rate",
        "emi"
    ]

    # Columns that can be used for customer identification (for deduplication)
    CUSTOMER_IDENTIFIER_COLUMNS = [
        "mobile_number",
        "pan_number",
        "aadhaar_ref_number",
        "ucid_number",
        "previous_loan_app_number"
    ]

    def parse_uploaded_file(self, file: UploadFile) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Parses an uploaded file (CSV or Excel) into a pandas DataFrame.
        Performs basic structural validation and separates valid rows from error rows.

        Args:
            file: The uploaded file object from FastAPI.

        Returns:
            A tuple containing:
            - pd.DataFrame: DataFrame of successfully parsed rows.
            - pd.DataFrame: DataFrame of rows that failed initial parsing/validation,
                            including an 'error_description' column.

        Raises:
            FileParsingError: If the file type is unsupported or file is empty.
        """
        file_content = BytesIO(file.file.read())
        filename = file.filename
        logger.info(f"Attempting to parse file: {filename}")

        df = pd.DataFrame()
        # Initialize error_df with all possible columns to ensure consistency
        all_possible_cols = list(set(self.REQUIRED_COLUMNS + self.CUSTOMER_IDENTIFIER_COLUMNS + ['error_description']))
        error_df = pd.DataFrame(columns=all_possible_cols)

        try:
            if filename.endswith('.csv'):
                df = self._read_csv(file_content)
            elif filename.endswith('.xlsx') or filename.endswith('.xls'):
                df = self._read_excel(file_content)
            else:
                raise FileParsingError("Unsupported file type. Only CSV and Excel files are supported.")

            if df.empty:
                raise FileParsingError("Uploaded file is empty or contains no data.")

            logger.info(f"Successfully read {len(df)} rows from {filename}.")

            # Perform initial column validation
            valid_rows, invalid_rows_with_errors = self._validate_columns(df)
            
            if not invalid_rows_with_errors.empty:
                error_df = pd.concat([error_df, invalid_rows_with_errors], ignore_index=True)

            return valid_rows, error_df

        except FileParsingError as e:
            logger.error(f"File parsing failed for {filename}: {e}")
            # If the entire file fails parsing, create an error entry for the file itself
            error_entry = pd.DataFrame([{'error_description': str(e)}], columns=['error_description'])
            # Ensure error_df has all expected columns for consistency, even if only one row
            error_df = pd.concat([error_df, error_entry], ignore_index=True)
            return pd.DataFrame(), error_df
        except Exception as e:
            logger.exception(f"An unexpected error occurred during file parsing for {filename}.")
            error_entry = pd.DataFrame([{'error_description': f"An unexpected error occurred: {e}"}], columns=['error_description'])
            error_df = pd.concat([error_df, error_entry], ignore_index=True)
            return pd.DataFrame(), error_df

    def _read_csv(self, file_content: BytesIO) -> pd.DataFrame:
        """Reads a CSV file into a DataFrame."""
        try:
            # Try reading with common delimiters and encodings
            df = pd.read_csv(file_content, encoding='utf-8', sep=',')
            return df
        except UnicodeDecodeError:
            file_content.seek(0) # Reset buffer position
            df = pd.read_csv(file_content, encoding='latin1', sep=',')
            return df
        except Exception as e:
            raise FileParsingError(f"Error reading CSV file: {e}")

    def _read_excel(self, file_content: BytesIO) -> pd.DataFrame:
        """Reads an Excel file into a DataFrame."""
        try:
            df = pd.read_excel(file_content)
            return df
        except Exception as e:
            raise FileParsingError(f"Error reading Excel file: {e}")

    def _validate_columns(self, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Performs basic column-level validation.
        Checks for the presence of at least one customer identifier column and product_type.
        Also checks for offer_start_date and offer_end_date.
        Adds an 'error_description' column for invalid rows.
        """
        valid_rows_list = []
        invalid_rows_list = []

        # Convert column names to lowercase for case-insensitive matching
        df.columns = df.columns.str.lower()
        
        # Prepare a list of all columns that should be present in the output DataFrames
        all_output_cols = list(set(self.REQUIRED_COLUMNS + self.CUSTOMER_IDENTIFIER_COLUMNS))

        for index, row in df.iterrows():
            row_errors = []
            row_dict = row.to_dict()

            # Ensure all expected columns are present in the row_dict, fill with None if not
            for col in all_output_cols:
                if col not in row_dict:
                    row_dict[col] = None # Use None for missing columns, pandas will convert to NaN

            # Check for at least one customer identifier
            has_identifier = False
            for col in self.CUSTOMER_IDENTIFIER_COLUMNS:
                if col in row_dict and pd.notna(row_dict[col]) and str(row_dict[col]).strip() != '':
                    has_identifier = True
                    break
            if not has_identifier:
                row_errors.append("Missing or empty customer identifier (mobile_number, pan_number, aadhaar_ref_number, ucid_number, or previous_loan_app_number).")

            # Check for product_type
            if "product_type" not in row_dict or pd.isna(row_dict["product_type"]) or str(row_dict["product_type"]).strip() == '':
                row_errors.append("Missing or empty 'product_type'.")

            # Check for offer_start_date and offer_end_date
            if "offer_start_date" not in row_dict or pd.isna(row_dict["offer_start_date"]):
                row_errors.append("Missing 'offer_start_date'.")
            if "offer_end_date" not in row_dict or pd.isna(row_dict["offer_end_date"]):
                row_errors.append("Missing 'offer_end_date'.")

            # Add more specific data type/format validation here if needed,
            # e.g., date format, numeric values for loan_amount.
            # For MVP, we'll rely on Pydantic models for stricter validation later.

            if row_errors:
                row_dict['error_description'] = "; ".join(row_errors)
                invalid_rows_list.append(row_dict)
            else:
                valid_rows_list.append(row_dict)

        valid_df = pd.DataFrame(valid_rows_list)
        invalid_df = pd.DataFrame(invalid_rows_list)

        # Ensure valid_df has all expected columns, even if some were not in the original file
        for col in all_output_cols:
            if col not in valid_df.columns:
                valid_df[col] = pd.NA
        
        # Ensure invalid_df has all expected columns, plus 'error_description'
        for col in all_output_cols + ['error_description']:
            if col not in invalid_df.columns:
                invalid_df[col] = pd.NA

        # Reorder columns for consistency
        valid_df = valid_df[all_output_cols]
        invalid_df = invalid_df[all_output_cols + ['error_description']]

        return valid_df, invalid_df