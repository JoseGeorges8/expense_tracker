import typer
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich import box

from expense_tracker.parsers.factory import ParserFactory
from expense_tracker.repositories.sqlite_transaction_repository import SQLiteTransactionRepository
from expense_tracker.database.connection import DatabaseConfig, DatabaseManager
from expense_tracker.services.transaction_service import TransactionService


app = typer.Typer(
    name="expense-tracker",
    help="Track and analyze your personal expenses",
    add_completion=False,
)

console = Console()

class State:
    verbose: bool = False
    service: Optional[TransactionService] = None


state = State()

@app.callback()
def main(
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Enable verbose output",
    )
):
    """
    Expense Tracker - Import, categorize, and analyze your expenses.
    """

    if state.service is None:
        ParserFactory.load_parsers_from_config()
        db_manager = DatabaseManager(DatabaseConfig())
        repository = SQLiteTransactionRepository(db_manager)
        state.service = TransactionService(repository)

    state.verbose = verbose

@app.command(name="import")
def import_transactions(
    filepath: Path = typer.Argument(
        ...,
        help="Path to financial institution file",
        exists=True,
        file_okay=True,
        dir_okay=False
    ),
    financial_institution: str = typer.Option(
        "amex",
        "--fi", "-f",
        help="Financial institution (amex, cibc, etc)"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview without saving to database",
    ),
):
    """
    Import transactions from a financial institution statement.
    
    Examples:
        expense-tracker import statement.xlsx
        expense-tracker import statement.xlsx --fi amex --dry-run
    """
    try:
        console.print(Panel.fit(
            f"[bold cyan]Import Configuration[/bold cyan]\n"
            f"File: {filepath}\n"
            f"Financial Institution: {financial_institution.upper()}\n"
            f"Mode: {'DRY RUN' if dry_run else 'LIVE'}",
            border_style="cyan"
        ))

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Importing transactions...", total=None)
            
            result = state.service.import_statement(
                filepath=filepath,
                financial_institution=financial_institution,
                dry_run=dry_run,
            )

            progress.update(task, completed=True)

        console.print(f"\n[bold]Found {result.total_parsed} transactions[/bold]")

        if result.imported or result.skipped:
            preview_transactions = (result.imported + result.skipped)[:5]
            preview_table = Table(title="Preview (first 5)")
            preview_table.add_column("Date", style="cyan")
            preview_table.add_column("Description", style="white")
            preview_table.add_column("Amount", justify="right")
            preview_table.add_column("Status", justify="center")

            for txn in preview_transactions:
                status = "[green]NEW[/green]" if txn in result.imported else "[yellow]DUP[/yellow]"
                amount_color = "green" if txn.type.value == "Credit" else "red"
                preview_table.add_row(
                    str(txn.date),
                    txn.description[:40],
                    f"[{amount_color}]${txn.amount:.2f}[/{amount_color}]",
                    status
                )
            
            console.print("\n")
            console.print(preview_table)

        console.print("")
        if dry_run:
            console.print(f"[yellow]DRY RUN - No changes made[/yellow]")
            console.print(f"[green]✓[/green] Would import: {result.new_transactions}")
            console.print(f"[yellow]⏭️[/yellow]  Would skip: {result.duplicates_skipped}")
        else:
            console.print(f"[bold green]✓ Imported {result.new_transactions} new transactions[/bold green]")
            if result.duplicates_skipped > 0:
                console.print(f"[yellow]⏭️  Skipped {result.duplicates_skipped} duplicates[/yellow]")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        if state.verbose:
            console.print_exception()
        raise typer.Exit(code=1)

def cli_main():
    """Entry point for the CLI"""
    app()


if __name__ == "__main__":
    cli_main()

