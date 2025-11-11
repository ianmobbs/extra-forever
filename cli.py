import json
import base64
from datetime import datetime
from pathlib import Path
import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Message

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
    
    # Create SQLite database
    engine = create_engine(SQLITE_DB_PATH, echo=False)
    
    if drop_existing:
        console.print("[yellow]Dropping existing tables...[/yellow]")
        Base.metadata.drop_all(engine)
    
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    messages = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Reading messages...", total=None)
        
        try:
            with open(filename, 'r') as f:
                for line in f:
                    data = json.loads(line)
                    body_decoded = base64.b64decode(data['body']).decode('utf-8')
                    date_obj = datetime.fromisoformat(data['date'].replace('Z', '+00:00'))
                    
                    message = Message(
                        id=data['id'],
                        subject=data['subject'],
                        sender=data['from'],
                        to=data['to'], 
                        snippet=data['snippet'],
                        body=body_decoded,
                        date=date_obj
                    )
                    messages.append(message)
        except Exception as e:
            console.print(f"[bold red]Error reading file:[/bold red] {e}")
            raise typer.Exit(code=1)
        
        progress.update(task, description=f"Loaded {len(messages)} messages")
    
    # Add all messages to database
    with console.status("[bold green]Saving to database..."):
        try:
            session.add_all(messages)
            session.commit()
        except Exception as e:
            console.print(f"[bold red]Error saving to database:[/bold red] {e}")
            session.rollback()
            raise typer.Exit(code=1)
    
    console.print(f"\n[bold green]✓[/bold green] Successfully imported {len(messages)} messages\n")
    
    # Query and display first 5 messages
    first_five = session.query(Message).limit(5).all()
    
    console.print(Panel.fit(
        "[bold]Preview: First 5 messages[/bold]",
        border_style="cyan"
    ))
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Subject", style="cyan", no_wrap=False)
    table.add_column("From", style="green")
    table.add_column("Date", style="yellow")
    table.add_column("Snippet", style="white", no_wrap=False, max_width=40)
    
    for msg in first_five:
        table.add_row(
            msg.subject[:50] + "..." if len(msg.subject) > 50 else msg.subject,
            msg.sender,
            msg.date.strftime("%Y-%m-%d %H:%M") if msg.date else "N/A",
            msg.snippet[:40] + "..." if msg.snippet and len(msg.snippet) > 40 else msg.snippet or ""
        )
    
    console.print(table)
    console.print()
    
    session.close()


if __name__ == "__main__":
    app()

