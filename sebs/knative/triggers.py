import concurrent.futures
import datetime
import json
import subprocess
from typing import Dict, List, Optional

from sebs.faas.function import ExecutionResult, Trigger

class KnativeLibraryTrigger(Trigger):
    def __init__(self, fname: str, func_cmd: Optional[List[str]] = None):
        super().__init__()
        self.fname = fname
        if func_cmd:
            self._func_cmd = [*func_cmd, "invoke", "--target", "remote"]

    @staticmethod
    def trigger_type() -> "Trigger.TriggerType":
        return Trigger.TriggerType.LIBRARY

    @property
    def func_cmd(self) -> List[str]:
        assert self._func_cmd
        return self._func_cmd

    @func_cmd.setter
    def func_cmd(self, func_cmd: List[str]):
        self._func_cmd = [*func_cmd, "invoke", "--target", "remote"]

    @staticmethod
    def get_command(payload: dict) -> List[str]:
        params = ["--data", json.dumps(payload)]
        return params

    def sync_invoke(self, payload: dict) -> ExecutionResult:
        command = self.func_cmd + self.get_command(payload)
        error = None
        try:
            begin = datetime.datetime.now()
            response = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            end = datetime.datetime.now()
            parsed_response = response.stdout.decode("utf-8")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            end = datetime.datetime.now()
            error = e

        knative_result = ExecutionResult.from_times(begin, end)
        if error is not None:
            self.logging.error("Invocation of {} failed!".format(self.fname))
            knative_result.stats.failure = True
            return knative_result

        return_content = json.loads(parsed_response)
        knative_result.parse_benchmark_output(return_content)
        return knative_result

    def async_invoke(self, payload: dict) -> concurrent.futures.Future:
        pool = concurrent.futures.ThreadPoolExecutor()
        fut = pool.submit(self.sync_invoke, payload)
        return fut

    def serialize(self) -> dict:
        return {"type": "Library", "name": self.fname}

    @staticmethod
    def deserialize(obj: dict) -> Trigger:
        return KnativeLibraryTrigger(obj["name"])

    @staticmethod
    def typename() -> str:
        return "Knative.LibraryTrigger"


class KnativeHTTPTrigger(Trigger):
    def __init__(self, fname: str, url: str):
        super().__init__()
        self.fname = fname
        self.url = url

    @staticmethod
    def typename() -> str:
        return "Knative.HTTPTrigger"

    @staticmethod
    def trigger_type() -> Trigger.TriggerType:
        return Trigger.TriggerType.HTTP

    def sync_invoke(self, payload: dict) -> ExecutionResult:
        self.logging.debug(f"Invoke function {self.url}")
        return self._http_invoke(payload, self.url, False)

    def async_invoke(self, payload: dict) -> concurrent.futures.Future:
        pool = concurrent.futures.ThreadPoolExecutor()
        fut = pool.submit(self.sync_invoke, payload)
        return fut

    def serialize(self) -> dict:
        return {"type": "HTTP", "fname": self.fname, "url": self.url}

    @staticmethod
    def deserialize(obj: dict) -> Trigger:
        return KnativeHTTPTrigger(obj["fname"], obj["url"])
