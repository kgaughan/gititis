import os
import stat


def check_mode(path: str, mode: int, *, is_file: bool = False, is_dir: bool = False) -> None:
    st = os.stat(path)
    if is_dir:
        assert stat.S_ISDIR(st.st_mode)
    if is_file:
        assert stat.S_ISREG(st.st_mode)

    got = stat.S_IMODE(st.st_mode)
    assert got == mode, f"File mode {got:04o}!={mode:04o} for {path}"
