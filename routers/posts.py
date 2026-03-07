# Imports:
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from schema import PostResponse, PostCreate, PostUpdate
from utils import check_exists
from database import get_db 
import models


# Setup:
router = APIRouter()


# Posts Routes:
@router.get('', response_model=list[PostResponse])
async def get_posts(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.Post).options(selectinload(models.Post.author)))
    posts = result.scalars().all()
    return posts


@router.get('/{post_id}', response_model=PostResponse)
async def get_post(post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    post: models.Post = await check_exists(db, models.Post, models.Post.id, post_id, return_obj=True, load_immediately=models.Post.author)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Post not found!')
    return post


@router.post('', response_model=PostResponse, status_code=status.HTTP_201_CREATED)
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


@router.put('/{post_id}', response_model=PostResponse)
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


@router.patch('/{post_id}', response_model=PostResponse)
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


@router.delete('/{post_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    post: models.Post = await check_exists(db, models.Post, models.Post.id, post_id, return_obj=True)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Post not found!')
    
    await db.delete(post)
    await db.commit()
