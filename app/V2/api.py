from fastapi import FastAPI, Request
from fastapi import File, UploadFile
from fastapi import Path
from fastapi import Query
from fastapi import Body
from fastapi import Form
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends
from fastapi import HTTPException, status
from fastapi import Security
from fastapi.security import APIKeyHeader, APIKeyQuery
from starlette.middleware.trustedhost import TrustedHostMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors  import RateLimitExceeded
from data import get_data, get_posts, get_stories, get_post_wl, get_highlights, get_data_wl, get_posts_in_date_wl, get_stories_in_date
from pydantic import BaseModel
from enum import Enum
from typing import Annotated
from instaloader import Instaloader
from instagrapi import Client
import json
from glob import glob
from log import log
from datetime import datetime, timezone

logger = log("ins_log", "ins_log.log", "%(asctime)s - %(name)s - %(levelname)s - %(message)s", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

def custom_key_func_ad(request: Request):
    set_api_keys = request.headers.get("SET-API-KEYS")
    users_api_keys = request.headers.get("USERS-API-KEYS")
    if set_api_keys:
        return set_api_keys
    return users_api_keys


limiter = Limiter(key_func=custom_key_func_ad)

tags_metadata = [
    {
        'name': "Setting",
        'description': 'Config api keys and instagram Login'
    },
    {
        'name': 'Profile Data',
        'description': 'Instagram Users Profile Data'
    },
    {
        'name': 'Profile Posts',
        'description': 'Instagram Users Profile Posts'
    },
    {
        'name': 'Live action',
        'description': 'Profile stories and highlights'
    }
]

app = FastAPI(title="Instagram API", openapi_tags=tags_metadata,
              description="gathering instagram data, if connection at /posts is refused try the /posts/wl endpoint",)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])


class Profile(BaseModel):
    Full_name: str = ""
    Followers: int = 0
    Following: int = 0
    posts: int = 0
    bio: str = ""
    url_in_bio: str = ""
    profile_hashtags: list[str] = []
    profile_mentions: list[str] = []
    profile_picture_url: str = ""

class User_Login(BaseModel):
    username: str
    password: str 

def save_json_data(data):
    with open("users_api_keys.json", "w") as f:
        f.write(json.dumps({"users": data}))

def get_json_data():
    if glob("users_api_keys.json"):
        with open("users_api_keys.json", "r") as f:
            users_api_keys = json.loads(f.read())
        return users_api_keys
    return {"users": "Empty"}


api_key_header = APIKeyHeader(name="SET-API-KEYS", scheme_name="SET-API-KEY")
api_key_users_header = APIKeyHeader(name="USERS-API-KEYS", scheme_name="USER-API-KEY")

root_api_key = "10987654321"

def set_api_keys_root(api_key: str = Security(api_key_header)):
    if api_key == root_api_key:
        return api_key
    logger.error("Invalid, Missing API-KEY for {0}".format(api_key))
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid, Missing API-KEY"
    )

def get_api_keys_users(api_key: str = Security(api_key_users_header)):
    users_api_keys = get_json_data()
    if api_key in users_api_keys["users"]:
        return api_key
    
    logger.error(f"Invalid, Missing API-KEY for {api_key}")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid, Missing API-KEY"
    )
    

@app.post("/set_api_keys", tags=['Setting'])
async def protected_root(
    users_api_keys: Annotated[list, Body(title="List of all users api_keys")],
    api_key: str = Security(set_api_keys_root)
    ):
    save_json_data(users_api_keys)
    return {"All Done": "API-Keys are saved"}


@app.get("/get_users_api_keys", tags=['Setting'])
async def get_users_api_keys(
    api_key: str = Security(set_api_keys_root)
    ):
    users_api_keys = get_json_data()
    return {"API-KEYS": users_api_keys["users"]}


@app.put("/set_user_pass", tags=['Setting'])
async def set_user_pass(
    login_info: Annotated[dict, Body(example={"username1": "password1", "username2": "password2"})], 
    api_key: str = Security(set_api_keys_root)
    ):
    with open("users_pass.json", "w") as f:
        f.write(json.dumps(login_info))
    return {"All Done": "Users and passwords are saved"}

async def load_user_pass() -> dict:
    with open("users_pass.json", "r") as f:
        users_pass = json.loads(f.read())
    return users_pass

@app.get("/show_user_pass", tags=['Setting'])
@limiter.limit("2/minute")
async def get_user_pass(
    request: Request,
    api_key: str = Security(set_api_keys_root)
    ):
    return await load_user_pass()
            
@app.get("/{profile_id}", tags=['Profile Data'])
@limiter.limit("2/minute")
async def get_profile(
    request: Request,
    profile_id: str,
    api_key: Annotated[str, Security(get_api_keys_users)]
    ):
    return Profile(**await get_data(profile_id))

@app.get("/{profile_id}/wl", tags=['Profile Data'])
async def get_profile_wl(
        profile_id: str,
        api_key: Annotated[str, Security(get_api_keys_users)]
):
    user_pass = await load_user_pass()
    client = Client()
    for user, passwd in user_pass.items():
        print(f"login with {user}")
        r = await login(user, passwd, client)
        if r == 0:
            print("login failed")
        else:
            print("login success")
            info = await get_data_wl(profile_id, client)
            client.logout()
            return info
        
@app.post("/{profile_id}/posts/{start}/{end}", tags=['Profile Posts'])
@limiter.limit("2/minute")
async def get_profile_posts(
                            request: Request,
                            profile_id: str, 
                            start: str, 
                            end: str,
                            api_key: Annotated[str, Security(get_api_keys_users)],
                            ):
    
    start_num = start.split("-")
    end_num = end.split("-")
    return await get_posts(profile_id, 
                           int(start_num[0]), 
                           int(start_num[1]), 
                           int(start_num[2]), 
                           int(end_num[0]), 
                           int(end_num[1]), 
                           int(end_num[2])
                           )

async def login(user, passwd, cl: Client):
    try:  
        cl.login(user, passwd)
        print("login and data gathering is completed")
    except Exception as e:
        print(e)
        return 0
        
@app.post("/{profile_id}/posts/wl/", tags=['Profile Posts'])
@limiter.limit("2/minute")
async def get_profile_posts_wl(
    request: Request,
    profile_id: str,
    number_of_posts: int,
    api_key: Annotated[str, Security(get_api_keys_users)],
    ):

    user_pass = await load_user_pass()
    client = Client()
    for user, passwd in user_pass.items():
        print(f"login with {user}")
        r = await login(user, passwd, client)
        if r == 0:
            print("login failed")
            logger.warning(f"login failed for {user}")
        else:
            logger.info(f"login with {user}")
            print("login success")
            return await get_post_wl(profile_id, number_of_posts, client)

@app.post("/{profile_id}/posts/indate/wl/{start}/{end}", tags=['Profile Posts'])
@limiter.limit("2/minute")
async def get_profile_posts_in_date_wl(
    request: Request,
    profile_id: str,
    limit: int,
    start: str, 
    end: str,
    api_key: Annotated[str, Security(get_api_keys_users)],
    ):

    start_number = start.split("-")
    end_number = end.split("-")

    start_date = datetime(int(start_number[0]), int(start_number[1]), int(start_number[2]), tzinfo=timezone.utc)
    end_date = datetime(int(end_number[0]), int(end_number[1]), int(end_number[2]), tzinfo=timezone.utc)

    user_pass = await load_user_pass()
    client = Client()
    for user, passwd in user_pass.items():
        print(f"login with {user}")
        r = await login(user, passwd, client)
        if r == 0:
            print("login failed")
            logger.warning(f"login failed for {user}")
        else:
            logger.info(f"login with {user}")
            print("login success")
            return await get_posts_in_date_wl(
            username=profile_id,
            limit=limit,
            start=start_date,
            end=end_date,
            cl=client
        )

@app.post("/{profile_id}/posts/ws/{start}/{end}", tags=['Profile Posts'])
@limiter.limit("2/minute")
async def get_profile_posts_ws(
    request: Request,
    profile_id: str,
    start: str, 
    end: str,
    api_key: Annotated[str, Security(get_api_keys_users)],
    username: str,
    file: Annotated[bytes, File(title="session file", description="session file to use for login")],
    ):
    
    with open("sessionfile", "wb") as f:
        f.write(file)

    try:
        loader = Instaloader()
        loader.load_session_from_file(username, "sessionfile")
    except Exception as e:
        logger.error(f"Error in loading session file: {e}")
        return {"Something went wrong in loading session file": str(e)}
    
    start_num = start.split("-")
    end_num = end.split("-")
    return await get_posts(profile_id, 
                           int(start_num[0]), 
                           int(start_num[1]), 
                           int(start_num[2]), 
                           int(end_num[0]), 
                           int(end_num[1]), 
                           int(end_num[2]),
                           loader
                           )

@app.post("/{profile_id}/highlights", tags=['Live action'])
@limiter.limit("2/minute")
async def highlights(
    request: Request,
    profile_id: Annotated[str, Path(title="profile username", example="instagram", min_length=3, max_length=20)],
    api_key: Annotated[str, Security(get_api_keys_users)]
    ):

    user_pass = await load_user_pass()
    client = Client()
    for user, passwd in user_pass.items():
        print(f"login with {user}")
        r = await login(user, passwd, client)
        if r == 0:
            logger.warning(f"login failed for {user}")
            print("login failed")
        else:
            logger.info(f"login with {user}")
            highlight_data = await get_highlights(client, profile_id)
            client.logout()
            return highlight_data

@app.post("/{profile_id}/stories", tags=['Live action'])
@limiter.limit("2/minute")
async def get_profile_stories(
    request: Request,
    profile_id: Annotated[str, Path(title="profile username", example="instagram", min_length=3, max_length=20)],
    number_of_stories: Annotated[int, Query(title="number of stories to get", gt=0, lt=10)],
    api_key: Annotated[str, Security(get_api_keys_users)]
    ):

    user_pass = await load_user_pass()
    client = Client()
    for user, passwd in user_pass.items():
        print(f"login with {user}")
        r = await login(user, passwd, client)
        if r == 0:
            logger.warning(f"login failed for {user}")
            print("login failed")
        else:
            logger.info(f"login with {user}")
            stories = await get_stories(client, profile_id, number_of_stories)
            client.logout()
            return stories

@app.post("/{profile_id}/stories/in_date", tags=['Live action'])
@limiter.limit("2/minute")
async def gete_profile_stories_in_date(
    request: Request,
    profile_id: Annotated[str, Path(title="profile username", example="instagram", min_length=3, max_length=20)],
    hour: Annotated[int, Query(title="Hour Ago", description='last hour ago')],
    api_key: Annotated[str, Security(get_api_keys_users)]
    ):
    user_pass = await load_user_pass()
    client = Client()
    for user, passwd in user_pass.items():
        print(f"login with {user}")
        r = await login(user, passwd, client)
        if r == 0:
            logger.warning(f"login failed for {user}")
            print("login failed")
        else:
            logger.info(f"login with {user}")
            stories = await get_stories_in_date(client, profile_id, hour)
            client.logout()
            return stories