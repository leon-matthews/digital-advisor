
import concurrent.futures
import itertools
import logging

logger = logging.getLogger(__name__)


def threadpool_generator(num_threads, function, args):
    """
    Adapt the excellent `concurrent.futures.ThreadPoolExecutor` to work
    with generators and large datasets.

    As documented, ThreadPoolExecutor queues all avaiable work without
    limit, creating a Future intstance for each.

    Here, we submit only a subset of our work, then continue to top that
    up as jobs are completed. Jobs are yielded in the order in which they
    are completed - the original ordering is not maintained.

    Args:
        function (callable):
            Function to run on each of the given arguments. If the argument
            needs to matched with the result, have the function return both
            in a 2-tuple.
        args (Iterable):
            Any iterable containing the arguments to apply to the function.
            Use a tuple to submit multiple arguments.
        num_threads (int):
            How many threads to run. If not given, defaults to the number of
            cores times four.

    Yields:
        Results of `function`, in some arbitary order.
    """
    queue_length = num_threads * 2
    logger.debug(
        "ThreadPool started using %s threads, queue length %s",
        num_threads,
        queue_length,
    )

    args = iter(args)

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        # Start first chunk of work
        futures = {
            executor.submit(function, arg) for arg in itertools.islice(args, queue_length)
        }

        # Monitor work, keep queue topped up:
        while futures:
            # ...wait for at least one (but possibly more) jobs to complete
            completed, futures = concurrent.futures.wait(
                futures, return_when=concurrent.futures.FIRST_COMPLETED,
            )

            # ...yield completed results
            for future in completed:
                yield future.result()

            # ...submit next chunk of work
            for arg in itertools.islice(args, len(completed)):
                futures.add(executor.submit(function, arg))
