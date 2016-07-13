import os
from decimal import Decimal

import mock
import pytest
import magic

import avtoolkit
from avtoolkit.util import tempdir, chainable


TEST_VID_PATH = "tests/test.mp4"
TEST_IMG_PATH = "tests/tux.png"


class EarlyExitException(Exception):
    """
    Exception used to exit a function when a Mock with this exception as a side effect is hit.
    """
    pass


def percentage_difference(a, b):
    """
    Calculate the percentage difference between two numbers.
    """
    if any(x == 0 for x in (a, b)):
        raise ValueError("Cannot compute difference if either number is zero.")
    return (float(abs(a-b))/float(a))*100


@mock.patch("avtoolkit.video.check_output")
def test_ffprobe_calls_check_output(mock_check_output):
    """
    Should call check_output with the ffprobe binary and supplied arguments.
    """
    args = ["a", "b", "c"]
    avtoolkit.video.ffprobe(args)
    assert mock_check_output.called
    assert mock_check_output.call_args[0][0] == [avtoolkit.video.FFPROBE_BIN]+args


@mock.patch("avtoolkit.video.check_output", return_value=b"Hi!")
def test_ffmpeg_calls_check_output(mock_check_output):
    """
    Should call check_output with the ffmpeg binary and supplied arguments when
    capture_stdout is True.
    """
    args = ["a", "b", "c"]
    ret = avtoolkit.video.ffmpeg(args, capture_stdout=True)
    assert mock_check_output.called
    assert mock_check_output.call_args[0][0] == [avtoolkit.video.FFMPEG_BIN, "-y"]+args
    assert ret == "Hi!"


@mock.patch("avtoolkit.video.check_call")
def test_ffmpeg_calls_check_call(mock_check_call):
    """
    Should call check_call with the ffmpeg binary and supplied carguments when
    capture_stdout is False.
    """
    args = ["a", "b", "c"]
    avtoolkit.video.ffmpeg(args, capture_stdout=False)
    assert mock_check_call.called
    assert mock_check_call.call_args[0][0] == [avtoolkit.video.FFMPEG_BIN, "-y"]+args


class TestUtil:
    def test_tempdir(self):
        """
        Should create a temporary directory and remove it afterwards.
        """
        @tempdir
        def test(tmpdir):
            assert os.path.exists(tmpdir)
            return tmpdir
        tmpdir = test()
        assert not os.path.exists(tmpdir)

    def test_tempdir_already_provided(self, tmpdir):
        """
        Should do nothing when a tempdir is already provided.
        """
        @tempdir
        def test(tmpdir):
            assert os.path.exists(tmpdir)
            return tmpdir
        tmpdir = str(tmpdir)
        assert os.path.exists(tmpdir)
        tmpdir = test(tmpdir=tmpdir)
        assert os.path.exists(tmpdir)

    def test_chainable(self, tmpdir):
        """
        Should allow for chaining operations without specifying output_path for the intermediate
        functions.
        """
        class Video(object):
            def __init__(self):
                self.ext = ".mp4"
                self.dirname = str(tmpdir)
                self.intermediate_file = None

            @chainable
            def test(self, output_path=None):
                assert os.path.exists(output_path)
                return Video()

        output_path = os.path.join(str(tmpdir), "output.mp4")
        open(output_path, "a").close()
        vid = Video()
        vid.test().test().test(output_path=output_path)

    def test_chainable_with_exception(self, tmpdir):
        """
        Should delete the intermediate file if the function raises and exception.
        """
        class MyException(Exception):
            pass

        class Video(object):
            def __init__(self):
                self.ext = ".mp4"
                self.dirname = str(tmpdir)
                self.intermediate_file = None

            @chainable
            def test(self, output_path=None):
                raise MyException()

        output_path = os.path.join(str(tmpdir), "output.mp4")
        open(output_path, "a").close()
        with mock.patch("os.unlink") as mock_unlink:
            with pytest.raises(MyException):
                Video().test()
            assert mock_unlink.called


class TestVideo:
    def test_video_exists(self):
        """
        Should raise a ValueError if a file does not exist at the path specified.
        """
        with pytest.raises(IOError):
            avtoolkit.Video("a_non_existent_file.none")

    @mock.patch("avtoolkit.video.ffprobe", return_value="{}")
    def test_data_calls_ffprobe(self, mock_ffprobe):
        """
        Should call ffprobe on the first 'get' of the `data` property and not
        on subsequent ones.
        """
        vid = avtoolkit.Video(TEST_VID_PATH)
        assert not mock_ffprobe.called
        vid.data
        assert mock_ffprobe.called
        assert mock_ffprobe.call_count == 1
        vid.data
        assert mock_ffprobe.call_count == 1

    def test_data_returns_dict(self):
        """
        Should return a dictionary containing information about the video.
        """
        vid = avtoolkit.Video(TEST_VID_PATH)
        assert vid.data
        assert isinstance(vid.data, dict)

    def test_data_contains_streams(self):
        """
        Should return a dict containing the "streams" key.
        """
        vid = avtoolkit.Video(TEST_VID_PATH)
        assert "streams" in vid.data

    def test_extract_audio(self, tmpdir):
        """
        Should extract the audio from a video and save it to the specified path.
        """
        vid = avtoolkit.Video(TEST_VID_PATH)
        audio_file = os.path.join(str(tmpdir), "audio.aac")
        vid.extract_audio(audio_file)
        assert os.path.exists(audio_file)
        assert magic.from_file(audio_file, mime=True) == "audio/x-hx-aac-adts"

    @pytest.mark.slow
    def test_to_images(self, tmpdir):
        """
        Should split the video into a sequence of images.
        """
        vid = avtoolkit.Video(TEST_VID_PATH)
        frame_count = int(vid.data["streams"][0]["nb_frames"])
        vid.to_images(str(tmpdir), "jpg")
        files = os.listdir(str(tmpdir))
        assert len(files) == frame_count
        assert magic.from_file(os.path.join(str(tmpdir), files[0]), mime=True) == "image/jpeg"

    @pytest.mark.slow
    def test_from_images(self, tmpdir):
        """
        Should build a video from a sequence of images and return it as a Video.
        """
        output_file = os.path.join(str(tmpdir), "output.mp4")
        avtoolkit.Video.from_images("tests/images/test-%03d.jpg", 25, output_file)
        assert os.path.exists(output_file)
        assert magic.from_file(output_file, mime=True) == "video/mp4"

    @pytest.mark.slow
    def test_overlay(self, tmpdir):
        """
        Should overlay a video on top of a section of the original video.
        """
        vid = avtoolkit.Video(TEST_VID_PATH)
        vid2 = avtoolkit.Video(TEST_VID_PATH)
        output_path = os.path.join(str(tmpdir), "joined.mp4")
        vid.overlay(vid2, 1, output_path=output_path)
        assert os.path.exists(output_path)
        assert magic.from_file(output_path, mime=True) == "video/mp4"

    @pytest.mark.slow
    def test_overlay_with_image(self, tmpdir):
        """
        Should overlay an image on top of a section of the original video.
        """
        vid = avtoolkit.Video(TEST_VID_PATH)
        img = avtoolkit.Video(TEST_IMG_PATH)
        output_path = os.path.join(str(tmpdir), "output.mp4")

        # Should raise an AttributeError if `overlay_duration` is not provided with an image.
        with pytest.raises(AttributeError):
            vid.overlay(img, 2, output_path=output_path)

        vid.overlay(img, 2, output_path=output_path, overlay_duration=2)
        assert os.path.exists(output_path)
        assert magic.from_file(output_path, mime=True) == "video/mp4"

    @pytest.mark.slow
    def test_reencode(self, tmpdir):
        """
        Should convert the video to the desired encoding based on the file extension.
        """
        assert magic.from_file(TEST_VID_PATH, mime=True) == "video/mp4"
        vid = avtoolkit.Video(TEST_VID_PATH)
        output_file = os.path.join(str(tmpdir), "output.avi")
        vid.reencode(output_path=output_file)
        assert magic.from_file(output_file, mime=True) == "video/x-msvideo"

    @pytest.mark.slow
    def test_split(self, tmpdir):
        """
        Should split a video at a given second and return two Videos.
        """
        a = os.path.join(str(tmpdir), "a.mp4")
        b = os.path.join(str(tmpdir), "b.mp4")
        vid = avtoolkit.Video(TEST_VID_PATH)
        original_length = Decimal(vid.data["streams"][0]["duration"])
        split_seconds = Decimal("2.52")

        result = vid.split(split_seconds, a, b)
        assert isinstance(result, tuple)
        vid_a, vid_b = result
        for output in (a, b):
            assert os.path.exists(output)
            assert magic.from_file(output, mime=True) == "video/mp4"
        assert Decimal(vid_a.data["streams"][0]["duration"]) == split_seconds
        assert Decimal(vid_b.data["streams"][0]["duration"]) == original_length - split_seconds

    @pytest.mark.slow
    def test_concatenate(self, tmpdir):
        """
        Should concatenate three videos together and reencode them.
        """
        vid = avtoolkit.Video(TEST_VID_PATH)
        length = Decimal(vid.data["streams"][0]["duration"])
        output_path = os.path.join(str(tmpdir), "joined.mp4")
        joined = vid.concatenate(output_path=output_path, before=(vid,), after=(vid,))
        assert os.path.exists(output_path)
        assert magic.from_file(output_path, mime=True) == "video/mp4"
        new_length = Decimal(joined.data["streams"][0]["duration"])
        assert percentage_difference(new_length, length*3) < 1

    def test_concatenate_no_reencode(self, tmpdir):
        """
        Should concatenate three videos together and not reencode them.
        """
        vid = avtoolkit.Video(TEST_VID_PATH)
        length = Decimal(vid.data["streams"][0]["duration"])
        output_path = os.path.join(str(tmpdir), "joined.mp4")
        joined = vid.concatenate(
            output_path=output_path, before=(vid,), after=(vid,), reencode=False)
        assert os.path.exists(output_path)
        assert magic.from_file(output_path, mime=True) == "video/mp4"
        new_length = Decimal(joined.data["streams"][0]["duration"])
        assert percentage_difference(new_length, length*3) < 1

    def test_concatenate_no_videos(self):
        """
        Should raise a ValueError if we don't provide videos to concatenate with.
        """
        vid = avtoolkit.Video(TEST_VID_PATH)
        with pytest.raises(ValueError):
            vid.concatenate(output_path="/dev/null")

    @pytest.mark.slow
    def test_scale(self, tmpdir):
        """
        Should scale a video.
        """
        vid = avtoolkit.Video(TEST_VID_PATH)
        orig_x = int(vid.data["streams"][0]["width"])
        orig_y = int(vid.data["streams"][0]["height"])
        new_x = orig_x/2
        new_y = orig_y/2
        output = os.path.join(str(tmpdir), "scaled.mp4")
        scaled = vid.scale((new_x, new_y), output_path=output)
        assert os.path.exists(output)
        assert magic.from_file(output, mime=True) == "video/mp4"
        assert int(scaled.data["streams"][0]["width"]) == new_x
        assert int(scaled.data["streams"][0]["height"]) == new_y

    @pytest.mark.slow
    def test_insert(self, tmpdir):
        """
        Should split the video at the given second and insert a video in the middle.
        """
        vid = avtoolkit.Video(TEST_VID_PATH)
        original_length = Decimal(vid.data["streams"][0]["duration"])
        output_path = os.path.join(str(tmpdir), "inserted.mp4")

        result = vid.insert(vid, 2.5, output_path=output_path, reencode=False)
        assert os.path.exists(output_path)
        assert magic.from_file(output_path, mime=True) == "video/mp4"
        new_length = Decimal(result.data["streams"][0]["duration"])
        assert percentage_difference(new_length, original_length*2) < 1

    @pytest.mark.slow
    def test_trim_start(self, tmpdir):
        """
        Should trim some seconds off the beginning of the video.
        """
        vid = avtoolkit.Video(TEST_VID_PATH)
        original_length = Decimal(vid.data["streams"][0]["duration"])
        output_path = os.path.join(str(tmpdir), "trimmed.mp4")
        trim_secs = 3

        trimmed = vid.trim_start(trim_secs, output_path=output_path)
        new_length = Decimal(trimmed.data["streams"][0]["duration"])
        assert new_length == (original_length-trim_secs)

    @pytest.mark.slow
    def test_trim_end(self, tmpdir):
        """
        Should trim some seconds off the beginning of the video.
        """
        vid = avtoolkit.Video(TEST_VID_PATH)
        original_length = Decimal(vid.data["streams"][0]["duration"])
        output_path = os.path.join(str(tmpdir), "trimmed.mp4")
        trim_secs = 3

        trimmed = vid.trim_end(trim_secs, output_path=output_path)
        new_length = Decimal(trimmed.data["streams"][0]["duration"])
        assert new_length == (original_length-trim_secs)
