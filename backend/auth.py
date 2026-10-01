import os
import jwt                      # JWTを読む・確かめる道具
from jwt import PyJWKClient     # Cognitoの公開鍵を取ってくる道具
from dotenv import load_dotenv
from fastapi import Header, HTTPException

load_dotenv()  # .env を読む（main.py より先にこのファイルが読まれても困らないように）

REGION = os.environ["COGNITO_REGION"]
USER_POOL_ID = os.environ["COGNITO_USER_POOL_ID"]
CLIENT_ID = os.environ["COGNITO_APP_CLIENT_ID"]

# 発行元（iss）：本物のCognitoなら必ずこの住所が書いてある
ISSUER = f"https://cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}"
# 公開鍵の置き場所：Cognitoが世界に公開している
jwks_client = PyJWKClient(f"{ISSUER}/.well-known/jwks.json")

##== 実際に検査ををて、公開鍵か、方式はRS256か、署名は本物か、期限内か、発行元はMingoのプールか、などを審査し、合格ならclaims(ユーザーIDなど)を返答します。 ==##
def verify_token(token: str) -> dict:
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=ISSUER,
            options={"require": ["exp", "iss", "token_use"]},
        )
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="invalid token")

    if claims.get("token_use") != "access" or claims.get("client_id") != CLIENT_ID:
        raise HTTPException(status_code=401, detail="invalid token")
    return claims

##== "Bearer" と JWT に分ける ==##
def get_current_user(authorization: str = Header(default="")) -> dict:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="missing token")
    return verify_token(token)