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
from twitter.scraper import Scraper
from tqdm import tqdm
from twitter.util import init_session
from instaloader import Instaloader, Profile

st.title("Social Media Scraper")

selected = st.selectbox("Select site to scrape.", ["Instagram", "Twitter", "Reddit"])

if selected == "Reddit":
    subreddit_name = st.text_input("Enter subreddit name (e.g., MachineLearning)")
    hot_or_top = st.selectbox("Select sort order", ["hot", "top"])
    if hot_or_top == "top":
        t = st.selectbox("Select time period", ["hour", "day", "week", "month", "year", "all"])
    number_of_posts = st.number_input("Number of posts to scrape", min_value=20, value=20, max_value=1000)

    if subreddit_name and st.button("Scrape Subreddit") and hot_or_top and (hot_or_top == "hot" or t):
        base_url = (
            f"https://www.popular.pics/reddit/subreddits/posts?r={subreddit_name}&sort={hot_or_top}"
            if hot_or_top == "hot"
            else f"https://www.popular.pics/reddit/subreddits/posts?r={subreddit_name}&sort=top&t={t}"
        )

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://www.google.com/",
        }

        media_urls = set()
        next_page_url = base_url
        progress_bar = st.progress(0)
        progress_placeholder = st.empty()
        pbar = tqdm(total=number_of_posts, desc="Scraping Media")

        while len(media_urls) < number_of_posts:
            response = httpx.get(next_page_url, headers=headers)

            if response.status_code != 200:
                st.error(f"Failed to fetch the page. Status code: {response.status_code}")
                break

            soup = BeautifulSoup(response.content, "html.parser")
            posts = soup.find_all("div", class_="post__media")

            for post in posts:
                if len(media_urls) >= number_of_posts:
                    break

                img_tag = post.find("img")
                if img_tag and img_tag.get("src"):
                    media_urls.add(img_tag["src"])

                video_tag = post.find("video")
                if video_tag and video_tag.get("src"):
                    media_urls.add(video_tag["src"])

                pbar.update(1)
                progress_bar.progress(len(media_urls) / number_of_posts)
                progress_placeholder.write(f"Scraped {len(media_urls)} of {number_of_posts} posts.")

            next_page_tag = soup.find("a", class_="button popup-trigger")
            if next_page_tag and next_page_tag.get("href"):
                next_page_url = f"https://www.popular.pics{next_page_tag['href']}"
            else:
                break

        pbar.close()
        st.write(f"Scraped {len(media_urls)} unique media items.")

        csv_filename = f"{subreddit_name}_media_urls.csv"
        pd.DataFrame(list(media_urls), columns=["Media URL"]).to_csv(csv_filename, index=False)

        st.download_button(
            label="Download CSV",
            data=pd.DataFrame(list(media_urls), columns=["Media URL"]).to_csv(index=False),
            file_name=csv_filename,
            mime="text/csv",
        )

        st.write("Displaying the first 20 media items:")
        for url in list(media_urls)[:20]:
            try:
                if any(ext in url.lower() for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                    response = httpx.get(url, headers=headers)
                    if response.status_code == 200:
                        img = Image.open(BytesIO(response.content))
                        st.image(img, use_column_width=True)
                elif any(ext in url.lower() for ext in [".mp4", ".webm", ".ogg"]):
                    st.video(url)
                else:
                    pass
            except Exception:
                pass

#------------------------------------------------
if selected == "Instagram":

    username = st.text_input("Enter Instagram username (e.g., natgeo)")
    max_pages = st.number_input("Number of pages to scrape (1 page scrapes 12 posts)", min_value=1, value=1, max_value=1000)
    total_posts = max_pages * 12
    acc_username = st.text_input("Account username(Optional if you want large scraping)")
    acc_password = st.text_input("Account password(Optional if you want large scraping)")
    media_urls = set()

    def fetch_user_posts_instaloader(username, total_posts, acc_username=None, acc_password=None):
        if acc_username is not None and acc_password is not None:
            st.write(f"Logging in with {acc_username} and {acc_password}")
            loader = Instaloader(acc_username, acc_password)
            st.write("Account login success")
        else:
            st.write("Logging in anonymously")
            loader = Instaloader()
            st.write("Anon Login Success")
        profile = Profile.from_username(loader.context, username)
        st.write("Scraping for", profile.username)
        response = httpx.get(profile.profile_pic_url)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            st.image(img, caption=username)
        post_count = 0
        progress_bar = st.progress(0)
        post_count = 0
        try:
            for post in profile.get_posts():
                if post_count >= total_posts:
                    break
                post_count += 1
                if post.url:
                    media_urls.add(post.url)
                if post.is_video:
                    media_urls.add(post.video_url)
                progress_bar.progress(post_count / total_posts)
                if post_count >= total_posts:
                    break
                post_count += 1
                if post.url:
                    media_urls.add(post.url)
                if post.is_video:
                    media_urls.add(post.video_url)
        except:
            return

    def fetch_user_posts_httpx(username, total_posts, max_pages):
        def generate_random_headers(csrf_token=None):
            user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.93 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Mozilla/5.0 (iPhone; CPU iPhone OS 14_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
            ]
            headers = {
                "x-ig-app-id": "936619743392459",
                "User-Agent": random.choice(user_agents),
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.instagram.com/",
            }
            if csrf_token:
                headers["x-csrftoken"] = csrf_token
            return headers

        def get_csrf_token(session):
            response = session.get("https://www.instagram.com/")
            return response.cookies.get("csrftoken", "")

        def scrape_user(username, session):
            url = f"https://i.instagram.com/api/v1/users/web_profile_info/?username={username}"
            result = session.get(url)
            data = json.loads(result.content)
            return data["data"]["user"]

        def scrape_user_posts(user_id, session, page_size=12, max_pages=None):
            base_url = "https://www.instagram.com/graphql/query/?query_hash=e769aa130647d2354c40ea6a439bfc08&variables="
            variables = {
                "id": user_id,
                "first": page_size,
                "after": None,
            }
            page_number = 1
            while page_number <= max_pages:
                resp = session.get(base_url + quote(json.dumps(variables)))
                data = resp.json()
                posts = data["data"]["user"]["edge_owner_to_timeline_media"]
                for post in posts["edges"]:
                    yield post["node"]
                if not posts["page_info"]["has_next_page"]:
                    break
                variables["after"] = posts["page_info"]["end_cursor"]
                page_number += 1

        with requests.Client(
            headers=generate_random_headers(),
        ) as session:
            csrf_token = get_csrf_token(session)
            session.headers.update(generate_random_headers(csrf_token=csrf_token))
            user_data = scrape_user(username, session)
            user_id = user_data["id"]
            total_scraped = 0
            progress_bar = st.progress(0)
            for post in scrape_user_posts(user_id, session, max_pages=max_pages):
                if post.get("is_video") and post.get("video_url"):
                    media_urls.add(post["video_url"])
                elif post.get("display_url"):
                    media_urls.add(post["display_url"])
                total_scraped += 1
                progress_bar.progress(total_scraped / total_posts)

    try:
        if username and st.button("Scrape Instagram"):
            if acc_username and acc_password:
                fetch_user_posts_instaloader(username, total_posts, acc_username, acc_password)
            else:
                fetch_user_posts_instaloader(username, total_posts)
            st.write(f"Scraped {len(media_urls)} media items using Instaloader.")
    except Exception as e:
        st.write("Instaloader failed. Trying HTTPX method.")
        try:
            fetch_user_posts_httpx(username, total_posts, max_pages)
            st.write(f"Scraped {len(media_urls)} media items using HTTPX.")
        except Exception as e:
            st.write(f"HTTPX method also failed: {e}")

    if len(media_urls) > 0:
        csv_filename = f"{username}_media_urls.csv"
        pd.DataFrame(list(media_urls), columns=["Media URL"]).to_csv(csv_filename, index=False)

        st.download_button(
            label="Download CSV",
            data=pd.DataFrame(list(media_urls), columns=["Media URL"]).to_csv(index=False),
            file_name=csv_filename,
            mime="text/csv",
        )

        st.write("Displaying the first 20 media items:")
        for url in list(media_urls)[:20]:
            if any(ext in url for ext in [".mp4", ".webm"]):
                st.video(url)
            else:
                try:
                    response = httpx.get(url)
                    if response.status_code == 200:
                        img = Image.open(BytesIO(response.content))
                        st.image(img, use_container_width=True)
                except Exception as e:
                    st.error(f"Error displaying image: {e}")
    else:
        st.write("No media items scraped.")
#------------------------------------------------
if selected == "Twitter":
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

    ct0_token = st.text_input("Log in to Twitter from web and click inspect > application > cookies > ct0")
    auth_token = st.text_input("Log in to Twitter from web and click inspect > application > cookies > auth_token")
    usernames = st.text_input("Enter usernames (comma-separated)")
    limit = st.number_input("Number of tweets to scrape", min_value=10, value=10, max_value=1000)
    acc_user = st.text_input("Account username")
    acc_password = st.text_input("Account password")
    
    if ((ct0_token and auth_token and usernames and limit) or (acc_user and acc_password)) and st.button("Scrape Twitter Media"):
        usernames = [username.strip() for username in usernames.split(",") if username.strip()]
        try:
            scraper = Scraper(acc_user, acc_password)
            users = scraper.users(usernames)
            st.write("Login success with username and password")
        except Exception:
            try:
                scraper = Scraper(cookies={"ct0": ct0_token, "auth_token": auth_token})
                users = scraper.users(usernames)
                st.write("Login success with cookies")
            except Exception as e:
                st.write(f"Login failed: {e}")

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
