# Imports:
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi import FastAPI, Request, Depends, status
from fastapi.staticfiles import StaticFiles

from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from schema import PostCreate, PostUpdate, PostResponse, UserCreate, UserResponse, UserUpdate
from database import Base, engine, get_db 
import models


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


# Helper Funcs:
async def check_exists(db: AsyncSession, model_obj: Any, val1: Any, val2: Any, return_obj=False, load_immediately=None):
    if load_immediately:
        result = await db.execute(select(model_obj).options(selectinload(load_immediately)).where(val1 == val2))
    result = await db.execute(select(model_obj).where(val1 == val2))
    if return_obj:
        return result.scalars().first()
    return bool(result.scalars().first())


# Routes:
@app.get('/')
def root():
    return {'msg': 'Hello World!'}


@app.get('/api/users/{user_id}', response_model=UserResponse)
async def get_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    user: models.User = await check_exists(db, models.User, models.User.id, user_id, return_obj=True, load_immediately=models.User.posts)
    if user:
        return user
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found!')


@app.post('/api/users', response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    existing_username = await check_exists(db, models.User, models.User.username, user.username)
    if existing_username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Username already exists!')
    
    existing_email = await check_exists(db, models.User, models.User.email, user.email)
    if existing_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='User email already exists!')
    
    new_user = models.User(
        username = user.username,
        email = user.email
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@app.patch('/api/users/{user_id}', response_model=UserResponse)
async def update_user(user_id: int, user_data: UserUpdate, db: Annotated[AsyncSession, Depends(get_db)]):
    user: models.User = await check_exists(db, models.User, models.User.id, user_id, return_obj=True, load_immediately=models.User.posts)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found!')

    if (user_data.username is not None) and (user_data.username != user.username):
        existing_username = await check_exists(db, models.User, models.User.username, user_data.username)
        if existing_username:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Username already exists!')
    
    if (user_data.email is not None) and (user_data.email != user.email):
        existing_email = await check_exists(db, models.User, models.User.email, user_data.email)
        if existing_email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='User email already exists!')
    
    updated_data = user_data.model_dump(exclude_unset=True)
    for field, value in updated_data.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    return user


@app.delete('/api/users/{user_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    user: models.User = await check_exists(db, models.User, models.User.id, user_id, return_obj=True)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found!')

    await db.delete(user)
    await db.commit()


@app.get('/api/users/{user_id}/posts', response_model=list[PostResponse])
async def get_user_posts(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    user = await check_exists(db, models.User, models.User.id, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found!')
    
    result = await db.execute(select(models.Post).options(selectinload(models.Post.author)).where(models.Post.user_id == user_id))
    posts = result.scalars().all()
    return posts


@app.get('/api/posts', response_model=list[PostResponse])
async def get_posts(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.Post).options(selectinload(models.Post.author)))
    posts = result.scalars().all()
    return posts


@app.get('/api/posts/{post_id}', response_model=PostResponse)
async def get_post(post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    post: models.Post = await check_exists(db, models.Post, models.Post.id, post_id, return_obj=True, load_immediately=models.Post.author)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Post not found!')
    return post


@app.post('/api/posts', response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(post: PostCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    user = await check_exists(db, models.User, models.User.id, post.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found!')
    
    new_post = models.Post(
        title = post.title,
        content = post.content,
        user_id = post.user_id
    )
    db.add(new_post)
    await db.commit()
    await db.refresh(new_post, attribute_names=['author'])
    return new_post


@app.put('/api/posts/{post_id}', response_model=PostResponse)
async def update_post_full(post_id: int, post_data: PostCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    post: models.Post = await check_exists(db, models.Post, models.Post.id, post_id, return_obj=True, load_immediately=models.Post.author)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Post not found!')
    
    if post_data.user_id != post.user_id:
        user = await check_exists(db, models.User, models.User.id, post_data.user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found!')

    post.title = post_data.title
    post.content = post_data.content
    post.user_id = post_data.user_id

    await db.commit()
    await db.refresh(post, attribute_names=['author'])
    return post


@app.patch('/api/posts/{post_id}', response_model=PostResponse)
async def update_post_partial(post_id: int, post_data: PostUpdate, db: Annotated[AsyncSession, Depends(get_db)]):
    post: models.Post = await check_exists(db, models.Post, models.Post.id, post_id, return_obj=True, load_immediately=models.Post.author)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Post not found!')
    
    updated_data = post_data.model_dump(exclude_unset=True)
    for field, value in updated_data.items():
        setattr(post, field, value)

    await db.commit()
    await db.refresh(post, attribute_names=['author'])
    return post


@app.delete('/api/posts/{post_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    post: models.Post = await check_exists(db, models.Post, models.Post.id, post_id, return_obj=True)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Post not found!')
    
    await db.delete(post)
    await db.commit()


# Handlers:
@app.exception_handler(StarletteHTTPException)
async def general_http_exception_handler(request: Request, exception: StarletteHTTPException):
    return await http_exception_handler(request, exception)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exception: RequestValidationError):
    return await request_validation_exception_handler(request, exception)

