import os
import unittest
import datetime
import shutil

from awfulutils.awfulclient import AwfulClient


class MyTestCase(unittest.TestCase):
    def setUp(self):
        self.awful_client = AwfulClient(os.environ['SOMETHINGAWFUL_USERID'], os.environ['SOMETHINGAWFUL_SESSION'])

    def test_fletcher_userinfo(self):
        userinfo = self.awful_client.userinfo(38563)
        self.assertEqual(userinfo.username, 'fletcher')
        self.assertEqual(userinfo.avatar, 'http://i.somethingawful.com/forumsystem/customtitles/title-fletcher.jpg')
        self.assertEqual(userinfo.title, 'ken park is my favorite movie')
        self.assertEqual(userinfo.icq_handle, 'not set')
        self.assertEqual(userinfo.aim_handle, 'cafe scholzen')
        self.assertEqual(userinfo.yahoo_handle, 'not set')

        self.assertEqual(userinfo.join_date, datetime.datetime(2003, 6, 26))
        self.assertGreaterEqual(userinfo.post_count, 6073)
        self.assertGreater(userinfo.posts_per_day, 0)
        self.assertGreaterEqual(userinfo.last_post, datetime.datetime(2014, 11, 6, hour=19, minute=23))
        self.assertEqual(userinfo.location, 'location')
        self.assertEqual(userinfo.interests, 'interests')
        self.assertEqual(userinfo.occupation, 'occupation')

    def test_negative_posts(self):
        userinfo = self.awful_client.userinfo(27691)
        self.assertLess(userinfo.post_count, 0)
        self.assertLess(userinfo.posts_per_day, 0)

    def test_export_thread(self):
        threadid = 3677640
        self.awful_client.export_thread(threadid)
        output_folder = 'somethingawful_thread_%d' % threadid
        self.assertTrue(os.path.exists(output_folder))
        shutil.rmtree(output_folder)


if __name__ == '__main__':
    unittest.main()
