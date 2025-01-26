from fastapi import FastAPI
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
from data import get_data, get_data_wl, get_posts, get_stories, get_post_wl, get_highlights
from pydantic import BaseModel
from enum import Enum
from typing import Annotated
from instaloader import Instaloader
from instagrapi import Client
import json
from glob import glob

app = FastAPI(title="Instagram API",
              description="gathering instagram data, if connection at /posts is refused try the /posts/wl endpoint", )


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


api_key_header = APIKeyHeader(name="SET-API-KEYS", scheme_name="SET-API-KEYS")
api_key_users_header = APIKeyHeader(name="USER-API-KEY", scheme_name="USER-API-KEY")

root_api_key = "10987654321"


def set_api_keys_root(api_key: str = Security(api_key_header)):
    if api_key == root_api_key:
        return api_key
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid, Missing API-KEY"
    )


def get_api_keys_users(api_key: str = Security(api_key_users_header)):
    users_api_keys = get_json_data()
    if api_key in users_api_keys["users"]:
        return api_key

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid, Missing API-KEY"
    )


@app.post("/set_api_keys")
async def protected_root(
        users_api_keys: Annotated[list, Body(title="List of all users api_keys")],
        api_key: str = Security(set_api_keys_root)
):
    save_json_data(users_api_keys)
    return {"All Done": "API-Keys are saved"}


@app.get("/get_users_api_keys")
async def get_users_api_keys(
        api_key: str = Security(set_api_keys_root)
):
    users_api_keys = get_json_data()
    return {"API-KEYS": users_api_keys["users"]}


@app.put("/set_user_pass")
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


@app.get("/show_user_pass")
async def get_user_pass(
        api_key: str = Security(set_api_keys_root)
):
    return await load_user_pass()


@app.get("/{profile_id}")
async def get_profile(
        profile_id: str,
        api_key: Annotated[str, Security(get_api_keys_users)]
):
    return Profile(**await get_data(profile_id))


@app.get("/{profile_id}/wl")
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


@app.post("/{profile_id}/posts/{start}/{end}")
async def get_profile_posts(profile_id: str,
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


@app.post("/{profile_id}/posts/wl/")
async def get_profile_posts_wl(
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
        else:
            print("login success")
            return await get_post_wl(profile_id, number_of_posts, client)


@app.post("/{profile_id}/posts/ws/{start}/{end}")
async def get_profile_posts_ws(
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


@app.post("/{profile_id}/highlights")
async def highlights(
        profile_id: Annotated[str, Path(title="profile username", example="instagram", min_length=3, max_length=20)],
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
            highlight_data = await get_highlights(client, profile_id)
            client.logout()
            return highlight_data


@app.post("/{profile_id}/stories")
async def get_profile_stories(
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
            print("login failed")
        else:
            stories = await get_stories(client, profile_id, number_of_stories)
            client.logout()
            return stories
