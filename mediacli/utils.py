import re
import os
import logging
import unicodedata
import logging

logger = logging.getLogger("mediacli")


class StringMetadata(str):
    metadata = None


def strip_accents(text):
    try:
        text = unicode(text, "utf-8")
    except NameError:  # unicode is a default on python 3
        pass
    text = unicodedata.normalize("NFD", text)
    text = text.encode("ascii", "ignore")
    text = text.decode("utf-8")
    return str(text)


def plw_urlify(s):
    s = re.sub(r"[^\w]", "-", s)
    # Replace all runs of whitespace with a single dash
    # s = re.sub(r"\s+", '-', s)
    return s


def plw_get_url(sourcefile, static_path="", static_url="", source_path=""):
    # import pdb; pdb.set_trace()
    logger.debug(
        "### geturl source file %s path %s, static url %s path %s"
        % (sourcefile, source_path, static_url, static_path)
    )

    sourcefile = sourcefile.lower()

    p, f = os.path.split(sourcefile)
    logger.debug("split p " + p + " f " + f)

    # check if sourcefile has order
    lenspace = f.find(" ")
    if lenspace != -1 and lenspace < 4:
        order = f[:lenspace]
        f = f[lenspace + 1 :]
        logger.debug("order is [" + order + "], file : " + f)

    # logger.info("p " +p +" f "+f +" s "+sourcefile)

    # return url with path convention
    if f.find(".") != -1:
        fe = f.split(".")
        if fe[1].lower() == "csv":
            furl = fe[0]
        else:
            furl = fe[0] + ".html"

    else:
        furl = f

    sourcefile = p + "\\" if p != "" else ""
    filename = sourcefile + furl

    """
	# remove extension
	if sourcefile.find('.') != -1:
		if sourcefile.find('.md') != -1:
			filename = sourcefile.split('.')[0]+'.html'
			logger.debug("find md")
		else:
			filename = sourcefile
	else:
		filename = sourcefile+'.html'
	"""

    filename = strip_accents(filename)
    logger.debug("url filename is " + filename)

    # remove source_path if any
    if source_path != "":
        source_path = source_path.lower()
        n = filename.find(source_path)
        # logger.info('n '+str(n)+' source '+source_path)
        if n == 0:
            filename = filename[len(source_path) :]
    ## has to check
    if os.path.exists(filename):
        fullfilename = re.sub(r"[^\w\\\\:.]", "-", filename)
    else:
        fullfilename = static_path + re.sub(r"[^\w\\\\:.]", "-", filename)

    # fullfilename = re.sub(r"[^\w\\\\:.]", '-', fullfilename)
    # logger.debug("static file: "+fullfilename)

    path = os.path.dirname(fullfilename)
    if not os.path.exists(path):
        logger.debug("path does not exist : " + path)
    # else:
    # 	logger.info("PATH IS "+path)

    # check if index
    if sourcefile.find("index"):
        filename = filename.split("index")[0]

    if filename.find(source_path) != -1:
        logger.info(filename + " " + source_path + " len " + str(len(source_path)))
        filename = filename[len(source_path) :]
        logger.info(" filename now just is " + filename)

    urldir = ""
    if len(sourcefile) > 0:
        urldir = sourcefile.replace(source_path, "")
        urldir = re.sub(r"[^\w\\\\:.]", "-", urldir)
        urldir = urldir.replace("\\", "/")
        urldir = strip_accents(urldir)

    filename = re.sub(r"[^\w\\\\:.]", "-", filename)
    url = (static_url + filename).replace("\\", "/")

    logger.debug("url: " + url)
    # import pdb; pdb.set_trace()
    return [url, fullfilename, furl, urldir]
