import mock

import ffchopper


def test_ffprobe_calls_check_call():
    """
    Should call check_call when output_capture is not True.
    """
    with mock.patch("subprocess.check_call") as mock_check_call:
        chopper.ffprobe(["a", "b", "c"])
        assert mock_check_call.called
