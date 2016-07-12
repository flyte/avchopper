from __future__ import print_function
import os
import locale
import json
import shutil
from subprocess import check_call, check_output

from .util import tempdir


FFMPEG_BIN = "ffmpeg"
FFPROBE_BIN = "ffprobe"
DEV_NULL = open(os.devnull, "w")
ENCODING = locale.getpreferredencoding()


def check_output_decoded(*args, **kwargs):
    """ Call check_output and decode the resulting bytes. """
    return check_output(*args, **kwargs).decode(ENCODING)


def ffmpeg(args, capture_stdout=False):
    """ Call ffmpeg and redirect stderr to /dev/null """
    func = check_output_decoded if capture_stdout else check_call
    # return func([FFMPEG_BIN]+args, stderr=DEV_NULL)
    return func([FFMPEG_BIN]+args)


def ffprobe(args):
    """ Call ffprobe and redirect stderr to /dev/null """
    return check_output_decoded([FFPROBE_BIN]+args, stderr=DEV_NULL)


class Video:
    def __init__(self, source):
        if not os.path.exists(source):
            raise IOError("File does not exist at %r" % source)
        self.source = os.path.abspath(source)
        self._data = None
        self._frame_paths = []

    @property
    def data(self):
        if self._data is None:
            self._data = self.probe(self.source)
        return self._data

    @staticmethod
    def probe(video_path):
        """
        Get the details of the video.
        """
        args = [
            "-print_format", "json",
            "-show_streams",
            video_path
        ]
        return json.loads(ffprobe(args))

    @staticmethod
    def from_images(images_path, fps, dest_path):
        """
        Create a video from `images_path` at `fps` frames per second.

        :returns: Video
        """
        args = [
            "-r", str(fps),
            "-i", images_path,
            dest_path
        ]
        print("Running ffmpeg command: %r" % " ".join(args))
        ffmpeg(args)
        return Video(dest_path)

    def extract_audio(self, output_path):
        """
        Extracts the audio stream(s) from the video.
        """
        args = [
            "-i", self.source,
            "-vn",
            "-acodec", "copy",
            output_path
        ]
        ffmpeg(args)

    def to_images(self, dest_dir=None, img_format="png"):
        """
        Convert this video to individual frame images.
        """
        name, _ = os.path.splitext(self.source)
        output_path = "%s-%%03d.%s" % (name, img_format)
        if dest_dir is not None:
            output_path = os.path.join(dest_dir, os.path.basename(output_path))
        args = [
            "-i", self.source,
            output_path
        ]
        print("Running command: %r" % " ".join(args))
        ffmpeg(args)
        self.frame_paths = [os.path.join(dest_dir, x) for x in sorted(os.listdir(dest_dir))]

    @tempdir
    def reencode(tmpdir, self, output_path):
        """
        Simply reencode the video to the specified output_path.
        """
        _, ext = os.path.splitext(output_path)
        output = os.path.join(tmpdir, "output%s" % ext)
        args = [
            "-i", self.source,
            output
        ]
        ffmpeg(args)
        shutil.move(output, output_path)
        return Video(output_path)

    @tempdir
    def split(tmpdir, self, seconds, beginning_path, end_path, end_offset_seconds=0):
        """
        Split a video into two parts at `seconds`. If `end_offset_seconds` is set, cut that amount
        of seconds off the beginning of the end part (useful for overlays).
        """
        _, beginning_ext = os.path.splitext(beginning_path)
        _, end_ext = os.path.splitext(end_path)
        beginning = os.path.join(tmpdir, "beginning%s" % beginning_ext)
        end = os.path.join(tmpdir, "end%s" % end_ext)
        args = [
            "-i", self.source,
            "-t", str(seconds),
            beginning,
            "-ss", str(seconds+end_offset_seconds),
            end
        ]
        ffmpeg(args)
        shutil.move(beginning, beginning_path)
        shutil.move(end, end_path)
        return (Video(beginning_path), Video(end_path))

    @tempdir
    def overlay(tmpdir, self, vid, start_seconds, output_path, overlay_duration=None):
        """
        Overlay the contents of `vid` onto this video starting at `start_seconds`.
        """
        if isinstance(vid, str):
            vid = Video(vid)

        _, ext = os.path.splitext(output_path)
        duration = overlay_duration or float(vid.data["streams"][0]["duration"])
        output = os.path.join(tmpdir, "overlay%s" % ext)
        x, y = (0, 0)

        cmd = [
            "-i", self.source,
            "-i", vid.source,
            "-filter_complex",
            "overlay=%d:%d:enable='between(t,%d,%d)'" % (
                x, y, start_seconds, start_seconds+duration
            ),
            output
        ]
        ffmpeg(cmd)

        # # Split original video into two parts, missing the overlay part
        # source_a = os.path.join(tmpdir, "source-a.mp4")
        # source_b = os.path.join(tmpdir, "source-b.mp4")
        # self.split(start_seconds, source_a, source_b, end_offset_seconds=overlay_duration)

        # filenames_txt = os.path.join(tmpdir, "files.txt")
        # with open(filenames_txt, "w") as f:
        #     f.writelines(["file %s\n" % x for x in (
        #         source_a,
        #         vid.source,
        #         source_b
        #     )])

        # # Join the three video parts together (source 1, new bit, source 2)
        # joined = os.path.join(tmpdir, "joined.mp4")
        # args = [
        #     "-f", "concat",
        #     "-safe", "0",
        #     "-i", filenames_txt,
        #     "-c", "copy",
        #     joined
        # ]
        # ffmpeg(args)
        shutil.move(output, output_path)
        return Video(output_path)

    @tempdir
    def overlay_image(
            tmpdir, self, img_path, start_seconds, duration, output_path, position=(0, 0)):
        """
        Overlay an image from `start_seconds` for `duration` seconds at `position` vector.
        """
        _, ext = os.path.splitext(output_path)
        output = os.path.join(tmpdir, "output%s" % ext)
        args = [
            "-i", self.source,
            "-i", img_path,
            "-filter_complex", "[0:v][1:v] overlay=%s:enable='between(t,%d,%d)'" % (
                ":".join(position),
                start_seconds,
                duration,
                output
            )
        ]
        ffmpeg(args)
        shutil.move(output, output_path)
        return Video(output_path)

    def insert(self, vid, start_seconds):
        """
        Insert the contents of `vid` into this video starting at `start_frame`
        for `limit` frames.
        """
        pass
