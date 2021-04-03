from threading import Thread


def gen_secid(rawcode: str) -> str:
    '''
    生成东方财富专用的secid
    '''
    if rawcode[:3] == '000':
        return f'1.{rawcode}'
    # 深证指数
    if rawcode[:3] == '399':
        return f'0.{rawcode}'
    # 沪市股票
    if rawcode[0] != '6':
        return f'0.{rawcode}'
    # 深市股票
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
