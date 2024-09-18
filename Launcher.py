from threading import Thread
from time import sleep
from typing import List
from NodeProcess import NodeProcess


def start_processes(total_processes: int, execution_time: int):

    def initialize_process(index: int):
        active_processes.append(NodeProcess(f"P{index}", total_processes))

    active_processes = []
    process_threads: List[Thread] = []

    for i in range(total_processes):
        process_threads.append(Thread(target=initialize_process, args=(i,)))

    for thread in process_threads:
        thread.start()
    for thread in process_threads:
        thread.join()

    sleep(execution_time)

    for process in active_processes:
        process.stop()


if __name__ == '__main__':
    start_processes(3, 5)
