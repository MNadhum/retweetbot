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
PASTEBIN_SITE2 = os.environ['PASTEBIN_SITE2']
CHROMEDRIVER_PATH = os.environ['CHROMEDRIVER_PATH']
GOOGLE_CHROME_BIN = os.environ["GOOGLE_CHROME_BIN"]


TWTR_SEARCH_URL = " https://twitter.com/search?q=https%3A%2F%2Ftwitter.com%2F"
TWTR_STATUS_URL = "%2Fstatus%2F"


auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
auth.set_access_token(ACCESS_KEY, ACCESS_SECRET)
api = tweepy.API(auth)


def go_to_textbox():
    '''
    Utilizes Selenium in order to navigate to a certain clipboard site page,
    logs in, and returns the textbox and driver
    elements
    :return: driver and textbox element, which is where last_tweet_id is written
    '''

    # Allows chrome to be opened without a display
    # and sets arguments to account for Heroku's restrictions
    chrome_options = webdriver.ChromeOptions()
    chrome_options.binary_location = GOOGLE_CHROME_BIN
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")

    # Driver goes to specified clipboard page
    driver = webdriver.Chrome(executable_path=CHROMEDRIVER_PATH,\
                              chrome_options=chrome_options)
    driver.get(PASTEBIN_SITE)
    
    # Driver finds elements using XPath
    user_login_box = driver.find_element_by_xpath("/html/body/div[2]/div/div/\
    div/div/div/div[1]/div[1]/div/div/div/div[2]/div[1]/div/input")
    
    password_login_box = driver.find_element_by_xpath("/html/body/div[2]/div/\
    div/div/div/div/div[1]/div[1]/div/div/div/div[2]/div[2]/div/div/input")
    
    login_button = driver.find_element_by_xpath("/html/body/div[2]/div/div/\
    div/div/div/div[1]/div[1]/div/div/div/div[2]/div[4]/button")

    
    # Logs into specific clipboard website account
    user_login_box.clear()
    user_login_box.send_keys(PASTEBIN_USER)

    password_login_box.clear()
    password_login_box.send_keys(PASTEBIN_PASS)

    login_button.click()

    time.sleep(1) # Waits in case loading occurs

    # URL is changed to specified page where textbox is found, as to not code
    # all the instructions to get there
    driver.get(PASTEBIN_SITE2)

    textbox = driver.find_element_by_xpath("/html/body/div[2]/div/div/div/\
    div/div/div[2]/div[2]/div[3]/textarea")

    return textbox, driver


def update_last_tweet_id(last_tweet_id):
    '''
    Updates last_tweet_id on clipboard page, saves it, then closes the browser.
    :param last_tweet_id: id of the last tweet bot responded to
    :return: None
    '''

    get_vars = go_to_textbox()

    textbox = get_vars[0]
    driver = get_vars[1]

    # Removes old last_tweet_id and replaces it
    # with the most recent tweet's tweet_id
    textbox.clear()
    textbox.send_keys(last_tweet_id)
    save_button = driver.find_element_by_xpath("/html/body/div[2]/div/div/div/\
div/div/div[2]/div[2]/div[5]/button")

    save_button.click()

    time.sleep(1)  # gives Chrome enough time to submit

    driver.quit()


def respond_to_user(last_tweet_id):
    """
    Uses Tweepy functions to look at mentions that account has received,
    and properly respond to user as well as calls update_last_tweet_id
    function in order to update the id of last tweet in mentions
    if necessary
    :param last_tweet_id: id of the last tweet bot responded to
    :return: None
    """

    mentions = api.mentions_timeline(int(last_tweet_id))
    if not mentions: # Checks if there are any new mentions
        print("No new mentions")
        pass
    else:
        # Iterates through mentions, starting from oldest to newest
        for mention in reversed(mentions):
            # Updates last_tweet_id variable after every new mention
            last_tweet_id = mention.id

            # Ensures it is not replying to its own tweet
            # as to not create infinite reply loop
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
                # Final length should be 0, or it doesn't respond, meaning
                # the tweet stated exactly: "@QuotedBot" and nothing else.
                # This was added as a preventative measure to stop bot from
                # responding to users who continued to mention @QuotedBot 
                # while having a conversation with other users
                if final_length == 0:
                    print("tweeting link", end="\n")
                    # Replies to user's tweet with a link to what was requested
                    api.update_status('@' + mention.user.screen_name
                                      + TWTR_SEARCH_URL +
                                      str(mention.in_reply_to_screen_name)
                                      + TWTR_STATUS_URL +
                                      str(mention.in_reply_to_status_id),
                                      mention.id)
        
        # Updates the saved tweet_id to the new one
        update_last_tweet_id(last_tweet_id)


    return last_tweet_id


def get_newest_id(last_tweet_id):
    """
    This function returns the most recent id, in order to be
    later updated on clipboard website
    :param last_tweet_id: id of last tweet bot responded to
    :return: most recent last_tweet_id, returned as "since_ret"
    """

    newest_id = respond_to_user(last_tweet_id)
    return newest_id


# Catches any errors that might occur, and
# immediately notifies me through a Twitter DM
try:

    # This following block gets the initial "last_tweet_id"
    # in order to initiate the autmoated process
    go_to_initial_run = go_to_textbox()
    last_tweet_id = (go_to_initial_run[0]).text
    initial_drive_quit = (go_to_initial_run[1]).quit()
    broke = False

    while True:
            new_id = get_newest_id(last_tweet_id)
            last_tweet_id = new_id
            # reruns the program every 15 seconds to prevent
            # reaching Twitter's API limit
            time.sleep(15)
except Exception as e:
    broke = True
    print(e)

if broke:
    # if an error has occured, send DM to my account
    api.send_direct_message(2703454358, "Program Stopped Running")
