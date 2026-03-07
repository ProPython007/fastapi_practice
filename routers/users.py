# Imports:
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from schema import PostResponse, UserCreate, UserResponse, UserUpdate
from utils import check_exists
from database import get_db 
import models


# Setup:
router = APIRouter()


# Users Routes:
@router.get('/{user_id}', response_model=UserResponse)
async def get_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    user: models.User = await check_exists(db, models.User, models.User.id, user_id, return_obj=True, load_immediately=models.User.posts)
    if user:
        return user
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found!')


@router.post('', response_model=UserResponse, status_code=status.HTTP_201_CREATED)
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


@router.patch('/{user_id}', response_model=UserResponse)
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


@router.delete('/{user_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    user: models.User = await check_exists(db, models.User, models.User.id, user_id, return_obj=True)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found!')

    await db.delete(user)
    await db.commit()


@router.get('/{user_id}/posts', response_model=list[PostResponse])
async def get_user_posts(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    user = await check_exists(db, models.User, models.User.id, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found!')
    
    result = await db.execute(select(models.Post).options(selectinload(models.Post.author)).where(models.Post.user_id == user_id).order_by(models.Post.date_posted.desc()))
    posts = result.scalars().all()
    return posts
