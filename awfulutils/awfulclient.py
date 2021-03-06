import concurrent.futures
import glob
import logging
import os
import re
import shutil
import urllib.request
import time
from datetime import datetime
from http.client import RemoteDisconnected
from urllib import parse
from urllib.error import URLError
from urllib.parse import urlparse, parse_qs, urljoin, quote

import requests
from bs4 import BeautifulSoup
from requests import Timeout

logger = logging.getLogger(__name__)


class AwfulClient:
    DATE_FORMAT = '%b %d, %Y'
    DATETIME_FORMAT = '%b %d, %Y %H:%M'
    USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:33.0) Gecko/20100101 Firefox/33.0'
    FORUMS_URL = 'http://forums.somethingawful.com'
    DEFAULT_TIMEOUT_SECONDS = 10

    def __init__(self, userid, sessionid, timeout=DEFAULT_TIMEOUT_SECONDS):
        self.userid = userid
        self.timeout = timeout
        self.session = requests.Session()
        self.session.cookies.set('bbuserid', str(userid))
        self.session.cookies.set('bbpassword', sessionid)
        self.session.headers.setdefault('User-Agent', self.USER_AGENT)

    def userinfo(self, userid):
        """
        Retrieve user details for a particular user id
        :param userid:
        :return:
        """
        r = self.session.get('%s/member.php?action=getinfo&userid=%d' % (self.FORUMS_URL, userid), timeout=self.timeout)
        soup = BeautifulSoup(r.text, 'html5lib')

        userinfo_elem = soup.find('dl', class_='userinfo')

        userinfo = UserInfo()
        userinfo.username = userinfo_elem.find('dt', class_='author').get_text()

        title_elem = userinfo_elem.find('dd', class_='title')
        userinfo.avatar = title_elem.find('img')['src']
        userinfo.title = title_elem.get_text().strip()

        contacts_elem = soup.find('dl', class_='contacts')
        userinfo.icq_handle = contacts_elem.find('dt', class_='icq').findNext('dd').get_text().strip()
        userinfo.aim_handle = contacts_elem.find('dt', class_='aim').findNext('dd').get_text().strip()
        userinfo.yahoo_handle = contacts_elem.find('dt', class_='yahoo').findNext('dd').get_text().strip()
        userinfo.home_page = contacts_elem.find('dt', class_='homepage').findNext('dd').get_text().strip()

        additional_elem = soup.find('dl', class_='additional')

        join_date_string = additional_elem.find('dt', text=re.compile('Member Since')).findNext('dd').get_text()
        userinfo.join_date = datetime.strptime(join_date_string, self.DATE_FORMAT)

        userinfo.post_count = int(additional_elem.find('dt', text=re.compile('Post Count')).findNext('dd').get_text())

        posts_per_day_string = additional_elem.find('dt', text=re.compile('Post Rate')).findNext('dd').get_text()
        userinfo.posts_per_day = float(re.findall("-?\d+.\d+", posts_per_day_string)[0])

        last_post_string = additional_elem.find('dt', text=re.compile('Last Post')).findNext('dd').get_text().strip()
        userinfo.last_post = datetime.strptime(last_post_string, self.DATETIME_FORMAT)

        location_elem = additional_elem.find('dt', text=re.compile('Location'))
        if location_elem:
            userinfo.location = location_elem.findNext('dd').get_text().strip()

        interests_elem = additional_elem.find('dt', text=re.compile('Interests'))
        if interests_elem:
            userinfo.interests = additional_elem.find('dt',
                                                      text=re.compile('Interests')).findNext('dd').get_text().strip()

        occupation_elem = additional_elem.find('dt', text=re.compile('Occupation'))
        if occupation_elem:
            userinfo.occupation = occupation_elem.findNext('dd').get_text().strip()

        return userinfo

    def export_thread(self, threadid):
        thread_export = ThreadExport(self.session, threadid, timeout=self.timeout)
        thread_export.save()


class UserInfo:
    def __init__(self):
        self.username = None
        self.post_count = 0
        self.posts_per_day = 0.0
        self.join_date = None
        self.icq_handle = None
        self.aim_handle = None
        self.yahoo_handle = None
        self.home_page = None
        self.last_post = None
        self.location = None
        self.interests = None
        self.occupation = None
        self.avatar = None
        self.title = None
        self.about_me = None


class ThreadExport:
    PAGE_PATTERN_FILENAME = 'page_%s.html'

    def __init__(self, session, threadid, timeout=AwfulClient.DEFAULT_TIMEOUT_SECONDS, posts_per_page=40):
        self.session = session
        self.threadid = threadid
        self.timeout = timeout
        self.posts_per_page = posts_per_page

        # setup an opener to download files
        self.opener = urllib.request.build_opener()
        self.opener.addheaders = [('User-Agent', AwfulClient.USER_AGENT)]

        # retrieve some basic info about the thread
        r = self.session.get(self.thread_url(1), timeout=self.timeout)
        soup = BeautifulSoup(r.text, 'html5lib')

        last_page_url = urlparse(soup.find('a', title='Last page')['href'])
        self.total_pages = int(parse_qs(last_page_url.query)['pagenumber'][0])
        self.page_pad_zeros = len(str(self.total_pages))

        # setup the output directory
        self.output_folder = 'somethingawful_thread_%d' % self.threadid
        if not os.path.exists(self.output_folder):
            os.mkdir(self.output_folder)
        self.images_folder = os.path.join(self.output_folder, 'images')
        if not os.path.exists(self.images_folder):
            os.mkdir(self.images_folder)
        self.css_folder = os.path.join(self.output_folder, 'css')
        if not os.path.exists(self.css_folder):
            os.mkdir(self.css_folder)

    def thread_url(self, page_number):
        return urljoin(AwfulClient.FORUMS_URL,
                       '/showthread.php?perpage=%d&threadid=%d&pagenumber=%d'
                       % (self.posts_per_page, self.threadid, page_number))

    def save(self):
        """
        Saves all the pages and images
        :return:
        """
        logger.info('Saving thread %d export to %s' % (self.threadid, self.output_folder))

        existing_pages = glob.glob(os.path.join(self.output_folder, 'page_*.html'))
        if existing_pages:
            existing_pages.sort()
            old_last_page = existing_pages[-1]
            logger.info('Deleting %s from previous export as it has probably changed' % old_last_page)
            os.remove(old_last_page)

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            # Start the load operations and mark each future with its URL
            future_pages = {
                executor.submit(self.__save_page, page_number): page_number
                for page_number in range(1, self.total_pages + 1)
            }
            for future in concurrent.futures.as_completed(future_pages):
                page_number = future_pages[future]
                try:
                    data = future.result()
                except Exception as e:
                    logger.exception('Error saving page %d' % page_number, e)
                else:
                    if data['skipped']:
                        logger.info('Skipped page %d/%d because it already exists' % (page_number, self.total_pages))
                    else:
                        logger.info('Finished page %d/%d (%d new images, %d new stylseheets) in %d seconds'
                                    % (page_number, self.total_pages, data['downloaded_images_count'],
                                       data['downloaded_stylesheets_count'], data['execution_time_seconds']))
        logger.info('Finished exporting thread')

    def __save_page(self, page_number):
        """
        Saves a single page and images
        :param page_number:
        :return:
        """
        start = time.time()
        skipped = False
        downloaded_images_count = 0
        downloaded_stylesheets_count = 0

        output_filename = os.path.join(self.output_folder,
                                       self.PAGE_PATTERN_FILENAME % str(page_number).zfill(self.page_pad_zeros))
        if os.path.exists(output_filename):
            skipped = True
        else:
            with open(output_filename, 'w') as output_file:
                logger.info('Starting thread %d page %d/%d' % (self.threadid, page_number, self.total_pages))
                r = self.session.get(self.thread_url(page_number), timeout=self.timeout)
                page_soup = BeautifulSoup(r.text, 'html5lib')
                self.__insert_custom_styles(page_soup)
                self.__process_hyperlinks(page_soup)
                self.__add_charset(page_soup)
                self.__add_favicon(page_soup)
                self.__remove_fluff(page_soup)
                downloaded_images_count = self.__process_images(page_soup, page_number)
                downloaded_stylesheets_count = self.__process_stylesheets(page_soup)
                self.__process_paginators(page_soup, page_number)
                output_file.write(page_soup.prettify())

        end = time.time()
        return {
            'skipped': skipped,
            'downloaded_images_count': downloaded_images_count,
            'downloaded_stylesheets_count': downloaded_stylesheets_count,
            'execution_time_seconds': end - start
        }

    @staticmethod
    def __insert_custom_styles(soup):
        """
        Adds styles that are specific to this AwfulClient
        :param soup:
        :return:
        """
        soup.head.append(soup.new_tag('style', type='text/css'))
        soup.style.append('.bbc-spoiler:hover { background-color: inherit; }')

    @staticmethod
    def __process_hyperlinks(soup):
        """
        Add the base url to relative links
        :param soup:
        :return:
        """
        for elem in soup.findAll(href=True):
            if elem['href'].startswith('//'):
                elem['href'] = 'http:' + elem['href']
            if not elem['href'].startswith('#'):
                elem['href'] = urljoin(AwfulClient.FORUMS_URL, elem['href'])

    @staticmethod
    def __add_charset(soup):
        """
        Specify the charset so special characters appear correctly
        :param soup:
        :return:
        """
        encoding_tag = soup.new_tag('meta', charset='utf-8')
        soup.find('head').append(encoding_tag)

    def __add_favicon(self, soup):
        """
        Adds the html tag for the favicon
        :param soup:
        :return:
        """
        favicon_tag = soup.new_tag('link', rel='icon', href='images/favicon.ico')
        soup.find('head').append(favicon_tag)
        with self.opener.open('%s/favicon.ico' % AwfulClient.FORUMS_URL, timeout=self.timeout) as response, \
                open(os.path.join(self.images_folder, 'favicon.ico'), 'wb') as output_file:
            shutil.copyfileobj(response, output_file)

    @staticmethod
    def __remove_fluff(soup):
        """
        Remove all the extra stuff on the page we don't need
        :param soup:
        :return:
        """
        soup.find(id='loggedinusername').extract()
        soup.find(id='nav_purchase').extract()
        soup.find('link', rel='apple-touch-icon').extract()
        [tag.extract() for tag in soup.findAll('ul', class_='navigation')]
        [tag.extract() for tag in soup.findAll('div', class_='bottom_forms')]
        [tag.extract() for tag in soup.findAll('div', class_='threadrate')]
        [tag.extract() for tag in soup.findAll('img', class_='thread_bookmark')]
        [tag.extract() for tag in soup.findAll('script')]
        [tag.extract() for tag in soup.findAll('noscript')]
        # we want the postbuttons to still take up space in the layout, so just hide them
        for tag in soup.findAll('ul', class_='postbuttons'):
            tag['style'] = 'visibility: hidden'

    @staticmethod
    def __handle_waffleimages_replacement(img_src, threadid, page_number):
        if 'waffleimages' in img_src:
            # Switch these to the mirror which has some but not all of the waffleimages archive
            parsed_url = urlparse(img_src)
            path_parts = parsed_url.path.split('/')
            if len(path_parts) not in [3, 4]:
                logger.error('Unable to parse waffleimages image %s on page %d of thread %d during'
                             ' attempt update it to use randomwaffle.gbs.fm mirror' % (img_src, page_number, threadid))
                return img_src
            img_id = path_parts[1]
            img_filename_parts = os.path.basename(parsed_url.path).split('.')
            if len(img_filename_parts) != 2:
                logger.error('Unable to parse waffleimages image %s on page %d of thread %d during'
                             ' attempt update it to use randomwaffle.gbs.fm mirror' % (img_src, page_number, threadid))
                return img_src
            img_ext = img_filename_parts[1].lower()
            waffleimages_mirror_url = '%s://%s/images/%s/%s.%s'\
                                      % (parsed_url.scheme, 'randomwaffle.gbs.fm', img_id[:2], img_id, img_ext)
            logger.info('Successfully parsed waffleimages url %s and swapped with backup mirror'
                         ' %s on page %d of thread %d'
                        % (img_src, waffleimages_mirror_url, threadid, page_number))

            return waffleimages_mirror_url
        return img_src

    def __process_images(self, soup, page_number):
        """
        Download all the images on the page and change references to local copy.  If the local copy already exists,
        it will not be downloaded again.
        :param soup:
        :return:
        """
        downloaded_images_count = 0
        for img in soup.findAll('img'):
            # Attachments need the base url prepended
            if not img['src'].startswith('http'):
                img['src'] = urljoin(AwfulClient.FORUMS_URL, img['src'])
            img['src'] = self.__handle_waffleimages_replacement(img['src'], self.threadid, page_number)

            image_url = urlparse(img['src'])
            image_path = image_url.path if '%' in image_url.path else quote(image_url.path)  # avoid double encoding
            if image_url.path == '/attachment.php':
                if 'attachmentid' in image_url.query:
                    output_filename = 'attachment_%d' % int(parse.parse_qs(image_url.query)['attachmentid'][0])
                else:
                    output_filename = 'attachment_%d' % int(parse.parse_qs(image_url.query)['postid'][0])
            else:
                output_filename = os.path.basename(image_path)

            # Update the image source to reference the local copy
            img['src'] = 'images/%s' % output_filename

            output_filename = os.path.join(self.images_folder, output_filename)
            if not os.path.exists(output_filename):
                image_download_url = str.rstrip('%s://%s%s?%s' % (image_url.scheme, image_url.netloc,
                                                                  image_path, image_url.query), '?')
                try:
                    with open(output_filename, 'wb') as output_file:
                        with self.opener.open(image_download_url, timeout=self.timeout) as response:
                            shutil.copyfileobj(response, output_file)
                            downloaded_images_count += 1
                except URLError as e:
                    logger.warning('Error downloading image %s on page %d due to %s'
                                   % (image_download_url, page_number, e.reason))
                except Timeout:
                    logger.warning('Error downloading image %s on page %d because %d second timeout was reached'
                                   % (image_download_url, page_number, self.timeout))
                except RemoteDisconnected:
                    logger.warning('Error downloading image %s on page %d because the remote disconnected'
                                   % (image_download_url, page_number))

        # Links to external images should be downloaded too
        for anchor in soup.findAll('a', href=re.compile('\.(gif|png|jpeg|jpg)$')):
            anchor['href'] = self.__handle_waffleimages_replacement(anchor['href'], self.threadid, page_number)
            image_url = urlparse(anchor['href'])
            image_path = image_url.path if '%' in image_url.path else quote(image_url.path)  # avoid double encoding
            image_filename = os.path.basename(image_path)

            # Update the link to point to the local copy
            anchor['href'] = 'images/%s' % image_filename

            output_filename = os.path.join(self.images_folder, image_filename)
            if not os.path.exists(output_filename):
                image_download_url = str.rstrip('%s://%s%s?%s' % (image_url.scheme, image_url.netloc,
                                                                  image_path, image_url.query), '?')
                try:
                    with open(output_filename, 'wb') as output_file:
                        with self.opener.open(image_download_url, timeout=self.timeout) as response:
                            shutil.copyfileobj(response, output_file)
                            downloaded_images_count += 1
                except URLError as e:
                    logger.warning('Error downloading image %s on page %d due to %s'
                                   % (image_download_url, page_number, e.reason))
                except Timeout:
                    logger.warning('Error downloading image %s on page %d because %d second timeout was reached'
                                   % (image_download_url, page_number, self.timeout))
                except RemoteDisconnected:
                    logger.warning('Error downloading image %s on page %d because the remote disconnected'
                                   % (image_download_url, page_number))
        # Make sure quoted images are visible
        for timg_elem in soup.findAll('img', class_='timg'):
            timg_elem['style'] = 'visibility: visible'

        return downloaded_images_count

    def __process_stylesheets(self, soup):
        """
        Download all the stylesheets on the page and change references to local copy. If the local copy already exists,
        it will not be downloaded again.
        :param soup:
        :return:
        """
        downloaded_stylesheets_count = 0
        for link in soup.findAll('link', rel='stylesheet'):
            original_href = link['href']

            stylesheet_url = urlparse(original_href)
            stylesheet_filename = os.path.basename(stylesheet_url.path)

            link['href'] = 'css/%s' % stylesheet_filename

            output_filename = os.path.join(self.css_folder, stylesheet_filename)
            if not os.path.exists(output_filename):
                with open(output_filename, 'wb') as output_file:
                    with self.opener.open(original_href, timeout=self.timeout) as response:
                        shutil.copyfileobj(response, output_file)
                        downloaded_stylesheets_count += 1
        return downloaded_stylesheets_count

    def __process_paginators(self, soup, page_number):
        """
        Make the paginators point to local pages
        :param soup:
        :return:
        """
        for first_page_elem in soup.findAll('a', title='First page'):
            first_page_elem['href'] = self.PAGE_PATTERN_FILENAME % str(1).zfill(self.page_pad_zeros)
        for prev_page_elem in soup.findAll('a', title='Previous page'):
            prev_page_elem['href'] = self.PAGE_PATTERN_FILENAME % str(page_number - 1).zfill(self.page_pad_zeros)
        for next_page_elem in soup.findAll('a', title='Next page'):
            next_page_elem['href'] = self.PAGE_PATTERN_FILENAME % str(page_number + 1).zfill(self.page_pad_zeros)
        for last_page_elem in soup.findAll('a', title='Last page'):
            last_page_elem['href'] = self.PAGE_PATTERN_FILENAME % str(self.total_pages)

        # update the jump to page picklist to point to the local pages
        for pages_elem in soup.findAll('div', class_='pages'):
            page_select_elem = pages_elem.find('select')
            del (page_select_elem['data-url'])
            page_select_elem['onchange'] = 'window.location = "page_"+this.value+".html"'
            for option_elem in page_select_elem.findAll('option'):
                option_elem['value'] = str(option_elem['value']).zfill(self.page_pad_zeros)
