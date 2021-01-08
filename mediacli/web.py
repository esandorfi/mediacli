import os
import logging


from mediacli.utils import plw_get_url, plw_urlify

logger = logging.getLogger("mediacli")


class Web(object):
    def __init__(self, FireFox=False):
        self.browser = None
        if FireFox:
            from selenium import webdriver

            self.browser = webdriver.Firefox()

    def __del__(self):
        if self.browser:
            self.browser.close()

    def screenshot(self, server, url, dirtosave, dir_th_url):
        if self.browser:
            self.browser.get(server + url)
            imgname = plw_urlify(url)
            imgname += ".png"
            urlimgname = (dir_th_url + imgname).replace("\\", "/")
            fullimgname = dirtosave + imgname
            if dirtosave != "" and os.path.exists(dirtosave) == False:
                os.makedirs(dirtosave, 0o777)

            self.browser.save_screenshot(fullimgname)
            logger.info(
                "save screenshot to fullimgname " + fullimgname + " url " + urlimgname
            )
        else:
            urlimgname = server + url

        return urlimgname