from sebs.faas.system import System
from sebs.faas.function import Function, Trigger, ExecutionResult
from sebs.faas.storage import PersistentStorage
from sebs.benchmark import Benchmark
from sebs.config import SeBSConfig
from sebs.cache import Cache
from sebs.utils import LoggingHandlers
from sebs.faas.config import Resources
from typing import Dict, Tuple, Type, List, Optional
import docker
import uuid

from .config import KnativeConfig

class KnativeSystem(System):
    def __init__(self, system_config: SeBSConfig, cache_client: Cache, docker_client: docker.client, logger_handlers: LoggingHandlers):
        super().__init__(system_config, cache_client, docker_client)
        # Initialize any additional Knative-specific attributes here
    _config: KnativeConfig

    @property
    def config(self) -> KnativeConfig:
        # Return the configuration specific to Knative
        return self._config

    @staticmethod
    def function_type() -> Type[Function]:
        # Return the specific function type for Knative
        return Function

    def get_storage(self, replace_existing: bool = False) -> PersistentStorage:
        # Implementation of persistent storage retrieval for Knative
        # This might involve creating a persistent volume or bucket in Knative's ecosystem
        pass

    def package_code(
        self,
        directory: str,
        language_name: str,
        language_version: str,
        benchmark: str,
        is_cached: bool,
    ) -> Tuple[str, int]:
        """
        Package code for Knative platform by building a Docker image.

        Args:
        - directory: Directory where the function code resides.
        - language_name: Name of the programming language (e.g., Python).
        - language_version: Version of the programming language.
        - benchmark: Identifier for the benchmark or function.
        - is_cached: Flag indicating if the code is cached.

        Returns:
        - Tuple containing the Docker image name (tag) and its size.
        """

        # Generate a unique Docker image name/tag for this function
        docker_image_name = f"{benchmark}:{language_version}"

        # Build Docker image from the specified directory
        image, _ = self._docker_client.images.build(path=directory, tag=docker_image_name)

        # Retrieve size of the Docker image
        image_size = image.attrs['Size']

        # Return the Docker image name (tag) and its size
        return docker_image_name, image_size


    def create_function(self, code_package: Benchmark, func_name: str) -> Function:
        # Implementation for creating functions
        return function

    def cached_function(self, function: Function):
        # Implementation of retrieving cached function details for Knative
        pass

    def update_function(self, function: Function, code_package: Benchmark):
        # Implementation of function update for Knative
        # might involve updating the Knative service with a new Docker image
        pass

    def update_function_configuration(self, cached_function: Function, benchmark: Benchmark):
        # Implementation of updating function configuration for Knative
        pass

    def default_function_name(self, code_package: Benchmark) -> str:
        # Implementation of default function naming for Knative
        return f"{code_package.name}-{code_package.language_name}-{code_package.language_version}"

    def enforce_cold_start(self, functions: List[Function], code_package: Benchmark):
        # Implementation of cold start enforcement for Knative
        # I am assuiming this might involve deleting and redeploying the service to force a cold start
        pass

    def download_metrics(self, function_name: str, start_time: int, end_time: int, requests: Dict[str, ExecutionResult], metrics: dict):
        # Implementation of metric downloading for Knative
        # Here I can review the knative inbuilt metric tool (flag) need to check
        pass

    def create_trigger(self, function: Function, trigger_type: Trigger.TriggerType) -> Trigger:
        # Implementation of trigger creation for Knative
        # have to involve in setting up HTTP routes or event sources
        trigger = Trigger(name=f"{function.name}-trigger", type=trigger_type)
        return trigger

    def shutdown(self) -> None:
        # Clean up any resources or connections
        pass

    @staticmethod
    def name() -> str:
        return "Knative"
