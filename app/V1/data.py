from instaloader import Instaloader
from instaloader import Profile
from instaloader import exceptions
import asyncio
from termcolor import cprint
from datetime import datetime, timedelta
from itertools import takewhile, dropwhile
import time
from instagrapi import Client

def WoM(in_str):
    cprint(in_str, "white", 'on_magenta', attrs=["bold"])

def WoR(in_str):
    cprint(in_str, "white", 'on_red', attrs=["bold"])
    

async def get_data(username):
    l = Instaloader(sleep=True)
    try:
        profile = Profile.from_username(l.context, username)
        
        data = {}
        data['Full_name'] = ""
        data['Followers'] = 0
        data['Following'] = 0
        data['posts'] = 0
        data['bio'] = None
        data['url_in_bio'] = ""
        data['profile_hashtags'] = []
        data['profile_mentions'] = []
        data['profile_picture_url'] = ""

        data['Full_name'] = str(profile.full_name)
        data['Followers'] = int(profile.followers)
        data['Following'] = int(profile.followees)
        data['posts'] = int(profile.mediacount)
        data['bio'] = str(profile.biography)
        data['url_in_bio'] = str(profile.external_url)
        data['profile_hashtags'] = list(profile.biography_hashtags)
        data['profile_mentions'] = list(profile.biography_mentions)
        data['profile_picture_url'] = str(profile.profile_pic_url)

    except Exception as e:
        WoM({"error type: ": type(e), "error message: ": str(e)})
        return {"error message: ": str(e)}
    
    l.close()
    return data

async def get_data_wl(username: str, cl: Client):
    try:
        usrid = cl.user_id_from_username(username)
        usr_info = cl.user_info(f"{usrid}")

    except Exception as e:
        WoM({"error type: ": type(e), "error message: ": str(e)})
        return {"Error in getting info": e}

    try: 
        data = {}
        data['Full_name'] = usr_info.full_name
        data['Followers'] = usr_info.follower_count
        data['Following'] = usr_info.following_count
        data['posts'] = usr_info.media_count
        data['bio'] = usr_info.biography
        data['url_in_bio'] = usr_info.external_url
        data['is_verified'] = usr_info.is_verified
        data['phone_number'] = usr_info.public_phone_number
        data['profile_picture_url_hd'] = str(usr_info.profile_pic_url_hd)
        data['profile_picture_url'] = str(usr_info.profile_pic_url)
        
    except Exception as e:
        data = {"message": "error"}
    
    return data

async def get_posts(username: str, 
                    st_year: int,
                    st_month: int,
                    st_day: int,
                    end_year: int,
                    end_month: int,
                    end_day: int,
                    loader: Instaloader = Instaloader(sleep=True)
                    ):
    
    global posts
    l = loader
    try:
        profile = Profile.from_username(l.context, username)
        posts = profile.get_posts()

    except Exception as e:
        WoM({"error type: ": type(e), "error message: ": str(e)})

    data = {}
    data['posts'] = []

    en = datetime(end_year, end_month, end_day)
    st = datetime(st_year, st_month, st_day)

    try:
        for post in takewhile(lambda p: p.date > st, dropwhile(lambda p: p.date > en, posts)):
            if post.is_video:
                data['posts'].append({
                                    'post_date': post.date.strftime("%Y-%m-%d"),
                                    'is_video': post.is_video,
                                    'post_slides': post.mediacount,
                                    'post_number_of_likes': post.likes,
                                    'comments': post.comments,
                                    "caption": post.pcaption,
                                    "caption_hashtags": post.caption_hashtags,
                                    'post_url': post.video_url,
                                    })
                
            if post.typename == "GraphImage":
                data['posts'].append({
                                    'post_date': post.date.strftime("%Y-%m-%d"),
                                    'is_video': post.is_video,
                                    'post_slides': post.mediacount,
                                    'post_number_of_likes': post.likes,
                                    'comments': post.comments,
                                    "caption": post.pcaption,
                                    "caption_hashtags": post.caption_hashtags,
                                    'post_url': post.url,
                                    })
                
            s_nodes = []
            if post.typename == "GraphSidecar":
                for n in post.get_sidecar_nodes():
                    s_nodes.append(n.display_url)

                data['posts'].append({
                                    'post_date': post.date.strftime("%Y-%m-%d"),
                                    'is_video': post.is_video,
                                    'post_slides': post.mediacount,
                                    'post_number_of_likes': post.likes,
                                    'comments': post.comments,
                                    "caption": post.pcaption,
                                    "caption_hashtags": post.caption_hashtags,
                                    'post_url': s_nodes,
                                    })

    except exceptions.ConnectionException as ex:
        data = {"something happend": "connection is refused"}

    l.close()

    return data
    
async def get_post_wl(username: str, 
                    number_of_posts: int,
                    cl: Client
                    ):
    try:
        usrid = cl.user_id_from_username(username)
        posts = cl.user_medias(f"{usrid}", amount=number_of_posts, sleep=2)

    except Exception as e:
        WoM({"error type: ": type(e), "error message: ": str(e)})
        return {"Error in getting posts": e}

    data = {}
    data['posts'] = []
    number_of_all_posts = cl.user_info_by_username(username).media_count

    try:
        for post in posts:
                data['posts'].append({
                                    'number_of_all_posts': number_of_all_posts,
                                    'post_date': post.taken_at.strftime("%Y-%m-%d"),
                                    'post_number_of_likes': post.like_count,
                                    'comments': post.comment_count,
                                    "caption": post.caption_text,
                                    'post_video_url': post.video_url,
                                    'post_thumbnail_url': post.thumbnail_url,
                                    })
    except Exception as e:           
        WoM({"error type: ": type(e), "error message: ": str(e)})
        return {"Error in getting posts": e}

    return data

async def get_stories(cl: Client, username, number_of_stories: int = 3):
    try:
        usrid = cl.user_id_from_username(username)
        stories = cl.user_stories(user_id=usrid, amount=number_of_stories)

    except Exception as e:
        WoM({"error type: ": type(e), "error message: ": str(e)})
        return {"Error in getting stories": e}
    
    stories_video_url = []
    stories_pic_url = []
    
    for story in stories:
        stories_video_url.append(story.video_url)
        stories_pic_url.append(story.thumbnail_url)
    
    return {"stories_video_url": stories_video_url, "stories_pic_url": stories_pic_url}

async def get_highlights(cl: Client, username):
    try:
        usrid = cl.user_id_from_username(username)
        highlights = cl.user_highlights(f"{usrid}")

    except Exception as e:
        WoM({"error type: ": type(e), "error message: ": str(e)})
        return {"Error in getting highlights": e}
    
    h_info = {}
    for highlight in highlights:
        h_info[highlight.title] = {
            "created_at": highlight.created_at,
            "is_pinned": highlight.is_pinned_highlight,
            "number_of_stories_in_highlight": highlight.media_count,
            "highlight_url": rf"https://www.instagram.com/stories/highlights/{highlight.pk}/",
            "cover_pic_url": highlight.cover_media['cropped_image_version']['url'],
        }

    return h_info

async def main():
    loader = Instaloader()
    loader.load_session_from_file("inside.black.room", "session-inside.black.room")

if __name__ == "__main__":
    asyncio.run(main())
