"""
FastAPI application entry point.
"""

from fastapi import FastAPI

from app.controllers.bootstrap_controller import BootstrapController
from app.controllers.categories_controller import CategoriesController
from app.controllers.messages_controller import MessagesController

# Create FastAPI app
app = FastAPI(
    title="Extra Forever API",
    description="Gmail-style message classification system",
    version="0.1.0",
)

# Initialize controllers
messages_controller = MessagesController()
categories_controller = CategoriesController()
bootstrap_controller = BootstrapController()

# Register controller routers
app.include_router(bootstrap_controller.router)
app.include_router(messages_controller.router)
app.include_router(categories_controller.router)


@app.get("/")
def read_root():
    """Health check endpoint."""
    return {"status": "ok", "app": "extra-forever", "version": "0.1.0"}


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
