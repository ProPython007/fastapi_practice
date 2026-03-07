# Imports:
from contextlib import asynccontextmanager

from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, Request

from starlette.exceptions import HTTPException as StarletteHTTPException

from database import Base, engine 
from routers import users, posts


# Setup:
@asynccontextmanager
async def lifespan(_app: FastAPI):
    # startup:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield

    # shutdown:
    await engine.dispose()


app = FastAPI()

app.mount('/static', StaticFiles(directory='static'), name='static')
app.mount('/media', StaticFiles(directory='media'), name='media')

app.include_router(users.router, prefix='/api/users', tags=['users'])
app.include_router(posts.router, prefix='/api/posts', tags=['posts'])

# Routes:
@app.get('/')
def root():
    return {'msg': 'Hello World!'}


# Handlers:
@app.exception_handler(StarletteHTTPException)
async def general_http_exception_handler(request: Request, exception: StarletteHTTPException):
    return await http_exception_handler(request, exception)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exception: RequestValidationError):
    return await request_validation_exception_handler(request, exception)

