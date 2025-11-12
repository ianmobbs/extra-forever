from pathlib import Path
import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel

from app.controllers.messages_controller import MessagesController
from app.controllers.categories_controller import CategoriesController
from app.controllers.bootstrap_controller import BootstrapController
from app.services.messages_service import ImportOptions, ClassificationOptions

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



# ===== Bootstrap Command =====

@app.command(name="bootstrap")
def bootstrap_system(
    messages_file: Path = typer.Option(
        Path("sample-messages.jsonl"),
        "--messages",
        "-m",
        help="Path to the JSONL file containing messages",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    categories_file: Path = typer.Option(
        Path("sample-categories.jsonl"),
        "--categories",
        "-c",
        help="Path to the JSONL file containing categories",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    drop_existing: bool = typer.Option(
        True,
        "--drop/--no-drop",
        help="Drop existing tables before bootstrapping"
    ),
    auto_classify: bool = typer.Option(
        True,
        "--classify/--no-classify",
        help="Automatically classify messages into categories"
    ),
    classification_top_n: int = typer.Option(
        3,
        "--top-n",
        "-n",
        help="Maximum number of categories per message"
    ),
    classification_threshold: float = typer.Option(
        0.5,
        "--threshold",
        "-t",
        help="Minimum similarity threshold for classification (0-1)"
    )
):
    """
    Bootstrap the system with sample messages and categories.
    
    This command initializes the database with sample data from JSONL files,
    making the system immediately usable for testing and exploration.
    
    Examples:
        extra bootstrap
        extra bootstrap --messages custom.jsonl --categories custom-cats.jsonl
        extra bootstrap --no-classify  # Skip auto-classification
    """
    console.print("\n[bold cyan]Bootstrapping system...[/bold cyan]")
    
    if drop_existing:
        console.print("[yellow]Dropping existing tables...[/yellow]")
    
    if auto_classify:
        console.print(f"[cyan]Auto-classification enabled (top_n={classification_top_n}, threshold={classification_threshold})[/cyan]\n")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Loading data...", total=None)
        
        try:
            controller = BootstrapController(db_path=SQLITE_DB_PATH)
            classification_opts = ClassificationOptions(
                auto_classify=auto_classify,
                top_n=classification_top_n,
                threshold=classification_threshold
            )
            result = controller.bootstrap(
                messages_file=messages_file,
                categories_file=categories_file,
                drop_existing=drop_existing,
                classification_options=classification_opts
            )
            progress.update(task, description="Complete!")
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            raise typer.Exit(code=1)
    
    console.print(f"\n[bold green]✓[/bold green] Successfully bootstrapped system")
    console.print(f"  • Categories: {result.total_categories}")
    console.print(f"  • Messages: {result.total_messages}")
    if auto_classify and result.total_classified > 0:
        console.print(f"  • Classified: {result.total_classified}\n")
    else:
        console.print()
    
    # Display category preview
    if result.preview_categories:
        console.print(Panel.fit(
            "[bold]Category Preview[/bold]",
            border_style="cyan"
        ))
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("ID", style="cyan", justify="right")
        table.add_column("Name", style="green")
        table.add_column("Description", style="white", no_wrap=False)
        
        for cat in result.preview_categories:
            table.add_row(
                str(cat.id),
                cat.name,
                cat.description[:60] + "..." if len(cat.description) > 60 else cat.description
            )
        
        console.print(table)
        console.print()
    
    # Display message preview
    if result.preview_messages:
        console.print(Panel.fit(
            "[bold]Message Preview[/bold]",
            border_style="cyan"
        ))
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Subject", style="cyan", no_wrap=False)
        table.add_column("From", style="green")
        table.add_column("Date", style="yellow")
        table.add_column("Snippet", style="white", no_wrap=False, max_width=40)
        table.add_column("Categories", style="magenta", no_wrap=False, max_width=25)
        
        for msg in result.preview_messages:
            table.add_row(
                msg.subject[:50] + "..." if len(msg.subject) > 50 else msg.subject,
                msg.sender,
                msg.date.strftime("%Y-%m-%d %H:%M") if msg.date else "N/A",
                msg.snippet[:40] + "..." if msg.snippet and len(msg.snippet) > 40 else msg.snippet or "",
                ", ".join([cat.name for cat in msg.categories])[:25] if msg.categories else "-"
            )
        
        console.print(table)
        console.print()


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
    ),
    auto_classify: bool = typer.Option(
        False,
        "--classify/--no-classify",
        help="Automatically classify messages into categories after import"
    ),
    classification_top_n: int = typer.Option(
        3,
        "--top-n",
        "-n",
        help="Maximum number of categories per message (when using --classify)"
    ),
    classification_threshold: float = typer.Option(
        0.5,
        "--threshold",
        "-t",
        help="Minimum similarity threshold for classification (0-1)"
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
    
    Examples:
        extra messages import sample.jsonl
        extra messages import sample.jsonl --classify --top-n 5 --threshold 0.7
    """
    console.print(f"\n[bold cyan]Importing messages from:[/bold cyan] {filename}")
    
    if drop_existing:
        console.print("[yellow]Dropping existing tables...[/yellow]")
    
    if auto_classify:
        console.print(f"[cyan]Auto-classification enabled (top_n={classification_top_n}, threshold={classification_threshold})[/cyan]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Processing messages...", total=None)
        
        try:
            # Use controller to handle the import
            controller = MessagesController(db_path=SQLITE_DB_PATH)
            classification_opts = ClassificationOptions(
                auto_classify=auto_classify,
                top_n=classification_top_n,
                threshold=classification_threshold
            )
            options = ImportOptions(drop_existing=drop_existing, classification=classification_opts)
            result = controller.import_messages(file_path=filename, options=options)
            progress.update(task, description=f"Loaded {result.total_imported} messages")
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            raise typer.Exit(code=1)
    
    console.print(f"\n[bold green]✓[/bold green] Successfully imported {result.total_imported} messages")
    if auto_classify:
        console.print(f"[bold green]✓[/bold green] Messages have been classified into categories\n")
    else:
        console.print()
    
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
    table.add_column("Categories", style="magenta", no_wrap=False, max_width=25)
    
    for msg in result.preview_messages:
        table.add_row(
            msg.subject[:50] + "..." if len(msg.subject) > 50 else msg.subject,
            msg.sender,
            msg.date.strftime("%Y-%m-%d %H:%M") if msg.date else "N/A",
            msg.snippet[:40] + "..." if msg.snippet and len(msg.snippet) > 40 else msg.snippet or "",
            ", ".join([cat.name for cat in msg.categories])[:25] if msg.categories else "-"
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
        table.add_column("Categories", style="magenta", no_wrap=False, max_width=30)
        
        for msg in messages:
            table.add_row(
                msg.id[:15] + "..." if len(msg.id) > 15 else msg.id,
                msg.subject[:30] + "..." if len(msg.subject) > 30 else msg.subject,
                msg.sender[:25] + "..." if len(msg.sender) > 25 else msg.sender,
                msg.date.strftime("%Y-%m-%d %H:%M") if msg.date else "N/A",
                ", ".join([cat.name for cat in msg.categories]) if msg.categories else "-"
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
            f"[bold]Categories:[/bold] {', '.join([cat.name for cat in msg.categories]) if msg.categories else 'None'}\n\n"
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


@messages_app.command(name="classify")
def classify_message(
    message_id: str = typer.Argument(..., help="Message ID to classify"),
    top_n: int = typer.Option(3, "--top-n", "-n", help="Maximum number of categories to return"),
    threshold: float = typer.Option(0.5, "--threshold", "-t", help="Minimum similarity score (0-1)"),
):
    """
    Classify a message into categories using cosine similarity.
    
    This will match the message against all available categories based on their
    embeddings and return the top N matches above the similarity threshold.
    
    Examples:
        extra messages classify msg123
        extra messages classify msg123 --top-n 5 --threshold 0.7
    """
    console.print(f"\n[bold cyan]Classifying message ID:[/bold cyan] {message_id}")
    console.print(f"[dim]Parameters: top_n={top_n}, threshold={threshold}, assign={assign}[/dim]\n")
    
    try:
        controller = MessagesController(db_path=SQLITE_DB_PATH)
        result = controller.classify_message(
            message_id,
            top_n=top_n,
            threshold=threshold
        )
        
        if not result.matched_categories:
            console.print("[yellow]No categories matched above the threshold.[/yellow]\n")
            return
        
        console.print(f"[bold green]✓[/bold green] Classification complete\n")
        
        # Display message info
        console.print(Panel.fit(
            f"[bold]Subject:[/bold] {result.message.subject}\n"
            f"[bold]From:[/bold] {result.message.sender}",
            title=f"Message {result.message.id}",
            border_style="cyan"
        ))
        console.print()
        
        # Display matched categories
        table = Table(show_header=True, header_style="bold magenta", title="Matched Categories")
        table.add_column("ID", style="cyan", justify="right")
        table.add_column("Name", style="green")
        table.add_column("Score", style="yellow", justify="right")
        table.add_column("Description", style="white", no_wrap=False)
        
        for cat, score in zip(result.matched_categories, result.scores):
            table.add_row(
                str(cat.id),
                cat.name,
                f"{score:.4f}",
                cat.description[:60] + "..." if len(cat.description) > 60 else cat.description
            )
        
        console.print(table)
        
        if assign:
            console.print("\n[bold green]✓[/bold green] Categories assigned to message")
        
        console.print()
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)
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

