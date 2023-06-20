from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import schemas
from app.chain.user import UserChain
from app.core import security
from app.core.config import settings
from app.db import get_db
from app.db.models.user import User
from app.log import logger

router = APIRouter()


@router.post("/login/access-token", summary="获取token", response_model=schemas.Token)
async def login_access_token(
        db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    获取认证Token
    """
    # 检查数据库
    user = User.authenticate(
        db=db,
        name=form_data.username,
        password=form_data.password
    )
    if not user:
        # 请求协助认证
        logger.warn("登录用户本地不匹配，尝试辅助认证 ...")
        token = UserChain().user_authenticate(form_data.username, form_data.password)
        if not token:
            raise HTTPException(status_code=400, detail="用户名或密码不正确")
        else:
            logger.info(f"辅助认证成功，用户信息: {token}")
            user = schemas.User(id=-1, name=form_data.username, is_active=True, is_superuser=False)
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="用户未启用")
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return schemas.Token(
        access_token=security.create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        token_type="bearer",
    )
