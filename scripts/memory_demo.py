from memory_profiler import profile

@profile
def load_data():
    for x in range(10_000):
        yield x  # shows: +382 MiB


load_data()
