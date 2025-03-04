import streamlit as st
import pandas as pd
import httpx
import os
import tempfile
from twitter.scraper import Scraper
from twitter.util import init_session
from tweepy_authlib import CookieSessionUserHandler
from urllib.parse import quote
from typing import Dict
import random

st.set_page_config(layout="wide")

st.title("Twitter Media Scraper")


if st.button("Refresh Session"):
    st.write(st.secrets["username"])
    auth_handler = CookieSessionUserHandler(
        screen_name=st.secrets["username"],
        password=st.secrets["password"],
    )
    cookies_dict = auth_handler.get_cookies().get_dict()
    os.environ["ct0"] = cookies_dict["ct0"]
    os.environ["auth_token"] = cookies_dict["auth_token"]
    st.write("Session refreshed, refresh the tab.")

def flatten_dict(d):
    ret = {}
    for k, v in d.items():
        if isinstance(v, dict):
            for k2, v2 in flatten_dict(v).items():
                ret.setdefault(k2, []).extend(v2 if isinstance(v2, list) else [v2])
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, dict):
                    for k2, v2 in flatten_dict(item).items():
                        ret.setdefault(k2, []).extend(v2 if isinstance(v2, list) else [v2])
                else:
                    ret.setdefault(k, []).append(item)
        else:
            ret.setdefault(k, []).append(v)
    return ret

def get_media_urls(tweets):
    image_urls, video_urls = set(), set()
    for tweet in tweets:
        flattened_tweet = flatten_dict(tweet)
        if "media_url_https" in flattened_tweet:
            image_urls.update(flattened_tweet["media_url_https"])
        if "url" in flattened_tweet:
            for url in flattened_tweet["url"]:
                if any(ext in url for ext in [".mp4", ".webm"]):
                    video_urls.add(url)
    return image_urls, video_urls

usernames = st.text_input("Enter usernames (comma-separated)")
limit = st.number_input("Number of tweets to scrape", min_value=10, value=10, max_value=1000)

if st.button("Scrape Twitter Media"):
    usernames = [username.strip() for username in usernames.split(",") if username.strip()]
    try:
        scraper = Scraper(cookies={"ct0": os.environ["ct0"], "auth_token": os.environ["auth_token"]})
        users = scraper.users(usernames)
    except Exception as e:
        st.error(f"Login failed: {e}")
        st.stop()

    st.success("Login successful with cookies")

    media_urls = {"images": set(), "videos": set()}
    user_ids = []
    
    for i, user in enumerate(users):
        st.write(f"Scraping for {usernames[i]}, Description: {flatten_dict(user).get('description', [''])[0]}")
        profile_url = flatten_dict(user).get("profile_image_url_https", [""])[0]
        st.image(profile_url, caption=usernames[i])
        user_id = flatten_dict(user)["rest_id"][0]
        user_ids.append(user_id)

    try:
        tweets = scraper.tweets(user_ids, limit=limit, progress_bar=True)
        if tweets:
            image_urls, video_urls = get_media_urls(tweets)
            media_urls["images"].update(image_urls)
            media_urls["videos"].update(video_urls)

            st.write(f"Scraped {len(media_urls['images'])} images and {len(media_urls['videos'])} videos.")

            temp_dir = tempfile.gettempdir()
            csv_path = os.path.join(temp_dir, "twitter_media_urls.csv")
            all_tweet_df = pd.DataFrame([flatten_dict(tweet) for tweet in tweets]).fillna("")
            all_tweet_df.to_csv(csv_path, index=False)

            st.download_button(
                label="Download Media URLs CSV",
                data=all_tweet_df.to_csv(index=False),
                file_name="twitter_media_urls.csv",
                mime="text/csv",
            )

            def display_media(media_list):
                cols = st.columns(3)
                for idx, url in enumerate(media_list):
                    media_type = "image"
                    if any(ext in url for ext in [".mp4", ".webm"]):
                        media_type = "video"
                    with cols[idx % 3]:
                        if media_type == "image":
                            st.image(url)
                        elif media_type == "video":
                            st.video(url)
            all_media = list(set(media_urls["images"]) | set(media_urls["videos"]))
            all_media = [m for m in all_media if "thumb" not in m]
            all_media = list(set(all_media))
            random.shuffle(all_media)
            display_media(all_media)

    except Exception as e:
        st.error(f"Media Fetching failed: {e}. Please refresh and try new cookies.")
