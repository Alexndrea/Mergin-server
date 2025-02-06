# Copyright (C) Lutra Consulting Limited
#
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-MerginMaps-Commercial

import math
import os
import hashlib
import re
import secrets
from threading import Timer
from uuid import UUID
from shapely import wkb
from shapely.errors import ShapelyError
from gevent import sleep
from flask import Request
from typing import Optional
from sqlalchemy import text
from pathvalidate import validate_filename, ValidationError
import magic


def generate_checksum(file, chunk_size=4096):
    """
    Generate checksum for file from chunks.

    :param file: file to calculate checksum
    :param chunk_size: size of chunk
    :return: sha1 checksum
    """
    checksum = hashlib.sha1()
    with open(file, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            sleep(0)  # to unblock greenlet
            if not chunk:
                return checksum.hexdigest()
            checksum.update(chunk)


class Toucher:
    """
    Helper class to periodically update modification time of file during
    execution of longer lasting task.

    Example of usage:
    -----------------
    with Toucher(file, interval):
        do_something_slow

    """

    def __init__(self, lockfile, interval):
        self.lockfile = lockfile
        self.interval = interval
        self.running = False
        self.timer = None

    def __enter__(self):
        self.acquire()

    def __exit__(self, type, value, tb):  # pylint: disable=W0612,W0622
        self.release()

    def release(self):
        self.running = False
        if self.timer:
            self.timer.cancel()
            self.timer = None

    def acquire(self):
        self.running = True
        self.touch_lockfile()

    def touch_lockfile(self):
        # do an NFS ACCESS procedure request to clear the attribute cache (for various pods to actually see the file)
        # https://docs.aws.amazon.com/efs/latest/ug/troubleshooting-efs-general.html#custom-nfs-settings-write-delays
        os.access(self.lockfile, os.W_OK)
        with open(self.lockfile, "a"):
            os.utime(self.lockfile, None)
        if self.running:
            self.timer = Timer(self.interval, self.touch_lockfile)
            self.timer.start()


def is_qgis(path: str) -> bool:
    """
    Check if file is a QGIS project file.
    """
    _, ext = os.path.splitext(path)
    return ext.lower() in [".qgs", ".qgz"]


def int_version(version):
    """Convert v<n> format of version to integer representation."""
    return int(version.lstrip("v")) if re.match(r"v\d", version) else None


def is_versioned_file(file):
    """Check if file is compatible with geodiff lib and hence suitable for versioning."""
    diff_extensions = [".gpkg", ".sqlite"]
    f_extension = os.path.splitext(file)[1]
    return f_extension.lower() in diff_extensions


def is_file_name_blacklisted(path, blacklist):
    blacklisted_dirs = get_blacklisted_dirs(blacklist)
    blacklisted_files = get_blacklisted_files(blacklist)
    if blacklisted_dirs:
        regexp_dirs = re.compile(
            r"({})".format(
                "|".join(".*" + re.escape(x) + ".*" for x in blacklisted_dirs)
            )
        )
        if regexp_dirs.search(os.path.dirname(path)):
            return True
    if blacklisted_files:
        regexp_files = re.compile(
            r"({})".format(
                "|".join(".*" + re.escape(x) + ".*" for x in blacklisted_files)
            )
        )
        if regexp_files.search(os.path.basename(path)):
            return True

    return False


def get_blacklisted_dirs(blacklist):
    return [p.replace("/", "") for p in blacklist if p.endswith("/")]


def get_blacklisted_files(blacklist):
    return [p for p in blacklist if not p.endswith("/")]


def get_user_agent(request):
    """Return user agent from request headers

    In case of browser client a parsed version from werkzeug utils is returned else raw value of header.
    """
    if request.user_agent.browser and request.user_agent.platform:
        client = request.user_agent.browser.capitalize()
        version = request.user_agent.version
        system = request.user_agent.platform.capitalize()
        return f"{client}/{version} ({system})"
    else:
        return request.user_agent.string


def get_ip(request):
    """Returns request's IP address based on X_FORWARDED_FOR header
    from proxy webserver (which should always be the case)
    """
    forwarded_ips = request.environ.get(
        "HTTP_X_FORWARDED_FOR", request.environ.get("REMOTE_ADDR", "untrackable")
    )
    # seems like we get list of IP addresses from AWS infra (beginning with external IP address of client, followed by some internal IP)
    ip = forwarded_ips.split(",")[0]
    return ip


def generate_location():
    """Return random location where project is saved on disk

    Example:
        >>> generate_location()
        '1c/624c6af4d6d2710bbfe1c128e8ca267b'
    """
    return os.path.join(secrets.token_hex(1), secrets.token_hex(16))


def is_valid_uuid(uuid):
    """Check object can be parse as valid UUID"""
    try:
        UUID(uuid)
        return True
    except (ValueError, AttributeError):
        return False


# inspired by C++ implementation https://github.com/lutraconsulting/geodiff/blob/master/geodiff/src/drivers/sqliteutils.cpp
# in geodiff lib (MIT licence)
def parse_gpkgb_header_size(gpkg_wkb):
    """Parse header of geopackage wkb and return its size"""
    # some constants
    no_envelope_header_size = 8
    flag_byte_pos = 3
    envelope_size_mask = 14

    try:
        flag_byte = gpkg_wkb[flag_byte_pos]
    except IndexError:
        return -1  # probably some invalid input
    envelope_byte = (flag_byte & envelope_size_mask) >> 1
    envelope_size = 0

    if envelope_byte == 1:
        envelope_size = 32
    elif envelope_byte == 2:
        envelope_size = 48
    elif envelope_byte == 3:
        envelope_size = 48
    elif envelope_byte == 4:
        envelope_size = 64

    return no_envelope_header_size + envelope_size


def gpkg_wkb_to_wkt(gpkg_wkb):
    """Convert WKB (with gpkg header) to WKT"""
    wkb_header_length = parse_gpkgb_header_size(gpkg_wkb)
    wkb_geom = gpkg_wkb[wkb_header_length:]
    try:
        wkt = wkb.loads(wkb_geom).wkt
    except ShapelyError:
        wkt = None
    return wkt


def get_byte_string(size_bytes):
    """Return string of size_bytes in string

    :param size_bytes: size_bytes to string.
    :type size_bytes: int

    :return: size bytes in string.
    :rtype: str
    """

    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    power = math.pow(1024, i)
    size = round(size_bytes / power, 2)
    return "%s %s" % (size, size_name[i])


def convert_byte(size_bytes, unit):
    """Convert byte into other unit

    :param size_bytes: size_bytes to target.
    :type size_bytes: int

    :param unit: target unit .
    :type unit: str

    :return: size in target unit.
    :rtype: float
    """

    if size_bytes == 0:
        return "0B"
    units = ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]
    i = 0
    try:
        i = units.index(unit.upper())
    except ValueError:
        pass
    if i > 0:
        power = math.pow(1024, i)
        size_bytes = round(size_bytes / power, 2)
    return size_bytes


def is_reserved_word(name: str) -> str | None:
    """Check if name is reserved in system"""
    reserved = r"^support$|^helpdesk$|^merginmaps$|^lutraconsulting$|^mergin$|^lutra$|^input$|^admin$|^sales$"
    if re.match(reserved, name) is not None:
        return "The provided value is invalid."
    return None


def has_valid_characters(name: str) -> str | None:
    """Check if name contains only valid characters"""
    if re.match(r"^[\w\s\-\.]+$", name) is None:
        return "Please use only alphanumeric or the following -_. characters."
    return None


def has_valid_first_character(name: str) -> str | None:
    """Check if name contains only valid characters in first position"""
    if re.match(r"^[\s^\.].*$", name) is not None:
        return f"Value can not start with space or dot."
    return None


def is_valid_filename(name: str) -> str | None:
    """Check if name contains only valid characters for filename"""
    error = None
    try:
        validate_filename(name)
    except ValidationError:
        error = "The provided value is invalid."
    return error


def workspace_names(workspaces):
    """Helper to extract only names from list of workspaces"""
    return list(map(lambda x: x.name, workspaces))


def workspace_ids(workspaces):
    """Helper to extract only ids from list of workspaces"""
    return list(map(lambda x: x.id, workspaces))


def get_project_path(project):
    """Create path for the project."""
    project_path = project.workspace.name + "/" + project.name
    return project_path


def split_project_path(project_path):
    """Extract workspace and project names out of path."""
    workspace_name, project_name = project_path.split("/")
    return workspace_name, project_name


def get_device_id(request: Request) -> Optional[str]:
    """Get device uuid from http header X-Device-Id"""
    return request.headers.get("X-Device-Id")


def files_size():
    """Get total size of all files"""
    from mergin.app import db

    files_size = text(
        f"""
        WITH partials AS (
            WITH latest_files AS (
                SELECT distinct unnest(file_history_ids) AS file_id
                FROM latest_project_files pf
            )
            SELECT
                SUM(size)
            FROM file_history
            WHERE change = 'create'::push_change_type OR change = 'update'::push_change_type
            UNION
            SELECT
                SUM(COALESCE((diff ->> 'size')::bigint, 0))
            FROM file_history
            WHERE change = 'update_diff'::push_change_type
            UNION
            SELECT
                SUM(size)
            FROM latest_files lf
            LEFT OUTER JOIN file_history fh ON fh.id = lf.file_id
            WHERE fh.change = 'update_diff'::push_change_type
        )
        SELECT COALESCE(SUM(sum), 0) FROM partials;
        """
    )
    return db.session.execute(files_size).scalar()


ALLOWED_EXTENSIONS = {
    # Geospatial
    # Shapefile components
    ".shp",
    ".shx",
    ".dbf",
    ".prj",
    ".cpg",
    ".qix",
    ".sbn",
    ".sbx",
    # Vector data formats
    ".geojson",
    ".kml",
    ".kmz",
    ".gpx",
    ".dxf",
    ".svg",
    ".gpkg",
    ".json",
    # Raster data formats
    ".tif",
    ".tiff",
    ".geotiff",
    ".asc",
    ".vrt",
    ".grd",
    ".img",
    ".adf",
    # Point cloud data formats
    ".las",
    ".laz",
    ".ply",
    ".xyz",
    ".e57",
    ".pcd",
    # Database and container formats
    ".mbtiles",
    ".sqlite",
    ".gpkg",
    # Geospatial metadata and styles
    ".sld",
    ".qml",
    ".lyr",
    ".qgz",
    ".qgs",
    # Other specialized formats
    ".hdf",
    ".hdf5",
    ".netcdf",
    ".nc",
    ".dem",
    ".dt2",
    ".dt0",
    ".map",
    ".tab",
    ".mif",
    ".mid",
    # Images
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".gif",
    ".heic",
    ".webp",
    ".tif",
    ".tiff",
    # Text documents
    ".pdf",
    ".doc",
    ".docx",
    ".odt",
    ".rtf",
    ".txt",
    # Others
    ".zip",
}
ALLOWED_MIME_TYPES = {
    "application/x-shapefile",
    "application/x-dbf",
    "text/plain",
    "application/octet-stream",
    "application/geo+json",
    "application/vnd.google-earth.kml+xml",
    "application/vnd.google-earth.kmz",
    "application/gpx+xml",
    "image/vnd.dxf",
    "image/svg+xml",
    "application/geopackage+sqlite3",
    "application/vnd.sqlite3",
    "application/json",
    "image/tiff",
    "text/xml",
    "application/vnd.mapbox-vector-tile",
    "application/x-sqlite3",
    "application/vnd.ogc.sld+xml",
    "application/xml",
    "application/x-qgis",
    "application/x-hdf",
    "application/x-hdf5",
    "application/x-netcdf",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.oasis.opendocument.text",
    "application/rtf",
    "image/jpeg",
    "image/png",
    "image/bmp",
    "image/gif",
    "image/heic",
    "image/webp",
    "text/plain",
    "application/zip",
}


def supported_extension(filename) -> bool:
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def supported_type(head) -> bool:
    mime_type = magic.Magic(mime=True).from_buffer(head)
    return mime_type in ALLOWED_MIME_TYPES
