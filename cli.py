from pathlib import Path
import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel

from app.controllers.messages_controller import MessagesController
from app.services.messages_service import ImportOptions

app = typer.Typer(
    name="extra",
    help="Message database management CLI",
    no_args_is_help=True,
)
console = Console()

SQLITE_DB_PATH = "sqlite:///messages.db"


@app.callback()
def callback():
    """
    Message database management CLI
    """
    pass


@app.command(name="import")
def import_messages(
    filename: Path = typer.Argument(
        ...,
        help="Path to the JSONL file containing messages to import",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    drop_existing: bool = typer.Option(
        True,
        "--drop/--no-drop",
        help="Drop existing tables before importing"
    )
):
    """
    Import messages from a JSONL file into the SQLite database.
    
    Each line in the JSONL file should contain a message object with:
    - id: unique message identifier
    - subject: message subject
    - from: sender email
    - to: recipient email(s)
    - snippet: short preview
    - body: base64 encoded message body
    - date: ISO-8601 formatted date string
    """
    console.print(f"\n[bold cyan]Importing messages from:[/bold cyan] {filename}")
    
    if drop_existing:
        console.print("[yellow]Dropping existing tables...[/yellow]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Processing messages...", total=None)
        
        try:
            # Use controller to handle the import
            controller = MessagesController(db_path=SQLITE_DB_PATH)
            options = ImportOptions(drop_existing=drop_existing)
            result = controller.import_messages(file_path=filename, options=options)
            progress.update(task, description=f"Loaded {result.total_imported} messages")
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            raise typer.Exit(code=1)
    
    console.print(f"\n[bold green]✓[/bold green] Successfully imported {result.total_imported} messages\n")
    
    # Display preview
    console.print(Panel.fit(
        "[bold]Preview: First 5 messages[/bold]",
        border_style="cyan"
    ))
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Subject", style="cyan", no_wrap=False)
    table.add_column("From", style="green")
    table.add_column("Date", style="yellow")
    table.add_column("Snippet", style="white", no_wrap=False, max_width=40)
    
    for msg in result.preview_messages:
        table.add_row(
            msg.subject[:50] + "..." if len(msg.subject) > 50 else msg.subject,
            msg.sender,
            msg.date.strftime("%Y-%m-%d %H:%M") if msg.date else "N/A",
            msg.snippet[:40] + "..." if msg.snippet and len(msg.snippet) > 40 else msg.snippet or ""
        )
    
    console.print(table)
    console.print()


if __name__ == "__main__":
    app()

