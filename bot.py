import json, os
import time
import praw, plemmy
import re

# Load config

WORKDIR = os.path.dirname(__file__)

with open(WORKDIR + '/communities.json', 'r') as f:
    communities = json.load(f)

with open(WORKDIR + '/reddit_credentials.json', 'r') as f:
    reddit_creds = json.load(f)

with open(WORKDIR + '/lemmy_credentials.json', 'r') as f:
    lemmy_creds = json.load(f)

try:
    with open(WORKDIR + '/past_posts.json', 'r') as f:
        past_posts = json.load(f)
except Exception as err:
    past_posts: {str: str} = {}     # {subreddit: [reddit_post_ids]}

# Initialize clients

r = praw.Reddit(**reddit_creds, user_agent="Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/114.0")
l = plemmy.LemmyHttp('https://' + lemmy_creds['account'].split('@')[1])
l.login(lemmy_creds['account'].split('@')[0], lemmy_creds['password'])

# Funcitons

def sync_community(subreddit_name, community_address, condition: str=None, delay=0):
    subreddit = r.subreddit(subreddit_name)
    community = plemmy.responses.GetCommunityResponse(
        _check_api_error(
            l.get_community(name=community_address)
        )
    ).community_view.community     # As per https://github.com/tjkessler/plemmy/blob/main/examples/search_and_post.ipynb

    existing_reposts = past_posts.get(subreddit_name, [])

    for i, submission in enumerate(subreddit.new(limit=10)):    # We limit ourselves to syncing the 10 newest posts so that we don't overwhelm the Lemmy servers
        if submission.id in existing_reposts:
            continue

        if condition:
            if not should_repost(submission, condition):
                continue

        print(f"\tReposting \"{submission.title}\"")
        make_lemmy_post(submission, community)
        existing_reposts.insert(0, submission.id)

        time.sleep(delay)
    
    past_posts[subreddit_name] = existing_reposts

def should_repost(submission, cond: str) -> bool:
    return eval(cond, {"post": submission, "re": re})

def make_lemmy_post(reddit_post, community):
    if  not reddit_post.is_self and (
        reddit_post.url.startswith('/r/') and '/comments/' in reddit_post.url):
        # It's a cross-post. Find the original.
        reddit_post = r.submission(reddit_post.url.split('/')[4])    # A crosspost url will be something like "/r/GainsForTheBrains/comments/16cek4i/early_mornings/"

    post = plemmy.responses.PostResponse(_check_api_error(l.create_post(
        community.id,
        reddit_post.title,
        body=(reddit_post.selftext if reddit_post.is_self else None),
        url=(None if reddit_post.is_self else reddit_post.url),
        nsfw=reddit_post.over_18
    ))).post_view.post
    
    comment_text = f"Original post made by [/u/{reddit_post.author.name}](https://reddit.com/u/{reddit_post.author.name}) on [/r/{reddit_post.subreddit.display_name}](https://reddit.com/{reddit_post.permalink})."
    _check_api_error(l.create_comment(
        comment_text,
        post.id
    ))

def _check_api_error(api_response):
    # if api_response.json().get('error'):
    if not 200 <= api_response.status_code < 300:
        raise Exception(f'Lemmy API error (code {api_response.status_code}) `{api_response.text}`')
    return api_response

def get_min_post_delay(site):
    s = plemmy.LemmyHttp(site)
    local_site_rate_limit = plemmy.responses.GetSiteResponse(_check_api_error(s.get_site())).site_view.local_site_rate_limit

    return ((local_site_rate_limit.post / local_site_rate_limit.post_per_second) // 1) + 1  # As per https://lemmy.ml/comment/2351393

# if __name__ == "__main__":
try:
    # Iterate over each entry in `communities.json`
    for subreddit, val in communities.items():
        if isinstance(val, dict):
            community = val["community"]
            condition = val.get("condition", None)
        else:
            community = val
            condition = None

        min_delay = get_min_post_delay('https://' + community.split("@")[1])
        print(f"Syncing /r/{subreddit} to {community} (min post delay: {min_delay}s) ...")
        sync_community(subreddit, community, condition=condition, delay=min_delay)
finally:
    with open(WORKDIR + '/past_posts.json', 'w') as f:
        json.dump(past_posts, f, indent=4)
    print("Updated list of reposts.")