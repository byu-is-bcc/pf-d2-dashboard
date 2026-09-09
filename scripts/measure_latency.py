"""
Measures prediction latency against a running service.

The claim you are going to publish contains a latency number, so the
measurement has to be something a reviewer can rerun. That is why this
script is committed rather than being a number you remember from a terminal
you have since closed.

Argument handling, the request loop, and the output format are done. The
two things this script exists to compute are not, and computing them is
part of the assignment.

Run against local:
  python scripts/measure_latency.py --url http://localhost:8000/predict

Run against your deployment, which is the number you actually publish:
  python scripts/measure_latency.py --url https://your-app.example.com/predict -n 200

Measure the deployed service, not localhost. Localhost latency is a
statement about your laptop.
"""

from __future__ import annotations

import argparse
import json
import sys

import requests

# One valid ticket. Sending the same body every time isolates service
# latency from the cost of building requests, which is what you want here.
DEFAULT_PAYLOAD = {
    "ticket_age_hours": 36.0,
    "customer_tenure_days": 820,
    "prior_tickets_90d": 3,
    "message_count": 7,
    "account_seats": 240,
    "plan_tier_rank": 2,
}


def percentile(values: list[float], p: float) -> float:
    """Return the p-th percentile of `values`, where p is 0 to 100.

    TODO(you): implement this.

    You need p50 and p95. `statistics.median` gets you one of them and
    `statistics.quantiles` can get you the other, or you can sort the list
    and index into it, which is worth doing once by hand so that you know
    what your monitoring tool is actually reporting.

    Two things to decide, and to be able to defend in an interview:

      - Which interpolation you use when the percentile falls between two
        samples. numpy, statistics.quantiles, and most dashboards do not
        all agree, and the differences show up most at p95 and above.
      - What the minimum sample size is for a p95 to mean anything. With
        20 requests your p95 is one unlucky sample. The brief asks for at
        least 100 for exactly this reason.
    """
    raise NotImplementedError(
        "percentile() is not implemented. See the TODO in "
        "scripts/measure_latency.py."
    )


def measure(url: str, count: int, warmup: int, payload: dict, timeout: float):
    """POST `payload` to `url` repeatedly and collect per-request latency.

    Returns (latencies_ms, failures). Warmup requests are sent and thrown
    away, because the first request to a free-tier service that has gone to
    sleep can take several seconds and it will dominate your p95.
    """
    session = requests.Session()

    for _ in range(warmup):
        try:
            session.post(url, json=payload, timeout=timeout)
        except requests.RequestException:
            pass

    latencies: list[float] = []
    failures = 0

    for i in range(count):
        try:
            # TODO(you): time this request and append the elapsed
            # milliseconds to `latencies`.
            #
            # Use time.perf_counter(), not time.time(). perf_counter is
            # monotonic and has much better resolution; time.time() can go
            # backwards when the system clock is adjusted.
            #
            # Measure only the request. Anything you do to the response
            # afterward is your latency, not the service's.
            response = session.post(url, json=payload, timeout=timeout)
            if response.status_code != 200:
                failures += 1
                if failures == 1:
                    print(
                        f"  first non-200 response: {response.status_code} "
                        f"{response.text[:120]}",
                        file=sys.stderr,
                    )
        except requests.RequestException as exc:
            failures += 1
            if failures == 1:
                print(f"  first request error: {exc}", file=sys.stderr)

        if (i + 1) % 25 == 0:
            print(f"  {i + 1}/{count} requests sent", file=sys.stderr)

    return latencies, failures


def report(url: str, count: int, warmup: int, latencies: list[float], failures: int) -> dict:
    """Print the measurement and return it as a dict."""
    if not latencies:
        print(
            "\nNo latencies were recorded. Either every request failed, or "
            "the timing capture in measure() is still a TODO.",
            file=sys.stderr,
        )
        sys.exit(1)

    result = {
        "url": url,
        "requests": count,
        "warmup_discarded": warmup,
        "failures": failures,
        "p50_ms": round(percentile(latencies, 50), 1),
        "p95_ms": round(percentile(latencies, 95), 1),
        "min_ms": round(min(latencies), 1),
        "max_ms": round(max(latencies), 1),
    }

    print()
    print(f"Endpoint      : {result['url']}")
    print(f"Requests      : {result['requests']} ({result['warmup_discarded']} warmup, discarded)")
    print(f"Failures      : {result['failures']}")
    print(f"Median (p50)  : {result['p50_ms']} ms")
    print(f"p95           : {result['p95_ms']} ms")
    print(f"Min / Max     : {result['min_ms']} / {result['max_ms']} ms")
    print()
    print("Report the median as your headline number and the p95 next to it.")
    print("A median with no p95 hides the requests your users complain about.")

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Measure /predict latency over many requests.",
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8000/predict",
        help="Full URL of the predict endpoint.",
    )
    parser.add_argument(
        "-n", "--requests",
        type=int, default=100, dest="count",
        help="Requests to measure. The brief requires at least 100.",
    )
    parser.add_argument(
        "--warmup",
        type=int, default=5,
        help="Requests to send and discard before measuring.",
    )
    parser.add_argument(
        "--timeout",
        type=float, default=30.0,
        help="Per-request timeout in seconds.",
    )
    parser.add_argument(
        "--payload",
        type=argparse.FileType("r"), default=None,
        help="JSON file with the request body. Defaults to a built-in ticket.",
    )
    parser.add_argument(
        "--out",
        type=argparse.FileType("w"), default=None,
        help="Write the result as JSON here, so the number in your README "
             "has a file behind it.",
    )
    args = parser.parse_args()

    if args.count < 100:
        print(
            f"Warning: {args.count} requests is below the 100 the brief "
            "requires. A p95 from a small sample is noise.",
            file=sys.stderr,
        )

    payload = json.load(args.payload) if args.payload else DEFAULT_PAYLOAD

    print(f"Measuring {args.count} requests against {args.url}", file=sys.stderr)
    latencies, failures = measure(
        args.url, args.count, args.warmup, payload, args.timeout
    )
    result = report(args.url, args.count, args.warmup, latencies, failures)

    if args.out:
        json.dump(result, args.out, indent=2)
        args.out.write("\n")


if __name__ == "__main__":
    main()
