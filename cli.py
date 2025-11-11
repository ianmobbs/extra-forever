from pathlib import Path
import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel

from app.controllers.messages_controller import MessagesController
from app.controllers.categories_controller import CategoriesController
from app.services.messages_service import ImportOptions

app = typer.Typer(
    name="extra",
    help="Gmail-style message classification system CLI",
    no_args_is_help=True,
)
console = Console()

SQLITE_DB_PATH = "sqlite:///messages.db"

# Create command groups
messages_app = typer.Typer(help="Message management commands")
category_app = typer.Typer(help="Category management commands")

# Register command groups
app.add_typer(messages_app, name="messages")
app.add_typer(category_app, name="category")


@app.callback()
def callback():
    """
    Gmail-style message classification system CLI
    """
    pass


# ===== Messages Commands =====

@messages_app.command(name="import")
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


@messages_app.command(name="list")
def list_messages(
    limit: int = typer.Option(10, "--limit", "-l", help="Maximum number of messages to display"),
    offset: int = typer.Option(0, "--offset", "-o", help="Number of messages to skip")
):
    """
    List messages from the database.
    """
    console.print(f"\n[bold cyan]Messages (limit={limit}, offset={offset}):[/bold cyan]\n")
    
    try:
        controller = MessagesController(db_path=SQLITE_DB_PATH)
        messages = controller.list_messages(limit=limit, offset=offset)
        
        if not messages:
            console.print("[yellow]No messages found.[/yellow]\n")
            return
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("ID", style="cyan", max_width=15)
        table.add_column("Subject", style="green", no_wrap=False, max_width=30)
        table.add_column("From", style="yellow", max_width=25)
        table.add_column("Date", style="white")
        
        for msg in messages:
            table.add_row(
                msg.id[:15] + "..." if len(msg.id) > 15 else msg.id,
                msg.subject[:30] + "..." if len(msg.subject) > 30 else msg.subject,
                msg.sender[:25] + "..." if len(msg.sender) > 25 else msg.sender,
                msg.date.strftime("%Y-%m-%d %H:%M") if msg.date else "N/A"
            )
        
        console.print(table)
        console.print()
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@messages_app.command(name="get")
def get_message(
    message_id: str = typer.Argument(..., help="Message ID")
):
    """
    Get a message by ID and display its details.
    """
    console.print(f"\n[bold cyan]Getting message ID:[/bold cyan] {message_id}\n")
    
    try:
        controller = MessagesController(db_path=SQLITE_DB_PATH)
        result = controller.get_message(message_id)
        
        if not result:
            console.print(f"[yellow]Message with ID {message_id} not found.[/yellow]\n")
            raise typer.Exit(code=1)
        
        msg = result.message
        
        # Display message details
        console.print(Panel.fit(
            f"[bold]Subject:[/bold] {msg.subject}\n"
            f"[bold]From:[/bold] {msg.sender}\n"
            f"[bold]To:[/bold] {', '.join(msg.to)}\n"
            f"[bold]Date:[/bold] {msg.date.strftime('%Y-%m-%d %H:%M:%S') if msg.date else 'N/A'}\n"
            f"[bold]Snippet:[/bold] {msg.snippet or 'N/A'}\n\n"
            f"[bold]Body:[/bold]\n{msg.body[:500] + '...' if msg.body and len(msg.body) > 500 else msg.body or 'N/A'}",
            title=f"Message {msg.id}",
            border_style="cyan"
        ))
        console.print()
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@messages_app.command(name="delete")
def delete_message(
    message_id: str = typer.Argument(..., help="Message ID"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt")
):
    """
    Delete a message by ID.
    
    Example:
        extra messages delete msg123 --yes
    """
    if not confirm:
        confirm = typer.confirm(f"Are you sure you want to delete message {message_id}?")
        if not confirm:
            console.print("[yellow]Cancelled.[/yellow]")
            raise typer.Exit(code=0)
    
    console.print(f"\n[bold cyan]Deleting message ID:[/bold cyan] {message_id}")
    
    try:
        controller = MessagesController(db_path=SQLITE_DB_PATH)
        success = controller.delete_message(message_id)
        
        if not success:
            console.print(f"[yellow]Message with ID {message_id} not found.[/yellow]\n")
            raise typer.Exit(code=1)
        
        console.print(f"[bold green]✓[/bold green] Successfully deleted message\n")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


# ===== Category Commands =====

@category_app.command(name="create")
def create_category(
    name: str = typer.Argument(..., help="Name of the category"),
    description: str = typer.Argument(..., help="Natural-language description of the category")
):
    """
    Create a new category.
    
    Example:
        extra category create "Work Travel" "Work-related travel receipts from airlines"
    """
    console.print(f"\n[bold cyan]Creating category:[/bold cyan] {name}")
    
    try:
        controller = CategoriesController(db_path=SQLITE_DB_PATH)
        result = controller.create_category(name, description)
        
        console.print(f"[bold green]✓[/bold green] Successfully created category\n")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Description", style="white")
        
        table.add_row(
            str(result.category.id),
            result.category.name,
            result.category.description
        )
        
        console.print(table)
        console.print()
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@category_app.command(name="list")
def list_categories():
    """
    List all categories.
    """
    console.print("\n[bold cyan]Categories:[/bold cyan]\n")
    
    try:
        controller = CategoriesController(db_path=SQLITE_DB_PATH)
        categories = controller.list_categories()
        
        if not categories:
            console.print("[yellow]No categories found.[/yellow]\n")
            return
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Description", style="white", no_wrap=False)
        
        for cat in categories:
            table.add_row(
                str(cat.id),
                cat.name,
                cat.description
            )
        
        console.print(table)
        console.print()
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@category_app.command(name="get")
def get_category(
    category_id: int = typer.Argument(..., help="Category ID")
):
    """
    Get a category by ID.
    """
    console.print(f"\n[bold cyan]Getting category ID:[/bold cyan] {category_id}\n")
    
    try:
        controller = CategoriesController(db_path=SQLITE_DB_PATH)
        result = controller.get_category(category_id)
        
        if not result:
            console.print(f"[yellow]Category with ID {category_id} not found.[/yellow]\n")
            raise typer.Exit(code=1)
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Description", style="white", no_wrap=False)
        
        table.add_row(
            str(result.category.id),
            result.category.name,
            result.category.description
        )
        
        console.print(table)
        console.print()
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@category_app.command(name="update")
def update_category(
    category_id: int = typer.Argument(..., help="Category ID"),
    name: str = typer.Option(None, "--name", help="New name for the category"),
    description: str = typer.Option(None, "--description", help="New description for the category")
):
    """
    Update a category.
    
    Example:
        extra category update 1 --name "Work Receipts" --description "All work-related receipts"
    """
    if name is None and description is None:
        console.print("[bold red]Error:[/bold red] Must provide at least one of --name or --description")
        raise typer.Exit(code=1)
    
    console.print(f"\n[bold cyan]Updating category ID:[/bold cyan] {category_id}")
    
    try:
        controller = CategoriesController(db_path=SQLITE_DB_PATH)
        result = controller.update_category(category_id, name=name, description=description)
        
        if not result:
            console.print(f"[yellow]Category with ID {category_id} not found.[/yellow]\n")
            raise typer.Exit(code=1)
        
        console.print(f"[bold green]✓[/bold green] Successfully updated category\n")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Description", style="white", no_wrap=False)
        
        table.add_row(
            str(result.category.id),
            result.category.name,
            result.category.description
        )
        
        console.print(table)
        console.print()
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@category_app.command(name="delete")
def delete_category(
    category_id: int = typer.Argument(..., help="Category ID"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt")
):
    """
    Delete a category.
    
    Example:
        extra category delete 1 --yes
    """
    if not confirm:
        confirm = typer.confirm(f"Are you sure you want to delete category {category_id}?")
        if not confirm:
            console.print("[yellow]Cancelled.[/yellow]")
            raise typer.Exit(code=0)
    
    console.print(f"\n[bold cyan]Deleting category ID:[/bold cyan] {category_id}")
    
    try:
        controller = CategoriesController(db_path=SQLITE_DB_PATH)
        success = controller.delete_category(category_id)
        
        if not success:
            console.print(f"[yellow]Category with ID {category_id} not found.[/yellow]\n")
            raise typer.Exit(code=1)
        
        console.print(f"[bold green]✓[/bold green] Successfully deleted category\n")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()

