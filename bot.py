import json, os
import time
import praw, plemmy

# Load config

WORKDIR = os.path.dirname(__file__)

with open(WORKDIR + '/communities.json', 'r') as f:
    communities = json.load(f)

with open(WORKDIR + '/reddit_credentials.json', 'r') as f:
    reddit_creds = json.load(f)

with open(WORKDIR + '/lemmy_credentials.json', 'r') as f:
    lemmy_creds = json.load(f)

try:
    with open(WORKDIR + '/last_posts.json', 'r') as f:
        last_posts = json.load(f)
except Exception as err:
    last_posts: {str: str} = {}     # {subreddit: post_id}

# Initialize clients

r = praw.Reddit(**reddit_creds, user_agent="Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/114.0")
l = plemmy.LemmyHttp('https://' + lemmy_creds['account'].split('@')[1])
l.login(lemmy_creds['account'].split('@')[0], lemmy_creds['password'])

# Funcitons

def sync_community(subreddit_name, community_address, delay=0):
    subreddit = r.subreddit(subreddit_name)
    community = plemmy.responses.GetCommunityResponse(
        _check_api_error(
            l.get_community(name=community_address)
        )
    ).community_view.community     # As per https://github.com/tjkessler/plemmy/blob/main/examples/search_and_post.ipynb

    for i, submission in enumerate(subreddit.new(limit=10)):    # We limit ourselves to syncing the 10 newest posts so that we don't overwhelm the Lemmy servers
        if submission.id == last_posts.get(subreddit_name):
            break   # Since we're sorting by new, this means we've reposted all new posts since the last execution.
        if i == 0:
            last_posts[subreddit_name] = submission.id

        print(f"\tReposting \"{submission.title}\"")
        make_lemmy_post(submission, community)

        time.sleep(delay)

def make_lemmy_post(reddit_post, community):
    post = plemmy.responses.PostResponse(_check_api_error(l.create_post(
        community.id,
        reddit_post.title,
        body=(reddit_post.selftext if reddit_post.is_self else None),
        url=(None if reddit_post.is_self else reddit_post.url),
        nsfw=reddit_post.over_18
    ))).post_view.post
    
    comment_text = f"Original post made by [/u/{reddit_post.author.name}](https://reddit.com/u/{reddit_post.author.name}) on [/r/{reddit_post.subreddit.display_name}]({reddit_post.permalink})."
    _check_api_error(l.create_comment(
        comment_text,
        post.id
    ))

def _check_api_error(api_response):
    if api_response.json().get('error'):
        raise Exception(f'Lemmy API error `{api_response.json().get("error")}`')
    return api_response

def get_min_post_delay(site):
    s = plemmy.LemmyHttp(site)
    local_site_rate_limit = plemmy.responses.GetSiteResponse(_check_api_error(s.get_site())).site_view.local_site_rate_limit

    return ((local_site_rate_limit.post / local_site_rate_limit.post_per_second) // 1) + 1  # As per https://lemmy.ml/comment/2351393

# if __name__ == "__main__":
if True:
    for k, v in communities.items():
        min_delay = get_min_post_delay('https://' + v.split("@")[1])
        print(f"Syncing /r/{k} to {v} (min post delay: {min_delay}s) ...")
        sync_community(k, v, delay=min_delay)

# Save updated config

with open(WORKDIR + '/last_posts.json', 'w') as f:
    json.dump(last_posts, f, indent=4)