# IMPORT
import sys
import os
import datetime, time
import logging

from jinja2 import (
    Environment,
    PackageLoader,
    select_autoescape,
    FileSystemLoader,
    TemplateNotFound,
    TemplateSyntaxError,
    UndefinedError,
)
import markdown2
import json
import csv

# from pprint import pprint

logger = logging.getLogger("mediacli")

from mediacli.utils import plw_get_url, StringMetadata


JSONDIR_URLLIST = 2
JSONDIR_ZENQUERY = 1
JSONDIR_TOCLIST = 0


"""
class StringMetadata(str):
    metadata = None
"""

#
# Generate Index files
#
class Scan(object):
    def __init__(self, outpath="", sourcepath="", buildmap="buildmap"):
        self.static_idx_path = outpath

        self.routeidx = {}
        self.routeidxname = ""
        self.routeisopen = False
        self.buildmap = buildmap

        # set by scanoption()
        self.static_path = ""  # where html is generated
        self.screenshot_static_path = ""  # where screenshot images are generated
        self.screenshot_url = ""  # where screenshot images are generated as url

        self.static_url = ""  # which server is used to load web pages
        self.source_path = sourcepath.lower()  # what is the drive path

        # set by activeurl()
        self.active_url = ""  # current url managed by PlwData

        # extension
        self.extload = {
            ".md": self.ext_md,
            ".csv": self.ext_csv,
            ".jpg": self.ext_img,
            ".png": self.ext_img,
            ".avi": self.ext_video,
            ".mp4": self.ext_video,
            ".htm": self.ext_html,
            ".html": self.ext_html,
            ".odt": self.ext_file,
            ".ods": self.ext_file,
            ".indd": self.ext_file,
            ".pdf": self.ext_file,
            ".doc": self.ext_file,
            ".xls": self.ext_file,
            ".docx": self.ext_file,
            ".xlsx": self.ext_file,
        }

        # use web selenium for screenshot
        self.useweb = 0

    def __del__(self):
        if self.useweb == 1:
            del self.web

    def openidx(self, name=""):
        if self.routeisopen == True:
            # logger.info("SCAN is opened - skip or need to close first")
            return False
        self.routeisopen = True
        if name == "":
            name = self.buildmap
        self.routeidxname = name
        logger.debug("IDX OPEN for " + name)
        return True

    def closeidx(self):
        if self.routeisopen == False:
            # logger.info("SCAN not opened - skip")
            return False

        fout = self.static_idx_path + self.buildmap + ".json"
        try:
            myFile = open(fout, "w", encoding="utf-8")
        except FileNotFoundError as e:
            getdir = os.path.dirname(fout)
            logger.info("create directory " + getdir + " from " + fout)
            try:
                os.makedirs(getdir, 0o777)
                try:
                    myFile = open(fout, "w", encoding="utf-8")
                except FileNotFoundError as e:
                    logger.critical("impossible to use file " + fout)
                    return False
            except:
                raise
            #
            # more error check to add
            #
        try:
            json.dump(self.routeidx, myFile, indent=4)
        except ValueError as e:
            logger.critical("ERROR in json generation " + str(e))
        myFile.close()
        myFileinfo = os.stat(fout)
        logger.info(
            "WRITE > %s : %d bytes (%d items)"
            % (fout, myFileinfo.st_size, len(self.routeidx))
        )
        # logger.debug(data)
        self.routeisopen = False
        return True

    def addidx(self, data):
        """
        add url to scanmap
        """
        if self.routeisopen == False:
            logger.info("SCAN not opened - skip")
            return False
        if "url" not in data:
            import pdb

            pdb.set_trace()

        info = {}
        url = data["url"]
        # print(data)
        # print(type(data))

        info["url"] = data["url"]
        try:
            info["pagetitle"] = data["pagetitle"]
        except:
            pass

        try:
            info["pagedescription"] = data["pagedescription"]
        except:
            pass

        try:
            info["zengabarit"] = data["zengabarit"]
        except:
            pass

        try:
            info["source"] = data["source"]
            info["source"].replace(self.source_path, "")
        except:
            pass

        try:
            info["json"] = data["json"].replace(self.static_idx_path, "").lower()
            info["json"] = info["json"].replace(self.static_path, "")
        except:
            pass

        if "type" in data:
            info["type"] = data["type"]
            type = data["type"]

            if type == "zenquery" or type == "zenscan":
                url = url.replace(".json", "")
        else:
            type = "url"
            info["type"] = type
            url = url.replace(self.static_url, "").replace(".html", "")

            """
            slug = url.split('/')
            if( len(slug) > 0 )
                info['slug']
            """

        if type not in self.routeidx:
            self.routeidx[type] = {}
        self.routeidx[type][url] = info
        logger.debug(
            "SCAN ADD IDX " + type + " ==> " + info["url"] + " -- " + self.static_path
        )

        return True

    def scan(
        self, sourcedir, scanfor="", soption="@none", jsonfile="idx.json", isQuery=0
    ):
        """
        start scan
        """
        # if sourcedir[-1:] == '\\':
        #    sourcedir = sourcedir[:-1]
        # import pdb; pdb.set_trace()

        # scan option :
        #    @none
        #    @files
        #    @screenshot
        #    @from=relative path to add to source dir
        #

        scanoption = soption.lower()
        if sourcedir == "":
            sourcedir = self.source_path
        logger.debug(
            "%s source %s for %s (option %s)"
            % (
                "ZENSCAN" if isQuery == 0 else "ZENQUERY",
                sourcedir,
                scanfor,
                scanoption,
            )
        )
        isScanOnlyfiles = scanoption.find("@files")
        isScreenshot = scanoption.find("@screenshot")
        if isScreenshot == 0:
            logger.info("ZENSCAN open selenium Firefox.. takes a little time...")
            try:
                self.web = None  # PlwWeb()
                self.useweb = 1
            except Exception as e:
                logger.critical("Selenium Firefox can not be set up " + str(e))
                logger.critical("No screenshot generated")
                self.useweb = 0
        nbgeneration = -1
        if scanoption.find("@fromsourcepath") == 0:
            if scanoption.find("@fromsourcepath=") == 0:
                sourcedir = self.source_path + scanoption[16:]
            else:
                sourcedir = self.source_path
            logger.debug("change sourcedir for scan to " + sourcedir)
        elif scanoption.find("@fromabsolutepath=") == 0:
            sourcedir = scanoption[18:]
            logger.debug("change sourcedir for scan to " + sourcedir)

        try:
            for dirnum, (dirpath, dirs, files) in enumerate(os.walk(sourcedir)):
                logger.debug("scan find directory : %s", dirpath)

                nbgeneration = dirpath.count("\\")

                # root
                if dirnum == 0:
                    self.idxroot = dirpath.lower()
                    self.idxgeneration = nbgeneration
                    self.generation = 0
                    self.parent = 0
                    self.idx = self.idxroot.split(self.source_path)[-1]
                    self.scanid = []
                    self.scanid.append(1)  # check if ok
                    self.lenidbefore = 0
                    self.countid = 1
                    self.tochtml = []
                    self.toclist = {}
                    self.urllist = {}
                    if len(self.idx) > 0 and self.idx[-1] == "\\":
                        self.breadcrump = [self.idx[-1]]
                    else:
                        self.breadcrump = [self.idx]
                else:
                    """
                    scanid and countid manage order position
                    parent and child numerotation into list scanid as [1, 1, 2, 1...]
                    """
                    if self.parent != nbgeneration:
                        if nbgeneration < self.parent:
                            # previous generation
                            idtoremove = self.parent - nbgeneration
                            del self.scanid[-idtoremove:]
                            # logger.debug('breadcrump len '+str(len(self.breadcrump)))
                            idtoremove += 1
                            del self.breadcrump[-idtoremove:]
                            # logger.debug('breadcrump len '+str(len(self.breadcrump)))
                            # logger.debug("previous generation nb to remove "+str(idtoremove))
                            self.countid = self.scanid[-1] + 1
                            self.scanid[-1] = self.countid
                        else:
                            # new generation
                            self.countid = 1
                            self.scanid.append(self.countid)
                        self.parent = nbgeneration
                    else:
                        self.countid += 1
                        if len(self.scanid) > 1:
                            self.scanid[-1] = self.countid
                        else:
                            self.scanid.append(self.countid)
                        del self.breadcrump[-1:]

                    self.generation = nbgeneration
                    self.idx = dirpath.split(self.idxroot + "\\")[-1].split("\\")[-1]
                    # check for -
                    sep = self.idx.find("-")
                    if sep != -1:
                        # logger.info('sep is find : as '+self.idx[:sep])
                        if self.idx[:sep].isnumeric() is True:
                            sep = sep + 1
                            self.idx = self.idx[sep:]
                            # logger.info('is numeric now :' +self.idx)

                    self.curdirnum = dirnum
                    self.breadcrump.append(self.idx)
                    logger.debug(
                        "add breadcrump "
                        + self.idx
                        + " len "
                        + str(len(self.breadcrump))
                        + " breadcrump "
                        + ">".join(self.breadcrump)
                    )

                # add to scan memory the directory
                if len(files) == 0:
                    isEmpty = True
                    # import pdb; pdb.set_trace()
                    self.lenidbefore = len("".join(map(str, self.scanid)))
                    tocid = ".".join(map(str, self.scanid))
                    logger.debug("SCAN " + tocid + " FOR " + scanfor)
                    i = 1
                    self.emptyfile(tocid, i)
                else:
                    isEmpty = False
                    self.scandir(dirpath, dirs, files)
                    # just pure number without .
                    self.lenidbefore = len("".join(map(str, self.scanid)))
                    if scanfor != "":
                        tocid = ".".join(map(str, self.scanid))
                        logger.debug("SCAN " + tocid + " FOR " + scanfor)
                        i = 1
                        self.toclist[tocid]["scan"] = {}
                        for filename in files:

                            multiplescanfor = tuple(scanfor.lower().split("|"))
                            if filename.endswith(multiplescanfor):

                                # if filename.rfind(scanfor) != -1:
                                if i > 1:
                                    logger.debug(
                                        "SCAN ADD " + tocid + " FOR " + scanfor
                                    )
                                ok = self.scanfile(
                                    tocid,
                                    scanfor,
                                    dirpath,
                                    filename,
                                    -1 if isQuery == 1 else i,
                                )
                                if ok == True:
                                    i += 1
                                elif ok == 2:
                                    logger.debug("skip option for : " + filename)
                                else:
                                    logger.critical("error walking file : " + filename)
                                    logger.info("skip it ")

                if isEmpty == False:
                    self.toclist[tocid]["breadcrump"] = list(self.breadcrump)
                    self.toclist[tocid]["scanlen"] = len(self.toclist[tocid]["scan"])
                    if isScanOnlyfiles != -1:
                        logger.debug("scan only files - option set with @files")
                        break
                else:
                    self.toclist[tocid]["scanlen"] = 0

        # except ValueError as e:
        except Exception as e:
            logger.critical("error walking dir : " + sourcedir + " " + str(e))
            if self.useweb:
                self.useweb = 0
                del self.web
            return ""
        if nbgeneration == -1:
            logger.critical("find nothing in dir " + sourcedir)
            return ""

        # make deep to close and open <ul> analyse
        lastdeep = 1
        for keyid, data in reversed(sorted(self.toclist.items())):
            closelevel = data["deepbefore"] - data["deep"]
            if closelevel < 0:
                closelevel = 0
            if data["deep"] > data["deepbefore"]:
                openlevel = 1
            if lastdeep > data["deep"]:
                openlevel = 1
            else:
                openlevel = 0
            if data["deep"] == lastdeep:
                samelevel = 1
            else:
                samelevel = 0
            logger.debug(
                "deep %d before %d lastdeep %d close %d open %d same %d - %s"
                % (
                    data["deep"],
                    data["deepbefore"],
                    lastdeep,
                    closelevel,
                    openlevel,
                    samelevel,
                    keyid,
                )
            )
            data["deepopen"] = openlevel
            data["deepclose"] = closelevel
            data["deepsame"] = samelevel
            lastdeep = data["deep"]

        # write json
        # self.htmldir()
        if jsonfile.find(".json") == -1:
            jsonfile += ".json"

        # logger.info('JSONDIR')
        self.jsondir(jsonfile, isQuery)

        # urljsonfile = jsonfile + '.url'
        # self.jsondir(urljsonfile, JSONDIR_URLLIST)

        return jsonfile

    def htmldir(self):
        logger.debug("HTML")
        logger.debug(self.tochtml)

    def jsondir(self, fout, isQuery=0):
        logger.debug("JSON with " + fout)
        if isQuery == JSONDIR_ZENQUERY:  # from zenquery
            data = self.toclist["1"]["scan"]
        # elif( isQuery == JSONDIR_URLLIST ):
        #    data = self.urllist
        else:
            data = self.toclist

        # if len(self.urllist):
        #    data['source'] = self.urllist

        try:
            myFile = open(fout, "w", encoding="utf-8")
        except FileNotFoundError as e:
            getdir = os.path.dirname(fout)
            logger.info("create directory " + getdir + " from " + fout)
            try:
                os.makedirs(getdir, 0o777)
                try:
                    myFile = open(fout, "w", encoding="utf-8")
                except FileNotFoundError as e:
                    logger.critical("impossible to use file " + fout)
                    return False
            except:
                raise
            #
            # more error check to add
            #
        try:
            json.dump(data, myFile, indent=4)
        except ValueError as e:
            logger.critical("ERROR in json generation " + str(e))
        myFile.close()
        myFileinfo = os.stat(fout)
        logger.info("WRITE > %s : %d bytes" % (fout, myFileinfo.st_size))
        # logger.debug(data)

        info = {
            "url": os.path.split(fout)[1],
            "type": "zenscan" if isQuery == 0 else "zenquery",
            "json": fout,
        }
        self.addidx(info)
        return True

    def scandir(self, dirpath, dirs, files):
        nbdirs = len(dirs)
        nbfiles = len(files)
        scanid = ".".join(map(str, self.scanid))

        sep = self.idx.find("-")
        if sep != -1:
            # logger.info('sep is find : as '+self.idx[:sep])
            if self.idx[:sep].isnumeric() is True:
                sep = sep + 1
                self.idx = self.idx[sep:]
                # logger.info('is numeric now :' +self.idx)

        logger.info("   ===> " + scanid + ", " + self.idx)
        info = {}
        if len(self.idx) > 0:
            if self.idx[-1] == "\\":
                info["folder"] = self.idx[:-1]
            else:
                info["folder"] = self.idx
        else:
            info["folder"] = "/"

        info["scanid"] = str(self.scanid)
        info["order"] = self.countid
        info["nbfiles"] = nbfiles

        # manage deep as
        # <li>
        #    <ul><li>
        #        <ul><li>
        info["deep"] = len(self.scanid)
        # deep previous element
        info["deepbefore"] = self.lenidbefore
        # deep need to close </li></ul> will be managed after everybody is filled
        # for moment, just say no
        logger.debug(info)
        self.toclist[scanid] = info
        # self.toclist[scanid] = ( self.idx, nbfiles, 'url to add' )
        logger.debug(
            "IDX %s %s%s"
            % (
                str(self.scanid),
                self.idx,
                " (" + str(nbfiles) + ")" if nbfiles > 0 else "",
            )
        )
        self.tochtml.append(
            "%s %s%s"
            % (
                str(self.scanid),
                self.idx,
                " (" + str(nbfiles) + ")" if nbfiles > 0 else "",
            )
        )
        # return scanid

    def ext_md(self, fname):
        logger.debug("load markdown file (ext_md)")
        html = markdown2.markdown_path(
            fname, extras=["metadata", "markdown-in-html", "tables"]
        )
        if "skip" in html.metadata.keys() and html.metadata["skip"] == "1":
            html = "skip"
        return html

    def ext_img(self, fname):
        logger.debug("load image file")
        html = StringMetadata(fname)
        html.metadata = {"filetype": "image"}
        return html

    def ext_csv(self, fname):
        logger.debug("load csv file " + fname)

        msgerror = ""
        noError = True
        datafile = fname

        htmlcontent = fname.replace(self.source_path, "")
        logger.debug("htmlcontent " + htmlcontent)
        html = StringMetadata(htmlcontent)
        """
        if not os.path.exists(datafile):
            if( self.source_pathdata != '' ):
                if( self.source_pathdata[-1] != '\\' ):
                    datafile = self.source_pathdata+'\\'+fdata
                else:
                    datafile = self.source_pathdata+fdata
            if not os.path.exists(datafile):
                datafile = self.static_path+fdata
                if not os.path.exists(datafile):
                    datafile = self.idxjson_path+fdata
                    if not os.path.exists(datafile):
                        logger.critical("skip csv file %s - doesn't exist in %s or in %s or in %s" %(fdata, self.source_pathdata, self.static_path, self.idxjson_path))
                        return False
        """
        logger.debug("load csv file " + datafile)
        fcsv = open(datafile, "r", encoding="utf-8")
        try:
            check_csvdelimiter = fcsv.readline()
            logger.debug("csv header : " + check_csvdelimiter)
            if check_csvdelimiter.find(",") > -1:
                csvsep = ","
            else:
                csvsep = ";"
            logger.debug("csv delimiter is " + csvsep)
            fcsv.seek(0, 0)

            reader = csv.DictReader(fcsv, delimiter=csvsep)
        except ValueError as e:
            msgerror = "CSV ERROR " + str(e)
            logger.critical(msgerror)
            noError = False

        tmplist = []
        if noError:
            try:
                key = "-".join(reader.fieldnames)
                for each in reader:
                    tmplist.append(each)
            except UnicodeDecodeError as e:
                msgerror = "CSV DECODE ERROR " + str(e)
                logger.critical(msgerror)
                noError = False

            except:
                msgerror = "CSV READ FORMAT ERROR "
                logger.critical(msgerror)
                noError = False

        if noError:
            html.metadata = {"filetype": "csv", "fieldnames": key, "data": tmplist}
        else:
            html.metadata = {"filetype": "csv", "errorfile": fname, "error": msgerror}
        return html

    def ext_html(self, fname):
        logger.debug("load html file")
        html = StringMetadata(fname)
        html.metadata = {"filetype": "html"}
        # import pdb; pdb.set_trace()
        if self.useweb == 1:
            if fname.find(self.source_path) != -1:
                logger.debug("screenshot " + fname + " " + self.source_path)
                fname = fname[len(self.source_path) :]
                logger.debug(" screenshot filename now just is " + fname)

            logger.info(
                "screenshot %s %s %s %s"
                % (
                    self.static_url,
                    fname,
                    self.screenshot_static_path,
                    self.screenshot_url,
                )
            )
            screenshot = self.web.screenshot(
                self.static_url, fname, self.screenshot_static_path, self.screenshot_url
            )
            html.metadata["screenshot"] = self.static_url + screenshot

        return html

    def ext_file(self, fname):
        html = StringMetadata(fname)
        finfo = os.stat(fname)
        html.metadata = {
            "filetype": "file",
            "filename": fname,
            "filesize": finfo.st_size,
            "filemodified": finfo.st_mtime,
        }

        return html

    def ext_video(self, fname):
        logger.debug("load video file")
        html = StringMetadata(fname)
        html.metadata = {"filetype": "video"}
        return html

    def emptyfile(self, tocid, i):
        html = StringMetadata("empty")
        html.metadata = {"filetype": "empty"}
        html.metadata["url"] = "empty"
        info = {}
        info["folder"] = self.idx
        info["nbfiles"] = 0
        info["deep"] = len(self.scanid)
        info["deepbefore"] = self.lenidbefore
        self.toclist[tocid] = info
        self.toclist[tocid]["scan"] = {}
        self.toclist[tocid]["scan"][i] = {}
        self.toclist[tocid]["scan"][i] = html.metadata
        return False

    def scanfile(self, tocid, scanfor, dirpath, filename, i):
        fname = os.path.join(dirpath, filename).lower()
        fnamext = os.path.splitext(fname)[1]
        # import pdb; pdb.set_trace()
        multiplescanfor = tuple(scanfor.lower().split("|"))
        if fname.endswith(multiplescanfor):
            try:
                statinfo = os.stat(fname)
                logger.debug(" file: " + fname + " size: " + str(statinfo.st_size))
                # info = self.toclist[tocid]
                # info = {'file':fname}
                # info['file'] = fname
                # info['filesize'] = statinfo.st_size

                # select from extension witch function to load
                loadfunc = self.extload.get(fnamext, lambda fname: None)
                html = loadfunc(fname)
                if not html:
                    logger.critical(
                        "do not know what to do with : "
                        + fnamext
                        + " file from scan :"
                        + fname
                    )
                    logger.critical(
                        "extension not found in parladata definition, skip as a warning"
                    )
                    return True
                elif html == "skip":
                    logger.debug("file marked as skip: 1 - nothing to do")
                    return 2  # CONST NEED TO BE DEFINED

                logger.debug("load " + fnamext + " file from scan " + fname)
                url = plw_get_url(
                    fname, self.static_path, self.static_url, self.source_path
                )
                logger.debug("url %s fname %s file %s" % (url[0], url[2], url[1]))
                html.metadata["url"] = url[0]
                html.metadata["fname"] = url[2]
                html.metadata["content"] = html
                # html.metadata['scanfile'] = fname
                html.metadata["contentsize"] = statinfo.st_size
                html.metadata["contentdate"] = datetime.datetime.fromtimestamp(
                    statinfo.st_mtime
                ).strftime("%Y-%m-%d %H:%M:%S")
                # time.ctime(statinfo.st_mtime)

                # is zenquery
                if i == -1:
                    i = url[2]

                logger.debug("active url %s and %s" % (self.active_url, url[0]))
                if self.active_url != "" and self.active_url == url[0]:
                    logger.debug("not include file as active url : " + self.active_url)
                else:
                    self.toclist[tocid]["scan"][i] = {}
                    self.toclist[tocid]["scan"][i] = html.metadata

                self.urllist[fname] = tocid
            except ValueError as e:
                logger.critical("Error as " + str(e))
                return False
            except:
                raise
            return True
        else:
            return False

    # SCANOPTION
    #    set path for plw_get_url
    def scanoption(
        self,
        static_path,
        static_url,
        source_path,
        screenshot_static_path="",
        screenshot_url="",
        static_idx_path="",
    ):

        logger.debug("scanoption")
        logger.debug("static_path " + static_path)
        logger.debug("static_url " + static_url)
        logger.debug("source_path " + source_path)
        logger.debug("screenshot_static_path " + screenshot_static_path)
        logger.debug("screenshot_url " + screenshot_static_path)
        logger.debug("static_idx_path " + static_idx_path)

        # import pdb; pdb.set_trace()

        if static_idx_path != "":
            self.static_idx_path = static_idx_path

        if static_path != "":
            self.static_path = static_path.lower()

        if screenshot_url != "":
            self.screenshot_url = screenshot_url.lower()

        if screenshot_static_path != "":
            self.screenshot_static_path = screenshot_static_path.lower()
        else:
            self.screenshot_static_path = static_path.lower()
        if self.screenshot_static_path[-1] != "\\":
            self.screenshot_static_path += "\\"

        if static_url != "":
            self.static_url = static_url.lower()
        if source_path != "":
            self.source_path = source_path.lower()

        logger.debug("scanoption")
        logger.debug("static_path " + self.static_path)
        logger.debug("static_url " + self.static_url)
        logger.debug("source_path " + self.source_path)
        logger.debug("screenshot_static_path " + self.screenshot_static_path)
        logger.debug("screenshot_url " + self.screenshot_url)
        logger.debug("static_idx_path " + self.static_idx_path)

    # INITLOAD
    #    loadconfig
    def initload(self, config):
        self.static_idx_path = config["build"]["static_idx_path"]
        self.static_path = config["build"]["static_path"].lower()
        if "screenshot_url" in config["build"]:
            self.screenshot_url = config["build"]["screenshot_url"].lower()
            self.screenshot_static_path = config["build"][
                "screenshot_static_path"
            ].lower()
            if self.screenshot_static_path[-1] != "\\":
                self.screenshot_static_path += "\\"

        try:
            self.static_url = config["framework"]["static_url"].lower()
        except:
            self.static_url = config["build"]["static_url"].lower()

        self.source_path = config["build"]["source_path"].lower()

        logger.debug("scanoption")
        logger.debug("static_path " + self.static_path)
        logger.debug("static_url " + self.static_url)
        logger.debug("source_path " + self.source_path)
        logger.debug("screenshot_static_path " + self.screenshot_static_path)
        logger.debug("screenshot_url " + self.screenshot_url)
        logger.debug("static_idx_path " + self.static_idx_path)

    # ACTIVE URL
    #    set active url (for not include in scan)
    def activeurl(self, url):
        self.active_url = url
