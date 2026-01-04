import typer
from pathlib import Path
from typing import Optional
from datetime import date

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from expense_tracker.parsers.factory import ParserFactory
from expense_tracker.repositories.sqlite_transaction_repository import SQLiteTransactionRepository
from expense_tracker.database.connection import DatabaseConfig, DatabaseManager
from expense_tracker.services.transaction_service import TransactionService
from expense_tracker.domain.enums import TransactionType

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
    categorize: bool = typer.Option(
        False,
        "--categorize",
        help="Categorize transactions as they are being imported",
    ),
):
    """
    Import transactions from a financial institution statement.
    
    Examples:
        expense-tracker import statement.xlsx
        expense-tracker import statement.xlsx --fi amex --dry-run
        expense-tracker import statement.xlsx --fi amex --categorize
    """
    try:
        console.print(Panel.fit(
            f"[bold cyan]Import Configuration[/bold cyan]\n"
            f"File: {filepath}\n"
            f"Financial Institution: {financial_institution.upper()}\n"
            f"Mode: {'DRY RUN' if dry_run else 'LIVE'}"
            f"Categorize: {'YES' if categorize else 'NO'}",
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
                categorize=categorize
            )

            progress.update(task, completed=True)

        console.print(f"\n[bold]Found {result.total_parsed} transactions[/bold]")

        if result.imported or result.skipped:
            preview_transactions = (result.imported + result.skipped)
            preview_table = Table(title="Preview (first 5)")
            preview_table.add_column("Date", style="cyan")
            preview_table.add_column("Description", style="white")
            preview_table.add_column("Category", style="magenta")
            preview_table.add_column("Amount", justify="right")
            preview_table.add_column("Status", justify="center")

            for txn in preview_transactions:
                status = "[green]NEW[/green]" if txn in result.imported else "[yellow]DUP[/yellow]"
                amount_color = "green" if txn.type.value == "Credit" else "red"
                preview_table.add_row(
                    str(txn.date),
                    txn.description[:40],
                    txn.category or "Uncategorized",
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
    
@app.command(name="report")
def report(
    month: Optional[int] = typer.Option(
        None,
        "--month", "-m",
        help="Month (1-12)",
        min=1,
        max=12
    ),
    year: Optional[int] = typer.Option(
        None,
        "--year", "-y",
        help="Year",
    ),
):
    """
    Generate a monthly expense report.

    Examples:
        expense-tracker report
        expense-tracker report --month --year 2025
    """
    try:
        if month is None:
            month = date.today().month

        if year is None:
            year = date.today().year

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Generating report...", total=None)
            
            summary = state.service.get_monthly_summary(
                year=year,
                month=month
            )

            progress.update(task, completed=True)

        month_name = summary.start_date.strftime("%B %Y")
        console.print(f"\n[bold cyan]Monthly Report: {month_name}[/bold cyan]")

        if summary.total_transactions == 0:
            console.print(Panel(
                "[yellow]No transactions found for this month[/yellow]",
                title="Empty Report",
                border_style="yellow"
            ))
            return

        # ═══════════════════════════════════════════════════════════
        # SUMMARY PANEL - Overview of income/expenses
        # ═══════════════════════════════════════════════════════════
        
        summary_text = (
            f"[bold]Transactions:[/bold] {summary.total_transactions}\n\n"
            f"[red]💸 Expenses:[/red]  ${summary.total_debits:>10,.2f}\n"
            f"[green]💰 Income:[/green]    ${summary.total_credits:>10,.2f}\n"
            f"{'─' * 30}\n"
        )
        
        # Net flow with color based on positive/negative
        if summary.net_flow >= 0:
            summary_text += f"[bold green]📈 Net:[/bold green]      ${summary.net_flow:>10,.2f}"
        else:
            summary_text += f"[bold red]📉 Net:[/bold red]      ${summary.net_flow:>10,.2f}"
        
        console.print(Panel(
            summary_text,
            title=f"[bold]{month_name} Summary[/bold]",
            border_style="cyan",
            padding=(1, 2)
        ))
        
        # ═══════════════════════════════════════════════════════════
        # SPENDING BY CATEGORY - Top categories
        # ═══════════════════════════════════════════════════════════
        
        if summary.debits_by_category:
            console.print(f"\n[bold]Top Spending Categories[/bold]")
            
            category_table = Table(show_header=True, box=None, padding=(0, 2))
            category_table.add_column("Category", style="cyan", no_wrap=True)
            category_table.add_column("Amount", justify="right", style="red")
            category_table.add_column("% of Total", justify="right", style="dim")
            
            for category, amount in summary.top_spending_categories[:10]:
                percentage = (amount / summary.total_debits * 100) if summary.total_debits > 0 else 0
                category_table.add_row(
                    category,
                    f"${amount:,.2f}",
                    f"{percentage:.1f}%"
                )
            
            console.print(category_table)
        
        # ═══════════════════════════════════════════════════════════
        # INCOME BY CATEGORY (if any)
        # ═══════════════════════════════════════════════════════════
        
        if summary.credits_by_category:
            console.print(f"\n[bold]Income by Category[/bold]")
            
            income_table = Table(show_header=True, box=None, padding=(0, 2))
            income_table.add_column("Category", style="cyan", no_wrap=True)
            income_table.add_column("Amount", justify="right", style="green")
            
            sorted_credits = sorted(
                summary.credits_by_category.items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            for category, amount in sorted_credits[:5]:
                income_table.add_row(category, f"${amount:,.2f}")
            
            console.print(income_table)
        
        # ═══════════════════════════════════════════════════════════
        # RECENT TRANSACTIONS - Latest activity
        # ═══════════════════════════════════════════════════════════
        
        console.print(f"\n[bold]Recent Transactions[/bold]")
        
        all_transactions = summary.debits + summary.credits
        all_transactions.sort(key=lambda t: t.date, reverse=True)
        
        txn_table = Table(show_header=True, padding=(0, 1))
        txn_table.add_column("Date", style="cyan", width=12)
        txn_table.add_column("Description", style="white", max_width=40)
        txn_table.add_column("Category", style="dim", width=15)
        txn_table.add_column("Financial Institution", justify="right", width=12)
        txn_table.add_column("Amount", justify="right", width=12)
        
        # Show up to 15 most recent transactions
        for txn in all_transactions[:15]:
            # Truncate description if too long
            desc = txn.description[:37] + "..." if len(txn.description) > 40 else txn.description
            
            # Color amount based on type
            if txn.type == TransactionType.DEBIT:
                amount_str = f"[red]-${txn.amount:,.2f}[/red]"
            else:
                amount_str = f"[green]+${txn.amount:,.2f}[/green]"
            
            txn_table.add_row(
                str(txn.date),
                desc,
                txn.category or "Uncategorized",
                txn.account,
                amount_str,
            )
        
        console.print(txn_table)
        
        # Footer with transaction count if we're showing a subset
        if len(all_transactions) > 15:
            console.print(f"\n[dim]Showing 15 of {len(all_transactions)} transactions[/dim]")
        
        if state.verbose:
            console.print(f"\n[dim]→ Report generated successfully[/dim]")
        

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

