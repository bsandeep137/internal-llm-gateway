#!/usr/bin/env python3
"""Demo CLI client for the Internal LLM Gateway."""

import argparse
import json
import httpx


BASE_URL = "http://localhost:8000"


def send_completion(prompt: str, model: str = "default") -> None:
    payload = {"prompt": prompt, "model": model}
    with httpx.Client() as client:
        response = client.post(f"{BASE_URL}/v1/completions", json=payload)
        response.raise_for_status()
        print(json.dumps(response.json(), indent=2))


def main():
    parser = argparse.ArgumentParser(description="LLM Gateway Demo Client")
    parser.add_argument("prompt", help="Prompt to send to the gateway")
    parser.add_argument("--model", default="default", help="Model to use")
    args = parser.parse_args()
    send_completion(args.prompt, args.model)


if __name__ == "__main__":
    main()
