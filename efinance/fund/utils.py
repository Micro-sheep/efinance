from threading import Thread


def gen_secid(rawcode: str) -> str:
    '''
    生成东方财富专用的secid
    '''
    if rawcode[0] != '6':
        return f'0.{rawcode}'
    return f'1.{rawcode}'


def threadmethod(func, *args, cores: int = 30, **kwargs):
    def thread(*args, **kwargs):
        threads = []
        for _ in range(cores):
            t = Thread(target=func, args=args, kwargs=kwargs)
            t.setDaemon(True)
            threads.append(t)
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        return 1

    return thread
