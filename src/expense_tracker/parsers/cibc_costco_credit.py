import pdfplumber
import re
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Tuple
from pathlib import Path

from expense_tracker.domain.models import Transaction
from expense_tracker.domain.enums import TransactionType
from expense_tracker.parsers.base import StatementParser


class CIBCCostcoCreditCardParser(StatementParser):
    """
    Parser for CIBC Costco World Mastercard PDF statements.
    
    Handles:
    - Payment transactions (credits)
    - Purchase transactions (debits)
    - Multiple card numbers on same statement
    - Foreign currency transactions
    - Bonus reward markers (Ý)
    - Multi-page statements
    
    Example:
        parser = CIBCCostcoCreditCardParser()
        transactions = parser.parse('statement.pdf')
    """
    
    # Known spend categories from CIBC statements
    SPEND_CATEGORIES = [
        "Retail and Grocery",
        "Home and Office Improvement",
        "Restaurants",
        "Transportation",
        "Health and Education",
        "Personal and Household Expenses",
        "Foreign Currency Transactions",
        "Hotel, Entertainment and Recreation",
        "Professional and Financial Services",
    ]
    
    # Patterns for section detection
    SECTION_MARKERS = {
        'payments': r'Your payments',
        'charges': r'Your new charges and credits',
        'summary': r'Your account at a glance',
    }
    
    # Patterns to skip
    SKIP_PATTERNS = [
        r'^Card number',
        r'^Trans\s+Post',
        r'^date\s+date',
        r'^Ý\s*$',  # Just the bonus marker alone
        r'^Page \d+',
        r'Identifies transactions',
        r'^Total payments',
        r'^Total for',
        r'^Information about',
        r'^\s*$',  # Empty lines
    ]
    
    def __init__(self):
        """Initialize the parser"""
        self.statement_year = None
        self.statement_month = None
        self.current_card_number = None
    
    def validate_file(self, filepath: str) -> None:
        """
        Validate that the file is a CIBC Costco statement.
        
        Args:
            filepath: Path to the PDF file
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is not a valid CIBC Costco statement
        """
        path = Path(filepath)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        if path.suffix.lower() != '.pdf':
            raise ValueError(f"File must be a PDF, got: {path.suffix}")
        
        try:
            with pdfplumber.open(filepath) as pdf:
                if not pdf.pages:
                    raise ValueError("PDF has no pages")
                
                first_page_text = pdf.pages[0].extract_text()
                
                if not first_page_text:
                    raise ValueError("Could not extract text from PDF")
                
                # Check for required identifiers
                required_identifiers = [
                    "CIBC Costco World Mastercard",
                    "Your account at a glance",
                ]
                
                for identifier in required_identifiers:
                    if identifier not in first_page_text:
                        raise ValueError(
                            f"Not a CIBC Costco statement - missing: {identifier}"
                        )
                        
        except Exception as e:
            if isinstance(e, (FileNotFoundError, ValueError)):
                raise
            raise ValueError(f"Error validating PDF: {e}")
    
    def parse(self, filepath: str) -> List[Transaction]:
        """
        Parse transactions from CIBC Costco statement.
        
        Args:
            filepath: Path to the PDF statement
            
        Returns:
            List of Transaction objects
            
        Raises:
            ValueError: If file is invalid or parsing fails
        """
        self.validate_file(filepath)
        
        transactions = []
        
        try:
            with pdfplumber.open(filepath) as pdf:
                # Extract metadata from first page
                self._extract_statement_metadata(pdf.pages[0])
                
                # Parse each page
                for page_num, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    
                    if not text:
                        print(f"Warning: No text extracted from page {page_num + 1}")
                        continue
                    
                    # Skip first page (summary only)
                    if page_num == 0:
                        continue
                    
                    # Parse transactions from this page
                    page_txns = self._parse_page_text(text)
                    transactions.extend(page_txns)
                    
        except Exception as e:
            raise ValueError(f"Error parsing PDF: {e}")
        
        if not transactions:
            print("Warning: No transactions found in statement")
        
        return transactions
    
    def _extract_statement_metadata(self, first_page) -> None:
        """
        Extract statement year and month from first page.
        
        Args:
            first_page: pdfplumber page object
        """
        text = first_page.extract_text()
        
        # Look for "Statement Date\nDecember 20, 2025"
        date_match = re.search(
            r'Statement Date[^\d]*(\w+)\s+(\d{1,2}),?\s+(\d{4})',
            text,
            re.IGNORECASE
        )
        
        if date_match:
            month_str, _, year = date_match.groups()
            self.statement_year = int(year)
            self.statement_month = month_str
        else:
            # Fallback: look for any date in format "November 21 to December 20, 2025"
            range_match = re.search(
                r'(\w+)\s+\d{1,2}\s+to\s+(\w+)\s+\d{1,2},?\s+(\d{4})',
                text
            )
            if range_match:
                _, end_month, year = range_match.groups()
                self.statement_year = int(year)
                self.statement_month = end_month
            else:
                # Last resort: current year
                self.statement_year = date.today().year
                self.statement_month = None
    
    def _parse_page_text(self, text: str) -> List[Transaction]:
        """
        Parse all transactions from a page of text.

        Uses state machine to track which section we're in:
        - payments section
        - charges section
        - neither (skip)

        Args:
            text: Extracted text from page

        Returns:
            List of Transaction objects
        """
        transactions = []
        lines = text.split('\n')
        current_section = None

        for line_num, line in enumerate(lines):
            section = self._detect_section_change(line)
            if section is not None:
                current_section = section
                continue

            if self._detect_card_number(line):
                continue

            if self._is_section_end(line):
                current_section = None
                continue

            if current_section is None or self._should_skip_line(line):
                continue

            txn = self._parse_transaction_line(line, current_section, line_num)
            if txn:
                transactions.append(txn)

        return transactions

    def _detect_section_change(self, line: str) -> Optional[str]:
        if re.search(self.SECTION_MARKERS['payments'], line, re.IGNORECASE):
            return "payments"
        elif re.search(self.SECTION_MARKERS['charges'], line, re.IGNORECASE):
            return "charges"
        return None

    def _detect_card_number(self, line: str) -> bool:
        card_match = re.search(r'Card number\s+(\d{4}\s+X+\s+X+\s+\d{4})', line)
        if card_match:
            self.current_card_number = card_match.group(1)
            return True
        return False

    def _is_section_end(self, line: str) -> bool:
        return re.match(r'^Total (payments|for)', line, re.IGNORECASE) is not None

    def _parse_transaction_line(self, line: str, current_section: str, line_num: int) -> Optional[Transaction]:
        try:
            if current_section == "payments":
                txn = self._parse_payment_line(line)
            else:
                txn = self._parse_charge_line(line)
            return txn
        except Exception as e:
            print(f"Warning: Failed to parse line {line_num + 1}: {e}")
            print(f"  Line content: {line[:100]}")
            return None
    
    def _should_skip_line(self, line: str) -> bool:
        """
        Check if a line should be skipped during parsing.
        
        Args:
            line: Text line to check
            
        Returns:
            True if line should be skipped
        """
        line = line.strip()
        
        # Empty line
        if not line:
            return True
        
        # Match against skip patterns
        for pattern in self.SKIP_PATTERNS:
            if re.match(pattern, line, re.IGNORECASE):
                return True
        
        return False
    
    def _parse_payment_line(self, line: str) -> Optional[Transaction]:
        """
        Parse a payment transaction line.
        
        Format: "Nov 27 Nov 28 PAYMENT THANK YOU/PAIEMENT MERCI 2,933.53"
        
        Args:
            line: Text line containing payment
            
        Returns:
            Transaction object or None if parsing fails
        """
        line = line.strip()
        
        # Pattern: trans_date post_date description amount
        # Date format: "Nov 27" or "Dec 5"
        pattern = r'^(\w{3}\s+\d{1,2})\s+\w{3}\s+\d{1,2}\s+(.+?)\s+([\d,]+\.\d{2})$'
        
        match = re.match(pattern, line)
        
        if not match:
            return None
        
        trans_date_str, description, amount_str = match.groups()
        
        # Parse components
        trans_date = self._parse_date(trans_date_str)
        if not trans_date:
            return None
        
        amount = self._parse_amount(amount_str)
        
        return Transaction(
            date=trans_date,
            description=description.strip(),
            amount=amount,
            type=TransactionType.CREDIT,  # Payments are always credits
            account="cibc-costco-credit",
            category=None
        )
    
    def _parse_charge_line(self, line: str) -> Optional[Transaction]:
        """
        Parse a charge/debit transaction line.
        
        Format: "Dec 10 Dec 11 ZEHRS KINSVILLE #572 KINGSVILLE ON Retail and Grocery 87.15"
        Or with bonus marker: "Ý Dec 07 Dec 08 DALDONGNAE 9 MISSISSAUGA ON Restaurants 102.15"
        
        Args:
            line: Text line containing charge
            
        Returns:
            Transaction object or None if parsing fails
        """
        # Remove bonus reward marker if present
        line = line.replace('Ý', '').strip()
        
        # Must start with a date
        if not re.match(r'^\w{3}\s+\d{1,2}', line):
            return None
        
        # Must end with an amount (optionally negative)
        amount_match = re.search(r'(-?[\d,]+\.\d{2})$', line)
        if not amount_match:
            return None
        
        amount_str = amount_match.group(1)
        
        # Extract transaction date (first two tokens)
        parts = line.split(None, 2)  # Split into max 3 parts
        if len(parts) < 3:
            return None
        
        month, day, rest_of_line = parts
        trans_date_str = f"{month} {day}"
        
        # Parse the rest: post_date description category amount
        # Remove amount from end
        middle = rest_of_line[:amount_match.start()].strip()
        
        # Skip post date (first token in middle)
        middle_parts = middle.split(None, 1)
        if len(middle_parts) < 2:
            return None
        
        _, desc_and_category = middle_parts
        
        # Extract category from end (if present)
        description = self._extract_description(
            desc_and_category
        )
        
        # Determine transaction type
        txn_type = self._determine_transaction_type(description, amount_str)
        
        # Parse date
        trans_date = self._parse_date(trans_date_str)
        if not trans_date:
            return None
        
        # Parse amount (always positive)
        amount = self._parse_amount(amount_str)
        
        return Transaction(
            date=trans_date,
            description=description,
            amount=abs(amount),  # Ensure positive
            type=txn_type,
            account="cibc-costco-credit",
            category=None
        )
    
    def _extract_description(
        self, 
        text: str
    ) -> str:
        """
        Extract category from end of text and return remaining description.
        
        Args:
            text: Combined description and category text
            
        Returns:
            description
        """
        description = text
        
        # Check if text ends with a known category
        for cat in self.SPEND_CATEGORIES:
            if text.endswith(cat):
                description = text[:-len(cat)].strip()
                break
        
        return description
    
    def _determine_transaction_type(
        self, 
        description: str, 
        amount_str: str
    ) -> TransactionType:
        """
        Determine if transaction is a debit or credit.
        
        Credits are:
        - Refunds
        - Returns
        - Credits (explicitly marked)
        - Negative amounts (though rare in CIBC format)
        
        Args:
            description: Transaction description
            amount_str: Original amount string (may have negative sign)
            
        Returns:
            TransactionType.DEBIT or TransactionType.CREDIT
        """
        # Check for negative amount
        if amount_str.startswith('-'):
            return TransactionType.CREDIT
        
        # Check for credit keywords in description
        credit_keywords = ['REFUND', 'RETURN', 'CREDIT', 'REVERSAL']
        description_upper = description.upper()
        
        for keyword in credit_keywords:
            if keyword in description_upper:
                return TransactionType.CREDIT
        
        # Default to debit
        return TransactionType.DEBIT
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """
        Parse date string like 'Nov 27' or 'Dec 5'.
        
        Args:
            date_str: Date string in format "MMM DD"
            
        Returns:
            date object or None if parsing fails
        """
        if not date_str or not self.statement_year:
            return None
        
        try:
            # Parse as "MMM DD YYYY"
            parsed = datetime.strptime(
                f"{date_str} {self.statement_year}",
                "%b %d %Y"
            )
            return parsed.date()
            
        except ValueError as e:
            print(f"Warning: Could not parse date '{date_str}': {e}")
            return None
    
    def _parse_amount(self, amount_str: str) -> Decimal:
        """
        Parse amount string to Decimal.
        
        Handles:
        - Comma thousands separators: "2,933.53"
        - Dollar signs: "$100.00"
        - Negative signs: "-50.00"
        
        Args:
            amount_str: Amount string
            
        Returns:
            Decimal value
            
        Raises:
            ValueError: If amount cannot be parsed
        """
        # Remove formatting
        cleaned = (
            amount_str
            .replace('$', '')
            .replace(',', '')
            .strip()
        )
        
        try:
            return Decimal(cleaned)
        except Exception as e:
            raise ValueError(f"Could not parse amount '{amount_str}': {e}")
    
    def __repr__(self) -> str:
        return "CIBCCostcoCreditCardParser()"


if __name__ == "__main__":
    parser = CIBCCostcoCreditCardParser()
    statement_filepath = '/Users/josegeorges/Documents/Personal/Projects/budget-planner/cibc_costco_credit_card.pdf'
    parser.validate_file(statement_filepath)
    transactions = parser.parse(statement_filepath)

    for transaction in transactions:
        print(f"{transaction}")

