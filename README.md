## A bot to mirror posts from Reddit subreddits to Lemmy communities.
We don't want to clutter Lemmy with too much bot-generated content, but for subreddits like /r/EarthPorn where the users subscribe mainly for the content (and not for the comments) this still makes sense.
  
This bot aims to be easy to use, with just a few self-explanatory JSON config files needed to set it up.
You need to run the script every time you want reposts to be made. You might want to schedule it with something like the `cron` command (see section below).

### Setup

Before you use the bot you need to create the following JSON files in the same directory as the script.

A `reddit_credentials.json` with:
```
{
    "client_id": "",
    "client_secret": ""
}
```

A `lemmy_credentials.json` with:
```
{
    "account": "",
    "password": ""
}
```

When specifying Lemmy account names and community addresses, you **do not** need to prefix them with a `@` or `!`, as this is known from the field that the address is in.

A `communities.json` containing a dicitonary where the key is the subreddit name and the value is the target Lemmy community address:
```
{
    "test": "test@lemmy.ml"
}
```

You can also only repost posts that meet a certain condition. This can be done like so:
```
    "test": {
        "community": "test@lemmy.ml",
        "condition": "'[meta]' in post.title.lower()"
    }
```

The condition is written in Python and the following variables are available:
* `post`, the source Reddit post in quesiton as a PRAW [`Submission`](https://praw.readthedocs.io/en/latest/code_overview/models/submission.html) object.
* `re`, the module for evaluating regular expressions.

### Scheduling the command

Run this:
```
crontab -e
```

Paste:
```
0 */4 * * * python3 /path/to/bot.py
```

**UNTESTED** so far
https://www.howtogeek.com/devops/what-is-a-cron-job-and-how-do-you-use-them/