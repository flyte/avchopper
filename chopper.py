import os
import json
from subprocess import check_call, check_output

FFMPEG_BIN = "ffmpeg"
FFPROBE_BIN = "ffprobe"


class Video:
    def __init__(self, source):
        self.source = source
        self._data = None

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
        cmd = [
            FFPROBE_BIN,
            "-print_format", "json",
            "-show_streams",
            video_path
        ]
        probe = json.loads(check_output(cmd))
        return probe

    @staticmethod
    def from_images(self, images, fps):
        """
        Create a video from `images` at `fps` frames per second.

        :returns: Video
        """
        pass

    def to_images(self, dest_dir=None):
        """
        Convert this video to individual frame images.
        """
        name, _ = os.path.splitext(self.source)
        output_path = "%s-%%03d.png" % name
        if dest_dir is not None:
            output_path = os.path.join(dest_dir, os.path.basename(output_path))
        cmd = [
            FFMPEG_BIN,
            "-i", self.source,
            output_path
        ]
        print "Running command: %r" % " ".join(cmd)
        check_call(cmd)

    def overlay(self, vid, start_frame, limit=None):
        """
        Overlay the contents of `vid` onto this video starting at `start_frame`
        for `limit` frames.
        """
        pass

    def splice(self, vid, start_frame, limit=None):
        """
        Splice the contents of `vid` into this video starting at `start_frame`
        for `limit` frames.
        """
        pass
