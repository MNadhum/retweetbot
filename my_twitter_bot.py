import tweepy
import time
import os
from boto.s3.connection import S3Connection
from selenium import webdriver
from selenium.webdriver.common.keys import Keys


ACCESS_KEY = os.environ['ACCESS_KEY']
ACCESS_SECRET = os.environ['ACCESS_SECRET']
CONSUMER_KEY = os.environ['CONSUMER_KEY']
CONSUMER_SECRET = os.environ['CONSUMER_SECRET']
PASTEBIN_SITE = os.environ['PASTEBIN_SITE']
PASTEBIN_USER = os.environ['PASTEBIN_USERNAME']
PASTEBIN_PASS = os.environ['PASTEBIN_PASSWORD']

auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
auth.set_access_token(ACCESS_KEY, ACCESS_SECRET)
api = tweepy.API(auth)


def go_to_textbox():
    '''
    Utilizes Selenium in order to navigate to a certain Pastebin.com page, login, and return the textbox and driver
    elements

    :return: driver and textbox element, which is where the last_tweet_id is written
    '''


    # Allows chrome to be opened without a display, and set arguments to account for Heroku restrictions
    chrome_options = webdriver.ChromeOptions()
    chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")

    # Driver goes to specified Pastebin page
    driver = webdriver.Chrome(executable_path=os.environ.get("CHROMEDRIVER_PATH"), chrome_options=chrome_options)
    driver.get(PASTEBIN_SITE)

    user_login_box = driver.find_element_by_name("user_name")
    password_login_box = driver.find_element_by_name("user_password")
    login_button = driver.find_element_by_name("submit")

    # Logs into specific Pastebin.com account in order to be able to update information on page
    user_login_box.clear()
    user_login_box.send_keys(PASTEBIN_USER)
    password_login_box.clear()
    password_login_box.send_keys(PASTEBIN_PASS)
    login_button.click()

    textbox = driver.find_element_by_name("paste_code")

    return textbox, driver


def update_last_tweet_id(last_tweet_id):
    '''
    Updates last_tweet_id variable on Pastebin page, then submits page, in order to save, then closes the browser.

    :param last_tweet_id: the id of the last tweet that the bot responded to in its mentions

    :return: None
    '''

    go_to_function_run = go_to_textbox()
    textbox = go_to_function_run[0]
    driver = go_to_function_run[1]

    # Removes old last_tweet_id and replaces it with the most recent tweet's tweet_id
    textbox.clear()
    textbox.send_keys(last_tweet_id)
    driver.find_element_by_name("submit").click()

    time.sleep(1)  # gives Chrome enough time to submit

    driver.quit()


def respond_to_user(last_tweet_id):
    """
    Uses Tweepy functions to look at mentions that account has received, and properly
    respond to user as well as calls update_last_tweet_id function in order to update the id of last tweet in mentions
    if necessary

    :param last_tweet_id: the id of the last tweet that the bot responded to in its mentions

    :return: None
    """

    mentions = api.mentions_timeline(int(last_tweet_id))
    if not mentions: # Checks if there are any new mentions
        print("No new mentions")
        pass
    else:
        for mention in reversed(mentions):  # Iterates through mentions, starting from oldest to newest
            last_tweet_id = mention.id  # Updates the last_tweet_id variable after every new mention

            # Ensures it is not replying to its own tweet, as to not create infinite reply loop
            if str(mention.in_reply_to_screen_name) != "QuotedBot":
                text = str(mention.text)
                text_lower = text.lower()
                users_mentioned_list = mention.entities.get("user_mentions")
                string_comparison = ""
                for i in users_mentioned_list:
                    string_comparison += "@"
                    string_comparison += i.get("screen_name")
                    string_comparison += " "
                string_comparison = string_comparison[:-1]
                length_string_comparison = len(string_comparison)
                final_length = len(text_lower) - length_string_comparison
                # Final length should be 0, or it doesn't respond, meaning the tweet stated exactly: "@QuotedBot"
                if final_length == 0:
                    print("tweeting link", end="\n")
                    # Replies to user under the same tweet they mentioned the account with a link to what they requested
                    api.update_status('@' + mention.user.screen_name +
                                      " https://twitter.com/search?q=https%3A%2F%2Ftwitter.com%2F" +
                                      str(mention.in_reply_to_screen_name) + "%2Fstatus%2F" +
                                      str(mention.in_reply_to_status_id), mention.id)
        update_last_tweet_id(last_tweet_id)
    return last_tweet_id


def since_id(last_tweet_id):
    """
    This function returns the most recent id, in order to be later updated on Pastebin

    :param last_tweet_id: the id of the last tweet that the bot responded to in its mentions

    :return: most recent last_tweet_id, returned as "since_ret"
    """

    since_ret = respond_to_user(last_tweet_id)
    return since_ret

# This following block gets the initial "last_tweet_id" in order to initiate the process
go_to_initial_run = go_to_textbox()
last_tweet_id = (go_to_initial_run[0]).text
initial_drive_quit = (go_to_initial_run[1]).quit()
broke = False

while True:
    # Catches any errors that might occur, and immediately notifies me through a Twitter DM
    try:
        new_id_being_used = since_id(last_tweet_id)
        last_tweet_id = new_id_being_used
        time.sleep(15)  # reruns the program every 15 seconds so that Twitter's API limit is not reached
    except Exception as e:
        broke = True
        print(e)
        break
if broke:
    api.send_direct_message(2703454358, "Program Stopped Running") # if an error occurs, send DM to my account
