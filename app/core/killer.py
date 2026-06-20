import psutil

_PROTECTED = {"system", "csrss.exe", "smss.exe", "wininit.exe", "lsass.exe", "services.exe"}

def is_protected(name: str) -> bool:
    return name.lower() in _PROTECTED

def kill_process(pid: int) -> tuple[bool, str]:
    try:
        proc = psutil.Process(pid)
        if is_protected(proc.name()):
            return False, f"'{proc.name()}'은(는) 시스템 보호 프로세스입니다."
        proc.kill()
        return True, ""
    except psutil.NoSuchProcess:
        return False, "프로세스가 이미 종료되었습니다."
    except psutil.AccessDenied:
        return False, "권한이 없습니다. 관리자 권한으로 실행해주세요."
    except Exception as e:
        return False, str(e)
