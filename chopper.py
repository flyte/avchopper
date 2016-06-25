import os
import json
import tempfile
import shutil
from subprocess import check_call, check_output

FFMPEG_BIN = "ffmpeg"
FFPROBE_BIN = "ffprobe"


class Video:
    def __init__(self, source):
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
        cmd = [
            FFPROBE_BIN,
            "-print_format", "json",
            "-show_streams",
            video_path
        ]
        probe = json.loads(check_output(cmd))
        return probe

    @staticmethod
    def from_images(images_path, fps, dest_path):
        """
        Create a video from `images_path` at `fps` frames per second.

        :returns: Video
        """
        cmd = [
            FFMPEG_BIN,
            "-r", str(fps),
            "-i", images_path,
            dest_path
        ]
        print "Running command: %r" % " ".join(cmd)
        check_call(cmd)
        return Video(dest_path)

    def extract_audio(self, output_path):
        """
        Extracts the audio stream(s) from the video.
        """
        cmd = [
            FFMPEG_BIN,
            "-i", self.source,
            "-vn",
            "-acodec", "copy",
            output_path
        ]
        check_call(cmd)

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
        self.frame_paths = [os.path.join(dest_dir, x) for x in sorted(os.listdir(dest_dir))]

    def overlay(self, vid, start_seconds, limit=None):
        """
        Overlay the contents of `vid` onto this video starting at `start_frame`
        for `limit` frames.
        """
        if isinstance(vid, str):
            vid = Video(vid)

        tmpdir = tempfile.mkdtemp()
        overlay_seconds = float(vid.data["streams"][0]["duration"])

        # Split original video into two parts, missing the overlay part
        source_a = os.path.join(tmpdir, "source-a.mp4")
        source_b = os.path.join(tmpdir, "source-b.mp4")
        cmd = [
            FFMPEG_BIN,
            "-i", self.source,
            "-t", str(start_seconds),
            source_a,
            "-ss", str(start_seconds + overlay_seconds),
            source_b
        ]
        check_call(cmd)

        filenames_txt = os.path.join(tmpdir, "files.txt")
        with open(filenames_txt, "w") as f:
            f.writelines(["file %s\n" % x for x in (
                source_a,
                vid.source,
                source_b
            )])

        # Join the three video parts together (source 1, new bit, source 2)
        joined = os.path.join(tmpdir, "joined.mp4")
        cmd = [
            FFMPEG_BIN,
            "-f", "concat",
            "-i", filenames_txt,
            "-c", "copy",
            joined
        ]
        check_call(cmd)

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

    def splice(self, vid, start_frame, limit=None):
        """
        Splice the contents of `vid` into this video starting at `start_frame`
        for `limit` frames.
        """
        pass
