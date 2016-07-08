import tempfile
import shutil
import os

import mock
import pytest
import magic

import ffchopper


TEST_VID_PATH = "tests/test.mp4"


class EarlyExitException(Exception):
    """
    Exception used to exit a function when a Mock with this exception as a side effect is hit.
    """
    pass


@mock.patch("ffchopper.video.check_output")
def test_ffprobe_calls_check_output(mock_check_output):
    """
    Should call check_output with the ffprobe binary and supplied arguments.
    """
    args = ["a", "b", "c"]
    ffchopper.video.ffprobe(args)
    assert mock_check_output.called
    assert mock_check_output.call_args[0][0] == [ffchopper.video.FFPROBE_BIN]+args


@mock.patch("ffchopper.video.check_output", return_value=b"Hi!")
def test_ffmpeg_calls_check_output(mock_check_output):
    """
    Should call check_output with the ffmpeg binary and supplied arguments when
    capture_stdout is True.
    """
    args = ["a", "b", "c"]
    ret = ffchopper.video.ffmpeg(args, capture_stdout=True)
    assert mock_check_output.called
    assert mock_check_output.call_args[0][0] == [ffchopper.video.FFMPEG_BIN]+args
    assert ret == "Hi!"


@mock.patch("ffchopper.video.check_call")
def test_ffmpeg_calls_check_call(mock_check_call):
    """
    Should call check_call with the ffmpeg binary and supplied carguments when
    capture_stdout is False.
    """
    args = ["a", "b", "c"]
    ffchopper.video.ffmpeg(args, capture_stdout=False)
    assert mock_check_call.called
    assert mock_check_call.call_args[0][0] == [ffchopper.video.FFMPEG_BIN]+args


class TestVideo:
    def test_video_exists(self):
        """
        Should raise a ValueError if a file does not exist at the path specified.
        """
        with pytest.raises(IOError):
            ffchopper.Video("a_non_existent_file.none")

    @mock.patch("ffchopper.video.ffprobe", return_value="{}")
    def test_data_calls_ffprobe(self, mock_ffprobe):
        """
        Should call ffprobe on the first 'get' of the `data` property and not
        on subsequent ones.
        """
        vid = ffchopper.Video(TEST_VID_PATH)
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
        vid = ffchopper.Video(TEST_VID_PATH)
        assert vid.data
        assert isinstance(vid.data, dict)

    def test_data_contains_streams(self):
        """
        Should return a dict containing the "streams" key.
        """
        vid = ffchopper.Video(TEST_VID_PATH)
        assert "streams" in vid.data

    def test_extract_audio(self):
        """
        Should extract the audio from a video and save it to the specified path.
        """
        vid = ffchopper.Video(TEST_VID_PATH)
        tempdir = tempfile.mkdtemp()
        audio_file = os.path.join(tempdir, "audio.aac")
        try:
            vid.extract_audio(audio_file)
            assert os.path.exists(audio_file)
            assert magic.from_file(audio_file, mime=True) == "audio/x-hx-aac-adts"
        finally:
            shutil.rmtree(tempdir)

    @pytest.mark.slow
    def test_to_images(self):
        """
        Should split the video into a sequence of images.
        """
        vid = ffchopper.Video(TEST_VID_PATH)
        frame_count = int(vid.data["streams"][0]["nb_frames"])
        tempdir = tempfile.mkdtemp()
        try:
            vid.to_images(tempdir, "jpg")
            files = os.listdir(tempdir)
            assert len(files) == frame_count
            assert magic.from_file(os.path.join(tempdir, files[0]), mime=True) == "image/jpeg"
        finally:
            shutil.rmtree(tempdir)

    @pytest.mark.slow
    def test_from_images(self):
        """
        Should build a video from a sequence of images and return it as a Video.
        """
        tempdir = tempfile.mkdtemp()
        output_file = os.path.join(tempdir, "output.mp4")
        try:
            ffchopper.Video.from_images("tests/images/test-%03d.jpg", 25, output_file)
            assert os.path.exists(output_file)
            assert magic.from_file(output_file, mime=True) == "video/mp4"
        finally:
            shutil.rmtree(tempdir)

    @pytest.mark.slow
    def test_overlay(self):
        """
        Should overlay a video on top of a section of the original video.
        """
        vid = ffchopper.Video(TEST_VID_PATH)
        vid2 = ffchopper.Video(TEST_VID_PATH)
        tempdir = tempfile.mkdtemp()
        try:
            output_path = os.path.join(tempdir, "joined.mp4")
            vid.overlay(vid2, 1, output_path)
            assert os.path.exists(output_path)
            assert magic.from_file(output_path, mime=True) == "video/mp4"
        finally:
            shutil.rmtree(tempdir)

    def test_overlay_accepts_string_path(self):
        """
        Should accept a string as the `vid` parameter by creating a new Video with the supplied path
        """
        vid = ffchopper.Video(TEST_VID_PATH)
        with mock.patch("ffchopper.Video.__init__", side_effect=EarlyExitException()) as mock_const:
            tempdir = tempfile.mkdtemp()
            try:
                output_path = os.path.join(tempdir, "joined.mp4")
                with pytest.raises(EarlyExitException):
                    vid.overlay(TEST_VID_PATH, 1, output_path)
                assert mock_const.called
                assert mock_const.call_args[0][0] == TEST_VID_PATH
            finally:
                shutil.rmtree(tempdir)

    def test_insert(self):
        """
        TODO
        """
        vid = ffchopper.Video(TEST_VID_PATH)
        vid.insert(vid, 1)
