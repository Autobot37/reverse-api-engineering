import streamlit as st
import pandas as pd
import httpx
from bs4 import BeautifulSoup
import re
from tqdm import tqdm
from PIL import Image
from io import BytesIO
import httpx
import tls_requests as requests
from urllib.parse import quote
from typing import Dict
import jmespath
import json
import random
import os
from twitter.scraper import Scraper
from tqdm import tqdm
from twitter.util import init_session
from tweepy_authlib import CookieSessionUserHandler

st.title("Fuck Twitter")

if st.button("refresh session"):
    st.write(st.secrets["username"])
    auth_handler = CookieSessionUserHandler(
        screen_name = st.secrets["username"],
        password = st.secrets["password"],
    )
    cookies_dict = auth_handler.get_cookies().get_dict()
    os.environ["ct0"] = cookies_dict["ct0"]
    os.environ["auth_token"] = cookies_dict["auth_token"]
    st.write("session refreshed, refresh the tab.")

#------------------------------------------------
def flatten_dict(d):
    ret = {}
    for k, v in d.items():
        if isinstance(v, dict):
            for k2, v2 in flatten_dict(v).items():
                if k2 not in ret:
                    ret[k2] = []
                ret[k2].extend(v2 if isinstance(v2, list) else [v2])
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, dict):
                    for k2, v2 in flatten_dict(item).items():
                        if k2 not in ret:
                            ret[k2] = []
                        ret[k2].extend(v2 if isinstance(v2, list) else [v2])
                else:
                    if k not in ret:
                        ret[k] = []
                    ret[k].append(item)
        else:
            if k not in ret:
                ret[k] = []
            ret[k].append(v)
    return ret

def get_media_urls(tweets):
    image_urls = set()
    video_urls = set()
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
        st.write(f"Login failed: {e}")
        if st.button("Try again"):
            auth_handler = CookieSessionUserHandler(
                screen_name = st.secrets["username"],
                password = st.secrets["password"],
            )
            cookies_dict = auth_handler.get_cookies().get_dict()
            print(cookies_dict)
            with open("cookies.json", "w") as f:
                f.write(cookies_dict)
            

            st.write("refreshing session refreshed, refresh the tab.")
        
    st.write("Login success with cookies")

    try:
        media_urls = {"images": set(), "videos": set()}
        user_ids = []
        for i, user in enumerate(users):
            st.write(f"Scraping for {usernames[i]}, Description: {flatten_dict(user).get('description', [''])[0]}")
            profile_url = flatten_dict(user).get("profile_image_url_https", [""])[0]
            st.image(profile_url, caption=usernames[i])
            user_id = flatten_dict(user)["rest_id"][0]
            user_ids.append(user_id)

        tweets = scraper.tweets(user_ids, limit=limit, progress_bar=True)
        if len(tweets) > 0:
            image_urls, video_urls = get_media_urls(tweets)
            media_urls["images"].update(image_urls)
            media_urls["videos"].update(video_urls)

            st.write(f"Scraped {len(media_urls['images'])} image URLs and {len(media_urls['videos'])} video URLs.")

            csv_filename = "twitter_media_urls.csv"
            all_tweet_data = [flatten_dict(tweet) for tweet in tweets]
            all_tweet_df = pd.DataFrame(all_tweet_data).fillna("")
            all_tweet_df.to_csv(csv_filename, index=False)

            st.download_button(
                label="Download Media URLs CSV",
                data=all_tweet_df.to_csv(index=False),
                file_name=csv_filename,
                mime="text/csv",
            )

            st.write("Displaying 20 random image URLs:")
            # random_images = random.sample(list(media_urls["images"]), min(20, len(media_urls["images"])))
            random_images = list(media_urls["images"])
            for url in random_images:
                st.image(url)

            st.write("Displaying 20 random video URLs:")
            # random_videos = random.sample(list(media_urls["videos"]), min(20, len(media_urls["videos"])))
            random_videos = list(media_urls["videos"])
            for url in random_videos:
                st.video(url)
    except Exception as e:
        st.write(f"Media Fetching failed: {e}. Please refresh and try new cookies.")