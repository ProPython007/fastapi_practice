# Imports:
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi import FastAPI, Request, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import select

from typing import Annotated, Any

from schema import PostCreate, PostUpdate, PostResponse, UserCreate, UserResponse, UserUpdate
from database import Base, engine, get_db 
import models


# Setup:
Base.metadata.create_all(bind=engine)

app = FastAPI()

app.mount('/static', StaticFiles(directory='static'), name='static')
app.mount('/media', StaticFiles(directory='media'), name='media')


# Helper Funcs:
def check_exists(db: Session, model_obj: Any, val1: Any, val2: Any, return_obj=False):
    result = db.execute(select(model_obj).where(val1 == val2))
    if return_obj:
        return result.scalars().first()
    return bool(result.scalars().first())


# Routes:
@app.get('/')
def root():
    return {'msg': 'Hello World!'}


@app.get('/api/users/{user_id}', response_model=UserResponse)
def get_user(user_id: int, db: Annotated[Session, Depends(get_db)]):
    user: models.User = check_exists(db, models.User, models.User.id, user_id, return_obj=True)
    if user:
        return user
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found!')


@app.patch('/api/users/{user_id}', response_model=UserResponse)
def update_user(user_id: int, user_data: UserUpdate, db: Annotated[Session, Depends(get_db)]):
    user: models.User = check_exists(db, models.User, models.User.id, user_id, return_obj=True)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found!')

    if (user_data.username is not None) and (user_data.username != user.username):
        existing_username = check_exists(db, models.User, models.User.username, user_data.username)
        if existing_username:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Username already exists!')
    
    if (user_data.email is not None) and (user_data.email != user.email):
        existing_email = check_exists(db, models.User, models.User.email, user_data.email)
        if existing_email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='User email already exists!')
    
    updated_data = user_data.model_dump(exclude_unset=True)
    for field, value in updated_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


@app.delete('/api/users/{user_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Annotated[Session, Depends(get_db)]):
    user: models.User = check_exists(db, models.User, models.User.id, user_id, return_obj=True)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found!')

    db.delete(user)
    db.commit()


@app.get('/api/users/{user_id}/posts', response_model=list[PostResponse])
def get_user_posts(user_id: int, db: Annotated[Session, Depends(get_db)]):
    user = check_exists(db, models.User, models.User.id, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found!')
    
    result = db.execute(select(models.Post).where(models.Post.user_id == user_id))
    posts = result.scalars().all()
    return posts


@app.post('/api/users', response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Annotated[Session, Depends(get_db)]):
    existing_username = check_exists(db, models.User, models.User.username, user.username)
    if existing_username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Username already exists!')
    
    existing_email = check_exists(db, models.User, models.User.email, user.email)
    if existing_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='User email already exists!')
    
    new_user = models.User(
        username = user.username,
        email = user.email
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.get('/api/posts', response_model=list[PostResponse])
def get_posts(db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.Post))
    posts = result.scalars().all()
    return posts


@app.get('/api/posts/{post_id}', response_model=PostResponse)
def get_post(post_id: int, db: Annotated[Session, Depends(get_db)]):
    post: models.Post = check_exists(db, models.Post, models.Post.id, post_id, return_obj=True)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Post not found!')
    return post


@app.post('/api/posts', response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create_post(post: PostCreate, db: Annotated[Session, Depends(get_db)]):
    user = check_exists(db, models.User, models.User.id, post.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found!')
    
    new_post = models.Post(
        title = post.title,
        content = post.content,
        user_id = post.user_id
    )
    db.add(new_post)
    db.commit()
    db.refresh(new_post)

    return new_post


@app.put('/api/posts/{post_id}', response_model=PostResponse)
def update_post_full(post_id: int, post_data: PostCreate, db: Annotated[Session, Depends(get_db)]):
    post: models.Post = check_exists(db, models.Post, models.Post.id, post_id, return_obj=True)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Post not found!')
    
    if post_data.user_id != post.user_id:
        user = check_exists(db, models.User, models.User.id, post_data.user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found!')

    post.title = post_data.title
    post.content = post_data.content
    post.user_id = post_data.user_id

    db.commit()
    db.refresh(post)
    return post


@app.patch('/api/posts/{post_id}', response_model=PostResponse)
def update_post_partial(post_id: int, post_data: PostUpdate, db: Annotated[Session, Depends(get_db)]):
    post: models.Post = check_exists(db, models.Post, models.Post.id, post_id, return_obj=True)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Post not found!')
    
    updated_data = post_data.model_dump(exclude_unset=True)
    for field, value in updated_data.items():
        setattr(post, field, value)

    db.commit()
    db.refresh(post)
    return post


@app.delete('/api/posts/{post_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_post(post_id: int, db: Annotated[Session, Depends(get_db)]):
    post: models.Post = check_exists(db, models.Post, models.Post.id, post_id, return_obj=True)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Post not found!')
    
    db.delete(post)
    db.commit()


# Handlers:
@app.exception_handler(StarletteHTTPException)
def general_http_exception_handler(request: Request, exception: StarletteHTTPException):
    message = (
        exception.detail
        if exception.detail
        else 'An error occurred. Please check your request and try again.'
    )

    return JSONResponse(
        status_code=exception.status_code,
        content={'detail': message},
    )


@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exception: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={'detail': exception.errors()},
    )
