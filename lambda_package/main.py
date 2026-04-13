import boto3
import random
from decimal import Decimal
from typing import Literal, Optional
from uuid import uuid4
from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from mangum import Mangum


# DynamoDB setup
dynamodb = boto3.resource("dynamodb", region_name="us-east-2")
table = dynamodb.Table("books")


class Book(BaseModel):
    name: str
    genre: Literal["fiction", "non-fiction"]
    price: float
    book_id: Optional[str] = None


app = FastAPI(root_path="/default")
handler = Mangum(app, api_gateway_base_path="/default")


@app.get("/")
async def root():
    return {"message": "Welcome to my bookstore app!"}


@app.get("/random-book")
async def random_book():
    response = table.scan()
    books = response.get("Items", [])
    if not books:
        raise HTTPException(404, "No books available.")
    book = random.choice(books)
    book["price"] = float(book["price"])
    return book


@app.get("/list-books")
async def list_books():
    response = table.scan()
    books = response.get("Items", [])
    for book in books:
        book["price"] = float(book["price"])
    return {"books": books}


@app.get("/book_by_index/{index}")
async def book_by_index(index: int):
    response = table.scan()
    books = response.get("Items", [])
    if index < len(books):
        books[index]["price"] = float(books[index]["price"])
        return books[index]
    else:
        raise HTTPException(404, f"Book index {index} out of range ({len(books)}).")


@app.post("/add-book")
async def add_book(book: Book):
    book.book_id = uuid4().hex
    table.put_item(Item={
        "book_id": book.book_id,
        "name": book.name,
        "genre": book.genre,
        "price": Decimal(str(book.price)),
    })
    return {"book_id": book.book_id}


@app.get("/get-book")
async def get_book(book_id: str):
    response = table.get_item(Key={"book_id": book_id})
    book = response.get("Item")
    if book:
        book["price"] = float(book["price"])
        return book
    raise HTTPException(404, f"Book ID {book_id} not found in database.")
