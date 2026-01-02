from typing import List
from pathlib import Path
from decimal import Decimal 
import pandas as pd
from expense_tracker.parsers.base import StatementParser
from expense_tracker.domain.models import Transaction
from expense_tracker.domain.enums import TransactionType

class AmexExcelParser(StatementParser):
    """
    Parser for American Express Excel/XLS Statements.

    Handles the Amex statement format with:
    - Header rows (account info, summary)
    - Transaction data starting at row 16
    - Dollar-sign formatted amounts
    
    """

    # Column names form AMEX file
    DATE_COL = "Date"
    DESCRIPTION_COL = "Description"
    AMOUNT_COL = "Amount"
    CARDMEMBER_COL = "Cardmember"
    MERCHANT_ADDR_COL = "Merchant Address"

    def validate_file(self, filepath):
        """
        Check if file exists, is an Excel file, and is a valid Amex statement.
        
        Validates by checking for Amex-specific identifiers in the header rows:
        - "American Express" in the header
        - "Transaction Details" or similar
        - Expected column structure (Date, Description, Amount)
        
        :param filepath: Path to the amex file
        """
        path = Path(filepath)
        
        if not path.exists():
            raise FileNotFoundError(f"File does not exist on path {path}")
        
        if path.suffix.lower() not in ['.xlsx', '.xls']:
            raise ValueError(f"File must be .xlsx or .xls, got {path.suffix}")
        
        try:
            df_raw = pd.read_excel(filepath, header=None)
        except Exception as e:
            print(f"Validation error: {e}")
            raise Exception
        
        header_row = self._find_header_row(df_raw)
        if header_row is None:
            raise ValueError(f"Could not find a header row in the file")
        
        try:
            df = pd.read_excel(filepath, header=header_row)
        except Exception as e:
            print(f"Validation error: {e}")
            raise Exception
        
        required_columns = [self.DATE_COL, self.DESCRIPTION_COL, self.AMOUNT_COL]

        if not all(col in df.columns for col in required_columns):
            raise ValueError(f"Header is missing required columns")

    def parse(self, filepath: str) -> List[Transaction]:
        """
        Parse Amex Excel statement.
        
        The Amex format has metadata and summary rows at the top,
        with actual transactions starting around row 16.
        """
        try:
            self.validate_file(filepath)
        except Exception as e:
            raise ValueError(f"Invalid file: {e}")

        try:
            # Read the entire file first to find the header row
            df_raw = pd.read_excel(filepath, header=None)
            
            # Find the row with column headers (contains 'Date', 'Description', 'Amount')
            header_row = self._find_header_row(df_raw)
            
            if header_row is None:
                raise ValueError("Could not find transaction header row in file")
            
            # Now read again with the correct header
            df = pd.read_excel(filepath, header=header_row)
            
        except Exception as e:
            raise ValueError(f"Failed to read Excel file: {e}")
        
        # Validate required columns exist (should pass since validate_file checked this)
        self._validate_columns(df)
        
        # Parse transactions
        transactions = []
        for _, row in df.iterrows():
            try:
                if not self._valid_row(row):
                    continue

                # Tracking payments will mess with the overall budget total
                if self._is_payment_row(row):
                    continue
                    
                transaction = self._parse_row(row)
                if transaction:
                    transactions.append(transaction)
            except Exception as e:
                print(f"Warning: Skipping row due to error: {e}")
                continue
        
        return transactions


    def _find_header_row(self, df_raw: pd.DataFrame) -> int:
        """
        Find the row index that contains the column headers.
        
        Looks for a row containing 'Date', 'Description', and 'Amount'
        
        Returns:
            Row index if found, None otherwise
        """
        for i in range(min(20, len(df_raw))):
            row = df_raw.iloc[i]
            row_str = ' '.join([str(x).lower() for x in row if pd.notna(x)])
            
            if 'date' in row_str and 'description' in row_str and 'amount' in row_str:
                return i
            
        return None
    
    def _validate_columns(self, df: pd.DataFrame) -> None:
        """Ensure all required columns are present"""
        required_columns = [self.DATE_COL, self.DESCRIPTION_COL, self.AMOUNT_COL]
        missing = [col for col in required_columns if col not in df.columns]
        if missing:
            raise ValueError(
                f"Missing required columns: {missing}. "
                f"Available columns: {list(df.columns)}"
            )
        
    def _valid_row(self, row: pd.Series) -> bool:
        # Skip rows with missing date
        if pd.isna(row[self.DATE_COL]):
            return False

        # credit rows in the excel sheet have a different structure
        is_credit_row = self._is_credit_row(row)

        if is_credit_row:
            # the amount is shown in the cardmember col
            if pd.isna(row[self.CARDMEMBER_COL]):
                False
        else:
            if pd.isna(row[self.AMOUNT_COL]):
                False

        return True
    
    def _is_payment_row(self, row: pd.Series) -> bool:
        return row.get(self.MERCHANT_ADDR_COL) == 'PAYMENT RECEIVED - THANK YOU'
    
    def _is_credit_row(self, row: pd.Series) -> bool:
        """
        Detect if this is a credit row (grey row) using multiple signals.
        
        Credit rows have:
        1. NaN in Description column
        2. Amount value in Cardmember column (with negative sign)
        3. Actual description in Merchant Address column
        """

        # Primary signal: Description is empty
        if(pd.isna(row[self.DESCRIPTION_COL])):
            # Secondary confirmation: Cardmember contains amount-like string
            cardmember_val = str(row.get(self.CARDMEMBER_COL, ''))
            if '-&' in cardmember_val or cardmember_val.startswith('-'):
                return True
        
        # Or check if Merchant Address has content (description moved there)
        if pd.notna(row.get(self.MERCHANT_ADDR_COL)):
            return True
        
        return False

        
    def _parse_row(self, row: pd.Series) -> Transaction:
        """
        Parse a single row into a Transaction.
        
        Handles two different row formats:
        1. Normal rows: Description in col 2, Cardmember in col 3, Amount in col 4
        2. Credit rows (grey): Description in col 9, Amount in col 3 (negative)
        """
        # Parse date
        date = pd.to_datetime(row[self.DATE_COL])
        
        # Check if this is a credit row (grey row with different structure)
        # Credit rows have NaN in the Description column but amount in a different position
        is_credit_row = self._is_credit_row(row)

        if is_credit_row:
            # This is a grey credit row - different column structure
            
            # Amount is in 'Cardmember' column (col 3 in raw), Description is in 'Merchant Address' column (col 9 in raw)
            amount_str = str(row[self.CARDMEMBER_COL])  # Amount is actually here for credit rows
            
            # Description is in a different column - try 'Merchant Address' or 'Additional Information'
            if pd.notna(row.get(self.MERCHANT_ADDR_COL)):
                description = str(row[self.MERCHANT_ADDR_COL]).strip()
            elif pd.notna(row.get('Additional Information')):
                description = str(row['Additional Information']).strip()
            else:
                description = "CREDIT"  

            # Parse amount - should have negative sign
            amount_str = amount_str.replace('$', '').replace(',', '').strip()
            amount_value = float(amount_str)
            
            # For credit rows, amount is already negative
            amount = Decimal(str(abs(amount_value)))
            transaction_type = TransactionType.CREDIT
        else:
            # Normal debit row - standard column structure
            description = str(row[self.DESCRIPTION_COL]).strip()
            
            amount_str = str(row[self.AMOUNT_COL])
            amount_str = amount_str.replace('$', '').replace(',', '').strip()
            amount_value = float(amount_str)
            amount = Decimal(str(amount_value))
            
            transaction_type = TransactionType.DEBIT

        return Transaction(
            date=date,
            description=description,
            amount=amount,
            type=transaction_type,
            account="amex",
            category=None
        )
        