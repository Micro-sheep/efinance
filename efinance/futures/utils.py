from threading import Thread





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
