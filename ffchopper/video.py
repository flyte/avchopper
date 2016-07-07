from __future__ import print_function
import os
import locale
import json
import tempfile
from subprocess import check_call, check_output


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
    return func([FFMPEG_BIN]+args, stderr=DEV_NULL)


def ffprobe(args):
    """ Call ffprobe and redirect stderr to /dev/null """
    return check_output_decoded([FFPROBE_BIN]+args, stderr=DEV_NULL)


class Video:
    def __init__(self, source):
        if not os.path.exists(source):
            raise IOError("File does not exist at %r" % source)
        self.source = source
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

    def to_images(self, dest_dir=None):
        """
        Convert this video to individual frame images.
        """
        name, _ = os.path.splitext(self.source)
        output_path = "%s-%%03d.png" % name
        if dest_dir is not None:
            output_path = os.path.join(dest_dir, os.path.basename(output_path))
        args = [
            "-i", self.source,
            output_path
        ]
        print("Running command: %r" % " ".join(args))
        ffmpeg(args)
        self.frame_paths = [os.path.join(dest_dir, x) for x in sorted(os.listdir(dest_dir))]

    def overlay(self, vid, start_seconds, limit=None):
        """
        Overlay the contents of `vid` onto this video starting at `start_frame`
        for `limit` seconds.
        """
        if isinstance(vid, str):
            vid = Video(vid)

        tmpdir = tempfile.mkdtemp()
        overlay_seconds = limit or float(vid.data["streams"][0]["duration"])

        # Split original video into two parts, missing the overlay part
        source_a = os.path.join(tmpdir, "source-a.mp4")
        source_b = os.path.join(tmpdir, "source-b.mp4")
        args = [
            "-i", self.source,
            "-t", str(start_seconds),
            source_a,
            "-ss", str(start_seconds + overlay_seconds),
            source_b
        ]
        ffmpeg(args)

        filenames_txt = os.path.join(tmpdir, "files.txt")
        with open(filenames_txt, "w") as f:
            f.writelines(["file %s\n" % x for x in (
                source_a,
                vid.source,
                source_b
            )])

        # Join the three video parts together (source 1, new bit, source 2)
        joined = os.path.join(tmpdir, "joined.mp4")
        args = [
            "-f", "concat",
            "-i", filenames_txt,
            "-c", "copy",
            joined
        ]
        ffmpeg(args)
        for path in (source_a, source_b, filenames_txt):
            os.unlink(path)

        # overlay_dir = os.path.join(tmpdir, "overlay")
        # os.mkdir(overlay_dir)
        # vid.to_images(overlay_dir)
        # overlay_filename = os.path.basename(vid.source)

        # source_dir = os.path.join(tmpdir, "source")
        # os.mkdir(source_dir)
        # # @TODO: Only create `limit` frames
        # self.to_images(source_dir)
        # source_filename = os.path.basename(self.source)

        # # Ensure that we don't try to replace more frames than exist
        # overlay_frame_count = len(os.listdir(overlay_dir))
        # if overlay_frame_count < limit:
        #     limit = overlay_frame_count

        # source_name, _ = os.path.splitext(source_filename)
        # overlay_name, _ = os.path.splitext(overlay_filename)
        # j = 1
        # for i in range(start_frame, start_frame+limit):
        #     file_path = os.path.join(source_dir, "%s-%03d.png" % (source_name, i))
        #     print "overlaying %s" % file_path
        #     os.unlink(file_path)
        #     new_file_path = os.path.join(overlay_dir, "%s-%03d.png" % (overlay_name, j))
        #     print "with %s" % new_file_path
        #     shutil.copy(new_file_path, file_path)
        #     j += 1

    def insert(self, vid, start_frame, limit=None):
        """
        Insert the contents of `vid` into this video starting at `start_frame`
        for `limit` frames.
        """
        pass
