import concurrent.futures
import datetime
import json
import requests
import subprocess
import time
from typing import Dict, List, Optional  # noqa

from sebs.faas.function import ExecutionResult, Trigger


class LibraryTrigger(Trigger):
    """
    Trigger implementation for invoking a Knative service using port forwarding and curl.

    Attributes:
        function_name (str): The name of the function to invoke.
        pod_name (str): The name of the Kubernetes pod where the function is deployed.
        namespace (str): The Kubernetes namespace where the pod is deployed (default is 'default').
    """

    def __init__(self, function_name: str, pod_name: str, namespace: str = "default"):
        """
        Initialize the LibraryTrigger with the function name, pod name, and namespace.

        Args:
            function_name (str): The name of the function to invoke.
            pod_name (str): The name of the Kubernetes pod where the function is deployed.
            namespace (str, optional): The Kubernetes namespace where the pod is deployed (default is 'default').
        """
        super().__init__()
        self.function_name = function_name
        self.pod_name = pod_name
        self.namespace = namespace

    @staticmethod
    def trigger_type() -> "Trigger.TriggerType":
        """
        Return the type of trigger (LibraryTrigger).

        Returns:
            Trigger.TriggerType: The trigger type (LibraryTrigger).
        """
        return Trigger.TriggerType.LIBRARY

    @staticmethod
    def get_curl_command(payload: dict) -> List[str]:
        """
        Generate a curl command for invoking the function.

        Args:
            payload (dict): The payload data to send with the request.

        Returns:
            List[str]: The curl command as a list of strings.
        """
        return [
            "curl",
            "-X",
            "POST",
            "http://localhost:8080/handle",
            "-d",
            json.dumps(payload),
            "-H",
            "Content-Type: application/json",
        ]

    def sync_invoke(self, payload: dict) -> ExecutionResult:
        """
        Synchronously invoke the function using port forwarding and curl.

        Args:
            payload (dict): The payload data to send with the request.

        Returns:
            ExecutionResult: The result of the function invocation.
        """
        port_forward_cmd = [
            "kubectl",
            "port-forward",
            f"pod/{self.pod_name}",
            "8080:8080",
            "-n",
            self.namespace,
        ]

        # Start port forwarding
        port_forward_proc = subprocess.Popen(
            port_forward_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        time.sleep(2)  # Give some time for port forwarding to start

        command = self.get_curl_command(payload)
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

        # Stop port forwarding
        port_forward_proc.terminate()

        knative_result = ExecutionResult.from_times(begin, end)
        if error is not None:
            self.logging.error(f"Invocation of {self.function_name} failed!")
            knative_result.stats.failure = True
            return knative_result

        return_content = json.loads(parsed_response)
        knative_result.parse_benchmark_output(return_content)
        return knative_result

    def async_invoke(self, payload: dict) -> concurrent.futures.Future:
        """
        Asynchronously invoke the function using port forwarding and curl.

        Args:
            payload (dict): The payload data to send with the request.

        Returns:
            concurrent.futures.Future: A future representing the asynchronous invocation.
        """
        pool = concurrent.futures.ThreadPoolExecutor()
        fut = pool.submit(self.sync_invoke, payload)
        return fut

    def serialize(self) -> dict:
        """
        Serialize the trigger configuration.

        Returns:
            dict: A dictionary representing the serialized trigger configuration.
        """
        return {
            "type": "Library",
            "name": self.function_name,
            "pod_name": self.pod_name,
            "namespace": self.namespace,
        }

    @staticmethod
    def deserialize(obj: dict) -> Trigger:
        """
        Deserialize a dictionary into a LibraryTrigger object.

        Args:
            obj (dict): The dictionary containing the serialized trigger configuration.

        Returns:
            Trigger: A LibraryTrigger object instantiated from the serialized data.
        """
        return LibraryTrigger(obj["name"], obj["pod_name"], obj["namespace"])

    @staticmethod
    def typename() -> str:
        """
        Return the typename of the trigger (Knative.LibraryTrigger).

        Returns:
            str: The typename of the trigger.
        """
        return "Knative.LibraryTrigger"


class HTTPTrigger(Trigger):
    """
    Trigger implementation for invoking a Knative service via HTTP.

    Attributes:
        function_name (str): The name of the function to invoke.
        url (str): The URL of the Knative service endpoint.
    """

    def __init__(self, function_name: str, url: str):
        """
        Initialize the HTTPTrigger with the function name and service URL.

        Args:
            function_name (str): The name of the function to invoke.
            url (str): The URL of the Knative service endpoint.
        """
        super().__init__()
        self.function_name = function_name
        self.url = url

    @staticmethod
    def typename() -> str:
        """
        Return the typename of the trigger (Knative.HTTPTrigger).

        Returns:
            str: The typename of the trigger.
        """
        return "Knative.HTTPTrigger"

    @staticmethod
    def trigger_type() -> Trigger.TriggerType:
        """
        Return the type of trigger (HTTPTrigger).

        Returns:
            Trigger.TriggerType: The trigger type (HTTPTrigger).
        """
        return Trigger.TriggerType.HTTP

    def sync_invoke(self, payload: dict) -> ExecutionResult:
        """
        Synchronously invoke the function via HTTP POST request.

        Args:
            payload (dict): The payload data to send with the request.

        Returns:
            ExecutionResult: The result of the function invocation.
        """
        self.logging.debug(f"Invoke function {self.url}")
        return self._http_invoke(payload, self.url, False)

    def async_invoke(self, payload: dict) -> concurrent.futures.Future:
        """
        Asynchronously invoke the function via HTTP POST request.

        Args:
            payload (dict): The payload data to send with the request.

        Returns:
            concurrent.futures.Future: A future representing the asynchronous invocation.
        """
        pool = concurrent.futures.ThreadPoolExecutor()
        fut = pool.submit(self.sync_invoke, payload)
        return fut

    def _http_invoke(self, payload: dict, url: str, async_invoke: bool) -> ExecutionResult:
        """
        Helper method for invoking the function via HTTP POST request.

        Args:
            payload (dict): The payload data to send with the request.
            url (str): The URL of the Knative service endpoint.
            async_invoke (bool): Whether the invocation is asynchronous (not used in this method).

        Returns:
            ExecutionResult: The result of the function invocation.
        """
        headers = {'Content-Type': 'application/json'}
        error = None
        try:
            begin = datetime.datetime.now()
            response = requests.post(url, json=payload, headers=headers)
            end = datetime.datetime.now()
            response.raise_for_status()
            parsed_response = response.json()
        except (requests.RequestException, ValueError) as e:
            end = datetime.datetime.now()
            error = e

        knative_result = ExecutionResult.from_times(begin, end)
        if error is not None:
            self.logging.error(f"HTTP invocation of {self.function_name} failed!")
            knative_result.stats.failure = True
            return knative_result

        knative_result.parse_benchmark_output(parsed_response)
        return knative_result

    def serialize(self) -> dict:
        """
        Serialize the trigger configuration.

        Returns:
            dict: A dictionary representing the serialized trigger configuration.
        """
        return {"type": "HTTP", "fname": self.function_name, "url": self.url}

    @staticmethod
    def deserialize(obj: dict) -> Trigger:
        """
        Deserialize a dictionary into an HTTPTrigger object.

        Args:
            obj (dict): The dictionary containing the serialized trigger configuration.

        Returns:
            Trigger: An HTTPTrigger object instantiated from the serialized data.
        """
        return HTTPTrigger(obj["fname"], obj["url"])
