"""
MEDIACLI   

version:    0.1
date:       6 janvier 2021
autheur:    esandorfi@parleweb    

objet:      client terminal qui gère les fichiers sur disque

"""

import os, json, re
import requests
import click
import fsutil
from datetime import datetime

from mediacli.settings import VERSION, PROGRAM, AUDIO_EXTENSION
from mediacli.scan import Scan

ALL_SOURCE = "*"


@click.command()
@click.argument("source", default=ALL_SOURCE)
@click.option("--audio", is_flag=True, flag_value=True, help="find audio files")
@click.option("--video", is_flag=True, flag_value=False, help="find video files")
@click.option("--image", is_flag=True, flag_value=False, help="find images files")
def main(source, audio, video, image):
    print(f"Mediacli v{VERSION}")
    curdir = os.getcwd()

    if source == ALL_SOURCE:
        basepath = f"{curdir}"
    else:
        if source.find(":"):
            basepath = source
        else:
            basepath = f"{curdir}/{source}"

    try:
        with os.scandir(basepath) as entries:
            print(f"Analise de {basepath}...")
            for entry in entries:
                if entry.is_dir():
                    print(f"DIR {entry.name} and scan...")
                elif not entry.name.startswith(".") and entry.is_file():
                    print(f"{entry.name}")
    except FileNotFoundError:
        print(f"Accès impossible à {basepath}")

    # for dirnum, (dirpath, dirs, files) in enumerate(os.walk(basepath)):
    #     print(f"{dirnum} - {dirpath} {dirs} {files}")

    wbufferfilename = ".data.json"
    filter = []
    catfunc = None
    if audio:
        filter += AUDIO_EXTENSION
        wbufferfilename = ".audio.json"
        catfunc = audiofunc
    list_files(basepath, filter, catfunc=catfunc, wbufferfilename=wbufferfilename)


def audiofunc(f, ext):

    # scan for a number

    nb = re.findall(r"\d+", f)
    if nb:
        print(nb)
        return nb[0]
    return "*"


class DateTimeEncoder(json.JSONEncoder):
    """
    serialize une datetime pour le json.dump
    """

    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()

        return json.JSONEncoder.default(self, o)


def list_files(startpath, filter=None, catfunc=None, wbufferfilename=".data.json"):
    """
    liste tous les fichiers (sous-répertoires inclus) à partir de 'startpath'
    puis filtre suivant les extensions données par 'filter' - exemple ['jpg', 'png']
    puis classe les fichiers en fonction de catfunc (défault *)
    puis écrit un fichier json dans le répertoire scanné (wbufferfilename)
    """
    for root, dirs, files in os.walk(startpath):
        # remove hidden
        files = [f for f in files if not f[0] == "."]
        dirs[:] = [d for d in dirs if not d[0] == "."]
        # tree
        level = root.replace(startpath, "").count(os.sep)
        indent = " " * 1 * (level)
        output_string = "{}{}/".format(indent, os.path.basename(root))
        subindent = "  " * 1 * (level + 1)
        # init dict for json
        wbuffer = dict()
        wbuffer["_root"] = {
            "root": root,
            "startpath": root.replace(startpath, ""),
            "level": level,
        }
        # cosmetic print
        print(f"{output_string}    {root} {filter}")
        # scan files
        for f in files:
            path = f"{root}/{f}"
            ext = os.path.splitext(f)[1][1:]
            file_noext = os.path.splitext(f)[0]
            # skip if ext not in filter
            if filter and ext not in filter:
                continue
            # get file informations
            f_date = fsutil.get_file_creation_date(path)
            f_size = fsutil.get_file_size(path)
            f_hash = fsutil.get_file_hash(path)
            # get file category by function and write dict for json
            if catfunc:
                cat = catfunc(file_noext, ext)
            else:
                cat = "*"
            _tmp = {
                "file": f,
                "ext": ext,
                "date": f_date,
                "size": f_size,
                "hash": f_hash,
            }
            if cat in wbuffer:
                wbuffer[cat].append(_tmp)
            else:
                wbuffer[cat] = [_tmp]
            # cosmetic
            print(f"{subindent} {ext} > {f} > {f_date} > {f_size} bytes > {f_hash}")

        # write json
        wbuffer_file = f"{root}/{wbufferfilename}"
        with open(wbuffer_file, "w+", encoding="utf-8") as fp:
            json.dump(wbuffer, fp, cls=DateTimeEncoder)
            # cosmetic
            print(f"file {wbuffer_file} saved")


if __name__ == "__main__":
    main()
