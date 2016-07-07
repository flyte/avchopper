import mock

import ffchopper


@mock.patch("ffchopper.video.check_output")
def test_ffprobe_calls_check_output(mock_check_output):
    """
    Should call check_output with the ffprobe binary and supplied arguments.
    """
    args = ["a", "b", "c"]
    ffchopper.video.ffprobe(args)
    assert mock_check_output.called
    assert mock_check_output.call_args[0][0] == [ffchopper.video.FFPROBE_BIN]+args


@mock.patch("ffchopper.video.check_output", return_value="Hi!")
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
