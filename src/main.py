__version__ = '0.7.1'
__author__ = 'gerenook'

import argparse
import json
import logging
import re
import sqlite3
import sys
import time
from io import BytesIO
from logging.handlers import TimedRotatingFileHandler
from math import ceil
from os import remove
import shutil

import praw
import requests
# from imgurpython import ImgurClient
# from imgurpython.helpers.error import (ImgurClientError,
                                    #    ImgurClientRateLimitError)
from PIL import Image, ImageDraw, ImageFont
from prawcore.exceptions import RequestException, ResponseException

# import apidata


class RedditImage:
    """RedditImage class

    :param image: the image
    :type image: PIL.Image.Image
    """
    margin = 10
    min_size = 500
    # TODO find a font for all unicode chars & emojis
    # font_file = 'seguiemj.ttf'
    font_file = 'roboto.ttf'
    font_scale_factor = 16
    regex_resolution = re.compile(r'\s?\[[0-9]+\s?[xX*×]\s?[0-9]+\]')

    def __init__(self, image):
        self._image = image
        self.upscaled = False
        width, height = image.size
        # upscale small images
        if image.size < (self.min_size, self.min_size):
            if width < height:
                factor = self.min_size / width
            else:
                factor = self.min_size / height
            self._image = self._image.resize((ceil(width * factor),
                                              ceil(height * factor)),
                                             Image.LANCZOS)
            self.upscaled = True
        self._width, self._height = self._image.size
        self._font_title = ImageFont.truetype(
            self.font_file,
            self._width // self.font_scale_factor
        )

    def _split_title(self, title):
        """Split title on [',', ';', '.'] into multiple lines

        :param title: the title to split
        :type title: str
        :returns: split title
        :rtype: list[str]
        """
        lines = ['']
        all_delimiters = [',', ';', '.']
        delimiter = None
        for character in title:
            # don't draw ' ' on a new line
            if character == ' ' and not lines[-1]:
                continue
            # add character to current line
            lines[-1] += character
            # find delimiter
            if not delimiter:
                if character in all_delimiters:
                    delimiter = character
            # end of line
            if character == delimiter:
                lines.append('')
        # if a line is too long, wrap title instead
        for line in lines:
            if self._font_title.getsize(line)[0] + RedditImage.margin > self._width:
                return self._wrap_title(title)
        # remove empty lines (if delimiter is last character)
        return [line for line in lines if line]

    def _wrap_title(self, title):
        """Wrap title

        :param title: the title to wrap
        :type title: str
        :returns: wrapped title
        :rtype: list
        """
        lines = ['']
        line_words = []
        words = title.split()
        for word in words:
            line_words.append(word)
            lines[-1] = ' '.join(line_words)
            if self._font_title.getsize(lines[-1])[0] + RedditImage.margin > self._width:
                lines[-1] = lines[-1][:-len(word)].strip()
                lines.append(word)
                line_words = [word]
        # remove empty lines
        return [line for line in lines if line]

    def add_title(self, title, boot, bg_color='#fff', text_color='#000'):
        """Add title to new whitespace on image

        :param title: the title to add
        :type title: str
        :param boot: if True, split title on [',', ';', '.'], else wrap text
        :type boot: bool
        """
        # remove resolution appended to title (e.g. '<title> [1000 x 1000]')
        title = RedditImage.regex_resolution.sub('', title)
        line_height = self._font_title.getsize(title)[1] + RedditImage.margin
        lines = self._split_title(title) if boot else self._wrap_title(title)
        whitespace_height = (line_height * len(lines)) + RedditImage.margin
        new = Image.new('RGB', (self._width, self._height + whitespace_height), bg_color)
        new.paste(self._image, (0, whitespace_height))
        draw = ImageDraw.Draw(new)
        for i, line in enumerate(lines):
            draw.text((RedditImage.margin, i * line_height + RedditImage.margin),
                      line, text_color, self._font_title)
        self._width, self._height = new.size
        self._image = new

    def upload(self, imgur, config):
        """Upload self._image to imgur

        :param imgur: the imgur api client
        :type imgur: imgurpython.client.ImgurClient
        :param config: imgur image config
        :type config: dict
        :returns: imgur url if upload successful, else None
        :rtype: str, NoneType
        """
        path_png = 'temp.png'
        path_jpg = 'temp.jpg'
        self._image.save(path_png)
        self._image.save(path_jpg)
        try:
            response = imgur.upload_from_path(path_png, config, anon=False)
        except: #ImgurClientError as error:
            #logging.warning('png upload failed, trying jpg | %s', error)
            #try:
            #    response = imgur.upload_from_path(path_jpg, config, anon=False)
            #except: # ImgurClientError as error:
            #    logging.error('jpg upload failed, returning | %s', error)
           return None
        finally:
            remove(path_png)
            remove(path_jpg)
        return response['link']
    
    def download(self,name):
        path_png = name+".png"
        path_jpg = name+".jpg"
        self._image.save(path_png)
        self._image.save(path_jpg)























# def _process_submission(self, submission, source_comment=None, custom_title=None):
#         """Generate new image with added title and author, upload to imgur, reply to submission

#         :param submission: the reddit submission object
#         :type submission: praw.models.Submission
#         :param source_comment: the comment that mentioned the bot, reply to this comment.
#             If None, reply at top level. (default None)
#         :type source_comment: praw.models.Comment, NoneType
#         :param custom_title: if not None, use as title instead of submission title
#         :type custom_title: str
#         """
#         # TODO really need to clean this method up
#         # return if author account is deleted
#         if not submission.author:
#             return
#         sub = submission.subreddit.display_name
#         # in r/fakehistoryporn, only process upvoted submissions
#         score_threshold = 500
#         if sub == 'fakehistoryporn' and not source_comment:
#             if submission.score < score_threshold:
#                 logging.debug('Score below %d in subreddit %s, skipping submission',
#                               score_threshold, sub)
#                 return
#         # check db if submission was already processed
#         author = submission.author.name
#         title = submission.title
#         url = submission.url
#         result = self._db.submission_select(submission.id)
#         if result:
#             if result['retry'] or source_comment:
#                 if result['imgur_url']:
#                     # logging.info('Submission id:%s found in database with imgur url set, ' +
#                     #              'trying to create reply', submission.id)
#                     # self._reply_imgur_url(result['imgur_url'], submission, source_comment)
#                     # return
#                     logging.info('Submission id:%s found in database with imgur url set',
#                                  submission.id)
#                     # db check disabled to allow custom titles
#                 else:
#                     logging.info('Submission id:%s found in database without imgur url set, ',
#                                  submission.id)
#             else:
#                 # skip submission
#                 logging.debug('Submission id:%s found in database, returning', result['id'])
#                 return
#         else:
#             logging.info('Found new submission subreddit:%s id:%s title:%s',
#                          sub, submission.id, title)
#             logging.debug('Adding submission to database')
#             self._db.submission_insert(submission.id, author, title, url)
#         # in r/boottoobig, only process submission with a rhyme in the title
#         boot = sub == 'boottoobig'
#         if boot and not source_comment:
#             triggers = [',', ';', 'roses']
#             if not any(t in title.lower() for t in triggers):
#                 logging.info('Title is probably not part of rhyme, skipping submission')
#                 return
#         if url.endswith('.gif') or url.endswith('.gifv'):
#             logging.info('Image is animated gif, skipping submission')
#             return
#         logging.debug('Trying to download image from %s', url)
#         try:
#             response = requests.get(url)
#             img = Image.open(BytesIO(response.content))
#         except OSError as error:
#             logging.warning('Converting to image failed, trying with <url>.jpg | %s', error)
#             try:
#                 response = requests.get(url + '.jpg')
#                 img = Image.open(BytesIO(response.content))
#             except OSError as error:
#                 logging.error('Converting to image failed, skipping submission | %s', error)
#                 return
#         image = RedditImage(img)
#         logging.debug('Adding title')
#         if custom_title:
#             image.add_title(custom_title, boot)
#         else:
#             image.add_title(title, boot)
#         logging.debug('Trying to upload new image')
#         imgur_config = {
#             'album': None,
#             'name': submission.id,
#             'title': '"{}" by /u/{}'.format(title, author),
#             'description': submission.shortlink
#         }
#         try:
#             imgur_url = image.upload(self._imgur, imgur_config)
#         # except ImgurClientRateLimitError as rate_error:
#         #     logging.error('Imgur ratelimit error, setting retry flag in database | %s', rate_error)
#         #     self._db.submission_set_retry(submission.id, bool(source_comment), source_comment)
#         #     return
#         except:
#             return
#         if not imgur_url:
#             logging.error('Cannot upload new image, skipping submission')
#             return
#         self._db.submission_set_imgur_url(submission.id, imgur_url)
#         if not self._reply_imgur_url(imgur_url, submission, source_comment, upscaled=image.upscaled):
#             return
#         logging.info('Successfully processed submission')










class Database:
    """Database class

    :param db_filename: database filename
    :type db_filename: str
    """
    def __init__(self, db_filename):
        self._sql_conn = sqlite3.connect(db_filename)
        self._sql = self._sql_conn.cursor()

    def message_exists(self, message_id):
        """Check if message exists in messages table

        :param message_id: the message id to check
        :type message_id: str
        :returns: True if message was found, else False
        :rtype: bool
        """
        self._sql.execute('SELECT EXISTS(SELECT 1 FROM messages WHERE id=? LIMIT 1)', (message_id,))
        if self._sql.fetchone()[0]:
            return True
        return False

    def message_insert(self, message_id, author, subject, body):
        """Insert message into messages table"""
        self._sql.execute('INSERT INTO messages (id, author, subject, body) VALUES (?, ?, ?, ?)',
                          (message_id, author, subject, body))
        self._sql_conn.commit()

    def submission_select(self, submission_id):
        """Select all attributes of submission

        :param submission_id: the submission id
        :type submission_id: str
        :returns: query result, None if id not found
        :rtype: dict, NoneType
        """
        self._sql.execute('SELECT * FROM submissions WHERE id=?', (submission_id,))
        result = self._sql.fetchone()
        if not result:
            return None
        return {
            'id': result[0],
            'author': result[1],
            'title': result[2],
            'url': result[3],
            'imgur_url': result[4],
            'retry': result[5],
            'timestamp': result[6]
        }

    def submission_insert(self, submission_id, author, title, url):
        """Insert submission into submissions table"""
        self._sql.execute('INSERT INTO submissions (id, author, title, url) VALUES (?, ?, ?, ?)',
                          (submission_id, author, title, url))
        self._sql_conn.commit()

    def submission_set_retry(self, submission_id, delete_message=False, message=None):
        """Set retry flag for given submission, delete message from db if desired

        :param submission_id: the submission id to set retry
        :type submission_id: str
        :param delete_message: if True, delete message from messages table
        :type delete_message: bool
        :param message: the message to delete
        :type message: praw.models.Comment, NoneType
        """
        self._sql.execute('UPDATE submissions SET retry=1 WHERE id=?', (submission_id,))
        if delete_message:
            if not message:
                raise TypeError('If delete_message is True, message must be set')
            self._sql.execute('DELETE FROM messages WHERE id=?', (message.id,))
        self._sql_conn.commit()

    def submission_clear_retry(self, submission_id):
        """Clear retry flag for given submission_id

        :param submission_id: the submission id to clear retry
        :type submission_id: str
        """
        self._sql.execute('UPDATE submissions SET retry=0 WHERE id=?', (submission_id,))
        self._sql_conn.commit()

    def submission_set_imgur_url(self, submission_id, imgur_url):
        """Set imgur url for given submission

        :param submission_id: the submission id to set imgur url
        :type submission_id: str
        :param imgur_url: the imgur url to update
        :type imgur_url: str
        """
        self._sql.execute('UPDATE submissions SET imgur_url=? WHERE id=?',
                          (imgur_url, submission_id))
        self._sql_conn.commit()



class Mainbot:
    def __init__(self, subreddit):
        # self._db = Database('database.db')
        self._reddit = praw.Reddit('client')
        self._subreddit = self._reddit.subreddit(subreddit)
        # self._imgur = ImgurClient(**apidata.imgur)
        # self._template = (
        #     '[Image with added title]({image_url})\n\n'
        #     '{upscaled}---\n\n'
        #     'summon me with /u/titletoimagebot | '
        #     '[feedback](https://reddit.com/message/compose/'
        #     '?to=TitleToImageBot&subject=feedback%20{submission_id}) | '
        #     '[source](https://github.com/gerenook/titletoimagebot)'
        # )
    def main(self,submission,source_comment=None, custom_title=None):
        sub = submission.subreddit.display_name
        
        # check db if submission was already processed
        author = submission.author.name
        title = submission.title
        url = submission.url
        # result = self._db.submission_select(submission.id)
        # if result:
        #     if result['retry'] or source_comment:
        #         if result['imgur_url']:
        #             # logging.info('Submission id:%s found in database with imgur url set, ' +
        #             #              'trying to create reply', submission.id)
        #             # self._reply_imgur_url(result['imgur_url'], submission, source_comment)
        #             # return
        #             logging.info('Submission id:%s found in database with imgur url set',
        #                             submission.id)
        #             # db check disabled to allow custom titles
        #         else:
        #             logging.info('Submission id:%s found in database without imgur url set, ',
        #                             submission.id)
        #     else:
        #         # skip submission
        #         logging.debug('Submission id:%s found in database, returning', result['id'])
        #         return
        # else:
        #     logging.info('Found new submission subreddit:%s id:%s title:%s',
        #                     sub, submission.id, title)
        #     logging.debug('Adding submission to database')
        #     self._db.submission_insert(submission.id, author, title, url)

        # in r/boottoobig, only process submission with a rhyme in the title
        # boot = sub == 'boottoobig'
        # if boot and not source_comment:
        #     triggers = [',', ';', 'roses']
        #     if not any(t in title.lower() for t in triggers):
        #         logging.info('Title is probably not part of rhyme, skipping submission')
        #         return
        if url.endswith('.gif') or url.endswith('.gifv'):
            logging.info('Image is animated gif, skipping submission')
            return
        logging.debug('Trying to download image from %s', url)
        try:
            response = requests.get(url)
            img = Image.open(BytesIO(response.content))
        except OSError as error:
            logging.warning('Converting to image failed, trying with <url>.jpg | %s', error)
            try:
                response = requests.get(url + '.jpg')
                img = Image.open(BytesIO(response.content))
            except OSError as error:
                logging.error('Converting to image failed, skipping submission | %s', error)
                return
        image = RedditImage(img)
        logging.debug('Adding title')
        # if custom_title:
            # image.add_title(custom_title, boot)
        # else:
            # image.add_title(title, boot)
        name = submission.id()    
        image.download(name)
        return     
        # logging.debug('Trying to upload new image')
        # imgur_config = {
        #     'album': None,
        #     'name': submission.id,
        #     'title': '"{}" by /u/{}'.format(title, author),
        #     'description': submission.shortlink
        # }
        # try:
            # imgur_url = image.upload(self._imgur, imgur_config)
        # except ImgurClientRateLimitError as rate_error:
        #     logging.error('Imgur ratelimit error, setting retry flag in database | %s', rate_error)
        #     self._db.submission_set_retry(submission.id, bool(source_comment), source_comment)
        #     return
        # except:
        #     return
        # if not imgur_url:
        #     logging.error('Cannot upload new image, skipping submission')
        #     return
        # self._db.submission_set_imgur_url(submission.id, imgur_url)
        # if not self._reply_imgur_url(imgur_url, submission, source_comment, upscaled=image.upscaled):
        #     return
        logging.info('Successfully processed submission')
# counter=0
def top_lvl():
    sub = "memes"
    tlimit=5
    bot = Mainbot(sub)
    r = praw.Reddit('client')
    for submission in r.subreddit(sub).new(limit=tlimit):
        bot.main(submission)
        time.sleep(2)
    # with open("img"+counter+".jpg", 'wb') as out_file:
    #     shutil.copyfileobj(response, out_file)    


if __name__ == '__main__':
    # r = praw.Reddit('client') 
    # maxToDownload = 3
    # targetSubreddit = "memes"
    # for submission in r.subreddit(targetSubreddit).new(limit=maxToDownload):
        # newinstance = Mainbot(submission)
    top_lvl()