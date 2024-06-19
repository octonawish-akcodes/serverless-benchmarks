from __future__ import annotations

from typing import cast, Optional
from dataclasses import dataclass

from sebs.benchmark import Benchmark
from sebs.faas.function import Function, FunctionConfig, Runtime
from sebs.storage.config import MinioConfig
from sebs.knative.trigger import LibraryTrigger, HTTPTrigger


@dataclass
class KnativeFunctionConfig(FunctionConfig):
    """
    Configuration class for Knative function specific configurations.

    Attributes:
        docker_image (str): Docker image for the function.
        namespace (str): Kubernetes namespace where the function is deployed (default is 'default').
        storage (Optional[MinioConfig]): Optional MinioConfig object for storage configuration.
    """

    docker_image: str = ""
    namespace: str = "default"
    storage: Optional[MinioConfig] = None

    @staticmethod
    def deserialize(data: dict) -> KnativeFunctionConfig:
        """
        Deserialize data from dictionary into KnativeFunctionConfig object.

        Args:
            data (dict): Dictionary containing serialized data.

        Returns:
            KnativeFunctionConfig: Deserialized KnativeFunctionConfig object.
        """
        keys = list(KnativeFunctionConfig.__dataclass_fields__.keys())
        data = {k: v for k, v in data.items() if k in keys}
        data["runtime"] = Runtime.deserialize(data["runtime"])
        if "storage" in data:
            data["storage"] = MinioConfig.deserialize(data["storage"])
        return KnativeFunctionConfig(**data)

    def serialize(self) -> dict:
        """
        Serialize KnativeFunctionConfig object into dictionary.

        Returns:
            dict: Dictionary containing serialized data.
        """
        return self.__dict__

    @staticmethod
    def from_benchmark(benchmark: Benchmark) -> KnativeFunctionConfig:
        """
        Create KnativeFunctionConfig object from a benchmark.

        Args:
            benchmark (Benchmark): Benchmark object.

        Returns:
            KnativeFunctionConfig: Initialized KnativeFunctionConfig object.
        """
        return super(KnativeFunctionConfig, KnativeFunctionConfig)._from_benchmark(
            benchmark, KnativeFunctionConfig
        )


class KnativeFunction(Function):
    """
    Class representing a Knative function.

    Attributes:
        name (str): Name of the function.
        benchmark (str): Benchmark associated with the function.
        code_package_hash (str): Hash of the code package associated with the function.
        cfg (KnativeFunctionConfig): Configuration object for the function.
    """

    def __init__(
        self, name: str, benchmark: str, code_package_hash: str, cfg: KnativeFunctionConfig
    ):
        """
        Initialize KnativeFunction object.

        Args:
            name (str): Name of the function.
            benchmark (str): Benchmark associated with the function.
            code_package_hash (str): Hash of the code package associated with the function.
            cfg (KnativeFunctionConfig): Configuration object for the function.
        """
        super().__init__(benchmark, name, code_package_hash, cfg)

    @property
    def config(self) -> KnativeFunctionConfig:
        """
        Get the configuration object of the function.

        Returns:
            KnativeFunctionConfig: Configuration object of the function.
        """
        return cast(KnativeFunctionConfig, self._cfg)

    @staticmethod
    def typename() -> str:
        """
        Return the typename of the KnativeFunction class.

        Returns:
            str: Typename of the KnativeFunction class.
        """
        return "Knative.Function"

    def serialize(self) -> dict:
        """
        Serialize KnativeFunction object into dictionary.

        Returns:
            dict: Dictionary containing serialized data.
        """
        serialized_data = super().serialize()
        serialized_data["config"] = self._cfg.serialize()
        return serialized_data

    @staticmethod
    def deserialize(cached_config: dict) -> KnativeFunction:
        """
        Deserialize dictionary into KnativeFunction object.

        Args:
            cached_config (dict): Dictionary containing serialized data.

        Returns:
            KnativeFunction: Deserialized KnativeFunction object.
        """
        cfg = KnativeFunctionConfig.deserialize(cached_config["config"])
        ret = KnativeFunction(
            cached_config["name"], cached_config["benchmark"], cached_config["hash"], cfg
        )
        for trigger in cached_config["triggers"]:
            trigger_type = cast(
                Trigger,
                {"Library": LibraryTrigger, "HTTP": HTTPTrigger}.get(trigger["type"]),
            )
            assert trigger_type, "Unknown trigger type {}".format(trigger["type"])
            ret.add_trigger(trigger_type.deserialize(trigger))
        return ret
